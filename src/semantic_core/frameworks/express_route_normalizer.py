class ExpressRouteNormalizer:

    def __init__(
        self,
        symbol_table,
        function_index
    ):

        self.symbol_table = symbol_table
        self.function_index = function_index

    # ======================================================
    # MAIN NORMALIZATION
    # ======================================================

    def get_arguments(self, code, matches):
        # QUERY = r"""
        #     (call_expression
        #         function: (member_expression
        #             object: (identifier) @router.obj 
        #             property: (property_identifier) @router.served_method
        #         )
        #     )
        #     """

        # query = Query(LANGUAGE, QUERY)
        # cursor = QueryCursor(query)

        # matches = cursor.matches(tree.root_node)

        for match_index, (pattern_index, captures) in enumerate(matches):
            # now we are going to check the call nodes
            
            call_node = None
            for capture_name, nodes in captures.items():
                if not isinstance(nodes, list):
                    nodes = [nodes]
                
                for node in nodes:
                    current = node
                    while current:
                        if current.type == 'call_expression':
                            call_node = current
                            break
                        current = current.parent
                    if call_node:
                        break
                
                if call_node:
                    break

            
            if call_node:
                arguments_child = None
                for child in call_node.children:
                    if child.type == 'arguments':
                        arguments_child = child
                        break
                
                # printing the arguments named child
                if arguments_child:
                    arguments = []
                    for child in arguments_child.named_children:
                        print(child.type,"|",child)
                        if not child.type == 'string':
                            arguments.append(child.text.decode("utf-8"))

                if arguments:
                    return arguments
        return None


    def normalize_route(
        self,
        semantic_match
    ):

        raw_arguments = (
            self.extract_route_arguments(
                semantic_match
            )
        )

        # print("raw_arguments",raw_arguments)

        if not raw_arguments:

            return None

        # ==================================================
        # EXPRESS SEMANTICS
        #
        # route(path, ...middlewares, handler)
        # ==================================================

        handler_argument = (
            raw_arguments[-1]
        )

        middleware_arguments = (
            raw_arguments[:-1]
        )

        normalized_handler = (
            self.normalize_handler(

                semantic_match.file_path,

                handler_argument
            )
        )

        normalized_middlewares = (
            self.normalize_middlewares(

                semantic_match.file_path,

                middleware_arguments
            )
        )

        return {

            "method":

                semantic_match.get(
                    "endpoint.served_method"
                ),

            "path":

                semantic_match.get(
                    "endpoint.served_route"
                ),

            "router":

                semantic_match.get(
                    "router.obj"
                ),

            "middlewares":
                normalized_middlewares,

            "handler":
                normalized_handler
        }

    # ======================================================
    # EXTRACT RAW ROUTE ARGUMENTS
    # ======================================================

    def extract_route_arguments(
        self,
        semantic_match
    ):

        """
        Expected capture:

        route.arguments

        Example:

        [
            "authMiddleware",
            "authController.login"
        ]
        """
        
        # call_node = None
        # for capture_name, nodes in semantic_match.captures.items():
        #     if not isinstance(nodes, list):
        #         nodes = [nodes]
            
        #     for node in nodes:
        #         current = node
        #         while current:
        #             if current.type == 'call_expression':
        #                 call_node = current
        #                 break
        #             current = current.parent
        #         if call_node:
        #             break
        #     if call_node:
        #         break

        # if call_node:
        #     arguments_child = None
        #     for child in call_node.children:
        #         if child.type == 'arguments':
        #             arguments_child = child
        #             break
            
        #     if arguments_child:
        #         arguments = []
        #         for child in arguments_child.named_children:
        #             print(child.type,"|",child)
        #             if not child.type == 'string':
        #                 arguments.append(child.text.decode("utf-8"))

        #         if arguments:
        #             print("arguments extracted in extract_route_arguments:",arguments)
        #             return arguments
        # return None
        # print("semantic_match.captures:",semantic_match.captures)
        route_arguments = (
            semantic_match.captures.get(
                "route.arguments"
            )
        )

        if not route_arguments:
            return []

        if isinstance(
            route_arguments,
            str
        ):
            route_arguments = [
                route_arguments
            ]

        return route_arguments

    # ======================================================
    # NORMALIZE FINAL HANDLER
    # ======================================================

    def normalize_handler(

        self,

        file_path,

        handler_value
    ):

        normalized = (
            self.normalize_symbol(

                file_path,

                handler_value
            )
        )

        normalized["type"] = (
            "ROUTE_HANDLER"
        )

        return normalized

    # ======================================================
    # NORMALIZE MIDDLEWARES
    # ======================================================

    def normalize_middlewares(

        self,

        file_path,

        middleware_arguments
    ):

        normalized_middlewares = []

        for middleware in middleware_arguments:

            normalized = (
                self.normalize_symbol(

                    file_path,

                    middleware
                )
            )

            normalized["type"] = (
                "MIDDLEWARE"
            )

            normalized_middlewares.append(
                normalized
            )

        return normalized_middlewares

    # ======================================================
    # NORMALIZE SYMBOL
    # ======================================================

    def normalize_symbol(

        self,

        file_path,

        symbol_value
    ):

        # ==============================================
        # MEMBER EXPRESSION
        #
        # authController.login
        # ==============================================

        if "." in symbol_value:

            parts = (
                symbol_value.split(".")
            )

            controller_name = (
                parts[0]
            )

            function_name = (
                parts[-1]
            )

        # ==============================================
        # IDENTIFIER
        #
        # deleteUser
        # ==============================================

        else:

            controller_name = None

            function_name = (
                symbol_value
            )

        # ==============================================
        # RESOLVE IMPORT
        # ==============================================

        resolved_file = None

        if controller_name:

            resolved_file = (

                self.symbol_table
                .resolve_import(

                    file_path,

                    controller_name
                )
            )

        # ==============================================
        # RESOLVE FUNCTION
        # ==============================================

        resolved_function = None

        if resolved_file:

            resolved_function = (

                self.function_index
                .resolve_function(

                    resolved_file,

                    function_name
                )
            )

        # ==============================================
        # FALLBACK 1 — DESTRUCTURED IMPORT
        # ==============================================

        if not resolved_function and not controller_name:

            destructured = (
                self.symbol_table
                .resolve_destructured(
                    file_path,
                    symbol_value
                )
            )

            if destructured:

                source_obj = destructured.get("source")

                func_name = destructured.get("function")

                if source_obj and func_name:

                    resolved_import_file = (
                        self.symbol_table
                        .resolve_import(
                            file_path,
                            source_obj
                        )
                    )

                    if resolved_import_file:

                        resolved_file = resolved_import_file

                        controller_name = source_obj

                        function_name = func_name

                        resolved_function = (
                            self.function_index
                            .resolve_function(
                                resolved_file,
                                function_name
                            )
                        )

        # ==============================================
        # FALLBACK 2 — DIRECT FUNCTION IMPORT
        # ==============================================

        if not resolved_function and not controller_name:

            direct_import_file = (
                self.symbol_table
                .resolve_import(
                    file_path,
                    symbol_value
                )
            )

            if direct_import_file:

                resolved_file = direct_import_file

                resolved_function = (
                    self.function_index
                    .resolve_function(
                        resolved_file,
                        symbol_value
                    )
                )

        # ==============================================
        # FALLBACK 3 — LOCAL DEFINITION
        # ==============================================

        if not resolved_function and not controller_name:

            local_function = (
                self.function_index
                .resolve_function(
                    file_path,
                    symbol_value
                )
            )

            if local_function:

                resolved_file = file_path

                resolved_function = local_function

        # ==============================================
        # NORMALIZED OUTPUT
        # ==============================================

        return {

            "controller":
                controller_name,

            "function":
                function_name,

            "resolved_file":
                resolved_file,

            "resolved_function":
                resolved_function,

            "resolved":
                resolved_function is not None
        }