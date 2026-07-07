from collections import deque


class GraphTraversal:

    def __init__(self, graph):
        self.graph = graph
        self.edges = graph.get("execution_edges", [])

    # ======================================================
    # FIND UPSTREAM NODES
    # ======================================================

    def find_upstream_nodes(self, target_node):
        visited = set()
        queue = deque()
        results = []
        queue.append(target_node)

        while queue:
            current = queue.popleft()
            current_key = str(current)
            if current_key in visited:
                continue

            visited.add(current_key)

            for edge in self.edges:
                to_node = edge["to"]
                from_node = edge["from"]

                if self.node_equals(to_node, current):
                    results.append({
                        "edge_type": edge["type"],
                        "from": from_node,
                        "to": to_node
                    })
                    queue.append(from_node)

        return results

    # ======================================================
    # FIND ROUTES IMPACTED BY DB MODEL
    # ======================================================

    def find_impacted_routes_by_model(self, model_name):
        target = {
            "type": "DATABASE",
            "model": model_name
        }

        upstream = self.find_upstream_nodes(target)
        routes = []
        for edge in upstream:
            from_node = edge["from"]
            if (from_node.get("type") == "ROUTE"):
                routes.append(from_node)
        return routes

    # ======================================================
    # NODE COMPARISON
    # ======================================================

    def node_equals(self, node1, node2):
        # DATABASE MATCH
        if (node1.get("type") == "DATABASE" and node2.get("type") == "DATABASE"):
            return (
                node1.get("model") == node2.get("model")
            )

        # FUNCTION MATCH
        if (
            node1.get("type") == "FUNCTION"
            and
            node2.get("type") == "FUNCTION"
        ):
            
            return (
                node1.get("file") == node2.get("file")
                and
                node1.get("function") == node2.get("function")
            )

        # ROUTE MATCH

        if (
            node1.get("type") == "ROUTE"
            and
            node2.get("type") == "ROUTE"
        ):
            return (
                node1.get("route") == node2.get("route")
                and
                node1.get("method") == node2.get("method")
            )

        return False