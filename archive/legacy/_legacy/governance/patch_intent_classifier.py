# ==========================================================
# PATCH INTENT CLASSIFIER
# ==========================================================

import re


class PatchIntentClassifier:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        self.comment_patterns = [

            r"^\s*//",

            r"^\s*/\*",

            r"^\s*\*"
        ]

        self.non_actionable_patterns = [

            r"no direct patch",

            r"review manually",

            r"consider introducing",

            r"consider breaking down",

            r"consider abstraction"
        ]

    # ======================================================
    # CLASSIFY
    # ======================================================

    def classify(

        self,

        patch
    ):

        patch_content = patch.get(
            "patch",
            ""
        ).strip()

        # ==================================================
        # EMPTY PATCH
        # ==================================================

        if not patch_content:

            return {

                "intent":
                    "NON_ACTIONABLE",

                "executable":
                    False,

                "confidence":
                    1.0,

                "reason":
                    "Patch content empty"
            }

        lowered = patch_content.lower()

        # ==================================================
        # NON ACTIONABLE
        # ==================================================

        for pattern in self.non_actionable_patterns:

            if pattern in lowered:

                return {

                    "intent":
                        "NON_ACTIONABLE",

                    "executable":
                        False,

                    "confidence":
                        0.95,

                    "reason":
                        f"Matched non-actionable "
                        f"pattern '{pattern}'"
                }

        # ==================================================
        # COMMENT ONLY
        # ==================================================

        lines = [

            line.strip()

            for line in patch_content.splitlines()

            if line.strip()
        ]

        comment_only = True

        for line in lines:

            matched = False

            for pattern in self.comment_patterns:

                if re.match(

                    pattern,

                    line
                ):

                    matched = True
                    break

            if not matched:

                comment_only = False
                break

        if comment_only:

            return {

                "intent":
                    "COMMENT_ONLY",

                "executable":
                    False,

                "confidence":
                    0.95,

                "reason":
                    "Patch only contains comments"
            }

        # ==================================================
        # EXECUTABLE REMEDIATION
        # ==================================================

        executable_indicators = [

            "+ ",

            "- ",

            "=",

            "return ",

            "const ",

            "let ",

            "await "
        ]

        executable = False

        for indicator in executable_indicators:

            if indicator in patch_content:

                executable = True
                break

        if executable:

            return {

                "intent":
                    "EXECUTABLE_REMEDIATION",

                "executable":
                    True,

                "confidence":
                    0.90,

                "reason":
                    "Patch contains executable code changes"
            }

        # ==================================================
        # ADVISORY
        # ==================================================

        return {

            "intent":
                "ADVISORY",

            "executable":
                False,

            "confidence":
                0.70,

            "reason":
                "Patch appears advisory"
        }