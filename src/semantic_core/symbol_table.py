import os
class SymbolTable:

    def __init__(self):

        self.imports = {}
        self.aliases = {}
        self.destructured = {}

    @property
    def registry(self):
        """Compatibility property for tests."""
        return self.imports

    # ======================================================
    # REGISTER IMPORT
    # ======================================================

    def register_import(
        self,
        file_path,
        import_name,
        import_source
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")

        if file_path not in self.imports:

            self.imports[file_path] = {}

        normalized = os.path.normpath(

            os.path.join(
                os.path.dirname(file_path),
                import_source
            )
        ).replace("\\",'/')

        if not normalized.endswith(".js"):
            normalized += ".js"
            
        self.imports[file_path][
            import_name
        ] = normalized
    # ======================================================
    # RESOLVE SYMBOL
    # ======================================================


    # ======================================================
    # REGISTER ALIAS
    # ======================================================

    def register_alias(

        self,

        file_path,

        scope_id,

        alias_name,

        original_name
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")

        if file_path not in self.aliases:

            self.aliases[file_path] = {}

        if scope_id not in self.aliases[file_path]:

            self.aliases[file_path][scope_id] = {}

        self.aliases[file_path][scope_id][
            alias_name
        ] = original_name


    def resolve_import(
        self,
        file_path,
        symbol_name
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")

        if file_path not in self.imports:
            return None

        return self.imports[
            file_path
        ].get(symbol_name)
    

    # ======================================================
    # RESOLVE ALIAS
    # ======================================================

    # def resolve_alias(

    #     self,

    #     file_path,

    #     symbol_name
    # ):

    #     if file_path not in self.aliases:

    #         return symbol_name

    #     return self.aliases[
    #         file_path
    #     ].get(

    #         symbol_name,

    #         symbol_name
    #     )
    def resolve_alias(

        self,

        file_path,

        scope_id,

        alias_name
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")

        if file_path not in self.aliases:

            return alias_name

        # ======================================================
        # CHECK CURRENT SCOPE
        # ======================================================

        if (

            scope_id in self.aliases[file_path]

            and

            alias_name in self.aliases[file_path][scope_id]
        ):

            return self.aliases[file_path][scope_id][
                alias_name
            ]

        # ======================================================
        # FALLBACK TO GLOBAL
        # ======================================================

        if (

            "GLOBAL" in self.aliases[file_path]

            and

            alias_name in self.aliases[file_path]["GLOBAL"]
        ):

            return self.aliases[file_path]["GLOBAL"][
                alias_name
            ]

        return alias_name

    # ======================================================
    # REGISTER DESTRUCTURED SYMBOL
    # ======================================================

    def register_destructured(
        self,
        file_path,
        local_name,
        source_object
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        if file_path not in self.destructured:
            self.destructured[file_path] = {}

        self.destructured[file_path][
            local_name
        ] = {
            "source": source_object,
            "function": local_name
        }


    # ======================================================
    # RESOLVE DESTRUCTURED SYMBOL
    # ======================================================

    def resolve_destructured(

        self,

        file_path,

        function_name
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")

        if file_path not in self.destructured:

            return None

        return self.destructured[
            file_path
        ].get(function_name)