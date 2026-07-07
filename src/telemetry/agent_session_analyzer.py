import json
import os
import re

from telemetry.token_estimator import AutoEstimator

class AgentSessionAnalyzer:
    def __init__(self, brain_dir=r"C:\Users\ajeem\.gemini\antigravity-ide\brain"):
        self.brain_dir = brain_dir

    def normalize_path(self, path_str):
        if not path_str:
            return None
        # Format slashes
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

    def extract_code_from_view_file_content(self, content):
        """
        Parses a VIEW_FILE step content to reconstruct file text if disk reading fails.
        Handles prefixed line numbers (e.g., '12: import os').
        """
        lines = content.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            # Look for lines starting with line numbers, e.g., "1: import os" or "123: class Foo"
            match = re.match(r'^\s*(\d+):\s(.*?)$', line)
            if match:
                code_lines.append(match.group(2))
                in_code_block = True
            elif in_code_block and line == "":
                # Preserve empty lines within the code block
                code_lines.append("")
        
        if code_lines:
            return "\n".join(code_lines)
        return content

    def analyze_session(self, session_id, provider="gemini"):
        log_path = os.path.join(self.brain_dir, session_id, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Transcript log not found for session {session_id} at {log_path}")

        estimator = AutoEstimator(provider)

        opened_files_list = []  # Chronological list of all view events
        modified_files_set = set() # Set of unique modified files
        
        # We also want to record the actual content lengths in case disk read fails
        log_fallback_contents = {}

        steps = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    steps.append(json.loads(line))
                except:
                    continue

        # Extract timestamps
        start_timestamp = steps[0].get("created_at") if steps else None
        end_timestamp = steps[-1].get("created_at") if steps else None

        # Map to find tool results corresponding to tool calls
        # We scan for MODEL tool calls in PLANNER_RESPONSE steps
        for idx, step in enumerate(steps):
            if step.get("type") == "PLANNER_RESPONSE" and step.get("source") == "MODEL":
                tool_calls = step.get("tool_calls", [])
                for tc in tool_calls:
                    name = tc.get("name")
                    args = tc.get("args", {})
                    
                    if name == "view_file":
                        raw_path = args.get("AbsolutePath")
                        norm_path = self.normalize_path(raw_path)
                        if norm_path:
                            opened_files_list.append(norm_path)
                            
                            # Scan forward to find the next VIEW_FILE step representing the result
                            for next_step in steps[idx+1:idx+10]: # Look ahead up to 10 steps
                                if next_step.get("type") == "VIEW_FILE" and next_step.get("source") == "MODEL":
                                    content = next_step.get("content", "")
                                    code = self.extract_code_from_view_file_content(content)
                                    log_fallback_contents[norm_path] = code
                                    break
                                    
                    elif name in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
                        raw_path = args.get("TargetFile")
                        norm_path = self.normalize_path(raw_path)
                        if norm_path:
                            modified_files_set.add(norm_path)

        # Unique lists
        unique_files_opened = sorted(list(set(opened_files_list)))
        unique_files_modified = sorted(list(modified_files_set))

        # Calculate character counts and token estimates for opened files
        files_metadata = {}
        repo_tokens = 0
        repo_tokens_actual = 0
        external_tokens = 0
        external_tokens_actual = 0
        gemini_tokens = 0
        gemini_tokens_actual = 0

        for path in unique_files_opened:
            char_count = 0
            read_success = False
            file_content = ""
            
            # 1. Try reading from disk
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                        char_count = len(file_content)
                        read_success = True
                except Exception as e:
                    pass
            
            # 2. Fall back to log content size if disk read fails
            if not read_success:
                file_content = log_fallback_contents.get(path, "")
                char_count = len(file_content)

            token_estimate = char_count // 4
            actual_token_estimate = estimator.estimate_tokens(file_content)

            files_metadata[path] = {
                "character_count": char_count,
                "token_estimate": token_estimate,
                "actual_tokens": actual_token_estimate
            }

            # Separate into categories
            category = self.categorize_path(path)
            if category == "repo":
                repo_tokens += token_estimate
                repo_tokens_actual += actual_token_estimate
            elif category == "external":
                external_tokens += token_estimate
                external_tokens_actual += actual_token_estimate
            elif category == "gemini":
                gemini_tokens += token_estimate
                gemini_tokens_actual += actual_token_estimate

        # Session Metrics
        investigation_character_count = sum(meta["character_count"] for meta in files_metadata.values())
        investigation_token_estimate = repo_tokens + external_tokens + gemini_tokens
        investigation_token_actual = repo_tokens_actual + external_tokens_actual + gemini_tokens_actual

        # Record open frequencies
        open_frequencies = {}
        for path in opened_files_list:
            open_frequencies[path] = open_frequencies.get(path, 0) + 1

        agent_baseline = {
            "estimated_tokens": investigation_token_estimate,
            "actual_tokens": investigation_token_actual,
            "estimator_type": estimator.estimator_type
        }

        metrics = {
            "session_id": session_id,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "files_opened_count": len(unique_files_opened),
            "files_modified_count": len(unique_files_modified),
            "investigation_character_count": investigation_character_count,
            "investigation_token_estimate": investigation_token_estimate,
            "investigation_token_estimate_actual": investigation_token_actual,
            "repo_tokens": repo_tokens,
            "repo_tokens_actual": repo_tokens_actual,
            "external_tokens": external_tokens,
            "external_tokens_actual": external_tokens_actual,
            "gemini_tokens": gemini_tokens,
            "gemini_tokens_actual": gemini_tokens_actual,
            "unique_files_opened": unique_files_opened,
            "unique_files_modified": unique_files_modified,
            "files_metadata": files_metadata,
            "open_frequencies": open_frequencies,
            "opened_files_history": opened_files_list,
            "agent_baseline": agent_baseline
        }
        return metrics

    def run_and_save(self, session_ids, provider="gemini", output_path=r"snapshots/agent_session_metrics.json"):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Load existing metrics if present
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    all_metrics = json.load(f)
            except:
                all_metrics = {}
        else:
            all_metrics = {}

        for s_id in session_ids:
            try:
                print(f"Analyzing session {s_id} with provider {provider}...")
                s_metrics = self.analyze_session(s_id, provider=provider)
                all_metrics[s_id] = s_metrics
            except Exception as e:
                print(f"Error analyzing session {s_id}: {e}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_metrics, f, indent=2)
            
        print(f"Saved session telemetry metrics to {output_path}")
        return all_metrics
