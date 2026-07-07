# ==========================================================
# PATCH VALIDATOR
# ==========================================================

import os

from language_config import (
    LanguageManager
)

# ==========================================================
# INIT
# ==========================================================

langmanager = LanguageManager()


class PatchValidator:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        project_root
    ):

        self.project_root = project_root

    # ======================================================
    # VALIDATE PATCH
    # ======================================================

    def validate_patch(

        self,

        patch
    ):

        file_path = patch.get(
            "file"
        )

        patch_content = patch.get(
            "patch"
        )

        if not file_path:

            return {

                "valid": False,

                "reason":
                    "Missing file path"
            }

        # ==================================================
        # ABSOLUTE FILE
        # ==================================================

        abs_path = os.path.join(

            self.project_root,

            file_path
        )

        if not os.path.exists(
            abs_path
        ):

            return {

                "valid": False,

                "reason":
                    "Target file not found"
            }

        # ==================================================
        # READ ORIGINAL FILE
        # ==================================================

        try:

            with open(

                abs_path,

                "r",

                encoding="utf-8"
            ) as f:

                original_code = (
                    f.read()
                )

        except Exception as e:

            return {

                "valid": False,

                "reason":
                    str(e)
            }

        # ==================================================
        # APPLY PATCH VIRTUALLY
        # ==================================================

        patched_code = (
            self.apply_virtual_patch(

                original_code,

                patch_content
            )
        )

        # ==================================================
        # PARSE TEST
        # ==================================================

        _, ext = os.path.splitext(
            abs_path
        )

        try:

            parser = (
                langmanager.get_parser(
                    ext
                )
            )

            tree = parser.parse(

                patched_code.encode(
                    "utf-8"
                )
            )

            # ==============================================
            # TREE-SITTER ERROR CHECK
            # ==============================================

            has_error = (
                tree.root_node.has_error
            )

            if has_error:

                return {

                    "valid": False,

                    "reason":
                        "AST syntax error"
                }

            return {

                "valid": True,

                "reason":
                    "Patch syntax valid"
            }

        except Exception as e:

            return {

                "valid": False,

                "reason":
                    str(e)
            }

    # ======================================================
    # APPLY VIRTUAL PATCH
    # ======================================================

    def apply_virtual_patch(

        self,

        original_code,

        patch_content
    ):

        patched_code = original_code

        lines = patch_content.splitlines()

        remove_lines = []

        add_lines = []

        # ==================================================
        # PARSE PATCH
        # ==================================================

        for line in lines:

            # ==============================================
            # REMOVED
            # ==============================================

            if (

                line.startswith("-")

                and

                not line.startswith("---")
            ):

                remove_lines.append(
                    line[1:]
                )

            # ==============================================
            # ADDED
            # ==============================================

            elif (

                line.startswith("+")

                and

                not line.startswith("+++")
            ):

                add_lines.append(
                    line[1:]
                )

        # ==================================================
        # APPLY REMOVALS
        # ==================================================

        for remove_line in remove_lines:

            patched_code = (
                patched_code.replace(

                    remove_line,

                    ""
                )
            )

        # ==================================================
        # APPLY ADDITIONS
        # ==================================================

        if add_lines:

            patched_code += (

                "\n"

                + "\n".join(add_lines)
            )

        return patched_code