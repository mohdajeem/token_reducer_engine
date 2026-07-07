from collections import deque


class GraphTraversal:
    """
    Breadth-First Search (BFS) graph traversal engine that computes caller dependency chains 
    forward (downstream dependents) and backward (upstream callers) across compiled execution edges.
    """

    def __init__(self, graph):
        """
        Initializes the GraphTraversal engine with the compiled semantic graph.
        
        Args:
            graph (Dict): The queryable semantic graph constructed by GraphBuilder.
        """
        self.graph = graph
        self.edges = graph.get("execution_edges", [])

    # ======================================================
    # FIND UPSTREAM NODES
    # ======================================================

    def find_upstream_nodes(self, target_node):
        """
        Performs a backward BFS traversal from the target node to locate all upstream callers.
        
        Args:
            target_node (Dict): The target function or route node mapping to trace.
            
        Returns:
            List[Dict]: List of connected edges representing the upstream dependency path.
        """
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
    # FIND DOWNSTREAM NODES
    # ======================================================

    def find_downstream_nodes(self, target_node):
        """
        Performs a forward BFS traversal from the target node to locate all downstream dependents.
        
        Args:
            target_node (Dict): The target node to trace forward dependencies from.
            
        Returns:
            List[Dict]: List of connected edges representing the downstream dependency path.
        """
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

                if self.node_equals(from_node, current):
                    results.append({
                        "edge_type": edge["type"],
                        "from": from_node,
                        "to": to_node
                    })
                    queue.append(to_node)

        return results

    # ======================================================
    # FIND ROUTES IMPACTED BY DB MODEL
    # ======================================================

    def find_impacted_routes_by_model(self, model_name):
        """
        Locates all route nodes that are impacted upstream by changes to a database model.
        
        Args:
            model_name (str): The name of the database model to trace.
            
        Returns:
            List[Dict]: List of ROUTE nodes that interact with or are downstream from the model.
        """
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
        """
        Compares two node structures for semantic equality based on their types and identifiers.
        
        Args:
            node1 (Dict): The first node to compare.
            node2 (Dict): The second node to compare.
            
        Returns:
            bool: True if the nodes represent the identical semantic entity, False otherwise.
        """
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
            import os
            file1 = os.path.normpath(str(node1.get("file"))).replace("\\", "/") if node1.get("file") else None
            file2 = os.path.normpath(str(node2.get("file"))).replace("\\", "/") if node2.get("file") else None
            
            return (
                file1 == file2
                and
                node1.get("function") == node2.get("function")
            )

        # MIDDLEWARE MATCH
        if (
            node1.get("type") == "MIDDLEWARE"
            and
            node2.get("type") == "MIDDLEWARE"
        ):
            import os
            file1 = os.path.normpath(str(node1.get("file"))).replace("\\", "/") if node1.get("file") else None
            file2 = os.path.normpath(str(node2.get("file"))).replace("\\", "/") if node2.get("file") else None
            
            return (
                file1 == file2
                and
                node1.get("function") == node2.get("function")
            )

        # ROUTE MATCH

        if (
            node1.get("type") == "ROUTE"
            and
            node2.get("type") == "ROUTE"
        ):
            import os
            file1 = os.path.normpath(str(node1.get("file"))).replace("\\", "/") if node1.get("file") else ""
            file2 = os.path.normpath(str(node2.get("file"))).replace("\\", "/") if node2.get("file") else ""
            
            if file1 and file2 and file1 != file2:
                return False
                
            return (
                node1.get("route") == node2.get("route")
                and
                node1.get("method") == node2.get("method")
            )

        return False