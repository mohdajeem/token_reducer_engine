# ==========================================================
# PATCH SIMULATOR
# ==========================================================

from validation.patch_semantic_extractor import (
    PatchSemanticExtractor
)

from impact_engine.symbol_query import (
    SymbolQuery
)

from impact_engine.function_query import (
    FunctionQuery
)

from semantic_core.trusted_symbol_registry import (
    TrustedSymbolRegistry
)


class PatchSimulator:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph
    ):

        self.graph = graph

        self.extractor = (
            PatchSemanticExtractor()
        )

        self.symbol_query = (
            SymbolQuery(graph)
        )

        self.function_query = (
            FunctionQuery(graph)
        )

        self.registry = (
            TrustedSymbolRegistry()
        )

    # ======================================================
    # SIMULATE PATCH
    # ======================================================

    def simulate(

        self,

        patch
    ):

        patch_content = patch.get(
            "patch",
            ""
        )

        file_path = patch.get(
            "file"
        )

        function_name = patch.get(
            "function"
        )

        semantics = self.extractor.extract(
            patch_content
        )

        findings = []

        simulation_score = 1.0

        # ==================================================
        # VARIABLE EXISTENCE
        # ==================================================

        for variable in semantics.get(

            "declared_variables",

            []
        ):

            if not self.symbol_query.symbol_exists(

                file_path,

                function_name,

                variable
            ):

                findings.append({

                    "type":
                        "NEW_VARIABLE",

                    "severity":
                        "LOW",

                    "symbol":
                        variable,

                    "message":
                        f"Variable "
                        f"'{variable}' "
                        f"introduced by patch"
                })

                simulation_score -= 0.05

        # ==================================================
        # UNKNOWN FUNCTIONS
        # ==================================================

        # for called_function in semantics.get(

        #     "called_functions",

        #     []
        # ):

        #     exists = (

        #         self.symbol_query
        #         .symbol_exists(

        #             file_path,

        #             function_name,

        #             called_function
        #         )
        #     )

        #     if not exists:
        for called_function in semantics.get(

            "called_functions",

            []
        ):

            exists = (

                self.symbol_query
                .symbol_exists(

                    file_path,

                    function_name,

                    called_function
                )
            )

            trusted_symbol = False

            # ==============================================
            # CHECK MEMBER EXPRESSIONS
            # ==============================================

            for member_expression in semantics.get(

                "member_expressions",

                []
            ):

                member_function = (
                    member_expression
                    .split(".")[-1]
                )

                if member_function == called_function:

                    if self.registry.is_trusted(

                        member_expression
                    ):

                        trusted_symbol = True
                        break

            if (

                not exists

                and

                not trusted_symbol
            ):
                findings.append({

                    "type":
                        "UNRESOLVED_CALL",

                    "severity":
                        "HIGH",

                    "symbol":
                        called_function,

                    "message":
                        f"Function "
                        f"'{called_function}' "
                        f"cannot be resolved"
                })

                simulation_score -= 0.25

        # ==================================================
        # ASYNC VIOLATION
        # ==================================================

        if "await " in patch_content:

            is_async = False

            for _, functions in self.graph.get(

                "functions",

                {}
            ).items():

                for fn in functions:

                    if (

                        fn.get("file")
                        == file_path

                        and

                        fn.get("function")
                        == function_name
                    ):

                        is_async = fn.get(
                            "async",
                            False
                        )

            if not is_async:

                findings.append({

                    "type":
                        "ASYNC_CONTEXT_VIOLATION",

                    "severity":
                        "HIGH",

                    "message":
                        "Await used inside "
                        "non-async function"
                })

                simulation_score -= 0.35

        # ==================================================
        # RETURN FLOW CHANGE
        # ==================================================

        if "return " in patch_content:

            downstream = (

                self.function_query
                .get_downstream_calls(

                    file_path,

                    function_name
                )
            )

            if downstream:

                findings.append({

                    "type":
                        "RETURN_FLOW_CHANGE",

                    "severity":
                        "MEDIUM",

                    "message":
                        "Patch modifies return flow "
                        "with downstream dependencies",

                    "downstream_count":
                        len(downstream)
                })

                simulation_score -= 0.10

        # ==================================================
        # NORMALIZE
        # ==================================================

        simulation_score = max(
            0.0,
            min(1.0, simulation_score)
        )

        # ==================================================
        # FINAL RESULT
        # ==================================================

        return {

            "simulation_score":
                round(simulation_score, 2),

            "safe_to_apply":
                simulation_score >= 0.70,

            "findings":
                findings,

            "semantics":
                semantics
        }