import os
import sys
from pathlib import Path
import time

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from api.mcp_server import (
    mcp_build_graph,
    mcp_query_context,
    mcp_impact_analysis,
    mcp_show_routes,
    mcp_show_graph_metrics
)

def test_mcp_tools():
    # Paths
    project_root = current_file.parent.parent.parent
    test_microservice = os.path.abspath(os.path.join(project_root, "test_microservice"))
    testing1 = os.path.abspath(r"C:\Users\ajeem\Downloads\downloads\testing\testing1")
    
    print("==================================================")
    print("Running MCP Tools Verification Assertions")
    print("==================================================")
    
    # 1. Build Graph (Full compile)
    print("Asserting: mcp_build_graph (force_rebuild=True)...")
    res = mcp_build_graph(test_microservice, force_rebuild=True)
    assert "Successfully compiled" in res, f"Expected success message, got: {res}"
    
    # 2. Build Graph (Cached load)
    print("Asserting: mcp_build_graph (force_rebuild=False)...")
    res_cached = mcp_build_graph(test_microservice, force_rebuild=False)
    assert "Successfully loaded cached" in res_cached, f"Expected cached load message, got: {res_cached}"
    
    # 3. Show metrics
    print("Asserting: mcp_show_graph_metrics...")
    metrics = mcp_show_graph_metrics()
    assert "metrics" in metrics, "Missing 'metrics' key"
    m = metrics["metrics"]
    for key in ["functions", "imports", "calls", "routes", "execution_edges", "taint_sources"]:
        assert key in m, f"Missing metric key: {key}"
        assert isinstance(m[key], int), f"Metric {key} is not an int"
    
    # 4. Show routes
    print("Asserting: mcp_show_routes...")
    routes = mcp_show_routes()
    assert "routes" in routes, "Missing 'routes' key"
    assert len(routes["routes"]) > 0, "Routes table is empty"
    
    # 5. Impact Analysis
    print("Asserting: mcp_impact_analysis...")
    impact = mcp_impact_analysis("FUNCTION:api.js:getUserById")
    assert "target" in impact, "Missing 'target' key in impact analysis"
    assert "upstream_nodes" in impact, "Missing 'upstream_nodes' key"
    assert "downstream_nodes" in impact, "Missing 'downstream_nodes' key"
    assert len(impact["upstream_nodes"]) == 1, f"Expected 1 upstream caller (route), got {len(impact['upstream_nodes'])}"
    
    # 6. Query Context (Long-form Spec)
    print("Asserting: mcp_query_context (Long-form spec)...")
    context = mcp_query_context("FUNCTION:api.js:getUserById", "DEFAULT")
    assert "code_snippets" in context, "Missing 'code_snippets' key"
    assert "relevant_files" in context, "Missing 'relevant_files' key"
    assert len(context["code_snippets"]) == 2, f"Expected 2 code snippets, got {len(context['code_snippets'])}"
    
    # 7. Query Context (Short-form Spec)
    print("Asserting: mcp_query_context (Short-form spec)...")
    context_short = mcp_query_context("FUNCTION:getUserById", "DEFAULT")
    assert len(context_short["code_snippets"]) == 2, f"Expected 2 code snippets in short spec, got {len(context_short['code_snippets'])}"
    
    # Optional test on testing1 if it exists
    if os.path.exists(testing1):
        print("\nAsserting on testing1 repository...")
        res_t1 = mcp_build_graph(testing1, force_rebuild=True)
        assert "Successfully compiled" in res_t1
        
        res_t1_cached = mcp_build_graph(testing1, force_rebuild=False)
        assert "Successfully loaded cached" in res_t1_cached
        
        metrics_t1 = mcp_show_graph_metrics()
        assert len(metrics_t1["metrics"]) > 0
        
        routes_t1 = mcp_show_routes()
        assert len(routes_t1["routes"]) > 0
        
    print("\n[SUCCESS] All MCP tools assertions passed successfully!")

if __name__ == "__main__":
    try:
        test_mcp_tools()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
