import os
# from config.debug_flags import *
from config.settings import *
from utils.logger import (
    logger
)


class FunctionIndex:

    def __init__(self):
        self.functions = {}
        # file -> name -> [metadata, ...] for every definition, in registration order; the
        # flat `functions` map keeps one entry per name for the historical API
        self.all_defs = {}

    @property
    def registry(self):
        """Compatibility property for tests."""
        return self.functions

    # ======================================================
    # REGISTER FUNCTION
    # ======================================================

    def register_function(
        self,
        file_path,
        function_name,
        metadata
    ):

        if DEBUG_FUNCTION_INDEX:
            # print(
            #     "\nREGISTERING FUNCTION:",
            #     file_path,
            #     function_name
            # )
            logger.debug(

                f"REGISTERING FUNCTION :: "

                f"{file_path} :: "

                f"{function_name}"
            )
        file_path = os.path.normpath(
            file_path
        ).replace("\\","/")
        if file_path not in self.functions:

            self.functions[file_path] = {}

        self.all_defs.setdefault(file_path, {}).setdefault(function_name, []).append(metadata)
        existing = self.functions[file_path].get(function_name)
        if (existing is not None and "." not in function_name
                and not existing.get("class") and isinstance(metadata, dict) and metadata.get("class")):
            # the bare name already points at a module-level function; a same-named method
            # must not shadow it (it is reachable as "Class.name")
            return
        self.functions[file_path][
            function_name
        ] = metadata

    def resolve_nearest(self, file_path, function_name, call_line):
        """For a bare call inside file_path: the same-named MODULE-LEVEL definition closest
        before the call (bundles define `edit$1` twice; the nearest one is in scope), else the
        first one after it (hoisting), else None."""
        file_path = os.path.normpath(file_path).replace("\\", "/")
        defs = [m for m in self.all_defs.get(file_path, {}).get(function_name, []) if isinstance(m, dict) and not m.get("class")]
        if not defs:
            return None
        before = [m for m in defs if (m.get("start_line") or 0) <= (call_line or 0)]
        if before:
            return max(before, key=lambda m: m.get("start_line") or 0)
        return min(defs, key=lambda m: m.get("start_line") or 0)

    def resolve_static(self, file_path, class_name, method, want_static):
        """Class.method where the class has both a static and an instance method of that name."""
        file_path = os.path.normpath(file_path).replace("\\", "/")
        defs = [m for m in self.all_defs.get(file_path, {}).get(f"{class_name}.{method}", []) if isinstance(m, dict)]
        if not defs:
            return None
        pref = [m for m in defs if bool(m.get("static")) == bool(want_static)]
        return (pref or defs)[0]

    # ======================================================
    # RESOLVE FUNCTION
    # ======================================================

    def resolve_function(
        self,
        file_path,
        function_name
    ):

        if DEBUG_FUNCTION_INDEX:
            logger.debug(
                "FUNCTION INDEX"
            )

            logger.debug(
                self.functions
            )
            # print(
            #     "\nFUNCTION INDEX:"
            # )

            # print(self.functions)
        file_path = os.path.normpath(
            file_path
        ).replace("\\","/")
        if file_path not in self.functions:
            return None

        return self.functions[
            file_path
        ].get(function_name)