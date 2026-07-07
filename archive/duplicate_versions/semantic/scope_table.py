# ==========================================================
# SCOPE TABLE
# ==========================================================

class ScopeTable:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        self.scopes = {}

    # ======================================================
    # REGISTER SCOPE ITEM
    # ======================================================

    def register(

        self,

        file_path,

        function_name,

        category,

        value
    ):

        # ==================================================
        # FILE
        # ==================================================

        if file_path not in self.scopes:

            self.scopes[file_path] = {}

        # ==================================================
        # FUNCTION
        # ==================================================

        if (

            function_name

            not in

            self.scopes[file_path]
        ):

            self.scopes[file_path][
                function_name
            ] = {

                "params": set(),

                "locals": set(),

                "imports": set(),

                "aliases": set(),

                "members": set()
            }

        scope = self.scopes[
            file_path
        ][
            function_name
        ]

        # ==================================================
        # REGISTER
        # ==================================================

        if category in scope:

            scope[category].add(
                value
            )

    # ======================================================
    # GET SCOPE
    # ======================================================

    def get_scope(

        self,

        file_path,

        function_name
    ):

        return (

            self.scopes

            .get(file_path, {})

            .get(function_name, {})
        )

    # ======================================================
    # TO DICT
    # ======================================================

    def to_dict(self):

        result = {}

        for file_path, functions in (

            self.scopes.items()
        ):

            result[file_path] = {}

            for fn_name, scope in (

                functions.items()
            ):

                result[file_path][fn_name] = {

                    key: list(values)

                    for key, values in scope.items()
                }

        return result