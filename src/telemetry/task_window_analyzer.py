import json
import os
import re
from datetime import datetime
from telemetry.token_estimator import CharBasedTokenEstimator, AutoEstimator

class TaskWindowAnalyzer:
    def __init__(self, brain_dir=r"C:\Users\ajeem\.gemini\antigravity-ide\brain", token_estimator=None):
        self.brain_dir = brain_dir
        self.token_estimator = token_estimator or CharBasedTokenEstimator()

    def normalize_path(self, path_str):
        if not path_str:
            return None
        path = path_str.replace("\\", "/").strip('"').strip("'")
        if path.startswith("file:///"):
            path = path[8:]
        elif path.startswith("file://"):
            path = path[7:]
        try:
            path = os.path.abspath(path).replace("\\", "/")
        except:
            pass
        return path

    def categorize_path(self, path_str):
        p_norm = path_str.replace("\\", "/").strip('"').strip("'")
        workspace_root = "c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system"
        if p_norm.lower().startswith(workspace_root.lower()):
            return "repo"
        gemini_root = "c:/users/ajeem/.gemini"
        if p_norm.lower().startswith(gemini_root.lower()):
            return "gemini"
        testing_root = "c:/users/ajeem/downloads/downloads/testing/testing1"
        if p_norm.lower().startswith(testing_root.lower()):
            return "external"
        return "external"

    def parse_iso_timestamp(self, ts_str):
        if not ts_str:
            return None
        ts_clean = ts_str.replace("Z", "")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                pass
        return None

    def extract_code_from_view_file_content(self, content):
        lines = content.split('\n')
        code_lines = []
        in_code_block = False
        for line in lines:
            match = re.match(r'^\s*(\d+):\s(.*?)$', line)
            if match:
                code_lines.append(match.group(2))
                in_code_block = True
            elif in_code_block and line == "":
                code_lines.append("")
        if code_lines:
            return "\n".join(code_lines)
        return content

    def extract_viewed_lines_and_code(self, content):
        lines = content.split('\n')
        viewed_lines = {}
        for line in lines:
            match = re.match(r'^\s*(\d+):(?:\s(.*))?$', line)
            if match:
                line_num = int(match.group(1))
                code_text = match.group(2) if match.group(2) is not None else ""
                viewed_lines[line_num] = code_text
        return viewed_lines

    def find_mcp_query_step_indices(self, steps):
        """
        Locates the indices of steps that called mcp_query_context.
        """
        query_indices = []
        for idx, step in enumerate(steps):
            if step.get("type") == "PLANNER_RESPONSE" and step.get("source") == "MODEL":
                tool_calls = step.get("tool_calls", [])
                for tc in tool_calls:
                    name = tc.get("name")
                    args = tc.get("args", {})
                    # Either call_mcp_tool with ToolName="mcp_query_context"
                    # or eager loaded tools containing query_context
                    is_mcp_query = (name == "call_mcp_tool" and "mcp_query_context" in str(args.get("ToolName", ""))) or \
                                   ("query_context" in name)
                    if is_mcp_query:
                        query_indices.append(idx)
                        break
        return query_indices

    def load_graph(self, repo_path):
        cache_path = os.path.join(repo_path, ".semantic_cache", "graph.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading graph from cache {cache_path}: {e}")
        return None

    def get_repo_relative_path(self, abs_path, repo_root):
        if not abs_path or not repo_root:
            return None
        norm_abs = abs_path.replace("\\", "/").lower()
        norm_repo = repo_root.replace("\\", "/").lower()
        if norm_abs.startswith(norm_repo):
            rel = abs_path[len(repo_root):].strip("/")
            return rel.replace("\\", "/")
        return None

    def resolve_relevant_files(self, repo_path, mcp_selected_files, unique_modified_files):
        mcp_set = {f.replace("\\", "/").strip("/") for f in mcp_selected_files}
        modified_set = {self.get_repo_relative_path(f, repo_path) or f for f in unique_modified_files}
        modified_set = {f.replace("\\", "/").strip("/") for f in modified_set if f}
        
        relevant_files = set(mcp_set).union(modified_set)
        
        graph = self.load_graph(repo_path)
        if not graph:
            return relevant_files

        # Undirected call graph building
        adj = {}
        def add_edge(n1, n2):
            k1 = str(n1)
            k2 = str(n2)
            if k1 not in adj: adj[k1] = (n1, [])
            if k2 not in adj: adj[k2] = (n2, [])
            adj[k1][1].append(n2)
            adj[k2][1].append(n1)

        for edge in graph.get("execution_edges", []):
            add_edge(edge["from"], edge["to"])

        # Identify starting nodes that belong to MCP selected files
        start_nodes = []
        distinct_nodes = []
        visited_keys = set()
        for edge in graph.get("execution_edges", []):
            for key in ("from", "to"):
                node = edge[key]
                node_key = str(node)
                if node_key not in visited_keys:
                    visited_keys.add(node_key)
                    distinct_nodes.append(node)

        for node in distinct_nodes:
            node_file = node.get("file")
            if node_file:
                clean_f = node_file.replace("\\", "/").strip("/")
                if clean_f in mcp_set:
                    start_nodes.append(node)

        # BFS
        from collections import deque
        queue = deque(start_nodes)
        visited = {str(n) for n in start_nodes}
        connected_nodes = list(start_nodes)

        while queue:
            curr = queue.popleft()
            curr_key = str(curr)
            if curr_key in adj:
                for neighbor in adj[curr_key][1]:
                    n_key = str(neighbor)
                    if n_key not in visited:
                        visited.add(n_key)
                        queue.append(neighbor)
                        connected_nodes.append(neighbor)

        # Collect files containing connected nodes
        for node in connected_nodes:
            node_file = node.get("file")
            if node_file:
                relevant_files.add(node_file.replace("\\", "/").strip("/"))

        return relevant_files

    def resolve_core_route_files(self, repo_path, target_route):
        if not target_route or not target_route.startswith("ROUTE:"):
            return set()
            
        parts = target_route.split(":")
        if len(parts) < 3:
            return set()
        method = parts[1].strip().lower()
        route_path = parts[2].strip()
        
        graph = self.load_graph(repo_path)
        if not graph:
            return set()
            
        edges = graph.get("execution_edges", [])
        imports = graph.get("imports", {})
        
        start_files = set()
        for e in edges:
            for node in (e.get('from', {}), e.get('to', {})):
                if node.get('type') == 'ROUTE' and node.get('route') == route_path:
                    n_method = node.get('method', '').lower()
                    if n_method == method:
                        n_file = node.get('file')
                        if n_file:
                            start_files.add(n_file.replace("\\", "/").strip("/"))
                            
        if not start_files:
            for e in edges:
                for node in (e.get('from', {}), e.get('to', {})):
                    if node.get('type') == 'ROUTE':
                        n_route = node.get('route', '')
                        n_method = node.get('method', '').lower()
                        if n_method == method and (route_path.endswith(n_route) or n_route.endswith(route_path)):
                            n_file = node.get('file')
                            if n_file:
                                start_files.add(n_file.replace("\\", "/").strip("/"))
                                
        queue = list(start_files)
        visited = set(start_files)
        
        file_adj = {}
        for e in edges:
            f_file = e.get('from', {}).get('file')
            t_file = e.get('to', {}).get('file')
            if f_file and t_file:
                f_file_norm = f_file.replace("\\", "/").strip("/")
                t_file_norm = t_file.replace("\\", "/").strip("/")
                if f_file_norm not in file_adj:
                    file_adj[f_file_norm] = set()
                file_adj[f_file_norm].add(t_file_norm)
                
        def resolve_import_path(file_path, import_source):
            if not import_source.startswith("."):
                return None
            dir_name = os.path.dirname(file_path)
            combined = os.path.normpath(os.path.join(dir_name, import_source)).replace("\\", "/")
            return combined
            
        while queue:
            curr = queue.pop(0)
            if curr in file_adj:
                for nxt in file_adj[curr]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            if curr in imports:
                for imp in imports[curr]:
                    src = imp.get('source', '')
                    resolved = resolve_import_path(curr, src)
                    if resolved:
                        variants = [resolved, resolved + ".js", resolved + ".ts", resolved + ".jsx", resolved + ".tsx"]
                        for var in variants:
                            if var not in visited:
                                visited.add(var)
                                queue.append(var)
                                
        return visited

    def classify_file(self, path, clean_rel, core_route_files, unique_modified, is_v4_relevant):
        if not clean_rel:
            return "UNKNOWN"
            
        clean_rel_lower = clean_rel.lower()
        is_modified = (path in unique_modified)
        
        if not is_modified:
            if "tests/" in clean_rel_lower or "test-" in clean_rel_lower or clean_rel_lower.endswith("_test.py") or clean_rel_lower.endswith("_test.js") or "test_flow" in clean_rel_lower:
                return "TEST"
            if "benchmark" in clean_rel_lower:
                return "BENCHMARK"
            if "telemetry" in clean_rel_lower or "report" in clean_rel_lower or clean_rel_lower.endswith(".md") or "audit" in clean_rel_lower:
                return "TELEMETRY"
            if clean_rel_lower.endswith(".env") or clean_rel_lower in ["package.json", "package-lock.json"]:
                return "CONFIG"
                
        if clean_rel in ["src/app.js", "src/server.js", "src/config/db.js", "mock-mongoose.js"]:
            return "INFRASTRUCTURE"
            
        if is_v4_relevant:
            # Check if in core route (resolved via BFS)
            is_in_core_route = False
            if core_route_files:
                is_in_core_route = any(c.lower() == clean_rel_lower for c in core_route_files)
                
            if is_in_core_route:
                if (
                    "src/routes/" in clean_rel_lower or
                    "src/controllers/" in clean_rel_lower or
                    "src/services/auth.service.js" in clean_rel_lower or
                    "src/models/user.model.js" in clean_rel_lower or
                    "src/middlewares/validation.middleware.js" in clean_rel_lower
                ):
                    return "CORE_ROUTE"
            return "DEPENDENCY"
            
        # If not v4 relevant
        if "tests/" in clean_rel_lower or "test-" in clean_rel_lower or clean_rel_lower.endswith("_test.py") or clean_rel_lower.endswith("_test.js") or "test_flow" in clean_rel_lower:
            return "TEST"
        if "benchmark" in clean_rel_lower:
            return "BENCHMARK"
        if "telemetry" in clean_rel_lower or "report" in clean_rel_lower or clean_rel_lower.endswith(".md") or "audit" in clean_rel_lower:
            return "TELEMETRY"
        if clean_rel_lower.endswith(".env") or clean_rel_lower in ["package.json", "package-lock.json"]:
            return "CONFIG"
            
        return "UNKNOWN"

    def run_window_analysis(self, session_ids, provider="gemini", vibecoding_path=r"snapshots/vibecoding_metrics.json", output_metrics_path=None):
        if output_metrics_path is None:
            output_metrics_path = r"snapshots/task_window_metrics_v9.json"

        if not os.path.exists(vibecoding_path):
            raise FileNotFoundError(f"Vibecoding telemetry not found at {vibecoding_path}")
            
        with open(vibecoding_path, 'r', encoding='utf-8') as f:
            mcp_queries = json.load(f)

        # Sort queries by query_id
        mcp_queries.sort(key=lambda x: x.get("query_id", 0))

        estimator = AutoEstimator(provider)

        # Collect all MCP query steps from transcripts of all sessions
        all_mcp_steps = []
        for s_id in session_ids:
            log_path = os.path.join(self.brain_dir, s_id, ".system_generated", "logs", "transcript.jsonl")
            if not os.path.exists(log_path):
                print(f"Warning: Transcript not found for session {s_id}")
                continue

            steps = []
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        steps.append(json.loads(line))
                    except:
                        continue
            
            for idx, step in enumerate(steps):
                if step.get("type") == "PLANNER_RESPONSE" and step.get("source") == "MODEL":
                    tool_calls = step.get("tool_calls", [])
                    for tc in tool_calls:
                        name = tc.get("name")
                        args = tc.get("args", {})
                        is_mcp_query = (name == "call_mcp_tool" and "mcp_query_context" in str(args.get("ToolName", ""))) or \
                                       ("query_context" in name)
                        if is_mcp_query:
                            raw_args = args.get("Arguments", "{}")
                            target_arg = None
                            policy_arg = None
                            if isinstance(raw_args, str):
                                try:
                                    parsed = json.loads(raw_args)
                                    target_arg = parsed.get("target") or parsed.get("Target")
                                    policy_arg = parsed.get("policy") or parsed.get("Policy")
                                except:
                                    pass
                            elif isinstance(raw_args, dict):
                                target_arg = raw_args.get("target") or raw_args.get("Target")
                                policy_arg = raw_args.get("policy") or raw_args.get("Policy")

                            all_mcp_steps.append({
                                "session_id": s_id,
                                "step_idx": idx,
                                "step_index_field": step.get("step_index"),
                                "timestamp": step.get("created_at"),
                                "target": target_arg,
                                "policy": policy_arg,
                                "created_at": step.get("created_at")
                            })
                            break

        # Sort all collected MCP query steps chronologically by timestamp
        all_mcp_steps.sort(key=lambda x: self.parse_iso_timestamp(x["created_at"]) or datetime.min)

        # Map steps to query records sequentially
        step_to_query = {}
        for i, step_obj in enumerate(all_mcp_steps):
            if i < len(mcp_queries):
                step_to_query[(step_obj["session_id"], step_obj["step_idx"])] = mcp_queries[i]

        results = {}

        for s_id in session_ids:
            log_path = os.path.join(self.brain_dir, s_id, ".system_generated", "logs", "transcript.jsonl")
            if not os.path.exists(log_path):
                continue

            steps = []
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        steps.append(json.loads(line))
                    except:
                        continue

            if not steps:
                continue

            # Find step indices where MCP query was proposed in this session
            session_query_steps = [s for s in all_mcp_steps if s["session_id"] == s_id]
            session_query_steps.sort(key=lambda x: x["step_idx"])

            windows = []
            num_queries = len(session_query_steps)

            # Determine fallback repo path for trailing window
            fallback_repo_path = None
            for step_obj in session_query_steps:
                q_rec = step_to_query.get((s_id, step_obj["step_idx"]))
                if q_rec and q_rec.get("repository_path"):
                    fallback_repo_path = q_rec.get("repository_path")
                    break

            for idx in range(num_queries + 1):
                # 1. Determine step index boundaries
                if idx == 0:
                    step_start_idx = 0
                    step_end_idx = session_query_steps[0]["step_idx"] if num_queries > 0 else len(steps) - 1
                elif idx < num_queries:
                    step_start_idx = session_query_steps[idx-1]["step_idx"] + 1
                    step_end_idx = session_query_steps[idx]["step_idx"]
                else:
                    step_start_idx = session_query_steps[-1]["step_idx"] + 1
                    step_end_idx = len(steps) - 1

                # If the step start index is out of bounds, make it a zero-length boundary
                if step_start_idx >= len(steps):
                    step_start_idx = len(steps) - 1

                if step_start_idx > step_end_idx:
                    # Empty range
                    w_steps = []
                    w_start_ts = steps[step_start_idx].get("created_at") if step_start_idx < len(steps) else steps[-1].get("created_at")
                    w_end_ts = w_start_ts
                else:
                    w_steps = [(i, steps[i]) for i in range(step_start_idx, step_end_idx + 1)]
                    w_start_ts = steps[step_start_idx].get("created_at")
                    w_end_ts = steps[step_end_idx].get("created_at")

                # Calculate duration
                dt_start = self.parse_iso_timestamp(w_start_ts)
                dt_end = self.parse_iso_timestamp(w_end_ts)
                duration = (dt_end - dt_start).total_seconds() if (dt_start and dt_end) else 0.0

                validation_status = "PASS"
                validation_flags = []

                if duration < 0:
                    validation_status = "FAIL"
                    validation_flags.append("negative_duration")
                elif duration == 0:
                    validation_flags.append("zero_length")

                task_name = f"Task {idx + 1}"
                is_trailing = (idx == num_queries)

                query_id = None
                target = "Trailing Session Verification"
                policy = "CLEANUP"
                mcp_tokens = 0
                mcp_files = 0
                repo_path = fallback_repo_path or "C:/Users/ajeem/Downloads/downloads/testing/testing1"
                selected_files = []

                if not is_trailing:
                    step_obj = session_query_steps[idx]
                    q_record = step_to_query.get((s_id, step_obj["step_idx"]))
                    if q_record:
                        query_id = q_record.get("query_id")
                        target = q_record.get("target") or step_obj.get("target") or "Unknown"
                        policy = q_record.get("policy") or step_obj.get("policy") or "Unknown"
                        mcp_tokens = q_record.get("context_token_estimate", 0)
                        mcp_files = len(q_record.get("selected_files", []))
                        repo_path = q_record.get("repository_path", repo_path)
                        selected_files = q_record.get("selected_files", [])
                    else:
                        # Fallback if query record is missing
                        query_id = idx + 1
                        target = step_obj.get("target") or "Unknown"
                        policy = step_obj.get("policy") or "Unknown"
                        mcp_tokens = 0
                        mcp_files = 0

                windows.append({
                    "task_index": idx + 1,
                    "query_id": query_id,
                    "target": target,
                    "policy": policy,
                    "window_start": w_start_ts,
                    "window_end": w_end_ts,
                    "duration_seconds": duration,
                    "step_start_idx": step_start_idx,
                    "step_end_idx": step_end_idx,
                    "w_steps": w_steps,
                    "validation_status": validation_status,
                    "validation_flags": validation_flags,
                    "mcp_tokens": mcp_tokens,
                    "mcp_files": mcp_files,
                    "repo_path": repo_path,
                    "selected_files": selected_files
                })

            # Check for duplicate window bounds across the session
            for idx1 in range(len(windows)):
                for idx2 in range(idx1 + 1, len(windows)):
                    w1 = windows[idx1]
                    w2 = windows[idx2]
                    if w1["window_start"] == w2["window_start"] and w1["window_end"] == w2["window_end"]:
                        w1["validation_status"] = "FAIL"
                        w2["validation_status"] = "FAIL"
                        w1["validation_flags"].append("duplicate_bounds")
                        w2["validation_flags"].append("duplicate_bounds")

            # Extract window telemetry
            window_metrics = []
            for w in windows:
                files_opened_chronological = []
                files_modified_chronological = []
                read_count = 0
                write_count = 0
                log_fallback_contents = {}
                cumulative_characters_returned = 0

                # V7 tracking
                file_viewed_lines = {}  # norm_path -> set of line numbers (1-indexed ints)
                file_line_code = {}     # norm_path -> dict(line_num -> code_text)
                cumulative_view_tokens = 0

                # V8 tracking
                file_read_tokens = 0
                search_tokens = 0
                mcp_tokens_loaded = 0
                command_output_tokens = 0

                # V9 tracking
                user_tokens = 0
                planner_tokens = 0
                file_view_tokens = 0
                search_tokens_v9 = 0
                mcp_tokens_v9 = 0
                command_tokens = 0
                diagnostic_tokens = 0
                tool_output_tokens = 0

                for s_idx, step in w["w_steps"]:
                    stype = step.get("type")
                    source = step.get("source")
                    content = step.get("content") or ""
                    if not isinstance(content, str):
                        try:
                            content = json.dumps(content)
                        except:
                            content = str(content)

                    # Compute actual tokens for the step content
                    step_tokens = estimator.estimate_tokens(content)

                    # Classify context tokens loaded into the model
                    is_injected_response = False
                    if source == "MODEL" and stype in ["VIEW_FILE", "GREP_SEARCH", "RUN_COMMAND", "MCP_TOOL", "LIST_DIRECTORY", "CODE_ACTION", "GENERIC"]:
                        is_injected_response = True
                    elif source == "SYSTEM" and stype in ["ERROR_MESSAGE", "SYSTEM_MESSAGE"]:
                        is_injected_response = True

                    if is_injected_response:
                        if stype == "VIEW_FILE":
                            file_read_tokens += step_tokens
                        elif stype in ["GREP_SEARCH", "SEARCH", "SEMANTIC_SEARCH"]:
                            search_tokens += step_tokens
                        elif stype == "MCP_TOOL":
                            mcp_tokens_loaded += step_tokens
                        else:
                            command_output_tokens += step_tokens

                    # Determine token category for V9
                    if stype == "USER_INPUT":
                        user_tokens += step_tokens
                    elif stype == "PLANNER_RESPONSE":
                        planner_tokens += step_tokens
                    elif stype == "VIEW_FILE":
                        file_view_tokens += step_tokens
                    elif stype in ["GREP_SEARCH", "SEARCH", "SEMANTIC_SEARCH"]:
                        search_tokens_v9 += step_tokens
                    elif stype == "MCP_TOOL":
                        mcp_tokens_v9 += step_tokens
                    elif stype in ["RUN_COMMAND", "GENERIC"]:
                        command_tokens += step_tokens
                    elif stype in ["ERROR_MESSAGE", "SYSTEM_MESSAGE"] or source == "SYSTEM":
                        diagnostic_tokens += step_tokens
                    else:
                        tool_output_tokens += step_tokens

                    if stype == "PLANNER_RESPONSE" and source == "MODEL":
                        tool_calls = step.get("tool_calls", [])
                        for tc in tool_calls:
                            name = tc.get("name")
                            args = tc.get("args", {})

                            if name == "view_file":
                                read_count += 1
                                raw_path = args.get("AbsolutePath")
                                norm_path = self.normalize_path(raw_path)
                                if norm_path:
                                    files_opened_chronological.append(norm_path)
                                    
                                    file_viewed_lines.setdefault(norm_path, set())
                                    file_line_code.setdefault(norm_path, {})
                                    
                                    start_ln = args.get("StartLine")
                                    end_ln = args.get("EndLine")
                                    try:
                                        if start_ln is not None:
                                            start_ln = int(start_ln)
                                        if end_ln is not None:
                                            end_ln = int(end_ln)
                                    except (ValueError, TypeError):
                                        start_ln = None
                                        end_ln = None
                                    
                                    # Scan ahead for the VIEW_FILE result step
                                    event_chars = 0
                                    found_view_file = False
                                    viewed_lines_parsed = {}
                                    for next_step in steps[s_idx+1:s_idx+10]:
                                        if next_step.get("type") == "VIEW_FILE" and next_step.get("source") == "MODEL":
                                            content = next_step.get("content", "")
                                            viewed_lines_parsed = self.extract_viewed_lines_and_code(content)
                                            code = self.extract_code_from_view_file_content(content)
                                            log_fallback_contents[norm_path] = code
                                            event_chars = len(code)
                                            found_view_file = True
                                            break
                                    
                                    if found_view_file:
                                        for ln, text in viewed_lines_parsed.items():
                                            file_viewed_lines[norm_path].add(ln)
                                            file_line_code[norm_path][ln] = text
                                        tool_view_tokens = estimator.estimate_tokens(log_fallback_contents[norm_path])
                                        cumulative_view_tokens += tool_view_tokens
                                    else:
                                        tool_view_content = ""
                                        if os.path.exists(norm_path):
                                            try:
                                                with open(norm_path, 'r', encoding='utf-8', errors='ignore') as f:
                                                    disk_content = f.read()
                                                    file_lines = disk_content.splitlines()
                                                    num_lines = len(file_lines)
                                                    sl = start_ln if start_ln is not None else 1
                                                    el = end_ln if end_ln is not None else num_lines
                                                    
                                                    viewed_lines_code = []
                                                    for ln in range(sl, el + 1):
                                                        if 1 <= ln <= num_lines:
                                                            file_viewed_lines[norm_path].add(ln)
                                                            viewed_lines_code.append(file_lines[ln - 1])
                                                    tool_view_content = "\n".join(viewed_lines_code)
                                                    event_chars = len(tool_view_content)
                                            except:
                                                pass
                                        else:
                                            if start_ln is not None and end_ln is not None:
                                                for ln in range(start_ln, end_ln + 1):
                                                    file_viewed_lines[norm_path].add(ln)
                                        
                                        tool_view_tokens = estimator.estimate_tokens(tool_view_content)
                                        cumulative_view_tokens += tool_view_tokens
                                            
                                    cumulative_characters_returned += event_chars
                                    
                            elif name in ["grep_search", "list_dir"]:
                                read_count += 1
                            elif name in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
                                write_count += 1
                                raw_path = args.get("TargetFile")
                                norm_path = self.normalize_path(raw_path)
                                if norm_path:
                                    files_modified_chronological.append(norm_path)

                unique_opened = sorted(list(set(files_opened_chronological)))
                unique_modified = sorted(list(set(files_modified_chronological)))
                unique_touched = sorted(list(set(unique_opened + unique_modified)))

                # Resolve relevance set using the call graph resolver
                relevant_files = self.resolve_relevant_files(w["repo_path"], w["selected_files"], unique_modified)
                
                # V5 directed core route files resolution
                core_route_files = self.resolve_core_route_files(w["repo_path"], w["target"])

                total_chars_read = 0
                repo_tokens = 0
                repo_tokens_actual = 0
                external_tokens = 0
                external_tokens_actual = 0
                gemini_tokens = 0
                gemini_tokens_actual = 0

                # V7 tracking
                viewed_repo_tokens_actual = 0
                viewed_external_tokens_actual = 0
                viewed_gemini_tokens_actual = 0

                agent_all_tokens = 0
                agent_all_tokens_actual = 0
                agent_relevant_tokens = 0
                agent_relevant_tokens_actual = 0
                agent_irrelevant_tokens = 0
                agent_irrelevant_tokens_actual = 0
                relevant_files_opened = []
                irrelevant_files_opened = []

                # V7 variables (viewed range)
                viewed_agent_all_tokens_actual = 0
                viewed_agent_relevant_tokens_actual = 0
                viewed_agent_irrelevant_tokens_actual = 0

                # V5 Metrics initialization
                core_route_tokens = 0
                core_route_tokens_actual = 0
                dependency_tokens = 0
                dependency_tokens_actual = 0
                infrastructure_tokens = 0
                infrastructure_tokens_actual = 0
                noise_tokens = 0
                noise_tokens_actual = 0

                # V7 Classification (viewed range)
                viewed_core_route_tokens_actual = 0
                viewed_dependency_tokens_actual = 0
                viewed_infrastructure_tokens_actual = 0
                viewed_noise_tokens_actual = 0
                
                core_route_files_list = []
                dependency_files_list = []
                infrastructure_files_list = []
                noise_files_list = []

                files_metadata = {}

                for path in unique_opened:
                    char_count = 0
                    read_success = False
                    file_content = ""
                    if os.path.exists(path):
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                                char_count = len(file_content)
                                read_success = True
                        except:
                            pass
                    if not read_success:
                        file_content = log_fallback_contents.get(path, "")
                        char_count = len(file_content)

                    total_chars_read += char_count
                    tokens = self.token_estimator.estimate_tokens(" " * char_count)
                    actual_tokens_file = estimator.estimate_tokens(file_content)

                    # Compute V7 viewed lines content
                    viewed_lines_code = []
                    file_lines = file_content.splitlines()
                    for ln in sorted(list(file_viewed_lines.get(path, set()))):
                        if 1 <= ln <= len(file_lines):
                            viewed_lines_code.append(file_lines[ln - 1])
                        else:
                            fallback_line = file_line_code.get(path, {}).get(ln)
                            if fallback_line is not None:
                                viewed_lines_code.append(fallback_line)
                    viewed_content = "\n".join(viewed_lines_code)
                    viewed_char_count = len(viewed_content)
                    actual_tokens_viewed = estimator.estimate_tokens(viewed_content)

                    files_metadata[path] = {
                        "character_count": char_count,
                        "token_estimate": tokens,
                        "actual_tokens": actual_tokens_file,
                        "viewed_lines": sorted(list(file_viewed_lines.get(path, set()))),
                        "viewed_character_count": viewed_char_count,
                        "viewed_tokens": actual_tokens_viewed
                    }

                    category = self.categorize_path(path)
                    if category == "repo":
                        repo_tokens += tokens
                        repo_tokens_actual += actual_tokens_file
                        viewed_repo_tokens_actual += actual_tokens_viewed
                    elif category == "external":
                        external_tokens += tokens
                        external_tokens_actual += actual_tokens_file
                        viewed_external_tokens_actual += actual_tokens_viewed
                    elif category == "gemini":
                        gemini_tokens += tokens
                        gemini_tokens_actual += actual_tokens_file
                        viewed_gemini_tokens_actual += actual_tokens_viewed

                    # Relevance categorisation
                    if category != "gemini":
                        rel_path = self.get_repo_relative_path(path, w["repo_path"])
                        is_relevant = False
                        clean_rel = ""
                        if rel_path:
                            clean_rel = rel_path.replace("\\", "/").strip("/")
                            if clean_rel in relevant_files:
                                is_relevant = True
                        if path in unique_modified:
                            is_relevant = True

                        agent_all_tokens += tokens
                        agent_all_tokens_actual += actual_tokens_file
                        viewed_agent_all_tokens_actual += actual_tokens_viewed
                        if is_relevant:
                            agent_relevant_tokens += tokens
                            agent_relevant_tokens_actual += actual_tokens_file
                            viewed_agent_relevant_tokens_actual += actual_tokens_viewed
                            relevant_files_opened.append(path)
                        else:
                            agent_irrelevant_tokens += tokens
                            agent_irrelevant_tokens_actual += actual_tokens_file
                            viewed_agent_irrelevant_tokens_actual += actual_tokens_viewed
                            irrelevant_files_opened.append(path)
                            
                        # V5 Classification
                        v5_cat = self.classify_file(path, clean_rel, core_route_files, unique_modified, is_relevant)
                        if v5_cat == "CORE_ROUTE":
                            core_route_tokens += tokens
                            core_route_tokens_actual += actual_tokens_file
                            core_route_files_list.append(path)
                            viewed_core_route_tokens_actual += actual_tokens_viewed
                        elif v5_cat == "DEPENDENCY":
                            dependency_tokens += tokens
                            dependency_tokens_actual += actual_tokens_file
                            dependency_files_list.append(path)
                            viewed_dependency_tokens_actual += actual_tokens_viewed
                        elif v5_cat == "INFRASTRUCTURE":
                            infrastructure_tokens += tokens
                            infrastructure_tokens_actual += actual_tokens_file
                            infrastructure_files_list.append(path)
                            viewed_infrastructure_tokens_actual += actual_tokens_viewed
                        else:
                            # TEST, BENCHMARK, TELEMETRY, CONFIG, UNKNOWN
                            noise_tokens += tokens
                            noise_tokens_actual += actual_tokens_file
                            noise_files_list.append(path)
                            viewed_noise_tokens_actual += actual_tokens_viewed

                unique_file_tokens = repo_tokens + external_tokens + gemini_tokens
                unique_file_viewed_tokens = viewed_repo_tokens_actual + viewed_external_tokens_actual + viewed_gemini_tokens_actual
                cumulative_read_tokens = cumulative_characters_returned // 4
                
                # Use unique_file_tokens as the baseline representation of files touched
                total_token_estimate = unique_file_tokens
                agent_code_tokens = repo_tokens + external_tokens
                agent_code_files = len([p for p in unique_opened if self.categorize_path(p) != "gemini"])
                agent_relevant_files_count = len([p for p in relevant_files_opened if self.categorize_path(p) != "gemini"])

                # Token/File reductions (0 if agent baseline is 0)
                token_reduction = (1.0 - (w["mcp_tokens"] / agent_code_tokens)) * 100 if agent_code_tokens else 0.0
                file_reduction = (1.0 - (w["mcp_files"] / agent_code_files)) * 100 if agent_code_files else 0.0

                v4_token_reduction = (1.0 - (w["mcp_tokens"] / agent_relevant_tokens)) * 100 if agent_relevant_tokens else 0.0
                file_reduction_v4 = (1.0 - (w["mcp_files"] / agent_relevant_files_count)) * 100 if agent_relevant_files_count else 0.0
                relevance_ratio = agent_relevant_tokens / agent_all_tokens if agent_all_tokens else 0.0

                # V5 Reductions
                mcp_vs_core_reduction = (1.0 - (w["mcp_tokens"] / core_route_tokens)) * 100 if core_route_tokens else 0.0
                mcp_vs_core_dep_reduction = (1.0 - (w["mcp_tokens"] / (core_route_tokens + dependency_tokens))) * 100 if (core_route_tokens + dependency_tokens) else 0.0
                mcp_vs_all_rel_reduction = (1.0 - (w["mcp_tokens"] / (core_route_tokens + dependency_tokens + infrastructure_tokens))) * 100 if (core_route_tokens + dependency_tokens + infrastructure_tokens) else 0.0

                # V6 actual tokens calculation for MCP Context
                mcp_tokens_actual = 0
                for sel_f in w["selected_files"]:
                    sel_path = self.normalize_path(os.path.join(w["repo_path"], sel_f))
                    if sel_path and os.path.exists(sel_path):
                        try:
                            with open(sel_path, 'r', encoding='utf-8', errors='ignore') as f:
                                mcp_tokens_actual += estimator.estimate_tokens(f.read())
                        except:
                            pass
                    else:
                        if estimator.estimator_type == "gemini":
                            mcp_tokens_actual += int(w["mcp_tokens"] * 4.0 / 3.75)
                        elif estimator.estimator_type == "groq_llama":
                            mcp_tokens_actual += int(w["mcp_tokens"] * 4.0 / 3.25)
                        else:
                            mcp_tokens_actual += w["mcp_tokens"]

                # Structured V7 baseline outputs
                agent_baseline = {
                    "estimated_tokens": agent_code_tokens,
                    "actual_tokens": repo_tokens_actual + external_tokens_actual,
                    "file_tokens": repo_tokens_actual + external_tokens_actual,
                    "viewed_tokens": viewed_repo_tokens_actual + viewed_external_tokens_actual,
                    "estimator_type": estimator.estimator_type
                }
                relevant_baseline = {
                    "estimated_tokens": agent_relevant_tokens,
                    "actual_tokens": agent_relevant_tokens_actual,
                    "file_tokens": agent_relevant_tokens_actual,
                    "viewed_tokens": viewed_agent_relevant_tokens_actual,
                    "estimator_type": estimator.estimator_type
                }
                core_route_baseline = {
                    "estimated_tokens": core_route_tokens,
                    "actual_tokens": core_route_tokens_actual,
                    "file_tokens": core_route_tokens_actual,
                    "viewed_tokens": viewed_core_route_tokens_actual,
                    "estimator_type": estimator.estimator_type
                }
                mcp_context = {
                    "estimated_tokens": w["mcp_tokens"],
                    "actual_tokens": mcp_tokens_actual,
                    "file_tokens": mcp_tokens_actual,
                    "viewed_tokens": mcp_tokens_actual,
                    "estimator_type": estimator.estimator_type
                }

                # V7 Reductions (read-level)
                v7_reduction_percent = (1.0 - (mcp_context["viewed_tokens"] / agent_baseline["viewed_tokens"])) * 100 if agent_baseline["viewed_tokens"] else 0.0
                v7_relevant_reduction_percent = (1.0 - (mcp_context["viewed_tokens"] / relevant_baseline["viewed_tokens"])) * 100 if relevant_baseline["viewed_tokens"] else 0.0
                v7_core_reduction_percent = (1.0 - (mcp_context["viewed_tokens"] / core_route_baseline["viewed_tokens"])) * 100 if core_route_baseline["viewed_tokens"] else 0.0

                # V8 Calculations
                total_context_tokens = file_read_tokens + search_tokens + mcp_tokens_loaded + command_output_tokens
                v8_reduction_percent = (1.0 - (mcp_context["actual_tokens"] / total_context_tokens)) * 100 if total_context_tokens > 0 else 0.0

                v6_baseline_agent = agent_baseline["file_tokens"]
                v7_baseline_agent = agent_baseline["viewed_tokens"]
                inflation_v6_v7 = (v6_baseline_agent - v7_baseline_agent) / v7_baseline_agent * 100 if v7_baseline_agent > 0 else 0.0
                inflation_v7_v8 = (total_context_tokens - v7_baseline_agent) / v7_baseline_agent * 100 if v7_baseline_agent > 0 else 0.0

                # V9 Calculations
                total_conversation_tokens = (
                    user_tokens + planner_tokens + file_view_tokens + search_tokens_v9 +
                    mcp_tokens_v9 + command_tokens + diagnostic_tokens + tool_output_tokens
                )
                actual_context_cost_reduction_percent = (
                    (total_conversation_tokens - mcp_tokens_actual) / total_conversation_tokens * 100
                    if total_conversation_tokens > 0 else 0.0
                )

                # V9 validation checks
                validation_flags = w["validation_flags"]
                if total_conversation_tokens < total_context_tokens:
                    validation_flags.append("v9_v8_violation")
                if total_context_tokens < agent_baseline["viewed_tokens"]:
                    validation_flags.append("v8_v7_violation")
                if agent_baseline["file_tokens"] < agent_baseline["viewed_tokens"]:
                    validation_flags.append("v6_v7_violation")

                conversation_breakdown = {
                    "user_tokens": user_tokens,
                    "planner_tokens": planner_tokens,
                    "file_view_tokens": file_view_tokens,
                    "search_tokens": search_tokens_v9,
                    "mcp_tokens": mcp_tokens_v9,
                    "command_tokens": command_tokens,
                    "diagnostic_tokens": diagnostic_tokens,
                    "tool_output_tokens": tool_output_tokens
                }

                context_level_attribution = {
                    "file_read_tokens": file_read_tokens,
                    "search_tokens": search_tokens,
                    "mcp_tokens": mcp_tokens_loaded,
                    "command_output_tokens": command_output_tokens,
                    "total_context_tokens": total_context_tokens
                }

                w_metrics = {
                    "task_index": w["task_index"],
                    "query_id": w["query_id"],
                    "target": w["target"],
                    "policy": w["policy"],
                    "window_start": w["window_start"],
                    "window_end": w["window_end"],
                    "duration_seconds": w["duration_seconds"],
                    "step_start_idx": w["step_start_idx"],
                    "step_end_idx": w["step_end_idx"],
                    "validation_status": w["validation_status"],
                    "validation_flags": w["validation_flags"],
                    "files_opened": files_opened_chronological,
                    "files_modified": files_modified_chronological,
                    "unique_files_opened": unique_opened,
                    "unique_files_modified": unique_modified,
                    "read_count": read_count,
                    "write_count": write_count,
                    "unique_file_count": len(unique_touched),
                    "total_characters_read": total_chars_read,
                    "cumulative_characters_returned": cumulative_characters_returned,
                    "total_token_estimate": total_token_estimate,
                    "unique_file_tokens": unique_file_tokens,
                    "cumulative_read_tokens": cumulative_read_tokens,
                    "repo_tokens": repo_tokens,
                    "repo_tokens_actual": repo_tokens_actual,
                    "external_tokens": external_tokens,
                    "external_tokens_actual": external_tokens_actual,
                    "gemini_tokens": gemini_tokens,
                    "gemini_tokens_actual": gemini_tokens_actual,
                    "agent_code_tokens": agent_code_tokens,
                    "agent_code_files": agent_code_files,
                    "mcp_tokens": w["mcp_tokens"],
                    "mcp_tokens_actual": mcp_tokens_actual,
                    "mcp_files": w["mcp_files"],
                    "token_reduction_percent": token_reduction,
                    "file_reduction_percent": file_reduction,
                    
                    # V4 Relevance fields
                    "agent_all_tokens": agent_all_tokens,
                    "agent_all_tokens_actual": agent_all_tokens_actual,
                    "agent_relevant_tokens": agent_relevant_tokens,
                    "agent_relevant_tokens_actual": agent_relevant_tokens_actual,
                    "agent_irrelevant_tokens": agent_irrelevant_tokens,
                    "agent_irrelevant_tokens_actual": agent_irrelevant_tokens_actual,
                    "relevance_ratio": relevance_ratio,
                    "v3_reduction_percent": token_reduction,
                    "v4_reduction_percent": v4_token_reduction,
                    "v4_file_reduction_percent": file_reduction_v4,
                    "relevant_files_opened": sorted(relevant_files_opened),
                    "irrelevant_files_opened": sorted(irrelevant_files_opened),
                    
                    # V5 Route Core fields
                    "core_route_tokens": core_route_tokens,
                    "core_route_tokens_actual": core_route_tokens_actual,
                    "dependency_tokens": dependency_tokens,
                    "dependency_tokens_actual": dependency_tokens_actual,
                    "infrastructure_tokens": infrastructure_tokens,
                    "infrastructure_tokens_actual": infrastructure_tokens_actual,
                    "noise_tokens": noise_tokens,
                    "noise_tokens_actual": noise_tokens_actual,
                    "core_route_files": sorted(core_route_files_list),
                    "dependency_files": sorted(dependency_files_list),
                    "infrastructure_files": sorted(infrastructure_files_list),
                    "noise_files": sorted(noise_files_list),
                    "mcp_vs_core_reduction_percent": mcp_vs_core_reduction,
                    "mcp_vs_core_dep_reduction_percent": mcp_vs_core_dep_reduction,
                    "mcp_vs_all_rel_reduction_percent": mcp_vs_all_rel_reduction,
 
                    # V6/V7 structured metrics
                    "agent_baseline": agent_baseline,
                    "relevant_baseline": relevant_baseline,
                    "core_route_baseline": core_route_baseline,
                    "mcp_context": mcp_context,
                    "files_metadata": files_metadata,
 
                    # V7 specific fields
                    "unique_file_viewed_tokens": unique_file_viewed_tokens,
                    "cumulative_view_tokens": cumulative_view_tokens,
                    "v7_reduction_percent": v7_reduction_percent,
                    "v7_relevant_reduction_percent": v7_relevant_reduction_percent,
                    "v7_core_reduction_percent": v7_core_reduction_percent,
 
                    # V8 specific fields
                    "file_read_tokens": file_read_tokens,
                    "search_tokens": search_tokens,
                    "v8_mcp_tokens": mcp_tokens_loaded,
                    "command_output_tokens": command_output_tokens,
                    "total_context_tokens": total_context_tokens,
                    "v8_reduction_percent": v8_reduction_percent,
                    "inflation_v6_v7": inflation_v6_v7,
                    "inflation_v7_v8": inflation_v7_v8,
                    "context_level_attribution": context_level_attribution,

                    # V9 specific fields
                    "conversation_breakdown": conversation_breakdown,
                    "total_conversation_tokens": total_conversation_tokens,
                    "actual_context_cost_reduction_percent": actual_context_cost_reduction_percent
                }
                window_metrics.append(w_metrics)

            results[s_id] = window_metrics

        # Save metrics to snapshot
        os.makedirs(os.path.dirname(output_metrics_path), exist_ok=True)
        with open(output_metrics_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        print(f"Saved task-window metrics to {output_metrics_path}")
        return results
