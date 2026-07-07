from enum import Enum

class TraversalPolicy(Enum):
    DEFAULT = "DEFAULT"
    LOCAL_EDIT = "LOCAL_EDIT"
    SIGNATURE_CHANGE = "SIGNATURE_CHANGE"
    NEW_FEATURE = "NEW_FEATURE"

class PolicyTraversalEngine:
    """
    Wrapper around the GraphTraversal engine that applies policies 
    to filter and prune control-flow paths based on user intent.
    """
    def __init__(self, traversal_engine):
        self.traversal_engine = traversal_engine

    def resolve_impact(self, target_node: dict, policy: TraversalPolicy = TraversalPolicy.DEFAULT) -> dict:
        """
        Runs the traversal engine and filters the upstream/downstream edges 
        according to the selected policy.
        """
        if not isinstance(policy, TraversalPolicy):
            try:
                policy = TraversalPolicy(policy)
            except ValueError:
                policy = TraversalPolicy.DEFAULT

        if policy == TraversalPolicy.LOCAL_EDIT:
            return {
                "target": target_node,
                "upstream": [],
                "downstream": []
            }
        
        elif policy == TraversalPolicy.SIGNATURE_CHANGE:
            all_upstream = self.traversal_engine.find_upstream_nodes(target_node)
            # Filter for one-hop upstream caller edges only
            one_hop_upstream = [
                edge for edge in all_upstream
                if self.traversal_engine.node_equals(edge["to"], target_node)
            ]
            return {
                "target": target_node,
                "upstream": one_hop_upstream,
                "downstream": []
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
                        if self.traversal_engine.node_equals(edge["to"], current):
                            queue.append((edge["from"], path + [edge]))
                            
                if found_routes:
                    # Prefer nearest route chain (shortest path)
                    routes.append(found_routes[0][0])
            elif target_node.get("type") == "ROUTE":
                routes.append(target_node)
                
            # Fallback: routes defined in the target node's file if no routes found via BFS
            if not routes and target_node.get("file"):
                for edge in self.traversal_engine.edges:
                    for node in [edge["from"], edge["to"]]:
                        if node.get("type") == "ROUTE" and node.get("file") == target_node["file"]:
                            if node not in routes:
                                routes.append(node)
                                
            # 2. Downstream vertical slice traversal
            slice_edges = []
            visited_nodes = set()
            
            for r in routes:
                route_key = get_node_key(r)
                if route_key in visited_nodes:
                    continue
                visited_nodes.add(route_key)
                
                for edge in self.traversal_engine.edges:
                    if self.traversal_engine.node_equals(edge["from"], r):
                        slice_edges.append(edge)
                        to_node = edge["to"]
                        
                        if to_node.get("type") == "FUNCTION":
                            controller_key = get_node_key(to_node)
                            if controller_key not in visited_nodes:
                                visited_nodes.add(controller_key)
                                
                                for c_edge in self.traversal_engine.edges:
                                    if c_edge["type"] == "FUNCTION_CALL" and self.traversal_engine.node_equals(c_edge["from"], to_node):
                                        slice_edges.append(c_edge)
                                        service_node = c_edge["to"]
                                        
                                        service_key = get_node_key(service_node)
                                        if service_key not in visited_nodes:
                                            visited_nodes.add(service_key)
                                            
                                            for s_edge in self.traversal_engine.edges:
                                                if s_edge["type"] == "DB_ACCESS" and self.traversal_engine.node_equals(s_edge["from"], service_node):
                                                    slice_edges.append(s_edge)
                                                    
            if not routes:
                # Fallback: 1-hop callers/callees of target_node
                for edge in self.traversal_engine.edges:
                    if self.traversal_engine.node_equals(edge["from"], target_node) or self.traversal_engine.node_equals(edge["to"], target_node):
                        slice_edges.append(edge)
                        
            return {
                "target": target_node,
                "upstream": [],
                "downstream": slice_edges
            }
        
        else: # DEFAULT
            upstream = self.traversal_engine.find_upstream_nodes(target_node)
            downstream = self.traversal_engine.find_downstream_nodes(target_node)
            return {
                "target": target_node,
                "upstream": upstream,
                "downstream": downstream
            }

