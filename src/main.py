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

def _find_qualified_function_file(repo_root, graph, class_name, actual_func):
    """
    Given "ClassName.method", find the file where THAT class's method actually lives --
    not just any file containing a same-named method. Confirmed live: resolve_target_node
    was discarding the class qualifier entirely and matching by bare method name alone,
    so any repo with the same method name in more than one class (__call__, __init__,
    run, execute -- all common) could silently return the wrong function's impact data,
    with no error. Candidate files are narrowed first via the graph's own (already-built)
    function index -- this re-parses only files that already contain a same-named
    function, not the whole repo.

    Modeled directly on context_engine.ContextExtractor.find_parent_class_name's proven
    tree-sitter ancestor-walk (parse the file, find a function_definition node, walk
    node.parent looking for class_definition) -- generalized from "first name match wins"
    to "check every name match's actual class, return the one that's really asked for."
    Python-only: every real case this was found against (sphinx, sympy, pytest) is Python,
    and this is additive -- unqualified/module-level lookups are completely unaffected.

    Returns (file_path, start_line) -- exactly one is None on failure (both None). The
    start_line is this exact occurrence's own definition line, needed on top of the file
    to disambiguate two same-named methods that live in the SAME file (the file alone
    can't tell them apart) -- see node_equals in impact_engine/graph_traversal.py.
    """
    if not repo_root:
        return None, None

    candidate_files = [
        file_path for file_path, fns in graph.get("functions", {}).items()
        if any((fn.get("name") if isinstance(fn, dict) else fn) == actual_func for fn in fns)
    ]
    if not candidate_files:
        return None, None

    from language_config import LanguageManager
    lm = LanguageManager()

    for file_path in candidate_files:
        full_path = os.path.normpath(os.path.join(repo_root, file_path))
        if not full_path.endswith(".py") or not os.path.exists(full_path):
            continue
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            parser = lm.get_parser(".py")
            if not parser:
                continue
            tree = parser.parse(bytes(content, "utf-8"))
        except Exception:
            continue

        def find_all_func_nodes(node, acc):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    try:
                        name_text = name_node.text.decode("utf-8")
                    except Exception:
                        name_text = str(name_node.text)
                    if name_text == actual_func:
                        acc.append(node)
            for child in node.children:
                find_all_func_nodes(child, acc)
            return acc

        for func_node in find_all_func_nodes(tree.root_node, []):
            p = func_node.parent
            while p:
                if p.type == "class_definition":
                    name_node = p.child_by_field_name("name")
                    if name_node:
                        try:
                            found_class = name_node.text.decode("utf-8")
                        except Exception:
                            found_class = str(name_node.text)
                        if found_class == class_name:
                            # start_point[0] is 0-indexed; +1 to match the convention
                            # used everywhere else in this codebase (e.g.
                            # graph_builder.py's "start_line": sm.start_point[0] + 1).
                            return file_path, func_node.start_point[0] + 1
                    break
                p = p.parent
    return None, None


class TargetSpecError(ValueError):
    """A target spec that cannot be resolved: malformed, unknown, or ambiguous. Raised (not
    sys.exit) so an MCP tool can report it; the message lists the candidates when ambiguous."""


def resolve_target_node(graph, target_spec, repo_root=None):
    """
    Parses a string target spec (e.g. FUNCTION:name or ROUTE:method:path)
    and resolves it to a valid node dictionary against the graph.

    repo_root is optional and defaults to None, preserving the exact existing behavior
    for any caller that doesn't pass it. When given, a qualified FUNCTION:ClassName.method
    spec is resolved via _find_qualified_function_file first (see its docstring for why);
    only if that finds nothing does resolution fall back to the original bare-name match.
    """
    parts = target_spec.split(":")
    if len(parts) < 2:
        raise TargetSpecError(f"Invalid target spec: {target_spec!r}. Expected FUNCTION:name, "
                              f"FUNCTION:file:name, FUNCTION:file:Class.method or ROUTE:method:path")

    node_type = parts[0].upper()
    if node_type == "FUNCTION":
        # Supports FUNCTION:name or FUNCTION:file_path:name
        if len(parts) == 2:
            func_name = parts[1]
            actual_func = func_name.split(".")[-1] if "." in func_name else func_name

            if "." in func_name:
                class_name = func_name.split(".")[0]
                qualified_file, qualified_line = _find_qualified_function_file(repo_root, graph, class_name, actual_func)
                if qualified_file:
                    # Confirmed live: execution_edges store ONLY bare function names (no
                    # graph-building step ever captures class qualification), and
                    # node_equals compares "function" as an exact string -- so a
                    # target_node carrying the qualified form ("Alpha.shared_method")
                    # matches ZERO edges during traversal, even once the file is
                    # correctly resolved. Returning actual_func (bare) here is what
                    # actually makes the file-level fix work end-to-end, not just look
                    # right in isolation. function_line additionally disambiguates two
                    # same-named methods in the SAME file, for node_equals to use.
                    return {
                        "type": "FUNCTION",
                        "file": qualified_file,
                        "function": actual_func,
                        "function_line": qualified_line
                    }

            # 1. Reverse symbol_index O(1) lookup. A bare name defined in several files is
            #    an ERROR listing the candidates, never a silent pick of the first: `draw`
            #    is defined in 18 Chart.js files, and an agent that edits the wrong one has
            #    no way to notice.
            symbol_index = graph.get("symbol_index", {})
            key = func_name if "." in func_name and func_name in symbol_index else actual_func
            files = list(dict.fromkeys(symbol_index.get(key) or []))
            if len(files) > 1:
                raise TargetSpecError(
                    f"Ambiguous target {target_spec!r}: {key!r} is defined in {len(files)} files. "
                    f"Qualify it as FUNCTION:<file>:{func_name} using one of: " + ", ".join(files[:12])
                    + (" ..." if len(files) > 12 else ""))
            if files:
                if "." not in func_name:
                    # one file, but several classes in it define this method (Gear.spin / Cache.spin)
                    owners = sorted({fn.get("class") for fn in graph.get("functions", {}).get(files[0], [])
                                     if isinstance(fn, dict) and fn.get("name") == actual_func and fn.get("class")})
                    if len(owners) > 1:
                        raise TargetSpecError(
                            f"Ambiguous target {target_spec!r}: {actual_func!r} is a method of {', '.join(owners)} "
                            f"in {files[0]}. Use FUNCTION:{files[0]}:<Class>.{actual_func}")
                return {
                    "type": "FUNCTION",
                    "file": files[0],
                    "function": actual_func,
                    **({"class": func_name.split(".")[0]} if "." in func_name else {}),
                }

            # 2. Iterate graph functions
            for file_path, fns in graph.get("functions", {}).items():
                for fn in fns:
                    name = fn.get("name") if isinstance(fn, dict) else fn
                    if name == actual_func:
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
            file_path = parts[1].replace("\\", "/")
            func_name = parts[2]
            actual_func = func_name.split(".")[-1] if "." in func_name else func_name

            cls = func_name.split(".")[0] if "." in func_name else None
            for registered_file in graph.get("functions", {}):
                norm_reg = registered_file.replace("\\", "/")
                if norm_reg.endswith(file_path) or file_path.endswith(norm_reg):
                    node = {
                        "type": "FUNCTION",
                        "file": registered_file,
                        # edges store the bare method name; the class travels separately
                        "function": actual_func,
                    }
                    if cls:
                        node["class"] = cls
                    else:
                        # A bare name that several classes in this file define. The file was
                        # given, so this is not fatal: the node stays class-less and matches
                        # every same-named method in the file (node_equals ignores the class
                        # when one side lacks it), and the ambiguity is reported on the node
                        # so a caller can ask again with FUNCTION:<file>:<Class>.<name>.
                        owners = sorted({fn.get("class") for fn in graph["functions"][registered_file]
                                         if isinstance(fn, dict) and fn.get("name") == actual_func and fn.get("class")})
                        if len(owners) > 1:
                            node["ambiguous_classes"] = owners
                    return node

            return {
                "type": "FUNCTION",
                "file": file_path,
                "function": func_name
            }
            
    elif node_type == "ROUTE":
        if len(parts) < 3:
            raise TargetSpecError(f"Invalid ROUTE target spec: {target_spec!r}. Expected ROUTE:method:path")
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
    elif node_type == "FILE":
        file_path = parts[1]
        resolved_path = None
        for fp in graph.get("functions", {}).keys():
            if fp == file_path or fp.replace("\\", "/").endswith(file_path.replace("\\", "/")):
                resolved_path = fp
                break
        if not resolved_path:
            for fp in graph.get("routes", {}).keys():
                if fp == file_path or fp.replace("\\", "/").endswith(file_path.replace("\\", "/")):
                    resolved_path = fp
                    break
        if not resolved_path:
            resolved_path = file_path

        return {
            "type": "FILE",
            "file": resolved_path
        }
    else:
        raise TargetSpecError(f"Unsupported node type {node_type!r} in {target_spec!r}. Supported: FUNCTION, ROUTE, FILE")


# ==========================================================
# CLI MAIN
# ==========================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Semantic Context Engine CLI")
    parser.add_argument("--dir", required=True, help="Target repository root directory")
    parser.add_argument("--build", action="store_true", help="Build semantic graph and show metrics")
    parser.add_argument("--incremental", action="store_true", help="Perform incremental build based on detected file changes")
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
