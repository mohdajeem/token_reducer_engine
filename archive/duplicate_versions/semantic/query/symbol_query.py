# ==========================================================
# SYMBOL QUERY
# ==========================================================

from semantic.query.function_query import (
    FunctionQuery
)


class SymbolQuery:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph
    ):

        self.graph = graph

        self.function_query = (
            FunctionQuery(graph)
        )

    # ======================================================
    # SYMBOL EXISTS
    # ======================================================

    def symbol_exists(

        self,

        file_path,

        function_name,

        symbol
    ):

        # ==================================================
        # LANGUAGE KEYWORD
        # ==================================================

        if self.is_language_keyword(
            symbol
        ):

            return True

        # ==================================================
        # FUNCTION NAME
        # ==================================================

        if self.is_function(
            symbol
        ):

            return True

        # ==================================================
        # PARAMETER
        # ==================================================

        if self.is_parameter(

            file_path,

            function_name,

            symbol
        ):

            return True

        # ==================================================
        # LOCAL VARIABLE
        # ==================================================

        if self.is_local_variable(

            file_path,

            function_name,

            symbol
        ):

            return True

        # ==================================================
        # IMPORTED SYMBOL
        # ==================================================

        if self.is_imported_symbol(
            
            symbol
        ):

            return True

        # ==================================================
        # SANITIZED VARIABLE
        # ==================================================

        if self.is_sanitized_variable(

            file_path,

            function_name,

            symbol
        ):

            return True

        return False

    # ======================================================
    # IS FUNCTION
    # ======================================================

    def is_function(

        self,

        symbol
    ):

        for _, functions in self.graph.get(

            "functions",

            {}
        ).items():

            for function_data in functions:

                if (

                    function_data.get(
                        "function"
                    )

                    ==

                    symbol
                ):

                    return True

        return False

    # ======================================================
    # IS PARAMETER
    # ======================================================

    # def is_parameter(

    #     self,

    #     file_path,

    #     function_name,

    #     symbol
    # ):

    #     for item in self.graph.get(

    #         "parameters",

    #         []
    #     ):

    #         if (

    #             item["file"]

    #             ==

    #             file_path

    #             and

    #             item["function"]

    #             ==

    #             function_name

    #             and

    #             item["parameter"]

    #             ==

    #             symbol
    #         ):

    #             return True

    #     return False

    # ======================================================
    # IS PARAMETER
    # ======================================================

    def is_parameter(

        self,

        file_path,

        function_name,

        symbol
    ):

        file_parameters = self.graph.get(

            "parameters",

            {}
        ).get(

            file_path,

            []
        )

        for item in file_parameters:

            if (

                item["function"]

                ==

                function_name
            ):

                if symbol in item["params"]:

                    return True

        return False

    # ======================================================
    # IS LOCAL VARIABLE
    # ======================================================

    def is_local_variable(

        self,

        file_path,

        function_name,

        symbol
    ):

        for state in self.graph.get(

            "variable_states",

            []
        ):

            if (

                state["file"]

                ==

                file_path

                and

                state["function"]

                ==

                function_name

                and

                state["variable"]

                ==

                symbol
            ):

                return True

        return False

    # ======================================================
    # IS IMPORTED SYMBOL
    # ======================================================

    def is_imported_symbol(

        self,

        symbol
    ):

        imports = self.graph.get(
            "imports",
            {}
        )

        for _, imported_symbols in (
            imports.items()
        ):

            if symbol in imported_symbols:

                return True

        return False

    # ======================================================
    # IS SANITIZED VARIABLE
    # ======================================================

    def is_sanitized_variable(

        self,

        file_path,

        function_name,

        symbol
    ):

        sanitized = (

            self.function_query
            .get_sanitized_variables(

                file_path,

                function_name
            )
        )

        for item in sanitized:

            if item["variable"] == symbol:

                return True

        return False

    # ======================================================
    # IS LANGUAGE KEYWORD
    # ======================================================

    def is_language_keyword(

        self,

        symbol
    ):

        keywords = {

            "return",

            "const",

            "let",

            "var",

            "async",

            "await",

            "if",

            "else",

            "true",

            "false",

            "null",

            "undefined",

            "new",

            "function"
        }

        return symbol in keywords