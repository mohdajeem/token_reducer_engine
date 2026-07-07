#!/usr/bin/env python3
"""
TEST 2: EXECUTION EDGES - REAL CALL CHAINS
Verifies execution edges form correct call chains from REAL project
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic_core import GraphBuilder
from semantic_core.match_extractor_fixed import safe_extract_semantic_matches
from language_config import LanguageManager
from tree_sitter import QueryCursor


class TestExecutionEdges:
    
    def __init__(self):
        self.test_dir = Path(__file__).parent.parent.parent / "test_microservice"
        self.language_manager = LanguageManager()
    
    def parse_project(self):
        """Parse all files and build semantic graph."""
        print("\n" + "=" * 80)
        print("PARSING REAL PROJECT FILES")
        print("=" * 80)
        
        builder = GraphBuilder()
        all_matches = []
        
        for file_path in sorted(self.test_dir.rglob("*.js")):
            ext = file_path.suffix
            parser = self.language_manager.get_parser(ext)
            if not parser:
                continue
            
            language = parser.language
            query_string = self.language_manager.get_master_query(ext)
            query = language.query(query_string)
            
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = parser.parse(bytes(source, "utf-8"))
            cursor = QueryCursor(query)
            matches = cursor.matches(tree.root_node)
            
            semantic_matches = safe_extract_semantic_matches(matches, str(file_path), tree)
            all_matches.extend(semantic_matches)
        
        builder.build(all_matches)
        return builder.graph
    
    def extract_edges(self):
        """Extract execution edges from graph."""
        edges = self.graph.get("execution_edges", [])
        formatted_edges = []
        
        for edge in edges:
            from_node = edge.get("from")
            to_node = edge.get("to")
            edge_type = edge.get("type")
            
            from_str = self._node_to_string(from_node)
            to_str = self._node_to_string(to_node)
            
            formatted_edges.append({
                "from": from_str,
                "to": to_str,
                "type": edge_type,
                "raw": edge,
            })
        
        return formatted_edges
    
    def _node_to_string(self, node):
        """Convert node dict to readable string."""
        if not node:
            return "None"
        
        node_type = node.get("type")
        
        if node_type == "ROUTE":
            method = node.get("method", "?").upper()
            path = node.get("route", "?")
            return f"Route({method} {path})"
        
        elif node_type == "FUNCTION":
            func_name = node.get("function") or "unnamed"
            file_path = node.get("file")
            if file_path:
                file_name = Path(file_path).name
                return f"Function({func_name} in {file_name})"
            return f"Function({func_name})"
        
        elif node_type == "DATABASE":
            model = node.get("model", "?")
            op = node.get("operation", "?")
            return f"Database({model}.{op})"
        
        else:
            return str(node)
    
    def print_execution_edges(self):
        """Print all execution edges found."""
        print("\n" + "=" * 80)
        print("EXECUTION EDGES FOUND")
        print("=" * 80)
        
        edges = self.extract_edges()
        
        if not edges:
            print("  [WARNING] No execution edges found!")
            return edges
        
        print(f"\nTotal edges: {len(edges)}\n")
        
        for i, edge in enumerate(edges, 1):
            print(f"  [{i}] {edge['from']}")
            print(f"      ↓ ({edge['type']})")
            print(f"      {edge['to']}\n")
        
        return edges
    
    def verify_expected_edges(self):
        """Verify expected execution edges exist."""
        print("\n" + "=" * 80)
        print("VERIFICATION - EXPECTED EXECUTION EDGES")
        print("=" * 80)
        
        edges = self.extract_edges()
        tests_passed = 0
        tests_failed = 0
        
        # EXPECTED EDGE 1: GET /users → getAllUsers
        print(f"\n[EXPECTED EDGE 1] GET /users → getAllUsers")
        route_to_controller = any(
            "GET /users" in e["from"] and "getAllUsers" in e["to"]
            for e in edges
        )
        if route_to_controller:
            print(f"  ✓ FOUND")
            tests_passed += 1
        else:
            print(f"  ✗ MISSING")
            edge_strs = [f"{e['from']} → {e['to']}" for e in edges[:3]]
            print(f"    Current edges: {edge_strs}")
            tests_failed += 1
        
        # EXPECTED EDGE 2: getAllUsers → fetchUsers
        print(f"\n[EXPECTED EDGE 2] getAllUsers → fetchUsers")
        controller_to_service = any(
            "getAllUsers" in e["from"] and "fetchUsers" in e["to"]
            for e in edges
        )
        if controller_to_service:
            print(f"  ✓ FOUND")
            tests_passed += 1
        else:
            print(f"  ✗ MISSING")
            tests_failed += 1
        
        # EXPECTED EDGE 3: fetchUsers → User.find (database)
        print(f"\n[EXPECTED EDGE 3] fetchUsers → Database(User.find)")
        service_to_database = any(
            "fetchUsers" in e["from"] and "Database" in e["to"]
            for e in edges
        )
        if service_to_database:
            print(f"  ✓ FOUND")
            tests_passed += 1
        else:
            print(f"  ✗ MISSING")
            tests_failed += 1
        
        # OVERALL: Check for complete chain
        print(f"\n[COMPLETE CHAIN] Route → Controller → Service → Database")
        has_chain = (route_to_controller and controller_to_service and service_to_database)
        if has_chain:
            print(f"  ✓ COMPLETE CHAIN EXISTS")
            tests_passed += 1
        else:
            print(f"  ✗ INCOMPLETE CHAIN")
            tests_failed += 1
        
        print(f"\n[TEST RESULTS]")
        print(f"  Passed: {tests_passed}/4")
        print(f"  Failed: {tests_failed}/4")
        
        return tests_failed == 0
    
    def run(self):
        """Run all tests."""
        print("\n" + "█" * 80)
        print("█ TEST 2: EXECUTION EDGES - REAL CALL CHAINS")
        print("█" * 80)
        
        self.graph = self.parse_project()
        
        edges = self.print_execution_edges()
        if not edges:
            print("\n[FAILURE] No execution edges extracted - engine broken")
            return False
        
        success = self.verify_expected_edges()
        
        print("\n" + "=" * 80)
        if success:
            print("[SUCCESS] Execution edges verified!")
        else:
            print("[FAILURE] Execution edges incomplete - see above")
        print("=" * 80)
        
        return success


if __name__ == "__main__":
    test = TestExecutionEdges()
    success = test.run()
    sys.exit(0 if success else 1)
