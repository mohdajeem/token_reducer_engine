from enum import Enum

class TraversalPolicy(Enum):
    DEFAULT = "DEFAULT"
    LOCAL_EDIT = "LOCAL_EDIT"
    SIGNATURE_CHANGE = "SIGNATURE_CHANGE"
    NEW_FEATURE = "NEW_FEATURE"
    TAINT_FLOW = "TAINT_FLOW"
    DEPENDENCY_ONLY = "DEPENDENCY_ONLY"
    # Aliases: several benchmark harnesses tag tasks with these two names, which
    # aren't distinct traversal strategies of their own. Without them,
    # TraversalPolicy["BUG_FIX"] / ["FEATURE_ADDITION"] raise KeyError, the caller's
    # broad except swallows it, and mcp_query_context silently returns {"error": ...}
    # with zero code context for every task tagged this way.
    BUG_FIX = "DEFAULT"
    FEATURE_ADDITION = "NEW_FEATURE"

class PolicyTraversalEngine:
    """
    Wrapper around the GraphTraversal engine that applies policies 
    to filter and prune control-flow paths based on user intent.
    """
    def __init__(self, traversal_engine):
        self.traversal_engine = traversal_engine

    def resolve_impact(
        self,
        target_node: dict,
        policy: TraversalPolicy = TraversalPolicy.DEFAULT,
        max_depth=None,
        direction="BOTH",
        include_types=None,
        include_tests=False,
        min_confidence=None,
    ) -> dict:
        """
        Runs the traversal engine and filters the upstream/downstream edges 
        according to the selected policy, depth limits, direction, and edge types.
        """
        self.traversal_engine.min_confidence = min_confidence
        if not isinstance(policy, TraversalPolicy):
            try:
                policy = TraversalPolicy(str(policy).upper())
            except ValueError:
                policy = TraversalPolicy.DEFAULT
        self.traversal_engine.include_tests = bool(include_tests)

        if policy == TraversalPolicy.LOCAL_EDIT:
            return {
                "target": target_node,
                "upstream": [],
                "downstream": []
            }

        elif policy == TraversalPolicy.DEPENDENCY_ONLY:
            types_filter = include_types or ["IMPORT", "CONTRACT", "MODULE_DEPENDENCY"]
            upstream = self.traversal_engine.find_upstream_nodes(target_node, max_depth=max_depth or 1, include_types=types_filter) if direction in ("UPSTREAM", "BOTH") else []
            downstream = self.traversal_engine.find_downstream_nodes(target_node, max_depth=max_depth or 1, include_types=types_filter) if direction in ("DOWNSTREAM", "BOTH") else []
            return {
                "target": target_node,
                "upstream": upstream,
                "downstream": downstream
            }

        elif policy == TraversalPolicy.SIGNATURE_CHANGE:
            # a changed signature breaks the callers, not the callees: direct callers by
            # default (deeper only when asked), callees only when explicitly asked for
            effective_depth = max_depth if max_depth is not None else 1
            all_upstream = self.traversal_engine.find_upstream_nodes(target_node, max_depth=effective_depth, include_types=include_types) if direction in ("UPSTREAM", "BOTH") else []
            if max_depth is None:
                all_upstream = [e for e in all_upstream if self.traversal_engine.node_equals(e.get("to") or {}, target_node)]
            all_downstream = self.traversal_engine.find_downstream_nodes(target_node, max_depth=effective_depth, include_types=include_types) if direction == "DOWNSTREAM" else []
            return {
                "target": target_node,
                "upstream": all_upstream,
                "downstream": all_downstream
            }

        elif policy == TraversalPolicy.TAINT_FLOW:
            types_filter = include_types or ["FUNCTION_CALL", "DB_ACCESS", "SECURITY_SINK", "TAINT_PROPAGATION"]
            downstream = self.traversal_engine.find_downstream_nodes(target_node, max_depth=max_depth, include_types=types_filter) if direction in ("DOWNSTREAM", "BOTH") else []
            upstream = self.traversal_engine.find_upstream_nodes(target_node, max_depth=max_depth, include_types=types_filter) if direction in ("UPSTREAM", "BOTH") else []
            return {
                "target": target_node,
                "upstream": upstream,
                "downstream": downstream
            }

        elif policy == TraversalPolicy.NEW_FEATURE:
            from collections import deque

            def get_node_key(node):
                if not node:
                    return ""
                ntype = node.get("type")
                if ntype == "DATABASE":
                    return f"DATABASE:{node.get('model')}"
                elif ntype in ("FUNCTION", "MIDDLEWARE"):
                    import os
                    fpath = os.path.normpath(str(node.get("file"))).replace("\\", "/") if node.get("file") else ""
                    return f"{ntype}:{fpath}:{node.get('function')}"
                elif ntype == "ROUTE":
                    return f"ROUTE:{node.get('route')}:{node.get('method', '').lower()}"
                else:
                    return str(node)

            # 1. Collect target routes
            routes = []
            if target_node.get("type") in ("FUNCTION", "MIDDLEWARE"):
                queue = deque([(target_node, [])])
                visited = set()
                found_routes = []
                min_hops = None

                while queue:
                    current, path = queue.popleft()
                    current_key = get_node_key(current)
                    if current_key in visited:
                        continue
                    visited.add(current_key)

                    if current.get("type") == "ROUTE":
                        if min_hops is None:
                            min_hops = len(path)
                        if len(path) == min_hops:
                            found_routes.append((current, path))
                        continue

                    if min_hops is not None and len(path) >= min_hops:
                        continue

                    for edge in self.traversal_engine.edges:
                        if include_types and edge["type"] not in include_types:
                            continue
                        if self.traversal_engine.node_equals(edge["to"], current):
                            queue.append((edge["from"], path + [edge]))

                if found_routes:
                    routes.append(found_routes[0][0])
            elif target_node.get("type") == "ROUTE":
                routes.append(target_node)

            if not routes and target_node.get("file"):
                for edge in self.traversal_engine.edges:
                    for node in [edge["from"], edge["to"]]:
                        if node.get("type") == "ROUTE" and node.get("file") == target_node["file"]:
                            if node not in routes:
                                routes.append(node)

            slice_edges = []
            visited_nodes = set()

            for r in routes:
                route_key = get_node_key(r)
                if route_key in visited_nodes:
                    continue
                visited_nodes.add(route_key)

                for edge in self.traversal_engine.edges:
                    if include_types and edge["type"] not in include_types:
                        continue
                    if self.traversal_engine.node_equals(edge["from"], r):
                        slice_edges.append(edge)
                        to_node = edge["to"]

                        if to_node.get("type") == "FUNCTION":
                            controller_key = get_node_key(to_node)
                            if controller_key not in visited_nodes:
                                visited_nodes.add(controller_key)

                                for c_edge in self.traversal_engine.edges:
                                    if include_types and c_edge["type"] not in include_types:
                                        continue
                                    if c_edge["type"] == "FUNCTION_CALL" and self.traversal_engine.node_equals(c_edge["from"], to_node):
                                        slice_edges.append(c_edge)
                                        service_node = c_edge["to"]

                                        service_key = get_node_key(service_node)
                                        if service_key not in visited_nodes:
                                            visited_nodes.add(service_key)

                                            for s_edge in self.traversal_engine.edges:
                                                if include_types and s_edge["type"] not in include_types:
                                                    continue
                                                if s_edge["type"] == "DB_ACCESS" and self.traversal_engine.node_equals(s_edge["from"], service_node):
                                                    slice_edges.append(s_edge)

            if not routes:
                for edge in self.traversal_engine.edges:
                    if include_types and edge["type"] not in include_types:
                        continue
                    if self.traversal_engine.node_equals(edge["from"], target_node) or self.traversal_engine.node_equals(edge["to"], target_node):
                        slice_edges.append(edge)

            return {
                "target": target_node,
                "upstream": [],
                "downstream": slice_edges
            }

        else: # DEFAULT
            upstream = self.traversal_engine.find_upstream_nodes(target_node, max_depth=max_depth, include_types=include_types) if direction in ("UPSTREAM", "BOTH") else []
            downstream = self.traversal_engine.find_downstream_nodes(target_node, max_depth=max_depth, include_types=include_types) if direction in ("DOWNSTREAM", "BOTH") else []
            return {
                "target": target_node,
                "upstream": upstream,
                "downstream": downstream
            }


