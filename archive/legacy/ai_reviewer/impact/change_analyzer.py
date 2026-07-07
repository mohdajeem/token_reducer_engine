# ==========================================================
# SEMANTIC CHANGE ANALYZER
# ==========================================================

import subprocess
import re
from utils.logger import (
    logger
)

from config.settings import *


class ChangeAnalyzer:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph,

        repo_path,

        function_index
    ):

        self.graph = graph

        self.repo_path = repo_path

        self.function_index = function_index
    # ======================================================
    # GET GIT DIFF
    # ======================================================

    def get_git_diff(self):

        try:

            result = subprocess.run(

                [

                    "git",

                    "diff"
                ],

                capture_output=True,

                text=True,

                cwd=self.repo_path
            )

            return result.stdout

        except Exception as e:
            logger.error(
                f"Git diff failed :: {e}"
            )

            return ""

    # ======================================================
    # ANALYZE CHANGES
    # ======================================================

    def analyze_changes(

        self,

        diff_text
    ):

        result = {

            "changed_files": [],

            "changed_functions": [],

            "change_types": [],

            "diff_hunks": []
        }

        # ======================================================
        # CURRENT FILE
        # ======================================================

        current_file = None

        lines = diff_text.splitlines()

        # ======================================================
        # GIT HUNK TRACKING
        # ======================================================

        current_line_number = 0

        current_hunk_line = 0

        # ======================================================
        # CURRENT DIFF HUNK
        # ======================================================

        current_hunk = {

            "file": None,

            "added": [],

            "removed": []
        }

        # ======================================================
        # ITERATE DIFF
        # ======================================================

        for line in lines:

            # ==================================================
            # FILE DETECTION
            # ==================================================

            if line.startswith("+++ b/"):

                # ==============================================
                # STORE PREVIOUS HUNK
                # ==============================================

                if (

                    current_hunk["added"]

                    or

                    current_hunk["removed"]
                ):

                    result[
                        "diff_hunks"
                    ].append(
                        current_hunk
                    )

                # ==============================================
                # NEW FILE
                # ==============================================

                current_file = (

                    line.replace(
                        "+++ b/",
                        ""
                    )
                )

                current_hunk = {

                    "file": current_file,

                    "added": [],

                    "removed": []
                }

                # ==============================================
                # STORE FILE
                # ==============================================

                if (

                    current_file

                    not in

                    result[
                        "changed_files"
                    ]
                ):

                    result[
                        "changed_files"
                    ].append(
                        current_file
                    )

                continue

            # ==================================================
            # GIT HUNK HEADER
            # @@ -21,6 +21,7 @@
            # ==================================================

            hunk_match = re.match(

                r"@@ -\d+(?:,\d+)? \+(\d+)",

                line
            )

            if hunk_match:

                current_hunk_line = int(

                    hunk_match.group(1)
                )

                continue

            # ==================================================
            # TRACK NEW FILE LINE NUMBERS
            # ==================================================

            if (

                line.startswith("+")

                and

                not line.startswith("+++")
            ):

                current_line_number = (
                    current_hunk_line
                )

                current_hunk_line += 1

            elif (

                not line.startswith("-")

                and

                not line.startswith("---")
            ):

                current_hunk_line += 1

            # ==================================================
            # REMOVED LINES
            # ==================================================

            if (

                line.startswith("-")

                and

                not line.startswith("---")
            ):

                current_hunk[
                    "removed"
                ].append(

                    line[1:]
                )

            # ==================================================
            # ADDED LINES
            # ==================================================

            if (

                line.startswith("+")

                and

                not line.startswith("+++")
            ):

                current_hunk[
                    "added"
                ].append(

                    line[1:]
                )

            # ==================================================
            # FUNCTION OWNERSHIP
            # ==================================================

            if (

                line.startswith("+")

                and

                not line.startswith("+++")
            ):

                changed_function = (

                    self.detect_function_owner(

                        current_file,

                        current_line_number
                    )
                )

                if changed_function:

                    if (

                        changed_function

                        not in

                        result[
                            "changed_functions"
                        ]
                    ):

                        result[
                            "changed_functions"
                        ].append(
                            changed_function
                        )

            # ==================================================
            # SECURITY CHANGE DETECTION
            # ==================================================

            security_change = (

                self.detect_security_change(
                    line
                )
            )

            if security_change:

                if (

                    security_change

                    not in

                    result[
                        "change_types"
                    ]
                ):

                    result[
                        "change_types"
                    ].append(
                        security_change
                    )

        # ======================================================
        # STORE FINAL HUNK
        # ======================================================

        if (

            current_hunk["added"]

            or

            current_hunk["removed"]
        ):

            result[
                "diff_hunks"
            ].append(
                current_hunk
            )

        return result

    # ======================================================
    # DETECT FUNCTION CHANGE
    # ======================================================

    # ==========================================================
    # DETECT FUNCTION OWNER
    # ==========================================================

    def detect_function_owner(

        self,

        file_path,

        changed_line_number
    ):

        if not file_path:
            return None


        # print("\nDEBUG FILE PATH:")
        # print("DIFF FILE:", file_path)

        # print("\nFUNCTION INDEX FILES:")
        # print(
        #     list(
        #         self.function_index.functions.keys()
        #     )
        # )
        if DEBUG_CHANGE_ANALYZER:

            logger.debug(

                f"DIFF FILE :: "

                f"{file_path}"
            )

            logger.debug(

                "FUNCTION INDEX FILES :: "

                f"{list(self.function_index.functions.keys())}"
            )


        functions = self.function_index.functions.get(
            file_path,
            {}
        )

        for function_name, metadata in functions.items():

            start_line = metadata.get(
                "start_line"
            )

            end_line = metadata.get(
                "end_line"
            )

            if (

                start_line is None

                or

                end_line is None
            ):

                continue

            # ==================================================
            # LINE INSIDE FUNCTION
            # ==================================================

            if (

                changed_line_number >= start_line

                and

                changed_line_number <= end_line
            ):

                return {

                    "file": file_path,

                    "function": function_name
                }

        return None



    # ======================================================
    # DETECT SECURITY CHANGE
    # ======================================================

    def detect_security_change(

        self,

        line
    ):

        patterns = {

            "RAW_SQL":

                r"SELECT|INSERT|UPDATE|DELETE",

            "PASSWORD_FLOW":

                r"password",

            "TOKEN_USAGE":

                r"token|jwt",

            "USER_INPUT":

                r"req\.body|req\.query|req\.params"
        }

        for change_type, pattern in patterns.items():

            if re.search(

                pattern,

                line,

                re.IGNORECASE
            ):

                return change_type

        return None