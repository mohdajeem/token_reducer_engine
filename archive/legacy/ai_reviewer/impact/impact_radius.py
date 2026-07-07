# ==========================================================
# IMPACT RADIUS ENGINE
# ==========================================================

class ImpactRadius:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph
    ):

        self.graph = graph

    # ======================================================
    # FIND ALL IMPACT
    # ======================================================

    def find_affected_by_function(

        self,

        file_path,

        function_name
    ):

        result = {

            "affected_routes": [],

            "affected_functions": [],

            "affected_files": [],

            "database_impact": [],

            "security_impact": []
        }

        visited = set()

        # ==================================================
        # START DFS
        # ==================================================

        self._walk_downstream(

            current_file=file_path,

            current_function=function_name,

            result=result,

            visited=visited
        )

        # ==================================================
        # UPSTREAM DFS
        # ==================================================

        self._walk_upstream(

            current_file=file_path,

            current_function=function_name,

            result=result,

            visited=visited
        )

        return result

    # ======================================================
    # WALK EXECUTION GRAPH
    # ======================================================

    def _walk_downstream(

        self,

        current_file,

        current_function,

        result,

        visited
    ):

        node_key = (
            current_file,
            current_function
        )

        # ==================================================
        # PREVENT CYCLES
        # ==================================================

        if node_key in visited:
            return

        visited.add(node_key)

        # ==================================================
        # EXECUTION EDGES
        # ==================================================

        for edge in self.graph.get(

            "execution_edges",

            []
        ):

            from_node = edge.get("from")

            to_node = edge.get("to")

            edge_type = edge.get("type")

            # ==================================================
            # MATCH CURRENT FUNCTION
            # ==================================================

            if (

                from_node.get("type")

                ==

                "FUNCTION"

                and

                from_node.get("file")

                ==

                current_file

                and

                from_node.get("function")

                ==

                current_function
            ):

                # ==============================================
                # FUNCTION CALL IMPACT
                # ==============================================

                if edge_type == "FUNCTION_CALL":

                    affected_function = {

                        "file":
                            to_node.get(
                                "file"
                            ),

                        "function":
                            to_node.get(
                                "function"
                            )
                    }

                    # ==========================================
                    # STORE FUNCTION
                    # ==========================================

                    if (

                        affected_function

                        not in

                        result[
                            "affected_functions"
                        ]
                    ):

                        result[
                            "affected_functions"
                        ].append(

                            affected_function
                        )

                    # ==========================================
                    # STORE FILE
                    # ==========================================

                    affected_file = (
                        to_node.get(
                            "file"
                        )
                    )

                    if (

                        affected_file

                        and

                        affected_file

                        not in

                        result[
                            "affected_files"
                        ]
                    ):

                        result[
                            "affected_files"
                        ].append(

                            affected_file
                        )

                    # ==========================================
                    # CONTINUE DFS
                    # ==========================================

                    self._walk_downstream(

                        current_file=
                            to_node.get(
                                "file"
                            ),

                        current_function=
                            to_node.get(
                                "function"
                            ),

                        result=result,

                        visited=visited
                    )

                # ==============================================
                # DATABASE IMPACT
                # ==============================================

                elif edge_type == "DB_ACCESS":

                    db_impact = {

                        "model":
                            to_node.get(
                                "model"
                            ),

                        "operation":
                            to_node.get(
                                "operation"
                            )
                    }

                    if (

                        db_impact

                        not in

                        result[
                            "database_impact"
                        ]
                    ):

                        result[
                            "database_impact"
                        ].append(

                            db_impact
                        )

        # ==================================================
        # FIND IMPACTED ROUTES
        # ==================================================

        for edge in self.graph.get(

            "execution_edges",

            []
        ):

            from_node = edge.get("from")

            to_node = edge.get("to")

            edge_type = edge.get("type")

            # ==================================================
            # ROUTE → FUNCTION
            # ==================================================

            if (

                edge_type

                ==

                "ROUTE_CALL"

                and

                to_node.get("file")

                ==

                current_file

                and

                to_node.get("function")

                ==

                current_function
            ):

                route_info = {

                    "route":
                        from_node.get(
                            "route"
                        ),

                    "method":
                        from_node.get(
                            "method"
                        )
                }

                if (

                    route_info

                    not in

                    result[
                        "affected_routes"
                    ]
                ):

                    result[
                        "affected_routes"
                    ].append(

                        route_info
                    )

        # ==================================================
        # SECURITY IMPACT
        # ==================================================

        for finding in self.graph.get(

            "security_findings",

            []
        ):

            if (

                finding.get(
                    "function"
                )

                ==

                current_function
            ):

                if (

                    finding

                    not in

                    result[
                        "security_impact"
                    ]
                ):

                    result[
                        "security_impact"
                    ].append(

                        finding
                    )

    
    # ======================================================
    # WALK UPSTREAM
    # ======================================================

    def _walk_upstream(

        self,

        current_file,

        current_function,

        result,

        visited
    ):

        # ==================================================
        # EXECUTION EDGES
        # ==================================================

        for edge in self.graph.get(

            "execution_edges",

            []
        ):

            from_node = edge.get("from")

            to_node = edge.get("to")

            edge_type = edge.get("type")

            # ==================================================
            # FIND CALLERS
            # ==================================================

            if (

                edge_type == "FUNCTION_CALL"

                and

                to_node.get("file")

                ==

                current_file

                and

                to_node.get("function")

                ==

                current_function
            ):

                caller_function = {

                    "file":
                        from_node.get(
                            "file"
                        ),

                    "function":
                        from_node.get(
                            "function"
                        )
                }

                # ==============================================
                # STORE FUNCTION
                # ==============================================

                if (

                    caller_function

                    not in

                    result[
                        "affected_functions"
                    ]
                ):

                    result[
                        "affected_functions"
                    ].append(
                        caller_function
                    )

                # ==============================================
                # STORE FILE
                # ==============================================

                caller_file = (
                    from_node.get(
                        "file"
                    )
                )

                if (

                    caller_file

                    and

                    caller_file

                    not in

                    result[
                        "affected_files"
                    ]
                ):

                    result[
                        "affected_files"
                    ].append(
                        caller_file
                    )

                # ==============================================
                # CONTINUE UPSTREAM
                # ==============================================

                self._walk_upstream(

                    current_file=
                        from_node.get(
                            "file"
                        ),

                    current_function=
                        from_node.get(
                            "function"
                        ),

                    result=result,

                    visited=visited
                )

            # ==================================================
            # ROUTE IMPACT
            # ==================================================

            elif (

                edge_type == "ROUTE_CALL"

                and

                to_node.get("file")

                ==

                current_file

                and

                to_node.get("function")

                ==

                current_function
            ):

                route_info = {

                    "route":
                        from_node.get(
                            "route"
                        ),

                    "method":
                        from_node.get(
                            "method"
                        )
                }

                if (

                    route_info

                    not in

                    result[
                        "affected_routes"
                    ]
                ):

                    result[
                        "affected_routes"
                    ].append(
                        route_info
                    )