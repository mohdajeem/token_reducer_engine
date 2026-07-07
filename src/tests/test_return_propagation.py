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
    print("RUNNING DEDICATED TEST: RETURN PROPAGATION")
    print("=" * 80)

    # 1. Sample code showing return User.find(...) and return service.fetch(...)
    code = """
    function getUserData(userId) {
        return User.find({ id: userId });
    }
    
    function fetchServiceData(service) {
        return service.fetch("some_endpoint");
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
    
    print("\n[INTERMEDIATE STATE: RETURNS]")
    print(graph.get("returns"))

    # 5. Assertions
    returns = graph.get("returns", [])
    assert len(returns) == 2, f"Expected 2 return values, got {len(returns)}"
    
    # Assert return from getUserData
    ret1 = next((r for r in returns if r["function"] == "getUserData"), None)
    assert ret1 is not None, "Failed to find return from getUserData"
    assert "User.find" in ret1["value"], f"Incorrect return value for getUserData: {ret1['value']}"
    
    # Assert return from fetchServiceData
    ret2 = next((r for r in returns if r["function"] == "fetchServiceData"), None)
    assert ret2 is not None, "Failed to find return from fetchServiceData"
    assert "service.fetch" in ret2["value"], f"Incorrect return value for fetchServiceData: {ret2['value']}"
    
    print("\n✅ RETURN PROPAGATION test successfully passed!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_test()
