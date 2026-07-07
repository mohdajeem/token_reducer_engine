# ==========================================================
# PATCH TRUST ANALYZER
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

class PatchTrustAnalyzer:

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

        # ==================================================
        # TRUSTED LIBRARIES
        # ==================================================

        # self.trusted_apis = {

        #     "bcrypt",

        #     "validator",

        #     "crypto",

        #     "jwt",

        #     "express"
        # }

        # ==================================================
        # DANGEROUS APIS
        # ==================================================

        self.dangerous_apis = {

            "eval",

            "exec",

            "Function",

            "child_process"
        }

    # ======================================================
    # ANALYZE PATCH TRUST
    # ======================================================

    def analyze(

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

        trust_score = 1.0

        # ==================================================
        # CHECK FUNCTION CALLS
        # ==================================================

        for function_name_called in semantics.get(

            "called_functions",

            []
        ):

            # ==============================================
            # DANGEROUS API
            # ==============================================

            if (

                function_name_called

                in

                self.dangerous_apis
            ):

                findings.append({

                    "type":
                        "DANGEROUS_API",

                    "severity":
                        "CRITICAL",

                    "symbol":
                        function_name_called,

                    "message":
                        f"Dangerous API "
                        f"'{function_name_called}' "
                        f"used in patch"
                })

                trust_score -= 0.5

                continue

            # ==============================================
            # TRUSTED SYMBOL
            # ==============================================

            symbol_exists = (

                self.symbol_query
                .symbol_exists(

                    file_path,

                    function_name,

                    function_name_called
                )
            )

            # trusted_library = False

            # for trusted in self.trusted_apis:

            #     if trusted in patch_content:

            #         trusted_library = True
            #         break

            # ==============================================
            # POSSIBLE HALLUCINATION
            # ==============================================

            # trusted_symbol = False

            # for member_expression in semantics.get(

            #     "member_expressions",

            #     []
            # ):

            #     if self.registry.is_trusted(

            #         member_expression
            #     ):

            #         trusted_symbol = True
            #         break

            trusted_symbol = False

            # ==============================================
            # CHECK EXACT MEMBER EXPRESSION
            # ==============================================

            for member_expression in semantics.get(

                "member_expressions",

                []
            ):

                # ==========================================
                # bcrypt.hash -> hash
                # ==========================================

                member_function = (
                    member_expression
                    .split(".")[-1]
                )

                if member_function == function_name_called:

                    if self.registry.is_trusted(

                        member_expression
                    ):

                        trusted_symbol = True
                        break

            if (

                not symbol_exists

                and

                not trusted_symbol
            ):

                findings.append({

                    "type":
                        "UNKNOWN_FUNCTION",

                    "severity":
                        "HIGH",

                    "symbol":
                        function_name_called,

                    "message":
                        f"Function "
                        f"'{function_name_called}' "
                        f"not found in semantic graph"
                })

                trust_score -= 0.2

        # ==================================================
        # TAINT RE-PROPAGATION
        # ==================================================

        tainted_variables = (

            self.function_query
            .get_tainted_variables(

                file_path,

                function_name
            )
        )

        for state in tainted_variables:

            variable_name = state[
                "variable"
            ]

            if variable_name in patch_content:

                findings.append({

                    "type":
                        "TAINT_REPROPAGATION",

                    "severity":
                        "CRITICAL",

                    "symbol":
                        variable_name,

                    "message":
                        f"Tainted variable "
                        f"'{variable_name}' "
                        f"still propagated in patch"
                })

                trust_score -= 0.4

        # ==================================================
        # NORMALIZE SCORE
        # ==================================================

        trust_score = max(
            0.0,
            min(1.0, trust_score)
        )

        # ==================================================
        # FINAL RESULT
        # ==================================================

        return {

            "trust_score":
                round(trust_score, 2),

            "trusted":
                trust_score >= 0.7,

            "findings":
                findings,

            "semantics":
                semantics
        }