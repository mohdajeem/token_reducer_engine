# ==========================================================
# PATCH SEMANTIC EXTRACTOR
# ==========================================================

import re


class PatchSemanticExtractor:

    # ======================================================
    # EXTRACT PATCH SEMANTICS
    # ======================================================

    def extract(self, patch_content):
        result = {
            "declared_variables": [],
            "called_functions": [],
            "member_expressions": [],
            "comments": [],
            "assignments": []
        }

        for raw_line in patch_content.splitlines():
            line = raw_line.strip()
            # ==================================================
            # ONLY PROCESS ADDED LINES
            # ==================================================
            if not line.startswith("+"):
                continue

            if line.startswith("+++"):
                continue

            clean_line = line[1:].strip()

            # ==================================================
            # COMMENT
            # ==================================================

            if clean_line.startswith("//"):
                result[
                    "comments"
                ].append(
                    clean_line
                )
                continue

            # ==================================================
            # VARIABLE DECLARATION
            # ==================================================

            declaration_match = re.search(
                r"\b(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                clean_line
            )

            if declaration_match:
                result[
                    "declared_variables"
                ].append(

                    declaration_match.group(1)
                )

            # ==================================================
            # FUNCTION CALLS
            # ==================================================

            function_calls = re.findall(
                r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                clean_line
            )

            for func in function_calls:
                if func not in {
                    "if",
                    "for",
                    "while",
                    "switch",
                    "return"
                }:
                    result[
                        "called_functions"
                    ].append(
                        func
                    )

            # ==================================================
            # MEMBER EXPRESSIONS
            # ==================================================
            member_expressions = re.findall(
                r"[a-zA-Z_][a-zA-Z0-9_\.]+",
                clean_line
            )

            for expr in member_expressions:
                if "." in expr:
                    result[
                        "member_expressions"
                    ].append(
                        expr
                    )

            # ==================================================
            # ASSIGNMENTS
            # ==================================================
            assignment_match = re.search(
                r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=",
                clean_line
            )

            if assignment_match:
                result[
                    "assignments"
                ].append(
                    assignment_match.group(1)
                )

        # ======================================================
        # REMOVE DUPLICATES
        # ======================================================

        for key in result:

            result[key] = list(

                set(result[key])
            )

        return result