import os
import sys
import json
import contextlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal

# Add the project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from mcp.server.fastmcp import FastMCP
from build_graph import build_graph
from impact_engine import GraphTraversal, TraversalPolicy, PolicyTraversalEngine
from context_engine import ContextExtractor
from main import resolve_target_node
from incremental_runtime.snapshot_manager import SnapshotManager
from telemetry.live_telemetry import live_telemetry_manager
from telemetry.task_window_analyzer import TaskWindowAnalyzer

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
    "graph": None
}

# ==========================================================
# MCP TOOLS
# ==========================================================

@mcp.tool()
def mcp_build_graph(repo_path: str, force_rebuild: bool = False) -> str:
    """
    Builds or updates the semantic context graph for a repository.
    Loads cached index if available to optimize start latency.
    
    Args:
        repo_path: Absolute path to the repository root directory.
        force_rebuild: If True, forces a full rebuild and bypasses the cache.
    """
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        return f"Error: Repository path '{repo_path}' is not a valid directory."
        
    SERVER_STATE["repo_path"] = repo_path
    cache_dir = os.path.join(repo_path, ".semantic_cache")
    snapshot_mgr = SnapshotManager(snapshot_dir=cache_dir)
    
    # Check cache first
    if not force_rebuild:
        try:
            with redirect_stdout_to_stderr():
                cached_graph = snapshot_mgr.load_snapshot("graph")
            if cached_graph:
                SERVER_STATE["graph"] = cached_graph
                # Compute metrics
                funcs = sum(len(v) for v in cached_graph.get("functions", {}).values())
                routes = sum(len(v) for v in cached_graph.get("routes", {}).values())
                edges = len(cached_graph.get("execution_edges", []))
                return (
                    f"Successfully loaded cached graph from .semantic_cache/graph.json!\n"
                    f"Metrics:\n"
                    f"  - Functions: {funcs}\n"
                    f"  - Routes: {routes}\n"
                    f"  - Execution Edges: {edges}"
                )
        except Exception as e:
            print(f"Failed to load cached graph: {e}", file=sys.stderr)
            
    # Compile graph
    try:
        print(f"Building semantic graph for: {repo_path}...", file=sys.stderr)
        with redirect_stdout_to_stderr():
            graph = build_graph(repo_path)
            # Save cache
            snapshot_mgr.save_snapshot(graph, "graph")
            
        SERVER_STATE["graph"] = graph
        
        funcs = sum(len(v) for v in graph.get("functions", {}).values())
        routes = sum(len(v) for v in graph.get("routes", {}).values())
        edges = len(graph.get("execution_edges", []))
        return (
            f"Successfully compiled semantic graph!\n"
            f"Metrics:\n"
            f"  - Functions: {funcs}\n"
            f"  - Routes: {routes}\n"
            f"  - Execution Edges: {edges}"
        )
    except Exception as e:
        return f"Error building graph: {e}"


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
def mcp_query_context(target: str, policy: str = "DEFAULT") -> dict:
    """
    Extracts pruned code snippets, execution chains, and route context matching a target change and policy.
    
    Args:
        target: Target spec string, e.g. 'FUNCTION:src/controllers/auth.controller.js:login'
                or 'ROUTE:post:/login'.
        policy: Blast radius pruning policy: 'DEFAULT', 'LOCAL_EDIT', 'SIGNATURE_CHANGE', or 'NEW_FEATURE'.
    """
    graph = SERVER_STATE.get("graph")
    repo_path = SERVER_STATE.get("repo_path")
    
    if not graph or not repo_path:
        return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
        
    try:
        # Resolve target
        with redirect_stdout_to_stderr():
            target_node = resolve_target_node(graph, target)
        if not target_node:
            return {"error": f"Failed to resolve target node: {target}"}
            
        policy_enum = TraversalPolicy[policy.upper()]
        
        # Traversal & Extraction
        with redirect_stdout_to_stderr():
            traversal = GraphTraversal(graph)
            policy_engine = PolicyTraversalEngine(traversal)
            extractor = ContextExtractor(graph, repo_path)
            
            impact = policy_engine.resolve_impact(target_node, policy_enum)
            context = extractor.extract_context(impact)
        
        # Standardize snippet relative paths for the agent
        for snippet in context.get("code_snippets", []):
            if snippet.get("file"):
                snippet["file"] = os.path.relpath(
                    os.path.join(repo_path, snippet["file"]),
                    repo_path
                ).replace("\\", "/")
                
        # Perform shadow logging of metrics
        log_query_telemetry(repo_path, target, policy, context)
        
        return context
    except Exception as e:
        return {"error": f"Failed to query context: {e}"}


@mcp.tool()
def mcp_impact_analysis(target: str) -> dict:
    """
    Resolves the blast radius of a change to show upstream callers and downstream dependents.
    
    Args:
        target: Target spec string, e.g. 'FUNCTION:src/services/auth.service.js:loginUser'.
    """
    graph = SERVER_STATE.get("graph")
    if not graph:
        return {"error": "Graph is not built yet. Please call mcp_build_graph(repo_path) first."}
        
    try:
        with redirect_stdout_to_stderr():
            target_node = resolve_target_node(graph, target)
        if not target_node:
            return {"error": f"Failed to resolve target node: {target}"}
            
        with redirect_stdout_to_stderr():
            traversal = GraphTraversal(graph)
            upstream = traversal.find_upstream_nodes(target_node)
            downstream = traversal.find_downstream_nodes(target_node)
        
        return {
            "target": target_node,
            "upstream_edges_count": len(upstream),
            "downstream_edges_count": len(downstream),
            "upstream_nodes": [edge["from"] for edge in upstream],
            "downstream_nodes": [edge["to"] for edge in downstream]
        }
    except Exception as e:
        return {"error": f"Failed to analyze impact: {e}"}


@mcp.tool()
def mcp_show_routes() -> dict:
    """
    Returns the flat HTTP routing table registered in the repository.
    """
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


if __name__ == "__main__":
    # Start the FastMCP server (default stdio transport)
    import sys
    print("mcp server started...", file=sys.stderr)
    mcp.run()
