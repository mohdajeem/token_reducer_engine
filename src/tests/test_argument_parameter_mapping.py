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
    print("RUNNING DEDICATED TEST: ARGUMENT -> PARAMETER MAPPING")
    print("=" * 80)

    # 1. Sample code
    code = """
    import { userService } from './test.js';
    function getAllUsers(req, res) {
        const safeEmail = req.body.email;
        userService.fetchUsers(safeEmail, req.body.password);
    }
    
    // In userService.js (simulated by same file here)
    function fetchUsers(email, password) {
        User.find({ password: password });
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
    
    print("\n[ALL SEMANTIC MATCHES DETECTED]")
    for sm in semantic_matches:
        print(f"Type: {sm.match_type}, captures: {sm.captures}, owner: {sm.owner_function}")
        
    builder = GraphBuilder()
    
    # 3. Build graph
    graph = builder.build(semantic_matches)
    
    print("\n[FUNCTION INDEX FUNCTIONS]")
    print(builder.function_index.functions)
    
    print("\n[INTERMEDIATE STATE: DATA FLOW]")
    print(graph.get("data_flow"))
    
    print("\n[INTERMEDIATE STATE: TAINT SOURCES]")
    print(graph.get("taint_sources"))

    # 5. Assertions
    data_flow = graph.get("data_flow", [])
    assert len(data_flow) > 0, "Data flow is empty!"
    
    # Assert safeEmail -> email mapping
    flow1 = next((flow for flow in data_flow if flow["source"] == "safeEmail"), None)
    assert flow1 is not None, "Failed to map safeEmail to target parameter!"
    assert flow1["target_param"] == "email", f"Incorrect parameter mapped: {flow1['target_param']}"
    assert flow1["target_function"] == "fetchUsers", f"Incorrect target function: {flow1['target_function']}"
    
    # Assert req.body.password -> password mapping
    flow2 = next((flow for flow in data_flow if flow["source"] == "req.body.password"), None)
    assert flow2 is not None, "Failed to map req.body.password to target parameter!"
    assert flow2["target_param"] == "password", f"Incorrect parameter mapped: {flow2['target_param']}"
    assert flow2["target_function"] == "fetchUsers", f"Incorrect target function: {flow2['target_function']}"
    
    # Assert taint source propagation worked
    taint_sources = graph.get("taint_sources", [])
    assert len(taint_sources) > 0, "No taint sources detected!"
    taint_password = next((t for t in taint_sources if t["source"] == "req.body.password"), None)
    assert taint_password is not None, "Failed to propagate taint to fetchUsers parameter!"
    assert taint_password["target_param"] == "password", "Taint mapped to wrong parameter!"
    
    print("\n✅ ARGUMENT -> PARAMETER MAPPING test successfully passed!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_test()
