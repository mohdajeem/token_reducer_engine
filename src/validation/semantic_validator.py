# ==========================================================
# SEMANTIC PATCH VALIDATOR
# ==========================================================

import re

from validation.patch_semantic_extractor import (
    PatchSemanticExtractor
)

from semantic_core.trusted_symbol_registry import (
    TrustedSymbolRegistry
)

from language_config import (
    LanguageManager
)

from impact_engine.function_query import (
    FunctionQuery
)

from impact_engine.symbol_query import (
    SymbolQuery
)


# ==========================================================
# INIT
# ==========================================================

langmanager = LanguageManager()


class SemanticValidator:
    """
    Validation engine designed to analyze incoming source code patches for semantic safety
    and compliance.
    
    This validator checks whether the patch references unrecognized identifiers (missing imports
    or undeclared variables), evaluates if active variables carry untrusted input tags (taints),
    and determines if those inputs have traversed appropriate sanitizer functions.
    """

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph
    ):
        """
        Initializes the SemanticValidator with the compiled semantic graph.

        Args:
            graph (Dict): The full semantic context graph containing execution edges, definitions, and taints.
        """

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
        """
        Validates the syntax and safety of a code patch by extracting newly introduced lines,
        evaluating identifier references against trusted symbol registries and declared variables,
        and launching taint-safety vulnerability checks.

        Args:
            patch (Dict): A dictionary representing the patch details, including keys:
                          - "file" (str): The file path being modified.
                          - "function" (str): The function block inside the file.
                          - "patch" (str): The raw git patch/diff string.

        Returns:
            Dict: A validation results dictionary containing keys:
                  - "valid" (bool): True if the patch passes standard safety validation, False if it uses unknown identifiers.
                  - "reason" (str): Textual reasoning for the validation state.
                  - "unknown_identifiers" (List[str], optional): List of unrecognized identifiers.
                  - "taint_findings" (List[Dict], optional): Taint propagation warnings or audit findings.
        """

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
        """
        Parses a raw line of code and extracts alphanumeric identifier words,
        omitting language-specific syntax keywords.

        Args:
            code_line (str): A string line of code to extract identifiers from.

        Returns:
            List[str]: A list of alphanumeric identifier strings.
        """

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
        """
        Scans the compiled semantic graph functions and local safe-identifier lists
        to check if a given identifier symbol has a recognized reference definition.

        Args:
            identifier (str): The identifier name to check.

        Returns:
            bool: True if the identifier is defined or belongs to a list of safe terms, False otherwise.
        """

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
        """
        Performs a security taint check on the patch content by intersecting modified variables
        against known active tainted variables and sanitized flows within the graph context.

        Args:
            patch (Dict): The patch target context dictionary specifying files, functions, and content.

        Returns:
            List[Dict]: List of safety finding alerts, detailing vulnerability risk categories (TAINT_PROPAGATION, SANITIZED_FLOW).
        """

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