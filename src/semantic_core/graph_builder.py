from dotenv import load_dotenv

load_dotenv()

from semantic_core.symbol_table import (
    SymbolTable
)

from semantic_core.function_index import (
    FunctionIndex
)

from config.debug_flags import DEBUG_GRAPH_BUILD
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

            # Barrel files: file -> {"star": [source files], "names": {exported: (source file, original)}}
            "reexports": {},

            # file -> {class name -> {"superclass": name or None}}
            "classes": {},
        }
        # Frameworks detected from the repo manifest (set by build_graph). Express/Mongoose/SQL
        # heuristics -- routes, DB sinks, req.* taint -- only run when the repo uses them; on a
        # charting library `chart.update()` used to become a DB_ACCESS edge to model "chart".
        self.frameworks = set()
        # key -> ClassName from `key: new Class()` defaults (set by build_graph)
        self.option_defaults = {}
        # (file, function, param) -> [ClassName, ...] when call sites disagree on the type
        self.param_candidates = {}
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
        
        if hasattr(self, "project_root"):
            self.symbol_table.project_root = self.project_root
            
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
            elif sm.match_type == "REEXPORT":
                self.handle_reexport(sm)

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
        # PASS — VARIABLE TYPE RESOLUTION
        # ======================================================
        for sm in semantic_matches:
            if sm.match_type == "VARIABLE_ASSIGNMENT":
                self.handle_variable_type(sm)

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

        # Python classes (CONTRACT matches) become class nodes before calls are resolved
        for sm in semantic_matches:
            if sm.match_type == "CONTRACT" and sm.file_path.endswith(".py"):
                self.handle_contract(sm)

        # ======================================================
        # PASS 4b — CALLABLE VALUES
        # ======================================================
        # `const isType = R.propEq('type')` / `const getProp = makeGetter(doc)`: a module-level
        # value that the code CALLS is a function whatever expression produced it. The query
        # only sees function literals; usage decides here. Registered like any function
        # (kind="value") so the ordinary bare-call resolution finds it.
        self._register_callable_values(semantic_matches)

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
        self.infer_parameter_types_from_flow()
        self.resolve_pending_calls()

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

    _WEB_FRAMEWORKS = {"express", "koa", "fastify", "hapi", "nest", "next", "flask", "django", "fastapi"}
    _DB_FRAMEWORKS = {"mongoose", "sequelize", "prisma", "typeorm", "knex", "pg", "mysql", "mysql2", "sqlite3",
                      "mongodb", "sqlalchemy", "redis", "ioredis"}

    def _note_framework_import(self, import_source):
        """Frameworks are inferred from what the code imports (a manifest is optional)."""
        pkg = (import_source or "").split("/")[0].lstrip("@").lower()
        if pkg in self._WEB_FRAMEWORKS or pkg in self._DB_FRAMEWORKS:
            self.frameworks.add(pkg)

    def _db_heuristics_enabled(self):
        # Express-style apps persist through SOME client, named or not; standalone libraries
        # (charting, markdown, PDF) do not -- there `chart.update()` is just a method call.
        return bool(self.frameworks & (self._WEB_FRAMEWORKS | self._DB_FRAMEWORKS))

    def handle_import(self, sm):

        self._note_framework_import(sm.get("import.source"))

        self.ensure_file(
            "imports",
            sm.file_path
        )

        resolved_file = self.symbol_table.register_import(
            file_path=sm.file_path,
            import_name=(
                sm.get("import.alias")
                or
                sm.get("import.name")
            ),

            import_source=sm.get(
                "import.source"
            ),
            exported_name=sm.get("import.name"),
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
            ),

            # project file this import reaches, None for stdlib / third-party
            "file": resolved_file if isinstance(resolved_file, str) else None,
        })

        # A Python package `__init__.py` that imports a name re-exports it:
        # `from .core.engine import boot` makes `from pkg import boot` reach engine.py.
        if sm.file_path.endswith("__init__.py") and resolved_file and sm.get("import.name"):
            entry = self.graph["reexports"].setdefault(sm.file_path, {"star": [], "names": {}})
            local = sm.get("import.alias") or sm.get("import.name")
            entry["names"][local] = [resolved_file, sm.get("import.name")]

    def handle_reexport(self, sm):
        """`export * from './core'` / `export { a as b } from './x'` recorded per file so call
        resolution can follow a barrel to the defining module."""
        source_file = self.symbol_table.resolve_module_path(sm.file_path, sm.get("reexport.source"))
        if not source_file:
            return
        entry = self.graph["reexports"].setdefault(sm.file_path, {"star": [], "names": {}})
        if sm.get("reexport.star"):
            if source_file not in entry["star"]:
                entry["star"].append(source_file)
        for exported, original in (sm.get("reexport.names") or []):
            entry["names"][exported] = [source_file, original]

    def resolve_through_reexports(self, file_path, func_name, _depth=0):
        """(file, function metadata, original name) for func_name as exported by file_path,
        following barrels up to 6 hops; (None, None, func_name) if nothing defines it."""
        if not file_path or _depth > 6:
            return None, None, func_name
        meta = self.function_index.resolve_function(file_path, func_name)
        if meta:
            return file_path, meta, func_name
        entry = self.graph["reexports"].get(file_path)
        if not entry:
            return None, None, func_name
        named = entry["names"].get(func_name)
        if named:
            f, meta, orig = self.resolve_through_reexports(named[0], named[1], _depth + 1)
            if meta:
                return f, meta, orig
        for src in entry["star"]:
            f, meta, orig = self.resolve_through_reexports(src, func_name, _depth + 1)
            if meta:
                return f, meta, orig
        return None, None, func_name

    def resolve_class_file(self, file_path, class_name):
        """File that defines class_name as seen from file_path: same file, else via imports/barrels."""
        if class_name in self.graph["classes"].get(file_path, {}):
            return file_path
        imported = self.symbol_table.resolve_import(file_path, class_name)
        if imported:
            exported_as = self.symbol_table.resolve_imported_name(file_path, class_name) or class_name
            found = self._find_class_through_reexports(imported, exported_as)
            if found:
                return found
        # not imported here (came in through options / a factory): the class is still
        # unambiguous when exactly one non-bundle file in the repo defines it
        owners = {(f, class_name) for f, cs in self.graph["classes"].items() if class_name in cs}
        pick = self._unique_owner(owners)
        return pick[0] if pick else None

    def _find_class_through_reexports(self, file_path, class_name, _depth=0):
        if not file_path or _depth > 6:
            return None
        if class_name in self.graph["classes"].get(file_path, {}):
            return file_path
        entry = self.graph["reexports"].get(file_path)
        if not entry:
            return None
        named = entry["names"].get(class_name)
        if named:
            f = self._find_class_through_reexports(named[0], named[1], _depth + 1)
            if f:
                return f
        for src in entry["star"]:
            f = self._find_class_through_reexports(src, class_name, _depth + 1)
            if f:
                return f
        return None

    def resolve_field_type(self, file_path, class_name, field, _depth=0):
        """Declared/assigned type of `this.<field>` in class_name (walking superclasses)."""
        if not class_name or _depth > 8:
            return None
        cls_file = self.resolve_class_file(file_path, class_name) or file_path
        entry = self.graph["classes"].get(cls_file, {}).get(class_name) or {}
        ftype = (entry.get("fields") or {}).get(field)
        if ftype and ftype.startswith("option:"):
            ftype = self.option_defaults.get(ftype[7:])
        if ftype:
            return ftype
        if entry.get("superclass"):
            return self.resolve_field_type(cls_file, entry["superclass"], field, _depth + 1)
        return None

    def infer_parameter_types_from_flow(self):
        """`wrap(new Engine())` types `x` inside `wrap(x)`; `wrap(e)` with a typed `e` too.
        Uses the argument->parameter flow the builder already computes."""
        import re as _re
        new_re = _re.compile(r"^\s*new\s+([A-Za-z_$][\w$.]*)\s*\(")
        seen = {}  # (file, function, param) -> set of types observed across call sites
        for flow in self.graph.get("data_flow", []):
            src = flow.get("source")
            tf, tfn, tp = flow.get("target_file"), flow.get("target_function"), flow.get("target_param")
            if not (isinstance(src, str) and tf and tfn and tp):
                continue
            if self.symbol_table.resolve_type(tf, tfn, tp):
                continue  # declared type (JSDoc / TS) wins
            t = None
            m = new_re.match(src)
            if m:
                t = m.group(1).split(".")[-1]
            elif _re.fullmatch(r"[A-Za-z_$][\w$]*", src.strip()) and flow.get("source_file"):
                t = self.symbol_table.resolve_type(flow["source_file"], flow.get("source_function") or "GLOBAL", src.strip())
            if t:
                seen.setdefault((tf, tfn, tp), set()).add(t)
        # one type across every call site -> a fact; several -> candidates, never a guess
        for (tf, tfn, tp), types in seen.items():
            if len(types) == 1:
                self.symbol_table.register_type(tf, tfn, tp, next(iter(types)))
            else:
                self.param_candidates[(tf, tfn, tp)] = sorted(types)

    _BUNDLE_RE = None

    def _is_bundle(self, file_path):
        import re as _re
        if GraphBuilder._BUNDLE_RE is None:
            GraphBuilder._BUNDLE_RE = _re.compile(r"(^|/)(lib|dist|build|bundle|umd|esm|cjs|min)(/|$)|[.](min|esm|umd|cjs|bundle)[.][cm]?js$")
        return bool(GraphBuilder._BUNDLE_RE.search(file_path))

    def _unique_owner(self, cands):
        """The single (file, class) that defines a method, or None. Built bundles that copy
        the source (lib/marked.js, lib/marked.esm.js next to src/Tokenizer.js) are the same
        class, not an ambiguity: when every candidate has one class name, prefer the
        non-bundle file, then the one under src/."""
        import re as _re
        if not cands:
            return None
        if len(cands) == 1:
            return next(iter(cands))
        if GraphBuilder._BUNDLE_RE is None:
            GraphBuilder._BUNDLE_RE = _re.compile(r"(^|/)(lib|dist|build|bundle|umd|esm|cjs|min)(/|$)|[.](min|esm|umd|cjs|bundle)[.][cm]?js$")
        # bundles first: a UMD/ESM build copies every source class (Babel even renames the
        # prototype holder `_proto`); source files decide uniqueness
        non_bundle = [c for c in cands if not GraphBuilder._BUNDLE_RE.search(c[0])]
        pool = non_bundle or list(cands)
        if len({c for _, c in pool}) != 1:
            return None
        in_src = [c for c in pool if "/src/" in "/" + c[0]]
        pool = in_src or pool
        if len(pool) == 1:
            return pool[0]
        return None

    # Methods that builtin / standard types have. When a bare receiver calls one of these, the
    # receiver may well be a dict / list / str / file / logger, so "only one class in the repo
    # defines it" is not evidence -- the precision audit (tests/audit_precision_py.py) put the
    # unique-name fallback at 27% on requests, almost entirely `kwargs.pop`, `x.setdefault`,
    # `f.read`, `log.info` resolving to a vendored OrderedDict / HTTPResponse / cookie jar.
    _BUILTIN_METHOD_NAMES = None

    @classmethod
    def builtin_method_names(cls):
        if cls._BUILTIN_METHOD_NAMES is None:
            names = set()
            for t in (dict, list, str, bytes, set, frozenset, tuple, int, float, complex, object, type, BaseException):
                names |= {n for n in dir(t) if not n.startswith("__")}
            names |= {"read", "readline", "readlines", "write", "writelines", "close", "flush", "seek", "tell",
                      "fileno", "truncate", "readable", "writable", "seekable", "isatty", "detach", "peek",
                      "info", "debug", "warning", "warn", "error", "exception", "critical", "log", "setLevel",
                      "addHandler", "removeHandler", "getLogger", "handle", "emit", "format",
                      "get", "put", "put_nowait", "get_nowait", "join", "start", "run", "stop", "cancel",
                      "send", "recv", "connect", "bind", "listen", "accept", "settimeout", "setblocking",
                      "acquire", "release", "wait", "notify", "notify_all", "set", "clear", "is_set",
                      "match", "search", "sub", "subn", "split", "findall", "finditer", "fullmatch", "groups",
                      "group", "groupdict", "span", "compile", "escape", "encode", "decode", "next", "throw",
                      "open", "exists", "is_file", "is_dir", "mkdir", "unlink", "resolve", "iterdir",
                      "cursor", "execute", "executemany", "fetchone", "fetchall", "commit", "rollback",
                      # JS: Array / String / Object / Map / Set / Promise / DOM
                      "push", "pop", "shift", "unshift", "slice", "splice", "map", "forEach", "filter",
                      "reduce", "reduceRight", "find", "findIndex", "some", "every", "indexOf", "lastIndexOf",
                      "includes", "concat", "sort", "reverse", "flat", "flatMap", "fill", "keys", "values",
                      "entries", "hasOwnProperty", "toString", "toFixed", "valueOf", "apply", "call", "bind",
                      "then", "catch", "finally", "has", "delete", "add", "size", "at", "from", "of", "assign",
                      "freeze", "create", "defineProperty", "getOwnPropertyNames", "isArray", "parse",
                      "stringify", "replace", "replaceAll", "trim", "toLowerCase", "toUpperCase", "charAt",
                      "charCodeAt", "substring", "substr", "startsWith", "endsWith", "padStart", "padEnd",
                      "repeat", "localeCompare", "addEventListener", "removeEventListener", "dispatchEvent",
                      "querySelector", "querySelectorAll", "getAttribute", "setAttribute", "appendChild",
                      "removeChild", "createElement", "getBoundingClientRect", "preventDefault",
                      "stopPropagation", "focus", "blur", "getContext", "toDataURL", "on", "off", "once",
                      "emit", "pipe", "end", "destroy", "resume", "pause", "setTimeout", "clearTimeout",
                      "toJSON", "toISOString", "getTime", "now", "abs", "min", "max", "floor", "ceil",
                      "round", "sqrt", "pow", "random", "test", "exec", "length", "done"}
            cls._BUILTIN_METHOD_NAMES = names
        return cls._BUILTIN_METHOD_NAMES

    def resolve_pending_calls(self):
        """Final pass over calls that stayed unresolved: receiver types learned late (argument
        flow), then a unique-method-name fallback. Fallback resolutions are flagged
        resolution="name-unique" on the call and confidence="name-unique" on the edge so a
        consumer can weigh them; a method name defined by more than one class stays
        unresolved -- guessing is worse than not knowing."""
        # method name -> {(file, class)} over production code
        owners = {}
        for file, fns in self.graph["functions"].items():
            for fn in fns:
                if not isinstance(fn, dict) or not fn.get("class") or fn.get("is_test"):
                    continue
                owners.setdefault(fn["name"], set()).add((file, fn["class"]))
        for file_path, calls in self.graph["calls"].items():
            # local aliases of imports that reach NO project file: `import * as R from 'ramda'`,
            # `const fs = require('fs')`, `import json`, `from os import path`
            external = {}
            for imp in self.graph["imports"].get(file_path, []):
                src = imp.get("source") or ""
                alias = imp.get("alias") or imp.get("name") or (src.split(".")[0] if src and not src.startswith(".") else None)
                if alias and src and imp.get("file") is None:
                    external[alias] = src.split("/")[0]
            for call in calls:
                if call.get("resolved_function"):
                    continue
                recv = call.get("receiver")
                func = call.get("function")
                if not recv or not func or recv in ("this", "super", "self"):
                    continue
                root = recv.split(".")[0].split("[")[0].split("(")[0]
                if root in external:
                    # a library call (R.compose, fs.readFile): unresolvable by design, and
                    # saying so is more useful than a silent None
                    call["external"] = external[root]
                    continue
                caller = call.get("caller_function") or "GLOBAL"
                typed_file = typed_meta = typed_class = None
                if "." not in recv:
                    t = self.symbol_table.resolve_type(file_path, caller, recv)
                    if t:
                        typed_file, typed_meta = self.resolve_method(file_path, t, func)
                        typed_class, how = t, "typed"
                    elif (file_path, caller, recv) in self.param_candidates:
                        # call sites disagree on the parameter's type: resolve to every
                        # candidate that defines the method, flagged so consumers can weigh it
                        resolved = []
                        for cand in self.param_candidates[(file_path, caller, recv)]:
                            cf, cm = self.resolve_method(file_path, cand, func)
                            if cm:
                                resolved.append((cf, cm, cand))
                        if len(resolved) == 1:
                            typed_file, typed_meta, typed_class = resolved[0]
                            how = "typed"
                        elif resolved:
                            call.update({"object": "|".join(c for _, _, c in resolved), "resolved_file": resolved[0][0],
                                         "resolved_function": resolved[0][1], "resolved_class": resolved[0][1].get("class") or resolved[0][2],
                                         "resolution": "candidates",
                                         "candidates": [{"file": cf, "class": cm.get("class") or c} for cf, cm, c in resolved]})
                            from_node = {"type": "FUNCTION", "file": file_path, "function": caller if caller != "GLOBAL" else "GLOBAL_SCOPE"}
                            if call.get("caller_class"):
                                from_node["class"] = call["caller_class"]
                            for cf, cm, c in resolved:
                                self.add_execution_edge(from_node=dict(from_node),
                                                        to_node={"type": "FUNCTION", "file": cf, "function": func, "class": cm.get("class") or c},
                                                        edge_type="FUNCTION_CALL", is_test=bool(call.get("is_test")))
                                self.graph["execution_edges"][-1]["confidence"] = "candidates"
                            continue
                if not typed_meta and "(" not in recv and "[" not in recv and func not in self.builtin_method_names():
                    # unique-name fallback also covers `this.tokenizer.space()` when the
                    # field's type is unknown but only one class defines `space`; never for
                    # names that builtin types also have (kwargs.pop is a dict, not our class).
                    # A bundle is self-contained: calls inside lib/marked.js resolve within it.
                    pool = owners.get(func, set())
                    if self._is_bundle(file_path):
                        pool = {c for c in pool if c[0] == file_path}
                    cands = self._unique_owner(pool)
                    if cands:
                        cf, cc = cands
                        typed_meta = self.function_index.resolve_function(cf, f"{cc}.{func}")
                        typed_file, typed_class, how = cf, cc, "name-unique"
                if not typed_meta:
                    continue
                call.update({"object": typed_class, "resolved_file": typed_file, "resolved_function": typed_meta,
                             "resolved_class": typed_meta.get("class") or typed_class, "resolution": how})
                from_node = {"type": "FUNCTION", "file": file_path, "function": caller if caller != "GLOBAL" else "GLOBAL_SCOPE"}
                if call.get("caller_class"):
                    from_node["class"] = call["caller_class"]
                is_test = bool(call.get("is_test"))
                self.add_execution_edge(
                    from_node=from_node,
                    to_node={"type": "FUNCTION", "file": typed_file, "function": func, "class": typed_meta.get("class") or typed_class},
                    edge_type="FUNCTION_CALL", is_test=is_test,
                )
                if how == "name-unique":
                    self.graph["execution_edges"][-1]["confidence"] = "name-unique"

    def resolve_method(self, file_path, class_name, method, _depth=0, _want_static=False):
        """(file, metadata) for class_name.method, walking the superclass chain. _want_static:
        the receiver is the class itself (`Lexer.lex(src)`), so a static method is preferred."""
        if not class_name or _depth > 8:
            return None, None
        cls_file = self.resolve_class_file(file_path, class_name) or file_path
        meta = self.function_index.resolve_static(cls_file, class_name, method, want_static=bool(_want_static)) \
            or self.function_index.resolve_function(cls_file, f"{class_name}.{method}")
        if meta:
            return cls_file, meta
        sup = (self.graph["classes"].get(cls_file, {}).get(class_name) or {}).get("superclass")
        if sup:
            return self.resolve_method(cls_file, sup, method, _depth + 1, _want_static)
        return None, None

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

    def _register_callable_values(self, semantic_matches):
        called = set()
        for sm in semantic_matches:
            if sm.match_type == "CALL" and not sm.get("call.obj_name") and sm.get("call.func_name"):
                called.add(sm.get("call.func_name"))
        if not called:
            return
        for sm in semantic_matches:
            if sm.match_type != "VARIABLE_ASSIGNMENT" or sm.owner_function:
                continue
            name = sm.get("assign.variable")
            if not name or name not in called:
                continue
            if self.function_index.resolve_function(sm.file_path, name):
                continue
            self.ensure_file("functions", sm.file_path)
            metadata = {
                "name": name,
                "file": sm.file_path,
                "start_line": sm.start_point[0] + 1,
                "end_line": sm.end_point[0] + 1,
                "kind": "value",
            }
            if getattr(sm, "is_test", False):
                metadata["is_test"] = True
            self.function_index.register_function(file_path=sm.file_path, function_name=name, metadata=metadata)
            self.graph["functions"][sm.file_path].append(dict(metadata))

    def handle_function_def(self, sm):

        function_name = sm.get(
            "function.name"
        )

        self.ensure_file(
            "functions",
            sm.file_path
        )

        owner_class = sm.get("function.class")
        superclass = sm.get("function.superclass")
        if owner_class:
            cls_entry = self.graph["classes"].setdefault(sm.file_path, {}).setdefault(owner_class, {"superclass": None})
            if superclass and not cls_entry.get("superclass"):
                cls_entry["superclass"] = superclass
            for field, ftype in (sm.get("function.field_types") or {}).items():
                cls_entry.setdefault("fields", {})[field] = ftype
        # declared receiver types (JSDoc @param / TS annotation), scoped to this function
        for pname, ptype in (sm.get("function.param_types") or {}).items():
            self.symbol_table.register_type(sm.file_path, function_name, pname, ptype)

        metadata = {
            "name": function_name,
            "file": sm.file_path,
            "start_line": sm.start_point[0] + 1,
            "end_line": sm.end_point[0] + 1,
        }
        if owner_class:
            metadata["class"] = owner_class
        if sm.get("function.static"):
            metadata["static"] = True
        if getattr(sm, "is_test", False):
            metadata["is_test"] = True

        # Methods are registered under their qualified name too, so `this.x()` / `obj.x()`
        # with a known receiver type resolve to THIS class's x, not whichever x was seen last.
        if owner_class:
            self.function_index.register_function(
                file_path=sm.file_path,
                function_name=f"{owner_class}.{function_name}",
                metadata=metadata,
            )

        self.function_index.register_function(

            file_path=sm.file_path,

            function_name=function_name,

            metadata=metadata

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
        ].append(dict(metadata))

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

        owner_fn = sm.owner_function or "GLOBAL"
        resolved_type = self.symbol_table.resolve_type(
            sm.file_path,
            owner_fn,
            raw_object_name
        )

        if resolved_type:
            obj = resolved_type
        else:
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
        # name the callee is DEFINED under when it differs from the local call name
        # (`import { helper as h }` -> h() targets helper)
        target_name = func

        # ==================================================
        # RECEIVER-TYPED RESOLUTION: this / super / new X()
        # ==================================================
        # `this.tick()` inside class Engine -> Engine.tick (0/2120 such calls resolved before
        # on Chart.js + p5.js); `super.x()` -> the superclass's x; `e.start()` after
        # `const e = new Engine()` -> Engine.start via the registered variable type.
        typed_file = typed_meta = typed_class = None
        field_type = None
        if not raw_object_name and func == "cls" and getattr(sm, "owner_class", None):
            cls_file = self.resolve_class_file(sm.file_path, sm.owner_class) or sm.file_path
            cmeta = self.function_index.resolve_function(cls_file, sm.owner_class)
            if cmeta:
                self.ensure_file("calls", sm.file_path)
                self.graph["calls"][sm.file_path].append({
                    "call_id": self.build_call_id(sm), "object": None, "receiver": None, "function": "cls",
                    "resolved_file": cls_file, "resolved_function": cmeta, "resolved_class": sm.owner_class,
                    "resolution": "typed", "caller_function": sm.owner_function,
                })
                self.add_execution_edge(from_node=self._from_node(sm),
                                        to_node={"type": "FUNCTION", "file": cls_file, "function": sm.owner_class},
                                        edge_type="FUNCTION_CALL", is_test=getattr(sm, "is_test", False))
                return
        if isinstance(raw_object_name, str) and raw_object_name.startswith(("this.", "self.")) and getattr(sm, "owner_class", None):
            field_type = self.resolve_field_type(sm.file_path, sm.owner_class, raw_object_name.split(".", 1)[1])
        if field_type:
            typed_file, typed_meta = self.resolve_method(sm.file_path, field_type, func)
            typed_class = field_type
        elif (raw_object_name in ("this", "self", "cls", "super") or (isinstance(raw_object_name, str) and raw_object_name.startswith("super("))) \
                and getattr(sm, "owner_class", None):
            cls = sm.owner_class
            if raw_object_name == "super" or raw_object_name.startswith("super("):
                cls = (self.graph["classes"].get(sm.file_path, {}).get(cls) or {}).get("superclass")
            typed_file, typed_meta = self.resolve_method(sm.file_path, cls, func)
            typed_class = cls
        elif resolved_type:
            typed_file, typed_meta = self.resolve_method(sm.file_path, resolved_type, func)
            typed_class = resolved_type
        elif isinstance(raw_object_name, str) and raw_object_name[:1].isupper() and "." not in raw_object_name \
                and self.resolve_class_file(sm.file_path, raw_object_name):
            # `Lexer.lex(src)`: the receiver is the class -> static method preferred
            typed_file, typed_meta = self.resolve_method(sm.file_path, raw_object_name, func, _want_static=True)
            typed_class = raw_object_name
        if typed_meta:
            self.ensure_file("calls", sm.file_path)
            call_id = self.build_call_id(sm)
            self.graph["calls"][sm.file_path].append({
                "call_id": call_id,
                # "object" keeps its historical meaning -- the RESOLVED receiver type;
                # the raw receiver text (this / super / the variable) is in "receiver".
                "object": typed_meta.get("class") or typed_class,
                "receiver": raw_object_name,
                "function": func,
                "resolved_file": typed_file,
                "resolved_function": typed_meta,
                "resolved_class": typed_meta.get("class") or typed_class,
                "resolution": "typed",
                "caller_function": sm.owner_function,
            })
            self.add_execution_edge(
                from_node=self._from_node(sm),
                to_node={"type": "FUNCTION", "file": typed_file, "function": func,
                         "class": typed_meta.get("class") or typed_class},
                edge_type="FUNCTION_CALL",
                is_test=getattr(sm, "is_test", False),
            )
            return


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
            if not resolved_function:
                # `import { boot } from './index'` where index.js re-exports it
                f2, m2, orig = self.resolve_through_reexports(resolved_file, func)
                if m2:
                    resolved_file, resolved_function, target_name = f2, m2, orig

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
                if not resolved_function:
                    imported_as = self.symbol_table.resolve_imported_name(sm.file_path, func) or func
                    f2, m2, orig = self.resolve_through_reexports(resolved_file, imported_as)
                    if m2:
                        resolved_file, resolved_function, target_name = f2, m2, orig

        # ==============================================
        # FALLBACK 3 — LOCAL DEFINITION
        # ==============================================
        if not resolved_function and not obj:
            # nearest module-level definition before the call site: a bundle defines
            # `edit$1` twice and last-wins picked the wrong one (JS precision audit)
            local_function = self.function_index.resolve_nearest(sm.file_path, func, sm.start_point[0] + 1 if sm.start_point else None)
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
            "express" in self.frameworks
            and
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

            "receiver": raw_object_name,

            "function": func,

            "resolved_file":
            resolved_file,

            "resolved_function":
            resolved_function,

            "caller_function":
            sm.owner_function,

            "caller_class": getattr(sm, "owner_class", None),

            "is_test": bool(getattr(sm, "is_test", False)),
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
            to_node = {
                "type": "FUNCTION",
                "file": resolved_file or sm.file_path,
                "function": (target_name if isinstance(resolved_function, dict) else func) or "GLOBAL_SCOPE"
            }
            if isinstance(resolved_function, dict) and resolved_function.get("class"):
                to_node["class"] = resolved_function["class"]
            self.add_execution_edge(
                from_node=self._from_node(sm),
                to_node=to_node,
                edge_type="FUNCTION_CALL",
                is_test=getattr(sm, "is_test", False),
            )

    def _from_node(self, sm):
        """The calling function as an edge endpoint: file + bare name, plus the specific
        occurrence's line and owning class so same-named methods stay distinguishable."""
        node = {
            "type": "FUNCTION",
            "file": sm.file_path,
            "function": sm.owner_function or "GLOBAL_SCOPE",
            "function_line": sm.owner_function_line,
        }
        if getattr(sm, "owner_class", None):
            node["class"] = sm.owner_class
        return node

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

        if not self._db_heuristics_enabled():
            return
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

        if sm.file_path.endswith(".py"):
            # python.scm captures `class X:` as contract.name. Register X as a class node
            # (kind="class") so `X(...)` resolves like any imported name, and so the
            # classes registry knows X even when it has no methods.
            name = sm.get("contract.name")
            if name:
                self.graph["classes"].setdefault(sm.file_path, {}).setdefault(name, {"superclass": None})
                if not self.function_index.resolve_function(sm.file_path, name):
                    self.ensure_file("functions", sm.file_path)
                    metadata = {"name": name, "file": sm.file_path, "start_line": sm.start_point[0] + 1,
                                "end_line": sm.end_point[0] + 1, "kind": "class"}
                    if getattr(sm, "is_test", False):
                        metadata["is_test"] = True
                    self.function_index.register_function(file_path=sm.file_path, function_name=name, metadata=metadata)
                    self.graph["functions"][sm.file_path].append(dict(metadata))
            return

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
        edge_type,
        is_test=False,
    ):
        edge = {
            "from": from_node,
            "to": to_node,
            "type": edge_type
        }
        if is_test:
            # Test-partition edges are kept but hidden from default traversal (see
            # GraphTraversal); `mcp_tests_for` / include_tests=True surface them.
            edge["is_test"] = True
        self.graph[
            "execution_edges"
        ].append(edge)

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

        param = sm.get("param.name")
        if not param:
            if sm.get("param.destructure_prop"):
                param = sm.get("param.destructure_prop")
            elif sm.get("param.rest"):
                param = f"...{sm.get('param.rest')}"
            elif sm.get("param.destructure_rest"):
                param = f"...{sm.get('param.destructure_rest')}"
            elif sm.get("param.star_args"):
                param = f"*{sm.get('param.star_args')}"
            elif sm.get("param.kw_args"):
                param = f"**{sm.get('param.kw_args')}"


        if not param:
            return

        if DEBUG_GRAPH_BUILD:
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

        if "param_groups" not in existing:
            existing["param_groups"] = []

        is_destructured = bool(sm.get("param.destructure_prop"))
        is_rest = bool(sm.get("param.rest") or sm.get("param.destructure_rest"))

        if is_destructured:
            if existing["param_groups"] and existing["param_groups"][-1]["type"] == "destructured":
                if param not in existing["param_groups"][-1]["keys"]:
                    existing["param_groups"][-1]["keys"].append(param)
            else:
                existing["param_groups"].append({"type": "destructured", "keys": [param]})
        elif is_rest:
            existing["param_groups"].append({"type": "rest", "name": param})
        else:
            existing["param_groups"].append({"type": "positional", "name": param})




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

        if DEBUG_GRAPH_BUILD:
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
                source_site = {"source_file": file_path, "source_function": call.get("caller_function") or "GLOBAL"}

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
                param_groups = []

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
                        param_groups = param_entry.get("param_groups", [])

                        break

                # ==================================================
                # CONNECT ARG → PARAM
                # ==================================================

                if not arguments or not (parameters or param_groups):
                    continue

                import re

                if param_groups:
                    for i in range(min(len(arguments), len(param_groups))):
                        arg_str = arguments[i]
                        group = param_groups[i]

                        if group["type"] == "destructured":
                            destructured_keys = group["keys"]
                            # If argument is an object literal (e.g. "{ email: req.body.email, password: safePass }")
                            if isinstance(arg_str, str) and arg_str.strip().startswith("{") and ":" in arg_str:
                                props = re.findall(r'(\w+)\s*:\s*([^,}]+)', arg_str)
                                if props:
                                    matched_prop = False
                                    for key, val in props:
                                        key = key.strip()
                                        val = val.strip()
                                        if key in destructured_keys:
                                            self.graph["data_flow"].append({
                                                **source_site,
                                                "source": val,
                                                "target_file": target_file,
                                                "target_function": target_function,
                                                "target_param": key
                                            })
                                            matched_prop = True
                                    if matched_prop:
                                        continue
                            # If not object literal or unmatched, map arg_str to all destructured keys
                            for key in destructured_keys:
                                self.graph["data_flow"].append({
                                    **source_site,
                                    "source": arg_str,
                                    "target_file": target_file,
                                    "target_function": target_function,
                                    "target_param": key
                                })

                        elif group["type"] == "rest":
                            rest_name = group["name"].lstrip(".")
                            for j in range(i, len(arguments)):
                                self.graph["data_flow"].append({
                                    **source_site,
                                    "source": arguments[j],
                                    "target_file": target_file,
                                    "target_function": target_function,
                                    "target_param": rest_name
                                })
                            break

                        else:  # positional
                            self.graph["data_flow"].append({
                                **source_site,
                                "source": arg_str,
                                "target_file": target_file,
                                "target_function": target_function,
                                "target_param": group["name"]
                            })
                else:
                    # Fallback if param_groups is not present
                    for i in range(min(len(arguments), len(parameters))):
                        self.graph["data_flow"].append({
                            **source_site,
                            "source": arguments[i],
                            "target_file": target_file,
                            "target_function": target_function,
                            "target_param": parameters[i]
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
            if not (self.frameworks & self._WEB_FRAMEWORKS):
                continue

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
            ) or sm.get(
                "field.variable"
            )

            value = sm.get(
                "assign.value"
            ) or ""


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

            if DEBUG_GRAPH_BUILD:
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
            ) or sm.get(
                "field.variable"
            )

            value = sm.get(
                "assign.value"
            ) or ""


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

            if DEBUG_GRAPH_BUILD:
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

    # ======================================================
    # VARIABLE TYPE RESOLUTION
    # ======================================================

    def handle_variable_type(self, sm):
        variable = sm.get("assign.variable") or sm.get("field.variable")
        value = sm.get("assign.value")
        
        class_name = sm.get("assign.type") or sm.get("assign.value_type") or sm.get("field.type")
        if not class_name and value:
            from semantic_core.symbol_resolver import SymbolResolver
            class_name = SymbolResolver.extract_instantiated_class(value)
            
        if variable and class_name:
            owner_fn = sm.owner_function or "GLOBAL"
            self.symbol_table.register_type(
                sm.file_path,
                owner_fn,
                variable,
                class_name
            )



