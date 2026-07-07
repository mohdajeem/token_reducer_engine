from impact_engine.graph_traversal import (
    GraphTraversal
)


class ImpactAnalysis:
    def __init__(self, graph):
        self.graph = graph
        self.traversal = (GraphTraversal(graph))

    # ======================================================
    # IMPACTED ROUTES BY DB MODEL
    # ======================================================

    def find_impacted_routes_by_db(self, model_name):
        return (
            self.traversal.find_impacted_routes_by_model(model_name)
        )

    # ======================================================
    # DOWNSTREAM CALLS
    # ======================================================

    def find_downstream_calls(self, file_path, function_name):
        target = {"type": "FUNCTION", "file": file_path, "function": function_name}

        visited = set()

        results = []

        self._dfs_downstream(
            current=target,
            visited=visited,
            results=results
        )

        return results

    # ======================================================
    # DFS DOWNSTREAM
    # ======================================================

    def _dfs_downstream(self, current, visited, results):
        key = str(current)
        if key in visited:
            return

        visited.add(key)

        for edge in self.graph["execution_edges"]:
            from_node = edge["from"]
            to_node = edge["to"]
            if self.traversal.node_equals(from_node, current):
                results.append({
                    "edge_type": edge["type"],
                    "from": from_node,
                    "to": to_node
                })

                self._dfs_downstream(
                    current=to_node,
                    visited=visited,
                    results=results
                )

    # ======================================================
    # FIND UPSTREAM DEPENDENCIES
    # ======================================================

    def find_upstream_dependencies(self, file_path, function_name):
        target = {
            "type": "FUNCTION",
            "file": file_path,
            "function": function_name
        }
        
        return (
            self.traversal
            .find_upstream_nodes(
                target
            )
        )