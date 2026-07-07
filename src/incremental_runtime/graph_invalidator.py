# ==========================================================
# GRAPH INVALIDATOR
# ==========================================================


class GraphInvalidator:

    # ======================================================
    # INVALIDATE FILE
    # ======================================================

    def invalidate_file(

        self,

        graph,

        file_path
    ):

        # ==================================================
        # FILE-BASED GRAPH SECTIONS
        # ==================================================

        file_based_sections = [

            "imports",

            "routes",

            "calls",

            "database",

            "errors",

            "contracts",

            "parameters",

            "arguments"
        ]

        for section in file_based_sections:

            if (

                section in graph

                and

                file_path in graph[section]
            ):

                del graph[section][file_path]

        # ==================================================
        # LIST-BASED GRAPH SECTIONS
        # ==================================================

        graph["execution_edges"] = [

            edge

            for edge in graph.get(

                "execution_edges",

                []
            )

            if not self.edge_matches_file(

                edge,

                file_path
            )
        ]

        graph["data_flow"] = [

            flow

            for flow in graph.get(

                "data_flow",

                []
            )

            if flow.get("file") != file_path
        ]

        graph["taint_sources"] = [

            source

            for source in graph.get(

                "taint_sources",

                []
            )

            if source.get("file") != file_path
        ]

        graph["security_sinks"] = [

            sink

            for sink in graph.get(

                "security_sinks",

                []
            )

            if sink.get("file") != file_path
        ]

        graph["security_findings"] = [

            finding

            for finding in graph.get(

                "security_findings",

                []
            )

            if finding.get("file") != file_path
        ]

        graph["sanitizers"] = [

            sanitizer

            for sanitizer in graph.get(

                "sanitizers",

                []
            )

            if sanitizer.get("file") != file_path
        ]

        graph["variable_states"] = [

            state

            for state in graph.get(

                "variable_states",

                []
            )

            if state.get("file") != file_path
        ]

        graph["returns"] = [

            ret

            for ret in graph.get(

                "returns",

                []
            )

            if ret.get("file") != file_path
        ]

        return graph

    # ======================================================
    # EDGE MATCHES FILE
    # ======================================================

    # def edge_matches_file(

    #     self,

    #     edge,

    #     file_path
    # ):

    #     from_node = edge.get(
    #         "from",
    #         {}
    #     )

    #     to_node = edge.get(
    #         "to",
    #         {}
    #     )

    #     return (

    #         from_node.get("file")
    #         == file_path

    #         or

    #         to_node.get("file")
    #         == file_path
    #     )
    

    def edge_matches_file(

        self,

        edge,

        file_path
    ):

        from_node = edge.get(
            "from",
            {}
        )

        to_node = edge.get(
            "to",
            {}
        )

        edge_type = edge.get(
            "type"
        )

        # ==================================================
        # FUNCTION_CALL EDGES
        # ==================================================

        # Caller owns the edge.
        # Do NOT delete edge just because
        # callee changed.

        if edge_type == "FUNCTION_CALL":

            return (
                from_node.get("file")
                == file_path
            )

        # ==================================================
        # DEFAULT EDGE POLICY
        # ==================================================

        return (

            from_node.get("file")
            == file_path

            or

            to_node.get("file")
            == file_path
        )
