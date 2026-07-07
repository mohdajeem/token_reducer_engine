# ==========================================================
# FUNCTION QUERY
# ==========================================================

from semantic.impact_analysis import (
    ImpactAnalysis
)


class FunctionQuery:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph
    ):

        self.graph = graph

        self.impact_analysis = (
            ImpactAnalysis(graph)
        )

    # ======================================================
    # GET FUNCTION CALLS
    # ======================================================

    def get_function_calls(self, file_path, function_name):
        calls = []
        # print("inside get_function_calls:", file_path, "|",function_name)
        # print("graph get execution_edge:", self.graph.get("execution_edges",[]))
        # print("="*50)
        # for edge in self.graph.get("execution_edges", []):
        #     print(edge)
            
        # print("="*50)
        for edge in self.graph.get("execution_edges", []):
            from_node = edge["from"]
            to_node = edge["to"]

            if (from_node.get("type") == "FUNCTION"
                    and from_node.get("file") == file_path
                         and from_node.get("function") == function_name
            ):
                
                if to_node.get("type") == "FUNCTION":
                    calls.append(to_node)

        return calls

    # ======================================================
    # GET FUNCTION ROUTES
    # ======================================================

    def get_function_routes(
        self, file_path, function_name
    ):

        routes = []

        for edge in self.graph.get("execution_edges", []):
            from_node = edge["from"]
            to_node = edge["to"]

            if (to_node.get("type") == "FUNCTION"
                 and  to_node.get("file") == file_path
                    and to_node.get("function") == function_name
            ):

                if from_node.get("type") == "ROUTE":
                    routes.append(
                        from_node
                    )

        return routes

    # ======================================================
    # GET FUNCTION RETURNS
    # ======================================================

    def get_function_returns(

        self,

        file_path,

        function_name
    ):

        returns = []

        for item in self.graph.get(

            "returns",

            []
        ):

            if (

                item["file"]

                ==

                file_path

                and

                item["function"]

                ==

                function_name
            ):

                returns.append(
                    item
                )

        return returns

    # ======================================================
    # GET TAINTED VARIABLES
    # ======================================================

    def get_tainted_variables(

        self,

        file_path,

        function_name
    ):

        results = []

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

                state.get("tainted")
            ):

                results.append(
                    state
                )

        return results

    # ======================================================
    # GET SANITIZED VARIABLES
    # ======================================================

    def get_sanitized_variables(

        self,

        file_path,

        function_name
    ):

        results = []

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

                state.get("sanitized")
            ):

                results.append(
                    state
                )

        return results

    # ======================================================
    # GET DOWNSTREAM CALLS
    # ======================================================

    def get_downstream_calls(

        self,

        file_path,

        function_name
    ):

        return (

            self.impact_analysis
            .find_downstream_calls(

                file_path,

                function_name
            )
        )