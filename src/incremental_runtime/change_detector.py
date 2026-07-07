import subprocess
import re
import os


class ChangeDetector:

    def __init__(self):

        pass

    # ======================================================
    # GET GIT DIFF
    # ======================================================
    
    def get_git_diff(self):

        # result = subprocess.run(

        #     [
        #         "git",
        #         "diff",
        #         "--unified=0"
        #     ],

        #     capture_output=True,

        #     text=True
        # )

        result = subprocess.run(

            [
                "git",
                "diff",
                "--unified=0"
            ],

            cwd=os.getcwd(),

            capture_output=True,

            text=True
        )

        return result.stdout

    # ======================================================
    # EXTRACT CHANGED FILES + LINES
    # ======================================================

    def extract_changes(
        self,
        diff_text
    ):

        changes = []

        current_file = None

        for line in diff_text.splitlines():

            # ==============================================
            # FILE
            # ==============================================

            if line.startswith("+++ b/"):

                current_file = (
                    line.replace(
                        "+++ b/",
                        ""
                    )
                )

            # ==============================================
            # HUNK
            # ==============================================

            elif line.startswith("@@"):

                match = re.search(

                    r"\+(\d+)(?:,(\d+))?",

                    line
                )

                if not match:
                    continue

                start_line = int(
                    match.group(1)
                )

                line_count = match.group(2)

                if line_count:
                    line_count = int(line_count)
                else:
                    line_count = 1

                changed_lines = list(

                    range(

                        start_line,

                        start_line + line_count
                    )
                )

                changes.append({

                    "file": current_file,

                    "changed_lines":
                    changed_lines
                })

        return changes