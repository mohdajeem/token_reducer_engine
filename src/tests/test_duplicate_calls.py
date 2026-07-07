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
    print("RUNNING DEDICATED TEST: CALL DEDUPLICATION")
    print("=" * 80)

    # 1. Sample code
    code = """
    function testCall(a) {
        myFunction(a);
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
    
    # 3. Simulate duplicate matches by duplicating the match results
    duplicated_matches = matches + matches
    print(f"Total raw matches passed (with simulated duplicates): {len(duplicated_matches)}")
    
    semantic_matches = safe_extract_semantic_matches(duplicated_matches, "test.js", tree)
    
    print("\n[INTERMEDIATE STATE: SEMANTIC MATCHES]")
    call_matches = [sm for sm in semantic_matches if sm.match_type == "CALL"]
    for sm in call_matches:
        print(f"Match type: {sm.match_type}, captures: {sm.captures}, range: {sm.start_byte}-{sm.end_byte}, owner: {sm.owner_function}")

    # 4. Assert semantic matches level deduplication
    assert len(call_matches) == 1, f"Expected exactly 1 CALL match after deduplication, got {len(call_matches)}"

    # 5. Build graph and assert graph level contains only 1 call
    builder = GraphBuilder()
    graph = builder.build(semantic_matches)
    
    calls_list = graph.get("calls", {}).get("test.js", [])
    print("\n[INTERMEDIATE STATE: GRAPH CALLS]")
    print(calls_list)
    
    assert len(calls_list) == 1, f"Expected exactly 1 call entry in graph, got {len(calls_list)}"
    assert calls_list[0]["function"] == "myFunction", f"Incorrect call function: {calls_list[0]['function']}"
    
    print("\n✅ CALL DEDUPLICATION test successfully passed!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_test()
