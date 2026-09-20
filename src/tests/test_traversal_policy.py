import os
import sys
import unittest
from pathlib import Path

# Add src/ to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from impact_engine.traversal_policy import TraversalPolicy, PolicyTraversalEngine

class MockTraversalEngine:
    def __init__(self):
        self.upstream_nodes = []
        self.downstream_nodes = []
        self.edges = []
        
    def find_upstream_nodes(self, target_node, **kwargs):
        return self.upstream_nodes
        
    def find_downstream_nodes(self, target_node, **kwargs):
        return self.downstream_nodes
        
    def node_equals(self, node1, node2):
        if not node1 or not node2:
            return False
        if node1.get("type") == "ROUTE" and node2.get("type") == "ROUTE":
            return (
                node1.get("route") == node2.get("route") and 
                node1.get("method", "").lower() == node2.get("method", "").lower()
            )
        return (
            node1.get("file") == node2.get("file") and 
            node1.get("function") == node2.get("function")
        )


class TestTraversalPolicy(unittest.TestCase):
    
    def setUp(self):
        self.mock_engine = MockTraversalEngine()
        self.policy_engine = PolicyTraversalEngine(self.mock_engine)
        self.target = {"type": "FUNCTION", "file": "controllers/userController.js", "function": "getAllUsers"}
        
    def test_local_edit_policy(self):
        # Setup mock data that would normally be returned by standard traversal
        self.mock_engine.upstream_nodes = [
            {"edge_type": "ROUTE_CALL", "from": {"type": "ROUTE", "route": "/users"}, "to": self.target}
        ]
        self.mock_engine.downstream_nodes = [
            {"edge_type": "FUNCTION_CALL", "from": self.target, "to": {"type": "FUNCTION", "file": "services/userService.js", "function": "fetchUsers"}}
        ]
        
        result = self.policy_engine.resolve_impact(self.target, TraversalPolicy.LOCAL_EDIT)
        
        self.assertEqual(result["target"], self.target)
        self.assertEqual(result["upstream"], [])
        self.assertEqual(result["downstream"], [])
        
    def test_signature_change_policy(self):
        # Target node
        target = self.target
        
        # 1-hop caller: A calling Target
        caller_1hop = {"type": "FUNCTION", "file": "api.js", "function": "apiHandler"}
        edge_1hop = {"edge_type": "FUNCTION_CALL", "from": caller_1hop, "to": target}
        
        # 2-hop caller: B calling A
        caller_2hop = {"type": "FUNCTION", "file": "server.js", "function": "startServer"}
        edge_2hop = {"edge_type": "FUNCTION_CALL", "from": caller_2hop, "to": caller_1hop}
        
        self.mock_engine.upstream_nodes = [edge_1hop, edge_2hop]
        self.mock_engine.downstream_nodes = [
            {"edge_type": "FUNCTION_CALL", "from": target, "to": {"type": "FUNCTION", "file": "services/userService.js", "function": "fetchUsers"}}
        ]
        
        result = self.policy_engine.resolve_impact(target, TraversalPolicy.SIGNATURE_CHANGE)
        
        self.assertEqual(result["target"], target)
        self.assertEqual(result["downstream"], [])
        # Should only contain direct (1-hop) caller where to == target
        self.assertEqual(len(result["upstream"]), 1)
        self.assertEqual(result["upstream"][0]["from"], caller_1hop)
        
    def test_default_policy(self):
        # Setup mock data
        self.mock_engine.upstream_nodes = [
            {"edge_type": "ROUTE_CALL", "from": {"type": "ROUTE", "route": "/users"}, "to": self.target}
        ]
        self.mock_engine.downstream_nodes = [
            {"edge_type": "FUNCTION_CALL", "from": self.target, "to": {"type": "FUNCTION", "file": "services/userService.js", "function": "fetchUsers"}}
        ]
        
        result = self.policy_engine.resolve_impact(self.target, TraversalPolicy.DEFAULT)
        
        self.assertEqual(result["target"], self.target)
        self.assertEqual(result["upstream"], self.mock_engine.upstream_nodes)
        self.assertEqual(result["downstream"], self.mock_engine.downstream_nodes)

    def test_invalid_policy_fallback_to_default(self):
        self.mock_engine.upstream_nodes = [{"edge_type": "ROUTE_CALL", "from": "foo", "to": "bar"}]
        self.mock_engine.downstream_nodes = [{"edge_type": "FUNCTION_CALL", "from": "bar", "to": "baz"}]
        
        # Pass a string or invalid type - should fallback to DEFAULT
        result = self.policy_engine.resolve_impact(self.target, "INVALID_POLICY")
        
        self.assertEqual(result["target"], self.target)
        self.assertEqual(result["upstream"], self.mock_engine.upstream_nodes)
        self.assertEqual(result["downstream"], self.mock_engine.downstream_nodes)

    def test_new_feature_policy(self):
        # Target node (Service)
        service = {"type": "FUNCTION", "file": "services/userService.js", "function": "fetchUsers"}
        controller = {"type": "FUNCTION", "file": "controllers/userController.js", "function": "getAllUsers"}
        route = {"type": "ROUTE", "route": "/users", "method": "get", "file": "api.js"}
        database = {"type": "DATABASE", "model": "User"}
        
        # Sibling route calling a different controller
        sibling_route = {"type": "ROUTE", "route": "/login", "method": "post", "file": "api.js"}
        sibling_controller = {"type": "FUNCTION", "file": "controllers/authController.js", "function": "login"}
        
        # Edges definition
        edge1 = {"type": "ROUTE_CALL", "from": route, "to": controller}
        edge2 = {"type": "FUNCTION_CALL", "from": controller, "to": service}
        edge3 = {"type": "DB_ACCESS", "from": service, "to": database}
        edge_sib = {"type": "ROUTE_CALL", "from": sibling_route, "to": sibling_controller}
        
        self.mock_engine.edges = [edge1, edge2, edge3, edge_sib]
        
        # Resolve impact using NEW_FEATURE policy
        result = self.policy_engine.resolve_impact(service, TraversalPolicy.NEW_FEATURE)
        
        self.assertEqual(result["target"], service)
        
        downstream = result["downstream"]
        self.assertIn(edge1, downstream)
        self.assertIn(edge2, downstream)
        self.assertIn(edge3, downstream)
        self.assertNotIn(edge_sib, downstream)


if __name__ == "__main__":
    unittest.main()

