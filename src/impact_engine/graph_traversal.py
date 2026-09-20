from collections import deque

# How much to trust an edge, highest first. "observed": seen in a dynamic trace (or a static
# edge the trace confirmed). "resolved": a plain static resolution. "name-unique" /
# "candidates" / "dispatch" / "dynamic": a static guess with several possible targets.
# "unobserved": one of those guesses that the trace contradicted (the caller ran, and
# called a sibling candidate instead).
CONFIDENCE_RANK = {"observed": 4, "resolved": 3, "name-unique": 2, "candidates": 2, "dispatch": 2, "dynamic": 2,
                   "convention": 2, "nested": 2, "uses": 3, "unobserved": 1}


def edge_confidence(edge):
    if edge.get("observed") or edge.get("source") == "trace":
        return "observed"
    return edge.get("confidence") or "resolved"


def edge_rank(edge):
    return CONFIDENCE_RANK.get(edge_confidence(edge), 2)


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
        # Test-partition edges (from a test function) are hidden by default: an impact
        # query answers "what production code depends on this"; tests are surfaced on
        # request (include_tests=True / mcp_tests_for).
        self.include_tests = False
        # minimum confidence an edge needs to be followed (None = follow everything);
        # a consumer that wants only certain callers asks for "resolved" and widens if empty
        self.min_confidence = None

    # ======================================================
    # FIND UPSTREAM NODES
    # ======================================================

    def find_upstream_nodes(self, target_node, max_depth=None, include_types=None, include_tests=None, min_confidence=None):
        """
        Performs a backward BFS traversal from the target node to locate upstream callers.
        
        Args:
            target_node (Dict): The target function or route node mapping to trace.
            max_depth (Optional[int]): Maximum traversal depth (number of hops).
            include_types (Optional[List[str]]): List of edge types to include (e.g. ['FUNCTION_CALL']).
            
        Returns:
            List[Dict]: List of connected edges representing the upstream dependency path.
        """
        visited = set()
        queue = deque()
        results = []
        queue.append((target_node, 0))

        while queue:
            current, depth = queue.popleft()
            current_key = str(current)
            if current_key in visited:
                continue

            visited.add(current_key)

            if max_depth is not None and depth >= max_depth:
                continue

            for edge in self.edges:
                if include_types and edge["type"] not in include_types:
                    continue
                if edge.get("is_test") and not (self.include_tests if include_tests is None else include_tests):
                    continue
                _minc = self.min_confidence if min_confidence is None else min_confidence
                if _minc and edge_rank(edge) < CONFIDENCE_RANK.get(_minc, 0):
                    continue

                to_node = edge["to"]
                from_node = edge["from"]

                if self.node_equals(to_node, current):
                    edge_dict = {
                        "edge_type": edge["type"],
                        "from": from_node,
                        "to": to_node,
                        "depth": depth + 1
                    }
                    if edge.get("confidence"):
                        edge_dict["confidence"] = edge["confidence"]  # name-unique / candidates / observed
                    if edge.get("is_test"):
                        edge_dict["is_test"] = True
                    for k in ("source", "observed", "stale", "via"):
                        if edge.get(k):
                            edge_dict[k] = edge[k]  # dynamic-trace provenance survives traversal
                    if edge_dict not in results:
                        results.append(edge_dict)
                    queue.append((from_node, depth + 1))

        return results

    # ======================================================
    # FIND DOWNSTREAM NODES
    # ======================================================

    def find_downstream_nodes(self, target_node, max_depth=None, include_types=None, include_tests=None, min_confidence=None):
        """
        Performs a forward BFS traversal from the target node to locate downstream dependents.
        
        Args:
            target_node (Dict): The target node to trace forward dependencies from.
            max_depth (Optional[int]): Maximum traversal depth (number of hops).
            include_types (Optional[List[str]]): List of edge types to include.
            
        Returns:
            List[Dict]: List of connected edges representing the downstream dependency path.
        """
        visited = set()
        queue = deque()
        results = []
        queue.append((target_node, 0))

        while queue:
            current, depth = queue.popleft()
            current_key = str(current)
            if current_key in visited:
                continue

            visited.add(current_key)

            if max_depth is not None and depth >= max_depth:
                continue

            for edge in self.edges:
                if include_types and edge["type"] not in include_types:
                    continue
                if edge.get("is_test") and not (self.include_tests if include_tests is None else include_tests):
                    continue
                _minc = self.min_confidence if min_confidence is None else min_confidence
                if _minc and edge_rank(edge) < CONFIDENCE_RANK.get(_minc, 0):
                    continue

                to_node = edge["to"]
                from_node = edge["from"]

                if self.node_equals(from_node, current):
                    edge_dict = {
                        "edge_type": edge["type"],
                        "from": from_node,
                        "to": to_node,
                        "depth": depth + 1
                    }
                    if edge.get("confidence"):
                        edge_dict["confidence"] = edge["confidence"]  # name-unique / candidates / observed
                    if edge.get("is_test"):
                        edge_dict["is_test"] = True
                    for k in ("source", "observed", "stale", "via"):
                        if edge.get(k):
                            edge_dict[k] = edge[k]  # dynamic-trace provenance survives traversal
                    if edge_dict not in results:
                        results.append(edge_dict)
                    queue.append((to_node, depth + 1))

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

            base_match = (
                file1 == file2
                and
                node1.get("function") == node2.get("function")
            )
            if not base_match:
                return False

            # Same-named methods of two classes in one file (Engine.tick vs Other.tick):
            # when BOTH sides carry an owning class, it must match. Either side missing it
            # falls back to the file+name comparison, so this only ever narrows.
            c1 = node1.get("class")
            c2 = node2.get("class")
            if c1 and c2 and c1 != c2:
                return False

            # Two same-named methods in the SAME file are indistinguishable by file +
            # name alone. When BOTH sides carry a function_line (the specific
            # occurrence's own definition line -- see resolve_target_node and
            # graph_builder.py's edge construction), require it to match too. Either
            # side missing it (the common case -- most edges don't carry this field)
            # falls back to exactly today's file+name-only comparison, so this can only
            # ever narrow an existing match, never break one that worked before.
            line1 = node1.get("function_line")
            line2 = node2.get("function_line")
            if line1 is not None and line2 is not None:
                return line1 == line2
            return True

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

        # FILE / MODULE MATCH
        if (node1.get("type") in ("FILE", "MODULE") and node2.get("type") in ("FILE", "MODULE")):
            import os
            file1 = os.path.normpath(str(node1.get("file"))).replace("\\", "/") if node1.get("file") else ""
            file2 = os.path.normpath(str(node2.get("file"))).replace("\\", "/") if node2.get("file") else ""
            return file1 == file2

        return False
