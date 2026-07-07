import os
# from config.debug_flags import *
from config.settings import *
from utils.logger import (
    logger
)


class FunctionIndex:

    def __init__(self):
        self.functions = {}

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

        self.functions[file_path][
            function_name
        ] = metadata

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