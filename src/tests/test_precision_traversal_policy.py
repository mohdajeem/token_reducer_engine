import unittest
from impact_engine.graph_traversal import GraphTraversal
from impact_engine.traversal_policy import TraversalPolicy, PolicyTraversalEngine

class TestPrecisionTraversalPolicy(unittest.TestCase):
    def setUp(self):
        # Construct a multi-hop test graph:
        # Route: GET /users -> Controller: getUsers -> Service: fetchUsers -> DB: User
        self.graph = {
            "execution_edges": [
                {
                    "type": "ROUTE_CALL",
                    "from": {"type": "ROUTE", "route": "/users", "method": "GET", "file": "routes.js"},
                    "to": {"type": "FUNCTION", "function": "getUsers", "file": "controller.js"}
                },
                {
                    "type": "FUNCTION_CALL",
                    "from": {"type": "FUNCTION", "function": "getUsers", "file": "controller.js"},
                    "to": {"type": "FUNCTION", "function": "fetchUsers", "file": "service.js"}
                },
                {
                    "type": "DB_ACCESS",
                    "from": {"type": "FUNCTION", "function": "fetchUsers", "file": "service.js"},
                    "to": {"type": "DATABASE", "model": "User"}
                },
                {
                    "type": "IMPORT",
                    "from": {"type": "MODULE", "file": "controller.js"},
                    "to": {"type": "MODULE", "file": "service.js"}
                }
            ]
        }
        self.traversal = GraphTraversal(self.graph)
        self.engine = PolicyTraversalEngine(self.traversal)

    def test_local_edit_policy(self):
        target = {"type": "FUNCTION", "function": "fetchUsers", "file": "service.js"}
        impact = self.engine.resolve_impact(target, policy=TraversalPolicy.LOCAL_EDIT)
        self.assertEqual(len(impact["upstream"]), 0)
        self.assertEqual(len(impact["downstream"]), 0)

    def test_signature_change_policy_with_depth(self):
        target = {"type": "FUNCTION", "function": "fetchUsers", "file": "service.js"}
        impact = self.engine.resolve_impact(target, policy=TraversalPolicy.SIGNATURE_CHANGE, max_depth=1)
        self.assertEqual(len(impact["upstream"]), 1)
        self.assertEqual(impact["upstream"][0]["from"]["function"], "getUsers")

    def test_depth_bounded_bfs_upstream(self):
        target = {"type": "DATABASE", "model": "User"}
        # max_depth=1 should find fetchUsers (1 hop)
        hop1 = self.traversal.find_upstream_nodes(target, max_depth=1)
        self.assertEqual(len(hop1), 1)
        self.assertEqual(hop1[0]["from"]["function"], "fetchUsers")

        # max_depth=2 should find fetchUsers (hop 1) and getUsers (hop 2)
        hop2 = self.traversal.find_upstream_nodes(target, max_depth=2)
        self.assertEqual(len(hop2), 2)

    def test_dependency_only_policy(self):
        target = {"type": "MODULE", "file": "controller.js"}
        impact = self.engine.resolve_impact(target, policy=TraversalPolicy.DEPENDENCY_ONLY)
        self.assertEqual(len(impact["downstream"]), 1)
        self.assertEqual(impact["downstream"][0]["edge_type"], "IMPORT")

    def test_taint_flow_policy(self):
        target = {"type": "ROUTE", "route": "/users", "method": "GET", "file": "routes.js"}
        impact = self.engine.resolve_impact(target, policy=TraversalPolicy.TAINT_FLOW, direction="DOWNSTREAM", include_types=["ROUTE_CALL", "FUNCTION_CALL", "DB_ACCESS"])
        self.assertTrue(len(impact["downstream"]) >= 2)


if __name__ == "__main__":
    unittest.main()
