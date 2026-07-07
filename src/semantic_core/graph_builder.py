from dotenv import load_dotenv

load_dotenv()

from semantic_core.symbol_table import (
    SymbolTable
)

from semantic_core.function_index import (
    FunctionIndex
)

# from config.debug_flags import *
from config.settings import *

from semantic_core.frameworks.express_route_normalizer import (
    ExpressRouteNormalizer
)


class GraphBuilder:
    """
    Central compiler engine for constructing a queryable semantic graph from Tree-sitter match captures.
    
    Coordinates the ingestion of strongly-typed SemanticMatch objects, maps scopes, 
    resolves static linkages via the SymbolTable, compiles inter-procedural call graphs, 
    evaluates parameter-argument data flows, and triggers security taint audits.
    """

    def __init__(self):
        """
        Initializes the Semantic Graph schema dictionary, the symbol linkage table, 
        the function metadata index registry, and Express routing normalization sub-engines.
        """

        self.graph = {

            "imports": {},

            "routes": {},

            "calls": {},

            "database": {},

            "functions": {},

            "errors": {},

            "contracts": {},

            "execution_edges": [],

            "parameters": {},

            "arguments": {},

            "data_flow": [],

            "taint_sources": [],

            "security_sinks": [],

            "security_findings": [],

            "sanitizers": [],

            "variable_states": [],

            "returns": [],
        }
        self.symbol_table = SymbolTable()
        self.function_index = (
            FunctionIndex()
        )
        self.model_registry = {} # Maps Mongoose model name to file path
        self.route_normalizer = (
            ExpressRouteNormalizer(

                self.symbol_table,

                self.function_index
            )
        )
        # sm.owner_function = None

    # ======================================================
    # MAIN ENTRY
    # ======================================================

    def build(
        self,
        semantic_matches
    ):
        """
        Ingests a list of extracted SemanticMatch blocks and executes multi-pass compilation 
        to compile execution edges, symbol linkages, parameters, data flows, and taint analysis.
        
        Args:
            semantic_matches (List[SemanticMatch]): Strongly-typed matches representing captured AST nodes.
            
        Returns:
            Dict: The complete, traced Semantic Graph dictionary.
        """
        
        self.semantic_matches = semantic_matches

        if DEBUG_MATCHES:
            print("\nBUILD RECEIVED MATCHES:")
            for sm in semantic_matches:

                print(
                    sm.match_type,
                    sm.captures
                )

        # ======================================================
        # PASS 0 — MODEL DECLARATIONS
        # ======================================================
        for sm in semantic_matches:
            if sm.match_type == "MODEL_DECLARATION":
                self.handle_model_declaration(sm)

        # ======================================================
        # PASS 1 — IMPORTS
        # ======================================================

        for sm in semantic_matches:
            if sm.match_type == "IMPORT":
                self.handle_import(sm)

        # ======================================================
        # PASS 2 — SYMBOL ALIASES
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "SYMBOL_ALIAS":

                self.handle_symbol_alias(sm)
        
        # ======================================================
        # PASS — DESTRUCTURED SYMBOLS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "DESTRUCTURE_ALIAS":

                self.handle_destructure_alias(sm)

        # ======================================================
        # PASS 3 — FUNCTION DEFINITIONS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "FUNCTION_DEF":

                self.handle_function_def(sm)

        # ======================================================
        # PASS — FUNCTION PARAMETERS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "FUNCTION_PARAMS":

                self.handle_function_params(sm)

        # ======================================================
        # PASS — RETURN VALUES
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "RETURN_VALUE":

                self.handle_return_value(sm)

        # ======================================================
        # PASS 4 — ROUTES
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "ROUTE":

                self.handle_route(sm)

        # ======================================================
        # PASS — CALL ARGUMENTS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "CALL_ARGUMENTS":

                self.handle_call_arguments(sm)

        # ======================================================
        # PASS 5 — CALLS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "CALL":

                self.handle_call(sm)

        # ======================================================
        # PASS 6 — DATABASE
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "DATABASE":

                self.handle_database(sm)

        # ======================================================
        # PASS 7 — ERRORS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "ERROR":

                self.handle_error(sm)

        # ======================================================
        # PASS 8 — CONTRACTS
        # ======================================================

        for sm in semantic_matches:

            if sm.match_type == "CONTRACT":

                self.handle_contract(sm)
        
        # ======================================================
        # BUILD DATA FLOW
        # ======================================================

        self.build_argument_parameter_flow()

        # ======================================================
        # DETECT TAINT SOURCES
        # ======================================================

        self.detect_taint_sources()

        # ======================================================
        # PROPAGATE RETURN TAINT
        # ======================================================

        self.propagate_return_taint()

        # ======================================================
        # DETECT SECURITY SINKS
        # ======================================================

        self.detect_security_sinks()
        # ======================================================
        # DETECT SANITIZERS
        # ======================================================

        self.detect_sanitizers()

        # ======================================================
        # TRACK VARIABLE STATES
        # ======================================================

        self.track_variable_states()
        # ======================================================
        # DETECT VULNERABILITIES
        # ======================================================

        self.detect_vulnerabilities()

        return self.graph


    


    # ======================================================
    #  BUILD SINGLE FILE
    # ======================================================

    def build_file(

        self,

        file_path,

        semantic_matches
    ):

        # ==================================================
        # STORE FILE MATCHES
        # ==================================================

        self.current_file_matches = (
            semantic_matches
        )

        # ==================================================
        # PASS 1 — IMPORTS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "IMPORT":

                self.handle_import(sm)

        # ==================================================
        # PASS 2 — SYMBOL ALIASES
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "SYMBOL_ALIAS":

                self.handle_symbol_alias(sm)

        # ==================================================
        # PASS 3 — DESTRUCTURED
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "DESTRUCTURE_ALIAS":

                self.handle_destructure_alias(sm)

        # ==================================================
        # PASS 4 — FUNCTIONS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "FUNCTION_DEF":

                self.handle_function_def(sm)

        # ==================================================
        # PASS 5 — PARAMETERS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "FUNCTION_PARAMS":

                self.handle_function_params(sm)

        # ==================================================
        # PASS 6 — RETURNS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "RETURN_VALUE":

                self.handle_return_value(sm)

        # ==================================================
        # PASS 7 — ROUTES
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "ROUTE":

                self.handle_route(sm)

        # ==================================================
        # PASS 8 — ARGUMENTS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "CALL_ARGUMENTS":

                self.handle_call_arguments(sm)

        # ==================================================
        # PASS 9 — CALLS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "CALL":

                self.handle_call(sm)

        # ==================================================
        # PASS 10 — DATABASE
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "DATABASE":

                self.handle_database(sm)

        # ==================================================
        # PASS 11 — ERRORS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "ERROR":

                self.handle_error(sm)

        # ==================================================
        # PASS 12 — CONTRACTS
        # ==================================================

        for sm in semantic_matches:

            if sm.match_type == "CONTRACT":

                self.handle_contract(sm)

        # ==================================================
        # FILE-SCOPED FLOW BUILD
        # ==================================================

        self.build_argument_parameter_flow()

        self.detect_taint_sources()

        self.propagate_return_taint()

        self.detect_security_sinks()

        self.detect_sanitizers()

        self.track_variable_states_for_matches(
            semantic_matches
        )

        self.detect_vulnerabilities()

        return self.graph


    # ======================================================
    # HELPERS
    # ======================================================

    def ensure_file(self, section, file_path):

        if file_path not in self.graph[section]:

            self.graph[section][file_path] = []

    # ==========================================================
    # SYMBOL ALIAS
    # ==========================================================

    def handle_symbol_alias(

        self,

        sm
    ):

        alias_name = sm.get(
            "alias.name"
        )

        actual_name = sm.get(
            "alias.value"
        )

        self.symbol_table.register_alias(

            sm.file_path,

            sm.scope_id,

            alias_name,

            actual_name
        )

    # ======================================================
    # IMPORTS
    # ======================================================

    def handle_import(self, sm):

        self.ensure_file(
            "imports",
            sm.file_path
        )

        self.symbol_table.register_import(
            file_path=sm.file_path,
            import_name=(
                sm.get("import.alias")
                or
                sm.get("import.name")
            ),

            import_source=sm.get(
                "import.source"
            )
        )

        self.graph["imports"][
            sm.file_path
        ].append({

            "source": sm.get(
                "import.source"
            ),

            "name": sm.get(
                "import.name"
            ),

            "alias": sm.get(
                "import.alias"
            )
        })

    # ======================================================
    # ROUTES
    # ======================================================

    # def handle_route(self, sm):
    #     print("z"*80)
    #     print("semantic_match in handle_route:",sm)
    #     print("z"*80)
    #     self.ensure_file(
    #         "routes",
    #         sm.file_path
    #     )

    #     controller_name = sm.get(
    #         "handler.controller"
    #     )

    #     resolved_file = (
    #         self.symbol_table.resolve_import(
    #             sm.file_path,
    #             controller_name
    #         )
    #     )
    #     function_name = sm.get(
    #         "handler.function"
    #     )

    #     resolved_function = None

    #     if resolved_file:
            
    #         resolved_function = (
    #             self.function_index.resolve_function(
    #                 resolved_file,
    #                 function_name
    #             )
    #         )
        

    #     self.graph["routes"][
    #         sm.file_path
    #     ].append({

    #         "method": (
    #             sm.get(
    #                 "endpoint.served_method"
    #             )
    #         ),

    #         "path": (
    #             sm.get(
    #                 "endpoint.served_route"
    #             )
    #         ),

    #         "router": (
    #             sm.get(
    #                 "router.obj"
    #             )
    #         ),
    #         "handler": {

    #             "controller": controller_name,

    #             "function": sm.get(
    #                 "handler.function"
    #             ),

    #             "resolved_file": resolved_file,

    #             "resolved_function": resolved_function
    #         },
            
    #     })
    #     print("\n[ROUTE DEBUG]")
    #     print("graph:",self.graph["routes"][sm.file_path][-1])
    #     # ==================================================
    #     # EXECUTION EDGE
    #     # ==================================================

    #     self.add_execution_edge(

    #         from_node={

    #             "type": "ROUTE",

    #             "route": sm.get(
    #                 "endpoint.served_route"
    #             ),

    #             "method": sm.get(
    #                 "endpoint.served_method"
    #             )
    #         },

    #         to_node={

    #             "type": "FUNCTION",

    #             "file": resolved_file,

    #             "function": function_name,

    #             "resolved_function":
    #             resolved_function
    #         },

    #         edge_type="ROUTE_CALL"
    #     )


    def handle_route(
        self,
        sm
    ):

        # print("z" * 80)
        # print("semantic_match in handle_route:", sm)
        # print("z" * 80)

        self.ensure_file(
            "routes",
            sm.file_path
        )

        # ==================================================
        # NORMALIZE ROUTE
        # ==================================================

        normalized_route = (

            self.route_normalizer
            .normalize_route(sm)
        )
        # normalized_route = sm.captures.get("route.arguments", [])

        if not normalized_route:
            return

        # ==================================================
        # STORE ROUTE
        # ==================================================

        self.graph["routes"][
            sm.file_path
        ].append(
            normalized_route
        )

        # ==================================================
        # ROUTE → HANDLER EDGE
        # ==================================================

        handler = (
            normalized_route.get(
                "handler",
                {}
            )
        )
        # print("normalized_route in handle_route:",normalized_route)
        self.add_execution_edge(

            from_node={

                "type": "ROUTE",

                "route":
                    normalized_route.get(
                        "path"
                    ),

                "method":
                    normalized_route.get(
                        "method"
                    ),

                "file": sm.file_path
            },

            to_node={

                "type": "FUNCTION",

                "file":
                    handler.get(
                        "resolved_file"
                    ) or sm.file_path,

                "function":
                    handler.get(
                        "function"
                    ) or "GLOBAL_SCOPE",

                "resolved_function":
                    handler.get(
                        "resolved_function"
                    )
            },

            edge_type="ROUTE_CALL"
        )

        # ==================================================
        # MIDDLEWARE EDGES
        # ==================================================

        middlewares = (
            normalized_route.get(
                "middlewares",
                []
            )
        )

        for middleware in middlewares:

            self.add_execution_edge(

                from_node={

                    "type": "ROUTE",

                    "route":
                        normalized_route.get(
                            "path"
                        ),

                    "method":
                        normalized_route.get(
                            "method"
                        ),

                    "file": sm.file_path
                },

                to_node={

                    "type": "MIDDLEWARE",

                    "file":
                        middleware.get(
                            "resolved_file"
                        ) or sm.file_path,

                    "function":
                        middleware.get(
                            "function"
                        ) or "GLOBAL_SCOPE",

                    "resolved_function":
                        middleware.get(
                            "resolved_function"
                        )
                },

                edge_type="ROUTE_MIDDLEWARE"
            )


    # ======================================================
    # FUNCTION DEFINITIONS
    # ======================================================

    def handle_function_def(self, sm):

        function_name = sm.get(
            "function.name"
        )

        self.ensure_file(
            "functions",
            sm.file_path
        )

        self.function_index.register_function(

            file_path=sm.file_path,

            function_name=function_name,

            metadata={

                "name": function_name,

                "file": sm.file_path,

                "start_line":
                    sm.start_point[0] + 1,

                "end_line":
                    sm.end_point[0] + 1
            }

            # metadata={

            #     "name": function_name,

            #     "file": sm.file_path
            # }
        )
        # print("\nFUNCTION INDEX METADATA:")
        # print(metadata)
        # sm.owner_function = function_name

        self.graph["functions"][
            sm.file_path
        ].append({

            "name": function_name,

            "file": sm.file_path,

            "start_line": sm.start_point[0] + 1,

            "end_line": sm.end_point[0] + 1
        })

    # ======================================================
    # CALLS
    # ======================================================

    def handle_call(self, sm):
        # print("\nCALL MATCH")
        # print("start:", sm.start_byte)
        # print("end:", sm.end_byte)
        # print("captures:", sm.captures)

        raw_object_name = sm.get(
            "call.obj_name"
        )

        obj = (
            self.symbol_table.resolve_alias(

                sm.file_path,

                sm.scope_id,

                raw_object_name
            )
        )

        func = sm.get(
            "call.func_name"
        )


        # ==================================================
        # DESTRUCTURED FUNCTION RESOLUTION
        # ==================================================

        destructured = (
            self.symbol_table.resolve_destructured(

                sm.file_path,

                func
            )
        )

        if destructured:

            obj = destructured["source"]

            raw_object_name = obj



        # ==================================================
        # RESOLVE FILE
        # ==================================================

        resolved_file = None

        if obj:

            resolved_file = (
                self.symbol_table.resolve_import(
                    sm.file_path,
                    obj
                )
            )

        # ==================================================
        # RESOLVE FUNCTION
        # ==================================================

        resolved_function = None
        if destructured:
            obj = destructured["source"]

        if resolved_file:
            
            resolved_function = (
                self.function_index.resolve_function(
                    resolved_file,
                    func
                )
            )

        # ==============================================
        # FALLBACK 1 — DESTRUCTURED IMPORT
        # ==============================================
        if not resolved_function and not obj:
            destructured_fallback = (
                self.symbol_table
                .resolve_destructured(sm.file_path, func)
            )
            if destructured_fallback:
                source_obj = destructured_fallback.get("source")
                func_name = destructured_fallback.get("function")
                if source_obj and func_name:
                    resolved_import_file = (
                        self.symbol_table
                        .resolve_import(sm.file_path, source_obj)
                    )
                    if resolved_import_file:
                        resolved_file = resolved_import_file
                        obj = source_obj
                        func = func_name
                        resolved_function = (
                            self.function_index
                            .resolve_function(resolved_file, func_name)
                        )

        # ==============================================
        # FALLBACK 2 — DIRECT FUNCTION IMPORT
        # ==============================================
        if not resolved_function and not obj:
            direct_import_file = (
                self.symbol_table
                .resolve_import(sm.file_path, func)
            )
            if direct_import_file:
                resolved_file = direct_import_file
                resolved_function = (
                    self.function_index
                    .resolve_function(resolved_file, func)
                )

        # ==============================================
        # FALLBACK 3 — LOCAL DEFINITION
        # ==============================================
        if not resolved_function and not obj:
            local_function = (
                self.function_index
                .resolve_function(sm.file_path, func)
            )
            if local_function:
                resolved_file = sm.file_path
                resolved_function = local_function

        # ==================================================
        # FILTER FRAMEWORK NOISE
        # ==================================================

        ignored_objects = {
            "router",
            "app",
            "express"
        }

        ignored_functions = {
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "use",
            "Router"
        }

        if (
            obj in ignored_objects
            and
            func in ignored_functions
        ):
            return

        self.ensure_file(
            "calls",
            sm.file_path
        )

        # ==================================================
        # STORE GRAPH
        # ==================================================
        call_id = self.build_call_id(sm)

        self.graph["calls"][
            sm.file_path
        ].append({
            "call_id": call_id,

            "object": obj,

            "function": func,

            "resolved_file":
            resolved_file,

            "resolved_function":
            resolved_function,

            "caller_function":
            sm.owner_function
        })
        # ==================================================
        # EXECUTION EDGE
        # ==================================================
        # print("\n[CALL DEBUG]")
        # print("OBJ:", obj)
        # print("FUNC:", func)
        # print("RESOLVED FILE:", resolved_file)
        # print("RESOLVED FUNCTION:", resolved_function)

        if resolved_file or resolved_function:

            self.add_execution_edge(

                from_node={

                    "type": "FUNCTION",

                    "file": sm.file_path,

                    "function": sm.owner_function or "GLOBAL_SCOPE"
                },

                to_node={

                    "type": "FUNCTION",

                    "file": resolved_file or sm.file_path,

                    "function": func or "GLOBAL_SCOPE"
                },

                edge_type="FUNCTION_CALL"
            )

    # ======================================================
    # MODEL DECLARATIONS
    # ======================================================

    def handle_model_declaration(self, sm):
        model_name = sm.get("model.name")
        if model_name:
            self.model_registry[model_name] = sm.file_path

    # ======================================================
    # DATABASE
    # ======================================================


    def handle_database(self, sm):

        self.ensure_file(
            "database",
            sm.file_path
        )

        self.graph["database"][
            sm.file_path
        ].append({

            "model": sm.get(
                "db.model"
            ),

            "operation": sm.get(
                "db.operation"
            ),

            "query": sm.get(
                "db.query"
            ),

            "connection": sm.get(
                "db.connection"
            ),

            "function":
            sm.owner_function or "GLOBAL_SCOPE"
        })

        # ==================================================
        # EXECUTION EDGE
        # ==================================================

        db_target = None

        if sm.get("db.model"):
            model_name = sm.get("db.model")
            resolved_file = self.model_registry.get(model_name) or ""

            db_target = {

                "type": "DATABASE",

                "model": model_name,

                "operation": sm.get(
                    "db.operation"
                ),

                "file": resolved_file
            }

        elif sm.get("db.query"):

            db_target = {

                "type": "SQL",

                "query": sm.get(
                    "db.query"
                )
            }

        if db_target:

            self.add_execution_edge(

                from_node={

                    "type": "FUNCTION",

                    "file": sm.file_path,

                    "function": sm.owner_function or "GLOBAL_SCOPE"
                },

                to_node=db_target,

                edge_type="DB_ACCESS"
            )

    # ======================================================
    # ERRORS
    # ======================================================

    def handle_error(self, sm):

        self.ensure_file(
            "errors",
            sm.file_path
        )

        self.graph["errors"][
            sm.file_path
        ].append({

            "throw": sm.get(
                "error.throw"
            )
        })

    # ======================================================
    # CONTRACTS
    # ======================================================

    def handle_contract(self, sm):

        self.ensure_file(
            "contracts",
            sm.file_path
        )

        self.graph["contracts"][
            sm.file_path
        ].append({

            "name": sm.get(
                "contract.name"
            )
        })
    
    # ======================================================
    # ADD EXECUTION EDGE
    # ======================================================

    def add_execution_edge(
        self,
        from_node,
        to_node,
        edge_type
    ):
        # print("\n[EDGE ADDED]")
        # print("FROM:", from_node)
        # print("TO:", to_node)
        # print("TYPE:", edge_type)

        self.graph[
            "execution_edges"
        ].append({

            "from": from_node,

            "to": to_node,

            "type": edge_type
        })


    # ==========================================================
    # DESTRUCTURED SYMBOL
    # ==========================================================

    def handle_destructure_alias(
        self,
        sm
    ):

        local_name = sm.get(
            "destructure.name"
        )

        source_object = sm.get(
            "destructure.source"
        )

        if DEBUG_MATCHES:
            print("\nREGISTERING DESTRUCTURED:")
            print(local_name)
            print(source_object)

        self.symbol_table.register_destructured(

            sm.file_path,

            local_name,

            source_object
        )

    # ==========================================================
    # FUNCTION PARAMETERS
    # ==========================================================

    def handle_function_params(

        self,

        sm
    ):

        self.ensure_file(
            "parameters",
            sm.file_path
        )

        function_name = sm.get(
            "function.name"
        ) or sm.owner_function or "GLOBAL_SCOPE"

        param = sm.get(
            "param.name"
        )

        from pathlib import Path
        print(f"📥 [GRAPH INSERT PARAMETER] File: {Path(sm.file_path).name}, Function: {function_name}, Parameter: {param}")

        existing = None

        # ======================================================
        # FIND EXISTING FUNCTION ENTRY
        # ======================================================

        for entry in self.graph["parameters"][
            sm.file_path
        ]:

            if entry["function"] == function_name:

                existing = entry
                break

        # ======================================================
        # CREATE NEW FUNCTION PARAM LIST
        # ======================================================

        if existing is None:

            existing = {

                "function": function_name,

                "params": []
            }

            self.graph["parameters"][
                sm.file_path
            ].append(existing)

        # ======================================================
        # APPEND PARAM
        # ======================================================

        if param not in existing["params"]:

            existing["params"].append(param)


    # ==========================================================
    # CALL ARGUMENTS
    # ==========================================================

    def handle_call_arguments(

        self,

        sm
    ):
        call_id = self.build_call_id(sm)

        self.ensure_file(
            "arguments",
            sm.file_path
        )

        arg = sm.get(
            "arg.value"
        )

        owner_function = (
            sm.owner_function or "GLOBAL_SCOPE"
        )

        from pathlib import Path
        print(f"📥 [GRAPH INSERT ARGUMENT] File: {Path(sm.file_path).name}, Call ID: {call_id}, Function: {owner_function}, Argument: {arg}")

        existing = None

        # ======================================================
        # FIND EXISTING OWNER FUNCTION
        # ======================================================

        for entry in self.graph["arguments"][
            sm.file_path
        ]:

            # if entry["function"] == owner_function:
            if entry["call_id"] == call_id:

                existing = entry
                break

        # ======================================================
        # CREATE NEW ENTRY
        # ======================================================

        if existing is None:

            # existing = {

            #     "function": owner_function,

            #     "arguments": []
            # }
            existing = {

                "call_id": call_id,

                "function": owner_function,

                "arguments": []
            }

            self.graph["arguments"][
                sm.file_path
            ].append(existing)

        # ======================================================
        # APPEND ARGUMENT
        # ======================================================

        existing["arguments"].append(arg)


    # ==========================================================
    # BUILD ARGUMENT → PARAMETER FLOW
    # ==========================================================

    def build_argument_parameter_flow(self):

        # ======================================================
        # ITERATE CALLS
        # ======================================================

        for file_path, calls in self.graph["calls"].items():

            for index, call in enumerate(calls):

                resolved_function = (
                    call.get("resolved_function")
                )
                # print("inside build_argument_parameter_flow (call):", call)
                # print("inside build_argument_parameter_flow (resolved_function):", resolved_function)
                if not resolved_function:
                    continue

                target_function = (
                    resolved_function["name"]
                )

                target_file = (
                    resolved_function["file"]
                )

                # ==================================================
                # FIND CALL ARGUMENTS
                # ==================================================

                arguments = []

                call_id = call.get("call_id")
                # print("inside build_argument_parameter_flow self.graph['arguments']:", self.graph["arguments"])

                for arg_entry in self.graph[
                    "arguments"
                ].get(file_path, []):

                    if (

                        arg_entry["call_id"]

                        ==

                        call_id
                    ):

                        arguments = (
                            arg_entry["arguments"]
                        )

                        break
                # ==================================================
                # FIND TARGET PARAMETERS
                # ==================================================

                parameters = []

                for param_entry in self.graph[
                    "parameters"
                ].get(target_file, []):

                    if (

                        param_entry["function"]

                        ==

                        target_function
                    ):

                        parameters = (
                            param_entry["params"]
                        )

                        break

                # ==================================================
                # CONNECT ARG → PARAM
                # ==================================================

                # print("\n" + "=" * 80)
                # print("BUILD FLOW DEBUG")
                # print("=" * 80)

                # print("CALL:")
                # print(call)

                # print("CALL ID:")
                # print(call_id)

                # print("ARGUMENTS GRAPH:")
                # print(self.graph["arguments"])

                # print("PARAMETERS GRAPH:")
                # print(self.graph["parameters"])


                for i in range(

                    min(
                        len(arguments),
                        len(parameters)
                    )
                ):

                    self.graph["data_flow"].append({

                        "source": arguments[i],

                        "target_file":
                            target_file,

                        "target_function":
                            target_function,

                        "target_param":
                            parameters[i]
                    })


    # ==========================================================
    # DETECT TAINT SOURCES
    # ==========================================================

    def detect_taint_sources(self):

        # ======================================================
        # ITERATE DATA FLOW
        # ======================================================
        # nothing goes in data flow

        for flow in self.graph["data_flow"]:

            source = flow["source"]

            # ==================================================
            # EXPRESS USER INPUT
            # ==================================================
            print("inside detect_taint_sources (flow):", flow)

            if (

                source.startswith("req.body")

                or

                source.startswith("req.query")

                or

                source.startswith("req.params")

                or

                source.startswith("req.headers")
            ):

                # self.graph["taint_sources"].append({

                #     "type": "USER_INPUT",

                #     "source": source,

                #     "target_function":
                #         flow["target_function"],

                #     "target_param":
                #         flow["target_param"]
                # })

                self.graph["taint_sources"].append({

                    "type": "USER_INPUT",

                    "file":
                        flow.get("target_file"),

                    "source": source,

                    "target_function":
                        flow["target_function"],

                    "target_param":
                        flow["target_param"]
                })


    # ==========================================================
    # DETECT SECURITY SINKS
    # ==========================================================

    def detect_security_sinks(self):

        # ======================================================
        # DATABASE OPERATIONS
        # ======================================================

        for file_path, db_ops in self.graph[
            "database"
        ].items():

            for db in db_ops:

                operation = db.get(
                    "operation"
                )

                # ==============================================
                # SQL SINK
                # ==============================================

                if operation == "query":

                    self.graph[
                        "security_sinks"
                    ].append({

                        "type": "SQL_QUERY",

                        "file": file_path,

                        "target_function":
                        db.get("function"),

                        "operation": operation,

                        "query": db.get("query")
                    })

                    # print(
                    #     "\nSECURITY SINK ADDED:",
                    #     self.graph["security_sinks"][-1]
                    # )
                # ==============================================
                # MONGOOSE SINK
                # ==============================================

                if operation in {

                    "find",
                    "findOne",
                    "updateOne",
                    "updateMany",
                    "deleteOne",
                    "aggregate"
                }:

                    self.graph[
                        "security_sinks"
                    ].append({

                        "type": "MONGODB_QUERY",

                        "file": file_path,

                        "target_function":
                        db.get("function"),

                        "model": db.get("model"),

                        "operation": operation
                    })
                    # print(
                    #     "\nSECURITY SINK ADDED:",
                    #     self.graph["security_sinks"][-1]
                    # )


    # ==========================================================
    # DETECT VULNERABILITIES
    # ==========================================================

    def detect_vulnerabilities(self):

        # ======================================================
        # ITERATE TAINT SOURCES
        # ======================================================

        for taint in self.graph[
            "taint_sources"
        ]:

            target_function = taint[
                "target_function"
            ]
            # ==================================================
            # CHECK SANITIZATION
            # ==================================================

            sanitized = False

            for sanitizer in self.graph[
                "sanitizers"
            ]:

                if (

                    sanitizer["caller_function"]

                    ==

                    target_function
                ):

                    sanitized = True
                    break

            if sanitized:
                continue

            # ==================================================
            # FIND EXECUTION FLOW
            # ==================================================

            for edge in self.graph[
                "execution_edges"
            ]:

                # ==============================================
                # FUNCTION → DB
                # ==============================================

                if (

                    edge["type"]

                    ==

                    "DB_ACCESS"
                ):

                    from_function = (
                        edge["from"].get(
                            "function"
                        )
                    )

                    # print("\nTAINT CHECK")

                    # print(
                    #     "TAINT FUNCTION:",
                    #     target_function
                    # )

                    # print(
                    #     "EDGE FUNCTION:",
                    #     from_function
                    # )

                    if from_function != target_function:
                        continue

                    sink = edge["to"]

                    # ==========================================
                    # SQL INJECTION
                    # ==========================================

                    if sink["type"] == "SQL":

                        self.graph[
                            "security_findings"
                        ].append({

                            "type":
                                "SQL_INJECTION",

                            "severity":
                                "HIGH",

                            "source":
                                taint["source"],

                            "sink":
                                "db.query",

                            "target_function":
                                target_function
                        })

                    # ==========================================
                    # NOSQL INJECTION
                    # ==========================================

                    if sink["type"] == "DATABASE":

                        self.graph[
                            "security_findings"
                        ].append({

                            "type":
                                "NOSQL_INJECTION",

                            "severity":
                                "HIGH",

                            "source":
                                taint["source"],

                            "sink":
                                sink["operation"],

                            "model":
                                sink["model"],

                            "target_function":
                                target_function
                        })


    # ==========================================================
    # DETECT SANITIZERS
    # ==========================================================

    def detect_sanitizers(self):

        sanitizer_functions = {

            "escape",

            "sanitize",

            "normalizeEmail",

            "xss"
        }

        # ======================================================
        # ITERATE CALLS
        # ======================================================

        for file_path, calls in self.graph[
            "calls"
        ].items():

            for call in calls:

                func = call.get(
                    "function"
                )

                if call.get("caller_function") is None:
                    continue

                if func not in sanitizer_functions:
                    continue

                self.graph[
                    "sanitizers"
                ].append({

                    "file": file_path,

                    "function": func,

                    "caller_function":
                        call.get(
                            "caller_function"
                        )
                })



    # ==========================================================
    # BUILD CALL ID
    # ==========================================================

    # def build_call_id(self, sm):

    #     return (

    #         f"{sm.file_path}:"

    #         f"{sm.start_byte}:"

    #         f"{sm.end_byte}"
    #     )

    #     # call_node = sm.raw_capture("call.node")

    #     # return (
    #     #     f"{sm.file_path}:"
    #     #     f"{call_node.start_byte}:"
    #     #     f"{call_node.end_byte}"
    #     # )
    def build_call_id(self, sm):
        call_start = sm.get(
            "call.start"
        )

        call_end = sm.get(
            "call.end"
        )

        if (
            call_start is not None
            and
            call_end is not None
        ):

            return (
                f"{sm.file_path}:"
                f"{call_start}:"
                f"{call_end}"
            )

        return (
            f"{sm.file_path}:"
            f"{sm.start_byte}:"
            f"{sm.end_byte}"
        )

    # ==========================================================
    # TRACK VARIABLE STATES
    # ==========================================================

    def track_variable_states(self):

        sanitizer_functions = {

            "escape",

            "sanitize",

            "normalizeEmail",

            "xss"
        }

        # ======================================================
        # ITERATE ASSIGNMENTS
        # ======================================================

        for sm in self.semantic_matches:

            if sm.match_type != "VARIABLE_ASSIGNMENT":
                continue
            
            # ==================================================
            # ALLOW GLOBAL ASSIGNMENTS AS GLOBAL_SCOPE
            # ==================================================

            owner_fn = sm.owner_function or "GLOBAL_SCOPE"

            variable = sm.get(
                "assign.variable"
            )

            value = sm.get(
                "assign.value"
            )

            tainted = False
            sanitized = False

            # ==================================================
            # USER INPUT
            # ==================================================

            if (

                "req.body" in value

                or

                "req.query" in value

                or

                "req.params" in value
            ):

                tainted = True

            # ==================================================
            # SANITIZER
            # ==================================================

            for sanitizer in sanitizer_functions:

                if sanitizer in value:

                    sanitized = True
                    tainted = False

            from pathlib import Path
            print(f"📥 [GRAPH INSERT VARIABLE] File: {Path(sm.file_path).name}, Function: {owner_fn}, Variable: {variable}, Value: {value[:30]}..., Tainted: {tainted}, Sanitized: {sanitized}")

            self.graph[
                "variable_states"
            ].append({

                "file": sm.file_path,

                "function":
                    owner_fn,

                "variable": variable,

                "value": value,

                "tainted": tainted,

                "sanitized": sanitized
            })




    # ==========================================================
    # TRACK VARIABLE STATES FOR MATCHES
    # ==========================================================

    def track_variable_states_for_matches(

        self,

        semantic_matches
    ):

        sanitizer_functions = {

            "escape",

            "sanitize",

            "normalizeEmail",

            "xss"
        }

        for sm in semantic_matches:

            if sm.match_type != "VARIABLE_ASSIGNMENT":
                continue

            owner_fn = sm.owner_function or "GLOBAL_SCOPE"

            variable = sm.get(
                "assign.variable"
            )

            value = sm.get(
                "assign.value"
            )

            tainted = False
            sanitized = False

            if (

                "req.body" in value

                or

                "req.query" in value

                or

                "req.params" in value
            ):

                tainted = True

            for sanitizer in sanitizer_functions:

                if sanitizer in value:

                    sanitized = True
                    tainted = False

            from pathlib import Path
            print(f"📥 [GRAPH INSERT VARIABLE FOR MATCHES] File: {Path(sm.file_path).name}, Function: {owner_fn}, Variable: {variable}, Value: {value[:30]}..., Tainted: {tainted}, Sanitized: {sanitized}")

            self.graph[
                "variable_states"
            ].append({

                "file": sm.file_path,

                "function":
                    owner_fn,

                "variable": variable,

                "value": value,

                "tainted": tainted,

                "sanitized": sanitized
            })

    # ==========================================================
    # HANDLE RETURN VALUES
    # ==========================================================

    def handle_return_value(

        self,

        sm
    ):

        self.graph[
            "returns"
        ].append({

            "file": sm.file_path,

            "function":
                sm.owner_function,

            "value":
                sm.get(
                    "return.value"
                )
        })



    # ==========================================================
    # PROPAGATE RETURN TAINT
    # ==========================================================

    def propagate_return_taint(self):

        for return_entry in self.graph[
            "returns"
        ]:

            returned_value = (
                return_entry["value"]
            )

            function_name = (
                return_entry["function"]
            )

            # ==================================================
            # CHECK IF RETURN VALUE IS TAINTED PARAM
            # ==================================================

            for flow in self.graph[
                "data_flow"
            ]:

                if (

                    flow["target_function"]

                    ==

                    function_name

                    and

                    flow["target_param"]

                    ==

                    returned_value
                ):

                    # self.graph[
                    #     "taint_sources"
                    # ].append({

                    #     "type":
                    #         "RETURN_TAINT",

                    #     "source":
                    #         flow["source"],

                    #     "target_function":
                    #         function_name,

                    #     "returned_value":
                    #         returned_value
                    # })
                    self.graph[
                        "taint_sources"
                    ].append({

                        "type":
                            "RETURN_TAINT",

                        "file":
                            return_entry.get("file"),

                        "source":
                            flow["source"],

                        "target_function":
                            function_name,

                        "returned_value":
                            returned_value
                    })


