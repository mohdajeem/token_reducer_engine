import os
import sys
import json
import contextlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal

# Add the project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from mcp.server.fastmcp import FastMCP
from build_graph import build_graph
from impact_engine import GraphTraversal, TraversalPolicy, PolicyTraversalEngine
from context_engine import ContextExtractor
from main import resolve_target_node, TargetSpecError
import re
from incremental_runtime.snapshot_manager import SnapshotManager
from telemetry.live_telemetry import live_telemetry_manager
from telemetry.task_window_analyzer import TaskWindowAnalyzer
from incremental_runtime.incremental_graph_manager import IncrementalGraphManager
from incremental_runtime.graph_watcher import GraphWatcher
from semantic_core.graph_builder import GraphBuilder

# ==========================================================
# STDOUT REDIRECTION TO PREVENT STREAM CORRUPTION
# ==========================================================

@contextlib.contextmanager
def redirect_stdout_to_stderr():
    """Context manager to redirect sys.stdout to sys.stderr to prevent debug print pollution on JSON-RPC stdio."""
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout

# ==========================================================
# INITIALIZE MCP SERVER & STATE
# ==========================================================

mcp = FastMCP("Semantic Context Engine")

SERVER_STATE = {
    "repo_path": None,
    "graph": None,
    # the GraphBuilder that built `graph` (symbol table, function index, option defaults):
    # incremental updates need it to resolve cross-file exactly like the original build
    "builder": None,
    # file hashes describing `graph` (the on-disk hash file may lag a background write)
    "hashes": None,
    "lock": threading.Lock(),
    "watcher": None
}


# ==========================================================
# MCP TOOLS
# ==========================================================
@mcp.tool()
def mcp_build_graph(repo_path: str, force_rebuild: bool = False, watch: bool = False, cache_subdir: str = "") -> str:
    """
    Builds or updates the semantic context graph for a repository.
    Loads cached index if available to optimize start latency.
    
    Args:
        repo_path: Absolute path to the repository root directory.
        force_rebuild: If True, forces a full rebuild and bypasses the cache.
        watch: If True, starts a background filesystem watcher to track changes in real-time (off by default; batch/agent use builds once per checkout).
        cache_subdir: Subdirectory under .semantic_cache to isolate different versions of the graph.
    """
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        return f"Error: Repository path '{repo_path}' is not a valid directory."
        
    from incremental_runtime.snapshot_manager import writers_paused
    with SERVER_STATE["lock"], writers_paused():
        # Stop existing watcher if active
        if SERVER_STATE.get("watcher"):
            try:
                SERVER_STATE["watcher"].stop()
            except Exception as ex:
                print(f"Failed to stop watcher: {ex}", file=sys.stderr)
            SERVER_STATE["watcher"] = None

        SERVER_STATE["repo_path"] = repo_path
        
        # Build isolated cache directory if requested
        if cache_subdir:
            cache_dir = os.path.join(repo_path, ".semantic_cache", cache_subdir)
        else:
            cache_dir = os.path.join(repo_path, ".semantic_cache")
            
        snapshot_mgr = SnapshotManager(snapshot_dir=cache_dir)
        
        # Check cache first
        from incremental_runtime.change_detector import ChangeDetector
        change_detector = ChangeDetector()

        graph = None
        loaded_from_cache = False
        rebuild_incrementally = False
        changed_files = []

        if not force_rebuild:
            try:
                # the graph already in memory for THIS repo is the snapshot's content (or
                # newer): don't re-read 27 MB of JSON on every tool call just to get it back
                live = SERVER_STATE.get("repo_path") == repo_path and SERVER_STATE.get("graph") is not None                     and SERVER_STATE.get("builder") is not None and snapshot_mgr.has_snapshot("graph")
                cached_graph = None
                if live:
                    cached_graph = SERVER_STATE["graph"]
                else:
                    with redirect_stdout_to_stderr():
                        cached_graph = snapshot_mgr.load_snapshot("graph")
                if cached_graph:
                    # live: compare against the hashes of the graph in memory (the on-disk
                    # hash file may lag behind a background snapshot write). The file is
                    # committed only once the snapshot it describes is on disk.
                    baseline = SERVER_STATE.get("hashes") if live else None
                    changed_files = change_detector.get_changed_files(repo_path, cache_dir=cache_dir, commit=False, baseline=baseline)
                    SERVER_STATE["hashes"] = change_detector.last_hashes
                    if changed_files:
                        # a live builder for THIS repo, else one restored from the snapshot;
                        # a snapshot without builder state cannot be updated correctly -> rebuild
                        builder = SERVER_STATE.get("builder") if live else None
                        if builder is None:
                            from build_graph import restore_builder
                            builder = restore_builder(cached_graph, repo_path)
                        if builder is not None:
                            rebuild_incrementally = True
                            print(f"Incrementally updating {len(changed_files)} changed files for: {repo_path}...", file=sys.stderr)
                            # a background write may still be reading this graph: abort it,
                            # the update below writes a newer one
                            snapshot_mgr.wait("graph", cancel=True)
                            with redirect_stdout_to_stderr():
                                from incremental_runtime.incremental_update import apply_update
                                apply_update(builder, cached_graph, repo_path, changed_files)
                            graph = cached_graph
                            SERVER_STATE["builder"] = builder
                            # the 27 MB astropy snapshot takes ~0.4 s to serialize + write:
                            # do it while the model thinks, not inside this call
                            snapshot_mgr.save_snapshot(graph, "graph", background=True, on_done=change_detector.committer())
                        else:
                            print(f"Snapshot has no builder state; rebuilding {repo_path} in full.", file=sys.stderr)
                    else:
                        graph = cached_graph
                        loaded_from_cache = True
                        if not snapshot_mgr.writing("graph"):
                            change_detector.committer()()  # nothing changed: only mtime stamps refreshed
                        if not live:
                            from build_graph import restore_builder
                            SERVER_STATE["builder"] = restore_builder(graph, repo_path)
            except Exception as e:
                print(f"Failed to load cached graph: {e}", file=sys.stderr)
                graph = None

        if graph is None:
            # Compile graph
            try:
                print(f"Building semantic graph for: {repo_path}...", file=sys.stderr)
                with redirect_stdout_to_stderr():
                    graph = build_graph(repo_path)
                    import build_graph as _bg
                    SERVER_STATE["builder"] = _bg.GLOBAL_BUILDER
                    # Save cache and initial hashes (snapshot written in the background; the
                    # hashes land only after it)
                    change_detector.get_changed_files(repo_path, cache_dir=cache_dir, commit=False)
                    SERVER_STATE["hashes"] = change_detector.last_hashes
                    snapshot_mgr.save_snapshot(graph, "graph", background=True, on_done=change_detector.committer())
            except Exception as e:
                return f"Error building graph: {e}"

        SERVER_STATE["graph"] = graph

        # Start the background watcher if requested
        if watch:
            try:
                builder = GraphBuilder()
                builder.graph = graph
                manager = IncrementalGraphManager(
                    graph_builder=builder,
                    match_extractor=None,
                    project_root=repo_path
                )
                watcher = GraphWatcher(
                    project_root=repo_path,
                    incremental_graph_manager=manager,
                    lock=SERVER_STATE["lock"],
                    interval=1.0
                )
                watcher.start()
                SERVER_STATE["watcher"] = watcher
                print(f"[MCP Server] Started real-time background watcher for {repo_path}", file=sys.stderr)
            except Exception as e:
                print(f"[MCP Server Warning] Failed to start background watcher: {e}", file=sys.stderr)

        funcs = sum(len(v) for v in graph.get("functions", {}).values())
        routes = sum(len(v) for v in graph.get("routes", {}).values())
        edges = len(graph.get("execution_edges", []))

        if rebuild_incrementally:
            return (
                f"Successfully incrementally updated {len(changed_files)} file(s) in semantic graph!\n"
                f"Updated files: {', '.join(changed_files[:5])}{'...' if len(changed_files) > 5 else ''}\n"
                f"Metrics:\n"
                f"  - Functions: {funcs}\n"
                f"  - Routes: {routes}\n"
                f"  - Execution Edges: {edges}"
            )
        elif loaded_from_cache:
            return (
                f"Successfully loaded cached graph from .semantic_cache/graph.json!\n"
                f"Metrics:\n"
                f"  - Functions: {funcs}\n"
                f"  - Routes: {routes}\n"
                f"  - Execution Edges: {edges}"
            )
        else:
            return (
                f"Successfully compiled semantic graph!\n"
                f"Metrics:\n"
                f"  - Functions: {funcs}\n"
                f"  - Routes: {routes}\n"
                f"  - Execution Edges: {edges}"
            )

def log_query_telemetry(repo_path: str, target: str, policy: str, context: dict):
    """
    Shadow logs context query metrics to snapshots/vibecoding_metrics.json.
    Excludes logging if context has errors.
    """
    if "error" in context:
        return
        
    import datetime
    try:
        # 1. Repo size calculations
        file_count = 0
        char_count = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "dist", "build", ".venv", "venv", ".sandbox", ".semantic_cache")]
            for file in files:
                if file.endswith((".js", ".ts", ".py", ".json", ".scm", ".md")):
                    file_count += 1
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            char_count += len(f.read())
                    except:
                        pass
                        
        repo_tokens = char_count // 4
        
        # 2. Semantic Context calculations
        snippets = context.get("code_snippets", [])
        selected_files = list({s.get("file") for s in snippets if s.get("file")})
        context_payload = json.dumps(snippets)
        context_chars = len(context_payload)
        context_tokens = context_chars // 4
        
        saved_tokens = max(0, repo_tokens - context_tokens)
        reduction_pct = round((1.0 - (context_chars / char_count)) * 100.0, 2) if char_count > 0 else 0.0
        reduction_pct = max(0.0, min(100.0, reduction_pct))
        
        # 3. Assemble record
        record = {
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repository_path": repo_path.replace("\\", "/"),
            "target": target,
            "policy": policy,
            "repository_character_count": char_count,
            "repository_token_estimate": repo_tokens,
            "repository_file_count": file_count,
            "context_character_count": context_chars,
            "context_token_estimate": context_tokens,
            "selected_files": selected_files,
            "selected_file_count": len(selected_files),
            "saved_tokens_vs_repo": saved_tokens,
            "reduction_percent_vs_repo": reduction_pct,
            
            # Agent Investigation Mode placeholders
            "files_opened_by_agent": None,
            "files_modified_by_agent": None,
            "investigation_character_count": None,
            "investigation_token_estimate": None,
            
            "agent_metadata": {
                "agent_name": "Antigravity",
                "session_id": os.environ.get("CONVERSATION_ID", "default_session")
            }
        }
        
        # 4. Save to snapshots/vibecoding_metrics.json
        project_root = Path(__file__).resolve().parent.parent.parent
        snapshots_dir = os.path.join(project_root, "snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)
        metrics_file = os.path.join(snapshots_dir, "vibecoding_metrics.json")
        
        metrics = []
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
                    if not isinstance(metrics, list):
                        metrics = []
            except:
                pass
                
        metrics.append(record)
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
            
    except Exception as e:
        print(f"[TELEMETRY WARNING] Failed to log query telemetry: {e}", file=sys.stderr)


@mcp.tool()
def mcp_query_context(
    target: Optional[str] = None,
    targets: Optional[List[str]] = None,
    policy: str = "DEFAULT"
) -> dict:
    """
    Extracts pruned code snippets, execution chains, and route context matching single or batch target changes.
    
    Args:
        target: Single target spec string or comma-separated targets, e.g. 'FUNCTION:app.init' or 'FUNCTION:init, FUNCTION:handle'.
        targets: Optional list of target spec strings for batch querying, e.g. ['FUNCTION:app.init', 'FUNCTION:app.handle'].
        policy: Blast radius pruning policy: 'DEFAULT', 'LOCAL_EDIT', 'SIGNATURE_CHANGE', 'NEW_FEATURE', 'TAINT_FLOW', or 'DEPENDENCY_ONLY'.
    """
    target_list = []
    if targets and isinstance(targets, list):
        target_list.extend(targets)
    if target:
        if "," in target:
            target_list.extend([t.strip() for t in target.split(",") if t.strip()])
        elif target not in target_list:
            target_list.append(target)

    if not target_list:
        return {"error": "No target specified. Please provide target or targets."}

    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        repo_path = SERVER_STATE.get("repo_path")
        
        if not graph or not repo_path:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
            
        try:
            combined_snippets = []
            seen_snippet_keys = set()
            combined_chains = []
            combined_files = []

            for single_target in target_list:
                try:
                    with redirect_stdout_to_stderr():
                        target_node = resolve_target_node(graph, single_target, repo_root=repo_path)
                except TargetSpecError as e:
                    return {"error": str(e)}
                if not target_node:
                    continue

                policy_enum = TraversalPolicy[policy.upper()]
                
                with redirect_stdout_to_stderr():
                    traversal = GraphTraversal(graph)
                    policy_engine = PolicyTraversalEngine(traversal)
                    extractor = ContextExtractor(graph, repo_path)
                    
                    impact = policy_engine.resolve_impact(target_node, policy_enum)
                    context = extractor.extract_context(impact)

                for snippet in context.get("code_snippets", []):
                    if snippet.get("file"):
                        rel_p = os.path.relpath(
                            os.path.join(repo_path, snippet["file"]),
                            repo_path
                        ).replace("\\", "/")
                        snippet["file"] = rel_p

                    key = (snippet.get("file"), snippet.get("function_name"), snippet.get("code"))
                    if key not in seen_snippet_keys:
                        seen_snippet_keys.add(key)
                        combined_snippets.append(snippet)

                for chain in context.get("execution_chains", []):
                    if chain not in combined_chains:
                        combined_chains.append(chain)
                for fpath in context.get("relevant_files", []):
                    rel_f = str(fpath).replace("\\", "/")
                    if rel_f not in combined_files:
                        combined_files.append(rel_f)

                log_query_telemetry(repo_path, single_target, policy, context)

            if not combined_snippets:
                return {"error": f"Failed to resolve any target nodes from: {target_list}"}

            return {
                "target_count": len(target_list),
                "code_snippets": combined_snippets,
                "execution_chains": combined_chains,
                "relevant_files": combined_files,
            }
        except Exception as e:
            return {"error": f"Failed to query context: {e}"}


@mcp.tool()
def mcp_impact_analysis(
    target: str,
    policy: str = "DEFAULT",
    max_depth: Optional[int] = None,
    direction: str = "BOTH",
    include_types: Optional[List[str]] = None,
    include_tests: bool = False,
) -> dict:
    """
    Resolves the blast radius of a change using precision policies, depth limits, and edge filters.
    
    Args:
        target: Target spec string, e.g. 'FUNCTION:src/services/auth.service.js:loginUser'.
        policy: Traversal policy ('DEFAULT', 'LOCAL_EDIT', 'SIGNATURE_CHANGE', 'NEW_FEATURE', 'TAINT_FLOW', 'DEPENDENCY_ONLY').
        max_depth: Optional maximum depth limit (number of hops).
        direction: Traversal direction ('UPSTREAM', 'DOWNSTREAM', or 'BOTH').
        include_types: Optional list of edge types to include (e.g. ['FUNCTION_CALL', 'DB_ACCESS']).
        include_tests: Also follow edges that originate in test files (hidden by default).
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
            
        try:
            try:
                with redirect_stdout_to_stderr():
                    target_node = resolve_target_node(graph, target, repo_root=SERVER_STATE.get("repo_path"))
            except TargetSpecError as e:
                return {"error": str(e)}
            if not target_node:
                return {"error": f"Failed to resolve target node: {target}"}

            policy_enum = TraversalPolicy[policy.upper()] if policy.upper() in TraversalPolicy.__members__ else TraversalPolicy.DEFAULT

            with redirect_stdout_to_stderr():
                traversal = GraphTraversal(graph)
                policy_engine = PolicyTraversalEngine(traversal)
                impact = policy_engine.resolve_impact(
                    target_node=target_node,
                    policy=policy_enum,
                    max_depth=max_depth,
                    direction=direction.upper(),
                    include_types=include_types,
                    include_tests=include_tests,
                )
            
            upstream = impact.get("upstream", [])
            downstream = impact.get("downstream", [])
            
            return {
                "target": target_node,
                "policy_applied": policy_enum.name,
                "max_depth_applied": max_depth,
                "direction": direction,
                "upstream_edges_count": len(upstream),
                "downstream_edges_count": len(downstream),
                "upstream_nodes": [edge["from"] for edge in upstream],
                "downstream_nodes": [edge["to"] for edge in downstream],
                "upstream_edges": upstream,
                "downstream_edges": downstream,
                "completeness": impact_completeness(graph, target_node, upstream, downstream, include_tests),
            }
        except Exception as e:
            return {"error": f"Failed to analyze impact: {e}"}



@mcp.tool()
def mcp_show_routes() -> dict:
    """
    Returns the flat HTTP routing table registered in the repository.
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
            
        return {
            "routes": graph.get("routes", {})
        }


@mcp.tool()
def mcp_show_graph_metrics() -> dict:
    """
    Returns diagnostic metrics of the compiled semantic graph.
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
            
        functions_count = sum(len(v) for v in graph.get("functions", {}).values())
        imports_count = sum(len(v) for v in graph.get("imports", {}).values())
        calls_count = sum(len(v) for v in graph.get("calls", {}).values())
        routes_count = sum(len(v) for v in graph.get("routes", {}).values())
        edges_count = len(graph.get("execution_edges", []))
        taints_count = len(graph.get("taint_sources", []))
        
        return {
            "metrics": {
                "functions": functions_count,
                "imports": imports_count,
                "calls": calls_count,
                "routes": routes_count,
                "execution_edges": edges_count,
                "taint_sources": taints_count
            }
        }



@mcp.tool()
def telemetry_start(task_name: str, mode: str) -> str:
    """
    Starts a live telemetry run.
    
    Args:
        task_name: Name of the task.
        mode: Mode of execution ('baseline' or 'token_reducer').
    """
    task_slug = task_name.lower().replace(" ", "_").replace("-", "_")
    mode_str = "baseline" if mode == "baseline" else "tokenreducer"
    run_id = f"{mode_str}_{task_slug}"
    
    live_telemetry_manager.start_run(run_id=run_id, task_name=task_name, mode=mode)
    return f"Run '{run_id}' started for task '{task_name}' in mode '{mode}'."


@mcp.tool()
def telemetry_snapshot() -> dict:
    """
    Takes a snapshot of the current active run.
    """
    try:
        snap = live_telemetry_manager.snapshot()
        return {
            "total_tokens": snap["total_tokens"],
            "files_opened": snap["files_opened"],
            "files_modified": snap["files_modified"],
            "category_breakdown": snap["categories"]
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def telemetry_end() -> dict:
    """
    Ends the current active run and returns final metrics.
    """
    try:
        res = live_telemetry_manager.end_run()
        return {
            "total_tokens": res["total_tokens"],
            "files_opened": res["files_opened"],
            "files_modified": res["files_modified"],
            "execution_time": res["execution_time_seconds"],
            "category_breakdown": res["categories"]
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def compare_runs(baseline_run_id: str, experiment_run_id: str) -> dict:
    """
    Compares baseline and experimental runs and produces a report.
    """
    try:
        res = live_telemetry_manager.compare_runs(baseline_run_id, experiment_run_id)
        return {
            "baseline_tokens": res["baseline_tokens"],
            "experiment_tokens": res["experiment_tokens"],
            "baseline_files": res["baseline_files"],
            "experiment_files": res["experiment_files"],
            "reduction_percent": res["reduction_percent"],
            "execution_time_baseline": res["execution_time_baseline"],
            "execution_time_experiment": res["execution_time_experiment"],
            "report_markdown": res["report_markdown"]
        }
    except Exception as e:
        return {"error": str(e)}


def get_current_session_id() -> str:
    # 1. Try environment variable CONVERSATION_ID
    sess_id = os.environ.get("CONVERSATION_ID")
    if sess_id and sess_id != "default_session":
        return sess_id
    
    # 2. Fallback: find the most recently modified transcript.jsonl under brain_dir
    brain_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-ide", "brain")
    if os.path.exists(brain_dir):
        newest_sess = None
        newest_time = 0
        for entry in os.listdir(brain_dir):
            sess_path = os.path.join(brain_dir, entry)
            if os.path.isdir(sess_path):
                log_file = os.path.join(sess_path, ".system_generated", "logs", "transcript.jsonl")
                if os.path.exists(log_file):
                    mtime = os.path.getmtime(log_file)
                    if mtime > newest_time:
                        newest_time = mtime
                        newest_sess = entry
        if newest_sess:
            return newest_sess
            
    return "default_session"


def aggregate_v9_session_metrics(session_id: str, provider: str) -> dict:
    brain_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-ide", "brain")
    analyzer = TaskWindowAnalyzer(brain_dir=brain_dir)
    
    # Resolve absolute paths relative to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    vibecoding_path = os.path.join(project_root, "snapshots", "vibecoding_metrics.json")
    output_metrics_path = os.path.join(project_root, "snapshots", "task_window_metrics_v9.json")
    
    # Run the existing window analysis
    results = analyzer.run_window_analysis(
        [session_id],
        provider=provider,
        vibecoding_path=vibecoding_path,
        output_metrics_path=output_metrics_path
    )
    
    windows = results.get(session_id)
    if not windows:
        return {"error": f"No V9 metrics calculated for session {session_id}."}
        
    total_conversation_tokens = 0
    breakdown = {
        "user_tokens": 0,
        "planner_tokens": 0,
        "file_view_tokens": 0,
        "search_tokens": 0,
        "mcp_tokens": 0,
        "command_tokens": 0,
        "diagnostic_tokens": 0,
        "tool_output_tokens": 0
    }
    validation_status = "PASS"
    
    for w in windows:
        total_conversation_tokens += w.get("total_conversation_tokens", 0)
        bd = w.get("conversation_breakdown", {})
        for k in breakdown:
            breakdown[k] += bd.get(k, 0)
        if w.get("validation_status") == "FAIL":
            validation_status = "FAIL"
            
    return {
        "session_id": session_id,
        "total_conversation_tokens": total_conversation_tokens,
        "breakdown": breakdown,
        "validation_status": validation_status,
        "provider": provider
    }


@mcp.tool()
def v9_analyze_current_session(provider: Literal["gemini", "groq"] = "gemini") -> dict:
    """
    Automatically resolves the current Antigravity session and returns conversation V9 telemetry metrics.
    
    Args:
        provider: Tokenizer provider ('gemini' or 'groq').
    """
    try:
        session_id = get_current_session_id()
        if session_id == "default_session":
            return {"error": "Could not determine current active Antigravity session."}
        return aggregate_v9_session_metrics(session_id, provider)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def v9_analyze_session(session_id: str, provider: Literal["gemini", "groq"] = "gemini") -> dict:
    """
    Runs V9 conversation analysis on any specified session ID.
    
    Args:
        session_id: The UUID of the session to analyze.
        provider: Tokenizer provider ('gemini' or 'groq').
    """
    try:
        return aggregate_v9_session_metrics(session_id, provider)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def mcp_expand_signature(file_path: str, function_name: str) -> str:
    """
    Given a file path and a function name, returns the full implementation body of that function.
    Useful when a previous query returned only the signature due to budget/traversal limits,
    but the LLM decides it needs the full implementation context.
    """
    with SERVER_STATE["lock"]:
        repo_path = SERVER_STATE.get("repo_path")
        if not repo_path:
            return "Error: Graph is not built yet. Please call mcp_build_graph(repo_path) first."
            
        try:
            extractor = ContextExtractor(graph={}, project_root=repo_path)
            full_code = extractor.extract_function_code(file_path, function_name)
            if not full_code:
                return f"Error: Could not locate function '{function_name}' in '{file_path}'."
            return full_code
        except Exception as e:
            return f"Error: {e}"


# ==========================================================
# COMPLETENESS -- every impact answer says how much of it is known
# ==========================================================
def _edge_confidence(edge):
    return edge.get("confidence") or "resolved"


def impact_completeness(graph, target_node, upstream, downstream, include_tests=False):
    """
    The graph is a LOWER BOUND on real dependencies: a call the builder could not resolve is a
    caller it cannot report. This block makes that visible on every impact answer:
      unresolved_calls_to_name -- call sites of the target's NAME that resolved to nothing (each
                                  may be a missed caller); listed with file / caller / receiver
      external_calls_to_name   -- same-named calls that are library / builtin (not missed)
      low_confidence_edges     -- reported edges that came from a name-unique or multi-candidate
                                  resolution rather than a typed / imported one
      verdict                  -- "complete" (no unresolved same-name calls), "partial" (some),
                                  "unknown" (target not in graph)
    """
    name = (target_node or {}).get("function")
    if not name:
        return {"verdict": "unknown"}
    unresolved, external = [], []
    for file, calls in (graph.get("calls") or {}).items():
        if not include_tests and any(part in {"test", "tests", "__tests__", "spec", "testing"} for part in file.split("/")[:-1]):
            continue
        for c in calls:
            if c.get("function") != name or c.get("resolved_function"):
                continue
            entry = {"file": file, "caller": c.get("caller_function") or "GLOBAL_SCOPE", "receiver": c.get("receiver")}
            if c.get("external"):
                entry["package"] = c["external"]
                external.append(entry)
            else:
                unresolved.append(entry)
    low = [{"from": e.get("from"), "to": e.get("to"), "confidence": _edge_confidence(e)}
           for e in list(upstream) + list(downstream) if _edge_confidence(e) != "resolved"]
    out = {
        "verdict": "complete" if not unresolved else "partial",
        "unresolved_calls_to_name": len(unresolved),
        "unresolved_examples": unresolved[:10],
        "external_calls_to_name": len(external),
        "low_confidence_edges": len(low),
        "low_confidence_examples": low[:10],
    }
    if unresolved:
        out["note"] = (f"{len(unresolved)} call(s) named '{name}' could not be attributed to a definition; "
                       f"any of them may be a caller of this target. Confirm with mcp_find_symbols / search "
                       f"before treating the blast radius as complete.")
    return out

# ==========================================================
# SKELETON VIEW -- signatures + docs first, bodies on demand
# ==========================================================
_DOC_START_RE = re.compile(r"^\s*(/\*\*|\"\"\"|'''|#|//|\*)")


def _first_doc_line(lines, start_idx, python: bool):
    """One-line summary from the doc attached to a definition: the first sentence of the
    `/** ... */` (or `//`) block directly above it, or of a Python docstring directly below."""
    if python:
        j = start_idx + 1
        while j < len(lines) and j < start_idx + 4:
            t = lines[j].strip()
            if t.startswith(("\"\"\"", "'''")):
                inner = t.strip("\"'").strip()
                if not inner and j + 1 < len(lines):
                    inner = lines[j + 1].strip().strip("\"'").strip()
                return inner[:140]
            if t and not t.startswith(("@", "#")) and not t.endswith(":"):
                return ""
            j += 1
        return ""
    j = start_idx - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j < 0:
        return ""
    t = lines[j].strip()
    if t.endswith("*/"):
        # walk up to the start of the comment block, then take its first text line
        k = j
        while k >= 0 and "/*" not in lines[k]:
            k -= 1
        for m in range(max(k, 0), j + 1):
            txt = lines[m].strip().lstrip("/*").strip(" *").strip()
            if txt.endswith("*/"):
                txt = txt[:-2].rstrip(" *").strip()
            if txt and not txt.startswith("@"):
                return txt[:140]
        return ""
    if t.startswith("//"):
        return t.lstrip("/ ").strip()[:140]
    return ""


def _signature_lines(lines, start_idx, python: bool, max_lines: int = 3):
    """The definition header: from the start line to the line that opens the body."""
    out = []
    for j in range(start_idx, min(len(lines), start_idx + max_lines)):
        out.append(lines[j].rstrip())
        t = lines[j].rstrip()
        if (python and t.endswith(":")) or (not python and ("{" in t or t.endswith("=>") or t.endswith(";"))):
            break
    sig = " ".join(x.strip() for x in out)
    return sig[:200]


@mcp.tool()
def mcp_skeleton(file_path: str, max_symbols: int = 120, keywords: Optional[List[str]] = None) -> dict:
    """
    A compressed view of one file: every function / method / class with its signature line,
    a one-line doc summary, and its line span -- grouped by class, in source order. Roughly
    3-8% of the tokens of the file itself. Read this first; then mcp_expand_signature /
    expand_symbol only the bodies you need. `keywords` marks symbols whose span contains a
    keyword (so the caller can see where an issue's terms land without reading bodies).

    Args:
        file_path: Repo-relative path.
        max_symbols: Cap on listed symbols (largest files first get truncated, with a note).
        keywords: Optional words to flag inside symbol bodies.
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        repo_path = SERVER_STATE.get("repo_path")
    if not graph or not repo_path:
        return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
    rel = file_path.replace("\\", "/")
    fns = None
    for f, entries in (graph.get("functions") or {}).items():
        if f == rel or f.endswith("/" + rel) or rel.endswith("/" + f):
            fns, rel = entries, f
            break
    full = os.path.join(repo_path, rel)
    if fns is None or not os.path.isfile(full):
        return {"error": f"{file_path!r} is not an indexed source file."}
    try:
        lines = open(full, encoding="utf-8", errors="replace").read().split("\n")
    except Exception as e:
        return {"error": str(e)}
    python = rel.endswith(".py")
    kws = list(dict.fromkeys(k.lower() for k in (keywords or []) if k))
    items = []
    for fn in sorted((x for x in fns if isinstance(x, dict) and x.get("start_line")), key=lambda x: x["start_line"]):
        i = fn["start_line"] - 1
        if i >= len(lines):
            continue
        body = "\n".join(lines[i:fn.get("end_line") or i + 1]).lower() if kws else ""
        items.append({
            "symbol": (fn["class"] + "." if fn.get("class") else "") + fn["name"],
            "kind": fn.get("kind") or ("method" if fn.get("class") else "function"),
            "lines": [fn["start_line"], fn.get("end_line") or fn["start_line"]],
            "signature": _signature_lines(lines, i, python),
            "doc": _first_doc_line(lines, i, python),
            **({"static": True} if fn.get("static") else {}),
            **({"is_test": True} if fn.get("is_test") else {}),
            **({"keyword_hits": [k for k in kws if k in body]} if kws else {}),
        })
    truncated = len(items) > max_symbols
    items = items[:max_symbols]
    text_lines = [f"# {rel}  ({len(lines)} lines, {len(items)} symbols{', truncated' if truncated else ''})"]
    for it in items:
        flag = ""
        if it.get("keyword_hits"):
            flag = "  <-- " + ", ".join(it["keyword_hits"])
        doc = f"  // {it['doc']}" if it["doc"] else ""
        text_lines.append(f"L{it['lines'][0]}-{it['lines'][1]}  {it['signature']}{doc}{flag}")
    return {"file": rel, "symbols": items, "truncated": truncated, "text": "\n".join(text_lines)}

# ==========================================================
# DISCOVERY TOOLS -- symbol / literal search and neighbourhoods
# ==========================================================
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")
_WORD_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "when", "should", "not", "are", "was",
         "have", "has", "but", "you", "can", "does", "into", "out", "all", "any", "use", "used", "using"}


def _subwords(name: str) -> set:
    return {w.lower() for w in _CAMEL_RE.findall(name or "") if len(w) >= 3}


@mcp.tool()
def mcp_find_symbols(query: str, limit: int = 10, include_tests: bool = False) -> dict:
    """
    Ranks files (and the symbols in them) against free text: identifier names, their
    camelCase sub-words, class names, and user-facing string literals / JSX text. Meant for
    turning an issue description into starting files: an exact quoted phrase that appears
    as a string literal is the strongest signal ("Store address is required"), then exact
    symbol names, then sub-word overlap.

    Args:
        query: Free text -- an issue sentence, an error message, or a symbol name.
        limit: Maximum number of files to return.
        include_tests: Rank test files too (off by default).
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
    q = (query or "").strip()
    if not q:
        return {"error": "Empty query."}
    q_low = q.lower()
    tokens = [t for t in _WORD_RE.findall(q) if len(t) >= 2]
    tok_low = {t.lower() for t in tokens} - _STOP
    tok_sub = set()
    for t in tokens:
        tok_sub |= _subwords(t)
    tok_sub -= _STOP

    import math
    scores, why = {}, {}
    # per-file caps per evidence kind: a charting library has hundreds of `chart*` symbols in
    # one file; without a cap that file wins every query containing the word "chart"
    caps = {"symbol": 30.0, "sub": 8.0, "lit": 24.0, "litpart": 6.0, "name": 3.0}
    spent = {}
    def bump(file, pts, reason, kind):
        used = spent.setdefault(file, {}).get(kind, 0.0)
        room = caps[kind] - used
        if room <= 0:
            return
        pts = min(pts, room)
        spent[file][kind] = used + pts
        scores[file] = scores.get(file, 0.0) + pts
        why.setdefault(file, [])
        if reason not in why[file] and len(why[file]) < 6:
            why[file].append(reason)

    # document frequency of sub-words over all symbols -> rare words carry the weight
    fn_entries = [(file, fn) for file, fns in (graph.get("functions") or {}).items() for fn in fns
                  if isinstance(fn, dict) and fn.get("name") and (include_tests or not fn.get("is_test"))]
    df = {}
    for _, fn in fn_entries:
        for w in _subwords(fn["name"]) | (_subwords(fn["class"]) if fn.get("class") else set()):
            df[w] = df.get(w, 0) + 1
    n_sym = max(1, len(fn_entries))
    idf = lambda w: max(0.15, 1.0 - math.log1p(df.get(w, 0)) / math.log1p(n_sym))

    class_hits = set()
    for file, fn in fn_entries:
        name = fn["name"]
        qual = f"{fn['class']}.{name}" if fn.get("class") else name
        nl = name.lower()
        if nl in tok_low:
            # exact name match, damped for names that are everywhere (`update`, `init`)
            bump(file, 10.0 * max(0.25, idf(nl)), f"symbol {qual}", "symbol")
        elif fn.get("class") and fn["class"].lower() in tok_low:
            # a class-name match is one piece of evidence per file, not one per method
            # (class Chart has ~100 methods; the query word "chart" must not score 100x)
            if (file, fn["class"]) not in class_hits:
                class_hits.add((file, fn["class"]))
                bump(file, 6.0 * max(0.25, idf(fn["class"].lower())), f"class {fn['class']}", "symbol")
        else:
            sw = _subwords(name) | (_subwords(fn["class"]) if fn.get("class") else set())
            ov = sw & tok_sub
            if ov and (len(ov) >= 2 or (len(sw) == 1 and idf(next(iter(ov))) > 0.6)):
                pts = sum(2.0 * idf(w) for w in ov)
                bump(file, pts, f"symbol {qual} ~ {'/'.join(sorted(ov))}", "sub")
    for file, lits in (graph.get("literals") or {}).items():
        if not include_tests and any(part in {"test", "tests", "__tests__", "spec"} for part in file.split("/")[:-1]):
            continue
        for lit in lits:
            ll = lit.lower()
            if len(ll) >= 6 and ll in q_low:
                bump(file, 8.0 + min(len(ll), 40) / 8.0, f"literal {lit!r}", "lit")
            elif len(q_low) >= 8 and q_low in ll:
                bump(file, 6.0, f"literal {lit!r}", "lit")
            else:
                words = {w for w in _WORD_RE.findall(ll) if len(w) >= 3} - _STOP
                ov = words & tok_low
                if len(ov) >= 2 and len(ov) >= len(words) * 0.5:
                    bump(file, 1.5 * len(ov), f"literal {lit!r} ~ {'/'.join(sorted(ov))}", "litpart")
    # a file whose NAME contains a query word
    for file in list(scores.keys()) + [f for f in (graph.get("functions") or {}) if f not in scores]:
        base = file.rsplit("/", 1)[-1].lower()
        for t in tok_low:
            if len(t) >= 4 and t in base:
                bump(file, 3.0, f"filename ~ {t}", "name")
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:max(1, limit)]
    return {"query": q, "hits": [{"file": f, "score": round(sc, 1), "why": why[f],
                                  "symbol": next((w.split(" ", 1)[1].split(" ~")[0] for w in why[f] if w.startswith("symbol ")), "")}
                                 for f, sc in ranked]}


@mcp.tool()
def mcp_neighbors(target: str, hops: int = 1, include_tests: bool = False, limit: int = 40) -> dict:
    """
    Functions within `hops` call-edges of the target, both directions (callers and callees),
    with the file each lives in. The one-hop neighbourhood is where a fix usually lands when
    the matched file is a UI component and the real logic sits in a helper it calls.

    Args:
        target: FUNCTION:file:name (or FUNCTION:file:Class.method).
        hops: Number of call-edges to follow (1-3).
        include_tests: Include test functions.
        limit: Maximum neighbours returned.
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
        try:
            with redirect_stdout_to_stderr():
                node = resolve_target_node(graph, target, repo_root=SERVER_STATE.get("repo_path"))
        except TargetSpecError as e:
            return {"error": str(e)}
        traversal = GraphTraversal(graph)
        traversal.include_tests = include_tests
        depth = max(1, min(int(hops or 1), 3))
        with redirect_stdout_to_stderr():
            up = traversal.find_upstream_nodes(node, max_depth=depth, include_types=["FUNCTION_CALL"])
            down = traversal.find_downstream_nodes(node, max_depth=depth, include_types=["FUNCTION_CALL"])
        out, seen = [], set()
        for direction, edges, key in (("caller", up, "from"), ("callee", down, "to")):
            for e in edges:
                n = e[key]
                if n.get("type") != "FUNCTION" or not n.get("file"):
                    continue
                k = (n["file"], n.get("function"), n.get("class"))
                if k in seen:
                    continue
                seen.add(k)
                out.append({"file": n["file"], "function": n.get("function"), "class": n.get("class"),
                            "relation": direction, "depth": e.get("depth")})
        out.sort(key=lambda x: (x["depth"] or 0, x["relation"], x["file"]))
        return {"target": node, "hops": depth, "neighbors": out[:limit]}


def file_dependents(graph, rel, hops=2):
    """Files that import `rel`, directly or through re-exporting packages / barrels, up to
    `hops` import steps. -> {file: depth}."""
    rel = rel.replace("\\", "/")
    importers = {}
    for f, imps in (graph.get("imports") or {}).items():
        for imp in imps:
            if imp.get("file"):
                importers.setdefault(imp["file"], set()).add(f)
    # a package __init__ / barrel that re-exports names from rel also "imports" it
    for f, entry in (graph.get("reexports") or {}).items():
        for src in (entry.get("star") or []):
            if isinstance(src, str):
                importers.setdefault(src, set()).add(f)
        for _, v in (entry.get("names") or {}).items():
            if isinstance(v, (list, tuple)) and v and isinstance(v[0], str):
                importers.setdefault(v[0], set()).add(f)
    out, frontier = {}, {rel}
    for depth in range(1, max(1, hops) + 1):
        nxt = set()
        for f in frontier:
            for g in importers.get(f, ()):
                if g != rel and g not in out:
                    out[g] = depth
                    nxt.add(g)
        frontier = nxt
        if not frontier:
            break
    return out


@mcp.tool()
def mcp_file_dependents(file_path: str, hops: int = 2, limit: int = 50) -> dict:
    """
    Who depends on a FILE: the files that import it (directly, or through a package
    __init__ / barrel that re-exports it), split into production and test files. The
    blast radius for a change that is not inside any function -- a module-level
    constant, a regex, a table, a default -- where call edges have nothing to say.

    Args:
        file_path: Repo-relative path of the changed file.
        hops: Import steps to follow (1 = direct importers; 2 also their importers).
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
        rel = file_path.replace("\\", "/")
        known = any(rel in (graph.get(sec) or {}) for sec in ("functions", "imports", "calls", "literals")) or             any(imp.get("file") == rel for imps in (graph.get("imports") or {}).values() for imp in imps)
        if not known:
            return {"error": f"{rel} is not in the graph (unknown file, or not an indexed source file)."}
        deps = file_dependents(graph, rel, hops=max(1, min(int(hops or 2), 4)))
        test_files = {f for f, fns in (graph.get("functions") or {}).items() if any(isinstance(x, dict) and x.get("is_test") for x in fns)}
        prod = sorted((f for f in deps if f not in test_files), key=lambda f: (deps[f], f))
        tests = sorted((f for f in deps if f in test_files), key=lambda f: (deps[f], f))
        return {"file": rel, "hops": hops,
                "dependents": [{"file": f, "depth": deps[f]} for f in prod[:limit]],
                "tests": [{"file": f, "depth": deps[f]} for f in tests[:limit]],
                "total_dependents": len(prod), "total_tests": len(tests)}


@mcp.tool()
def mcp_tests_for(target: str, hops: int = 2, limit: int = 30) -> dict:
    """
    Test functions that (transitively, up to `hops`) call the target -- the tests a change
    to it must keep passing, and the place to read the expected behaviour from.

    Args:
        target: FUNCTION:file:name (or FUNCTION:file:Class.method).
        hops: Call-edges to follow upstream (1-4).
    """
    with SERVER_STATE["lock"]:
        graph = SERVER_STATE.get("graph")
        if not graph:
            return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
        try:
            with redirect_stdout_to_stderr():
                node = resolve_target_node(graph, target, repo_root=SERVER_STATE.get("repo_path"))
        except TargetSpecError as e:
            return {"error": str(e)}
        traversal = GraphTraversal(graph)
        traversal.include_tests = True
        with redirect_stdout_to_stderr():
            up = traversal.find_upstream_nodes(node, max_depth=max(1, min(int(hops or 2), 4)), include_types=["FUNCTION_CALL"])
        test_files = {f for f, fns in (graph.get("functions") or {}).items() if any(isinstance(x, dict) and x.get("is_test") for x in fns)}
        out, seen = [], set()
        for e in up:
            n = e["from"]
            if n.get("file") in test_files and (n.get("file"), n.get("function")) not in seen:
                seen.add((n.get("file"), n.get("function")))
                out.append({"file": n["file"], "function": n.get("function"), "depth": e.get("depth")})
        result = {"target": node, "tests": out[:limit], "level": "function"}
        if not out and node.get("file"):
            # no call chain reaches a test function (dynamic dispatch, fixtures the graph
            # cannot type, ...): fall back to the test FILES that import the target's file,
            # directly or through re-exporting packages. Labelled so consumers know it is
            # coarser than a call chain.
            deps = file_dependents(graph, node["file"], hops=2)
            files = sorted((f for f in deps if f in test_files), key=lambda f: (deps[f], f))
            result["level"] = "file"
            result["test_files"] = [{"file": f, "depth": deps[f], "via": "import"} for f in files[:limit]]
            result["note"] = ("No test function reaches this symbol through resolved call edges; "
                              "test_files lists test files that import its module (file-level, coarser).")
        return result


if __name__ == "__main__":
    # Start the FastMCP server (default stdio transport)
    import sys
    print("mcp server started...", file=sys.stderr)
    mcp.run()
