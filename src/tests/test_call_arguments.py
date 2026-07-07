#!/usr/bin/env python3
import sys
from pathlib import Path
from tree_sitter import QueryCursor

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from language_config import LanguageManager, LANG_CONFIG
from semantic_core.match_extractor_fixed import safe_extract_semantic_matches
from semantic_core.graph_builder import GraphBuilder

def run_test():
    print("=" * 80)
    print("RUNNING DEDICATED TEST: CALL_ARGUMENTS EXTRACTION")
    print("=" * 80)

    # 1. Sample code
    code = """
    const safeEmail = validator.escape(req.body.email);
    function testCall(a) {
        myFunction(a, 123);
    }
    """
    
    # 2. Parse code
    lm = LanguageManager()
    ext = ".js"
    parser = lm.get_parser(ext)
    query_string = lm.get_master_query(ext)
    query = LANG_CONFIG[ext]["LANGUAGE"].query(query_string)
    
    tree = parser.parse(bytes(code, "utf-8"))
    cursor = QueryCursor(query)
    matches = list(cursor.matches(tree.root_node))
    
    semantic_matches = safe_extract_semantic_matches(matches, "test.js", tree)
    
    print("\n[INTERMEDIATE STATE: SEMANTIC MATCHES]")
    for sm in semantic_matches:
        print(f"Match type: {sm.match_type}, captures: {sm.captures}, owner: {sm.owner_function}")

    # 3. Build graph
    builder = GraphBuilder()
    graph = builder.build(semantic_matches)
    
    print("\n[INTERMEDIATE STATE: GRAPH ARGUMENTS]")
    print(graph.get("arguments"))

    # 5. Assertions
    args_list = graph.get("arguments", {}).get("test.js", [])
    assert len(args_list) > 0, "No arguments extracted!"
    
    # Assert global arguments are extracted
    global_arg_entry = next((entry for entry in args_list if entry["function"] == "GLOBAL_SCOPE"), None)
    assert global_arg_entry is not None, "Global arguments not extracted!"
    assert "req.body.email" in global_arg_entry["arguments"], "Failed to extract global argument value!"
    
    # Assert scoped arguments are extracted
    scoped_arg_entry = next((entry for entry in args_list if entry["function"] == "testCall"), None)
    assert scoped_arg_entry is not None, "Scoped arguments not extracted!"
    assert "a" in scoped_arg_entry["arguments"], "Failed to extract scoped argument value!"
    
    print("\n✅ CALL_ARGUMENTS extraction test successfully passed!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_test()
