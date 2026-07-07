# ==========================================================
# CONTEXT EXTRACTOR
# ==========================================================

import os
import re


class ContextExtractor:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph,

        project_root
    ):

        self.graph = graph

        self.project_root = project_root

    # ======================================================
    # EXTRACT CONTEXT
    # ======================================================

    def extract_context(

        self,

        impact_result
    ):

        context = {

            "relevant_files": [],

            "relevant_functions": [],

            "code_snippets": [],

            "execution_chain": [],

            "taint_flow": [],

            "route_context": []
        }

        # ==================================================
        # AFFECTED FUNCTIONS
        # ==================================================

        affected_functions = impact_result.get(

            "affected_functions",

            []
        )

        for item in affected_functions:

            file_path = item.get(
                "file"
            )

            function_name = item.get(
                "function"
            )

            if not file_path:
                continue

            # ==============================================
            # STORE FILE
            # ==============================================

            if (

                file_path

                not in

                context[
                    "relevant_files"
                ]
            ):

                context[
                    "relevant_files"
                ].append(file_path)

            # ==============================================
            # STORE FUNCTION
            # ==============================================

            context[
                "relevant_functions"
            ].append({

                "file": file_path,

                "function": function_name
            })

            # ==============================================
            # EXTRACT SNIPPET
            # ==============================================

            snippet = (
                self.extract_function_code(

                    file_path,

                    function_name
                )
            )

            if snippet:

                context[
                    "code_snippets"
                ].append({

                    "file": file_path,

                    "function": function_name,

                    "code": snippet
                })
                # ==============================================
                # EXECUTION CHAIN
                # ==============================================

                chain = self.extract_execution_chain(

                    file_path,

                    function_name
                )

                for item in chain:

                    if (

                        item

                        not in

                        context[
                            "execution_chain"
                        ]
                    ):

                        context[
                            "execution_chain"
                        ].append(item)

                # ==============================================
                # ROUTE CONTEXT
                # ==============================================

                routes = self.extract_route_context(

                    file_path,

                    function_name
                )

                for route in routes:

                    if (

                        route

                        not in

                        context[
                            "route_context"
                        ]
                    ):

                        context[
                            "route_context"
                        ].append(route)

                # ==============================================
                # TAINT FLOW
                # ==============================================

                taints = self.extract_taint_flow(
                    function_name
                )

                for item in taints:

                    if (

                        item

                        not in

                        context[
                            "taint_flow"
                        ]
                    ):

                        context[
                            "taint_flow"
                        ].append(item)

        return context

    # ======================================================
    # EXTRACT FUNCTION CODE
    # ======================================================

    def extract_function_code(

        self,

        relative_path,

        function_name
    ):

        full_path = os.path.join(

            self.project_root,

            relative_path
        )

        full_path = os.path.normpath(
            full_path
        )

        # ==================================================
        # FILE CHECK
        # ==================================================

        if not os.path.exists(full_path):

            return None

        # ==================================================
        # READ FILE
        # ==================================================

        try:

            with open(

                full_path,

                "r",

                encoding="utf-8"
            ) as f:

                content = f.read()

        except:

            return None

        # ==================================================
        # FUNCTION DECLARATION
        # function test() {}
        # ==================================================

        patterns = [

            rf"function\s+{function_name}\s*\([^)]*\)\s*\{{",

            # ==============================================
            # OBJECT PROPERTY
            # fetchUsers: async () => {}
            # ==============================================

            rf"{function_name}\s*:\s*async\s*\([^)]*\)\s*=>\s*\{{",

            rf"{function_name}\s*:\s*\([^)]*\)\s*=>\s*\{{",

            # ==============================================
            # VARIABLE DECLARATOR
            # const test = async () => {}
            # ==============================================

            rf"const\s+{function_name}\s*=\s*async\s*\([^)]*\)\s*=>\s*\{{",

            rf"const\s+{function_name}\s*=\s*\([^)]*\)\s*=>\s*\{{"
        ]

        # ==================================================
        # FIND FUNCTION
        # ==================================================

        for pattern in patterns:

            match = re.search(

                pattern,

                content,

                re.MULTILINE
            )

            if not match:
                continue

            start_index = match.start()

            # ==============================================
            # BRACE TRACKING
            # ==============================================

            brace_count = 0

            started = False

            end_index = start_index

            for i in range(

                start_index,

                len(content)
            ):

                char = content[i]

                if char == "{":

                    brace_count += 1
                    started = True

                elif char == "}":

                    brace_count -= 1

                # ==========================================
                # FUNCTION END
                # ==========================================

                if (

                    started

                    and

                    brace_count == 0
                ):

                    end_index = i + 1
                    break

            return content[
                start_index:end_index
            ]

        return None
    


    # ==========================================================
    # EXECUTION CHAIN
    # ==========================================================

    def extract_execution_chain(

        self,

        file_path,

        function_name
    ):

        chain = []

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

                edge_type == "ROUTE_CALL"

                and

                to_node.get("file") == file_path

                and

                to_node.get("function") == function_name
            ):

                chain.append({

                    "type": "ROUTE",

                    "route":
                        from_node.get(
                            "route"
                        ),

                    "method":
                        from_node.get(
                            "method"
                        ),

                    "target_function":
                        function_name
                })

            # ==================================================
            # FUNCTION → FUNCTION
            # ==================================================

            elif (

                edge_type == "FUNCTION_CALL"

                and

                to_node.get("file") == file_path

                and

                to_node.get("function") == function_name
            ):

                chain.append({

                    "type": "FUNCTION_CALL",

                    "caller_file":
                        from_node.get(
                            "file"
                        ),

                    "caller_function":
                        from_node.get(
                            "function"
                        ),

                    "target_function":
                        function_name
                })

        return chain


    # ==========================================================
    # ROUTE CONTEXT
    # ==========================================================

    def extract_route_context(

        self,

        file_path,

        function_name
    ):

        routes = []

        for edge in self.graph.get(

            "execution_edges",

            []
        ):

            if edge.get("type") != "ROUTE_CALL":
                continue

            to_node = edge.get("to")

            from_node = edge.get("from")

            if (

                to_node.get("file") == file_path

                and

                to_node.get("function") == function_name
            ):

                routes.append({

                    "route":
                        from_node.get(
                            "route"
                        ),

                    "method":
                        from_node.get(
                            "method"
                        )
                })

        return routes


    # ==========================================================
    # TAINT FLOW
    # ==========================================================

    def extract_taint_flow(

        self,

        function_name
    ):

        flows = []

        for taint in self.graph.get(

            "taint_sources",

            []
        ):

            if (

                taint.get(
                    "target_function"
                )

                ==

                function_name
            ):

                flows.append(taint)

        return flows