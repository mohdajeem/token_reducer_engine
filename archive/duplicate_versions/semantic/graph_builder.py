from dotenv import load_dotenv

load_dotenv()

from semantic.symbol_table import (
    SymbolTable
)

from semantic.function_index import (
    FunctionIndex
)

# from config.debug_flags import *
from config.settings import *


class GraphBuilder:

    def __init__(self):

        self.graph = {

            "imports": {},

            "routes": {},

            "calls": {},

            "database": {},

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
        # sm.owner_function = None

    # ======================================================
    # MAIN ENTRY
    # ======================================================

    def build(

        self,

        semantic_matches
    ):
        
        self.semantic_matches = semantic_matches

        if DEBUG_MATCHES:
            print("\nBUILD RECEIVED MATCHES:")
            for sm in semantic_matches:

                print(
                    sm.match_type,
                    sm.captures
                )

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

    def handle_route(self, sm):

        self.ensure_file(
            "routes",
            sm.file_path
        )

        controller_name = sm.get(
            "handler.controller"
        )

        resolved_file = (
            self.symbol_table.resolve_import(
                sm.file_path,
                controller_name
            )
        )
        function_name = sm.get(
            "handler.function"
        )

        resolved_function = None

        if resolved_file:
            
            resolved_function = (
                self.function_index.resolve_function(
                    resolved_file,
                    function_name
                )
            )
        

        self.graph["routes"][
            sm.file_path
        ].append({

            "method": (
                sm.get(
                    "endpoint.served_method"
                )
            ),

            "path": (
                sm.get(
                    "endpoint.served_route"
                )
            ),

            "router": (
                sm.get(
                    "router.obj"
                )
            ),
            "handler": {

                "controller": controller_name,

                "function": sm.get(
                    "handler.function"
                ),

                "resolved_file": resolved_file,

                "resolved_function": resolved_function
            },
            
        })

        # ==================================================
        # EXECUTION EDGE
        # ==================================================

        self.add_execution_edge(

            from_node={

                "type": "ROUTE",

                "route": sm.get(
                    "endpoint.served_route"
                ),

                "method": sm.get(
                    "endpoint.served_method"
                )
            },

            to_node={

                "type": "FUNCTION",

                "file": resolved_file,

                "function": function_name,

                "resolved_function":
                resolved_function
            },

            edge_type="ROUTE_CALL"
        )


    # ======================================================
    # FUNCTION DEFINITIONS
    # ======================================================

    def handle_function_def(self, sm):

        function_name = sm.get(
            "function.name"
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

    # ======================================================
    # CALLS
    # ======================================================

    def handle_call(self, sm):

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
        print("\n[CALL DEBUG]")
        print("OBJ:", obj)
        print("FUNC:", func)
        print("RESOLVED FILE:", resolved_file)
        print("RESOLVED FUNCTION:", resolved_function)

        if resolved_function:

            self.add_execution_edge(

                from_node={

                    "type": "FUNCTION",

                    "file": sm.file_path,

                    "function": sm.owner_function
                },

                to_node={

                    "type": "FUNCTION",

                    "file": resolved_file,

                    "function": func
                },

                edge_type="FUNCTION_CALL"
            )

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
            sm.owner_function
        })

        # ==================================================
        # EXECUTION EDGE
        # ==================================================

        db_target = None

        if sm.get("db.model"):

            db_target = {

                "type": "DATABASE",

                "model": sm.get(
                    "db.model"
                ),

                "operation": sm.get(
                    "db.operation"
                )
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

                    "function": sm.owner_function
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
        print("\n[EDGE ADDED]")
        print("FROM:", from_node)
        print("TO:", to_node)
        print("TYPE:", edge_type)

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
        )

        param = sm.get(
            "param.name"
        )

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
            sm.owner_function
        )

        # ======================================================
        # IGNORE FRAMEWORK-LEVEL CALLS
        # ======================================================

        if owner_function is None:

            return

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

                    print(
                        "\nSECURITY SINK ADDED:",
                        self.graph["security_sinks"][-1]
                    )
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
                    print(
                        "\nSECURITY SINK ADDED:",
                        self.graph["security_sinks"][-1]
                    )


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

    def build_call_id(self, sm):

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
            # IGNORE GLOBAL ASSIGNMENTS
            # ==================================================

            if sm.owner_function is None:
                continue

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

            self.graph[
                "variable_states"
            ].append({

                "file": sm.file_path,

                "function":
                    sm.owner_function,

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

            if sm.owner_function is None:
                continue

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

            self.graph[
                "variable_states"
            ].append({

                "file": sm.file_path,

                "function":
                    sm.owner_function,

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


