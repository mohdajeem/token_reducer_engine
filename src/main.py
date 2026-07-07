# ==========================================================
# SEMANTIC CONTEXT ENGINE - MAIN ENTRY
# ==========================================================
# This is the unified CLI entry point for the semantic engine.
# It supports building semantic graphs, querying target nodes,
# resolving impact traversal policies, and exporting AI context.

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from build_graph import build_graph
from impact_engine import GraphTraversal, TraversalPolicy, PolicyTraversalEngine, TaintTraversalEngine
from context_engine import ContextExtractor
from language_config import LANG_CONFIG, LanguageManager, IGNORE_DIRS
from utils.logger import set_debug
from config.settings import DEBUG_GRAPH_BUILD

if DEBUG_GRAPH_BUILD:
    set_debug()


# ==========================================================
# BACKWARD COMPATIBILITY HELPERS
# ==========================================================

def build_semantic_graph(target_dir):
    """Legacy wrapper for building semantic graph."""
    return build_graph(target_dir)


def analyze_impact(graph, file_path, function_name):
    """Legacy wrapper for analyzing impact."""
    traversal = GraphTraversal(graph)
    target = {
        "type": "FUNCTION",
        "file": file_path,
        "function": function_name
    }
    upstream = traversal.find_upstream_nodes(target)
    return {
        "upstream": upstream,
        "target": target
    }


def extract_context_for_ai(graph, impact_result):
    """Legacy wrapper for context extraction."""
    extractor = ContextExtractor(graph, ".")
    return extractor.extract_context(impact_result)


# ==========================================================
# TARGET NODE RESOLUTION
# ==========================================================

def resolve_target_node(graph, target_spec):
    """
    Parses a string target spec (e.g. FUNCTION:name or ROUTE:method:path)
    and resolves it to a valid node dictionary against the graph.
    """
    parts = target_spec.split(":")
    if len(parts) < 2:
        print(f"❌ Invalid target spec: {target_spec}. Expected format: FUNCTION:name or ROUTE:method:path")
        sys.exit(1)
        
    node_type = parts[0].upper()
    if node_type == "FUNCTION":
        # Supports FUNCTION:name or FUNCTION:file_path:name
        if len(parts) == 2:
            func_name = parts[1]
            for file_path, fns in graph.get("functions", {}).items():
                for fn in fns:
                    name = fn.get("name") if isinstance(fn, dict) else fn
                    if name == func_name:
                        return {
                            "type": "FUNCTION",
                            "file": file_path,
                            "function": func_name
                        }
            # Fallback to general spec
            return {
                "type": "FUNCTION",
                "file": "",
                "function": func_name
            }
        else:
            file_path = parts[1]
            func_name = parts[2]
            return {
                "type": "FUNCTION",
                "file": file_path,
                "function": func_name
            }
            
    elif node_type == "ROUTE":
        if len(parts) < 3:
            print(f"❌ Invalid ROUTE target spec: {target_spec}. Expected format: ROUTE:method:path")
            sys.exit(1)
        method = parts[1].lower()
        route_path = parts[2]
        
        # Try matching in edges first
        for edge in graph.get("execution_edges", []):
            for node in [edge["from"], edge["to"]]:
                if (node.get("type") == "ROUTE" and 
                    node.get("route") == route_path and 
                    node.get("method", "").lower() == method):
                    return node
                    
        # Try matching in routes
        for file_path, routes in graph.get("routes", {}).items():
            for r in routes:
                if (r.get("path") == route_path and 
                    r.get("method", "").lower() == method):
                    return {
                        "type": "ROUTE",
                        "route": route_path,
                        "method": method,
                        "file": file_path
                    }
                    
        # Fallback to general spec
        return {
            "type": "ROUTE",
            "route": route_path,
            "method": method,
            "file": ""
        }
    else:
        print(f"❌ Unsupported node type: {node_type}. Supported types: FUNCTION, ROUTE")
        sys.exit(1)


# ==========================================================
# CLI MAIN
# ==========================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Semantic Context Engine CLI")
    parser.add_argument("--dir", required=True, help="Target repository root directory")
    parser.add_argument("--build", action="store_true", help="Build semantic graph and show metrics")
    parser.add_argument("--target", help="Blast radius target node spec, e.g. FUNCTION:login or ROUTE:get:/users")
    parser.add_argument("--policy", choices=["DEFAULT", "LOCAL_EDIT", "SIGNATURE_CHANGE", "NEW_FEATURE"], default="DEFAULT", help="Traversal policy")
    parser.add_argument("--out", help="Path to write the context JSON output")
    parser.add_argument("--show-code", action="store_true", help="Print the actual extracted snippet bodies to stdout")
    
    args = parser.parse_args()
    
    target_dir = os.path.abspath(args.dir)
    if not os.path.exists(target_dir):
        print(f"❌ Target directory not found: {target_dir}")
        sys.exit(1)
        
    print(f"\nBuilding semantic graph for: {target_dir}...")
    graph = build_graph(target_dir)
    
    # Compute counts
    functions_count = sum(len(v) for v in graph.get("functions", {}).values())
    imports_count = sum(len(v) for v in graph.get("imports", {}).values())
    calls_count = sum(len(v) for v in graph.get("calls", {}).values())
    routes_count = sum(len(v) for v in graph.get("routes", {}).values())
    edges_count = len(graph.get("execution_edges", []))
    taints_count = len(graph.get("taint_sources", []))
    
    print("\n" + "="*80)
    print("✅ SEMANTIC ENGINE READY")
    print("="*80)
    print(f"Graph Metrics:")
    print(f"  - Functions:       {functions_count}")
    print(f"  - Imports:         {imports_count}")
    print(f"  - Call Sites:      {calls_count}")
    print(f"  - Routes:          {routes_count}")
    print(f"  - Execution Edges: {edges_count}")
    print(f"  - Taint Sources:   {taints_count}")
    print("="*80)
    
    if args.target:
        print(f"\nResolving target node: {args.target}...")
        target_node = resolve_target_node(graph, args.target)
        print(f"Target node resolved to: {target_node}")
        
        # Policy traversal & extraction
        policy = TraversalPolicy[args.policy]
        print(f"Running traversal under policy: {policy.name}...")
        
        traversal = GraphTraversal(graph)
        policy_engine = PolicyTraversalEngine(traversal)
        extractor = ContextExtractor(graph, target_dir)
        
        impact = policy_engine.resolve_impact(target_node, policy)
        context = extractor.extract_context(impact)
        
        # Print summary of context
        print("\n" + "="*80)
        print("🧠 CONTEXT EXTRACTION RESULTS")
        print("="*80)
        print(f"  - Relevant Files:     {len(context['relevant_files'])}")
        print(f"  - Relevant Functions: {len(context['relevant_functions'])}")
        print(f"  - Code Snippets:      {len(context['code_snippets'])}")
        
        if context['relevant_files']:
            print("\nSelected Files:")
            for rf in context['relevant_files']:
                print(f"  - {rf}")
                
        if context['code_snippets']:
            print("\nCode Snippets Extracted:")
            for snip in context['code_snippets']:
                print(f"  - File: {snip['file']} | Function: {snip['function']}")
                
        print("="*80)
        
        if args.show_code and context.get('code_snippets'):
            for idx, snip in enumerate(context['code_snippets'], 1):
                print(f"\n========================================================")
                print(f"SNIPPET {idx}")
                print(f"File: {snip['file']}")
                func_name = snip.get('function', '')
                if func_name.startswith("ROUTE ") or func_name.startswith("SCHEMA "):
                    label = f"Type: {func_name}"
                else:
                    label = f"Function: {func_name}"
                print(label)
                print("=" * len(label))
                print(f"\n{snip.get('code', '')}")
        
        if args.out:
            out_path = os.path.abspath(args.out)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=2)
            print(f"\n✓ Saved context extraction results to: {out_path}")


if __name__ == "__main__":
    main()
