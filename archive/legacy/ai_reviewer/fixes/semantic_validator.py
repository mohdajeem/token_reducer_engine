# ==========================================================
# SEMANTIC PATCH VALIDATOR
# ==========================================================

import re

from semantic.patch_semantic_extractor import (
    PatchSemanticExtractor
)

from semantic.trusted_symbol_registry import (
    TrustedSymbolRegistry
)

from language_config import (
    LanguageManager
)

from semantic.query.function_query import (
    FunctionQuery
)

from semantic.query.symbol_query import (
    SymbolQuery
)


# ==========================================================
# INIT
# ==========================================================

langmanager = LanguageManager()


class SemanticValidator:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph
    ):

        self.graph = graph
        self.query = FunctionQuery(
            graph
        )
        self.symbol_query = SymbolQuery(
            graph
        )
        self.extractor = (
            PatchSemanticExtractor()
        )

        self.registry = (
            TrustedSymbolRegistry()
        )


    # ======================================================
    # VALIDATE PATCH SEMANTICS
    # ======================================================

    def validate_patch_semantics(

        self,

        patch
    ):

        patch_content = patch.get(
            "patch",
            ""
        )

        # ==================================================
        # EXTRACT ADDED LINES
        # ==================================================

        added_lines = []

        for line in patch_content.splitlines():

            if (

                line.startswith("+")

                and

                not line.startswith("+++")
            ):

                added_lines.append(
                    line[1:]
                )

        # ==================================================
        # IDENTIFIER EXTRACTION
        # ==================================================

        # identifiers = []

        # for line in added_lines:

        #     identifiers.extend(

        #         self.extract_identifiers(
        #             line
        #         )
        #     )

        # ==================================================
        # PATCH SEMANTICS
        # ==================================================

        semantics = self.extractor.extract(
            patch_content
        )

        identifiers = []

        for line in added_lines:

            identifiers.extend(

                self.extract_identifiers(
                    line
                )
            )

        # ==================================================
        # DECLARED VARIABLES
        # ==================================================

        declared_variables = set(

            semantics.get(
                "declared_variables",
                []
            )
        )

        # ==================================================
        # ASSIGNMENT TARGETS
        # ==================================================

        assignment_targets = set(

            semantics.get(
                "assignments",
                []
            )
        )

        # ==================================================
        # TRUSTED MEMBER EXPRESSIONS
        # ==================================================

        trusted_members = set()

        for member_expression in semantics.get(

            "member_expressions",

            []
        ):

            if self.registry.is_trusted(

                member_expression
            ):

                parts = (
                    member_expression
                    .split(".")
                )

                trusted_members.update(
                    parts
                )

        # ==================================================
        # CHECK IDENTIFIERS
        # ==================================================

        unknown_identifiers = []

        # for identifier in identifiers:

        #     # if not self.identifier_exists(
        #     #     identifier
        #     # ):

        #     #     unknown_identifiers.append(
        #     #         identifier
        #     #     )
        #     if not self.symbol_query.symbol_exists(

        #         patch.get("file"),

        #         patch.get("function"),

        #         identifier
        #     ):


        # for identifier in identifiers:

        #     if not self.symbol_query.symbol_exists(

        #         patch.get("file"),

        #         patch.get("function"),

        #         identifier
        #     ):

        #         unknown_identifiers.append(
        #             identifier
        #         )
        for identifier in identifiers:
            # ==============================================
            # DECLARED INSIDE PATCH
            # ==============================================

            if identifier in declared_variables:
                continue

            # ==============================================
            # ASSIGNMENT TARGET
            # ==============================================

            if identifier in assignment_targets:
                continue

            # ==============================================
            # TRUSTED SYMBOLS
            # ==============================================

            if identifier in trusted_members:
                continue

            # ==============================================
            # GRAPH EXISTENCE
            # ==============================================

            if not self.identifier_exists(
                identifier
            ):

                unknown_identifiers.append(
                    identifier
                )


        # ==================================================
        # RESULT
        # ==================================================

        if unknown_identifiers:

            return {

                "valid": False,

                "reason":

                    "Unknown identifiers detected",

                "unknown_identifiers":
                    unknown_identifiers
            }

        # return {

        #     "valid": True,

        #     "reason":
        #         "Semantic validation passed"
        # }
        # ==================================================
        # TAINT VALIDATION
        # ==================================================

        taint_findings = (

            self.validate_taint_safety(
                patch
            )
        )

        return {

            "valid": True,

            "reason":
                "Semantic validation passed",

            "taint_findings":
                taint_findings
        }

    # ======================================================
    # EXTRACT IDENTIFIERS
    # ======================================================

    def extract_identifiers(

        self,

        code_line
    ):

        identifiers = re.findall(

            r"\b[a-zA-Z_][a-zA-Z0-9_]*\b",

            code_line
        )

        # ==================================================
        # IGNORE KEYWORDS
        # ==================================================

        ignore = {

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

            "null"
        }

        return [

            ident

            for ident in identifiers

            if ident not in ignore
        ]

    # ======================================================
    # IDENTIFIER EXISTS
    # ======================================================

    def identifier_exists(

        self,

        identifier
    ):

        # ==================================================
        # SEARCH FUNCTIONS
        # ==================================================

        for _, functions in self.graph.get(

            "functions",

            {}
        ).items():

            for function_data in functions:

                if (

                    function_data.get("function")

                    == identifier
                ):

                    return True

        # ==================================================
        # COMMON SAFE IDENTIFIERS
        # ==================================================

        safe_identifiers = {

            "email",

            "password",

            "req",

            "res",

            "user",

            "users"
        }

        if identifier in safe_identifiers:

            return True

        return False
    
    

    # ======================================================
    # VALIDATE TAINT SAFETY
    # ======================================================

    def validate_taint_safety(

        self,

        patch
    ):

        file_path = patch.get(
            "file"
        )

        function_name = patch.get(
            "function"
        )

        tainted_variables = (

            self.query
            .get_tainted_variables(

                file_path,

                function_name
            )
        )

        sanitized_variables = (

            self.query
            .get_sanitized_variables(

                file_path,

                function_name
            )
        )

        patch_content = patch.get(
            "patch",
            ""
        )

        findings = []

        # ==================================================
        # CHECK TAINTED VARIABLES
        # ==================================================

        for state in tainted_variables:

            variable_name = state[
                "variable"
            ]

            if variable_name in patch_content:

                findings.append({

                    "type":
                        "TAINT_PROPAGATION",

                    "severity":
                        "HIGH",

                    "variable":
                        variable_name,

                    "message":
                        f"Tainted variable "
                        f"'{variable_name}' "
                        f"still appears in patch"
                })

        # ==================================================
        # CHECK SANITIZED VARIABLES
        # ==================================================

        for state in sanitized_variables:

            variable_name = state[
                "variable"
            ]

            if variable_name in patch_content:

                findings.append({

                    "type":
                        "SANITIZED_FLOW",

                    "severity":
                        "INFO",

                    "variable":
                        variable_name,

                    "message":
                        f"Sanitized variable "
                        f"'{variable_name}' "
                        f"used in patch"
                })

        return findings