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
    print("RUNNING DEDICATED TEST: VARIABLE ASSIGNMENT TRACKING")
    print("=" * 80)

    # 1. Sample code showing global and scoped assignments with various taint/sanitized states
    code = """
    const rawPassword = req.body.password;
    
    function processUser(req) {
        const safeEmail = escape(req.body.email);
        const normalVar = "constant_value";
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
    
    print("\n[INTERMEDIATE STATE: VARIABLE STATES]")
    for vs in graph.get("variable_states", []):
        print(vs)

    # 5. Assertions
    var_states = graph.get("variable_states", [])
    assert len(var_states) > 0, "No variable states recorded!"
    
    # Assert global rawPassword assignment
    v_raw = next((v for v in var_states if v["variable"] == "rawPassword"), None)
    assert v_raw is not None, "Failed to record rawPassword variable state!"
    assert v_raw["function"] == "GLOBAL_SCOPE", f"Expected global scope, got {v_raw['function']}"
    assert v_raw["tainted"] is True, "rawPassword should be tainted!"
    assert v_raw["sanitized"] is False, "rawPassword should not be sanitized!"

    # Assert scoped safeEmail assignment
    v_email = next((v for v in var_states if v["variable"] == "safeEmail"), None)
    assert v_email is not None, "Failed to record safeEmail variable state!"
    assert v_email["function"] == "processUser", f"Expected function scope processUser, got {v_email['function']}"
    assert v_email["tainted"] is False, "safeEmail should not be tainted (sanitized)!"
    assert v_email["sanitized"] is True, "safeEmail should be sanitized!"

    # Assert scoped normalVar assignment
    v_normal = next((v for v in var_states if v["variable"] == "normalVar"), None)
    assert v_normal is not None, "Failed to record normalVar variable state!"
    assert v_normal["function"] == "processUser", f"Expected function scope processUser, got {v_normal['function']}"
    assert v_normal["tainted"] is False, "normalVar should not be tainted!"
    assert v_normal["sanitized"] is False, "normalVar should not be sanitized!"
    
    print("\n✅ VARIABLE ASSIGNMENT TRACKING test successfully passed!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_test()
