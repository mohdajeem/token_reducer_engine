import re
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
            if sm.match_type == "CLASS_DEF":
                self.handle_class_def(sm)

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

        return self.finalize()

    def ingest(self, semantic_matches):
        """The per-match passes of build() for a subset of files (incremental updates), without
        the graph-wide post-passes. Call finalize() once afterwards."""
        self._finalized = False
        saved = self.graph
        # build() runs the per-match passes then finalize(); run only the per-match part by
        # temporarily replacing finalize with a no-op
        self._skip_finalize = True
        try:
            self.build(semantic_matches)
        finally:
            self._skip_finalize = False
        return self.graph

    def finalize(self):
        """Graph-wide passes after all matches are in: argument->parameter flow, late type
        inference, unresolved-call resolution, taint / security analysis."""
        if getattr(self, "_skip_finalize", False):
            return self.graph
        # Late inference is a fixpoint: a call resolved by round N creates argument->parameter
        # flow that types a parameter, which resolves more calls in round N+1. Iterate until
        # nothing new resolves (bounded) so the result does not depend on how many times
        # finalize() has run -- an incremental update must land on the same graph as a full
        # build. Rounds after the first only cost the flow/inference passes (no re-parse).
        # variable states first: return-type inference reads `v = f()` assignments from them
        self.track_variable_states()
        for _round in range(6):
            before = sum(1 for calls in self.graph["calls"].values() for c in calls if c.get("resolved_function"))
            n_types = sum(len(v) for scopes in self.symbol_table.types.values() for v in scopes.values())
            self.graph["data_flow"] = []
            self.build_argument_parameter_flow()
            self.infer_parameter_types_from_flow()
            self.infer_types_from_returns()
            self.infer_stored_callables()
            self.infer_fixture_param_types()
            self.infer_class_attribute_injection()
            self.resolve_pending_calls()
            self.resolve_dispatch_calls()
            after = sum(1 for calls in self.graph["calls"].values() for c in calls if c.get("resolved_function"))
            n_types2 = sum(len(v) for scopes in self.symbol_table.types.values() for v in scopes.values())
            n_ret = len(getattr(self, "_return_types", None) or {})
            if after == before and n_types2 == n_types and n_ret == getattr(self, "_n_ret_prev", -1):
                break
            self._n_ret_prev = n_ret
        self.link_nested_functions()
        self.link_constant_uses()
        self.link_implementations()
        self.link_java_routes()

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

        # (variable states were tracked before the inference fixpoint above)
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

        if sm.get("import.star"):
            src_file = self.symbol_table.register_star_import(sm.file_path, sm.get("import.source"))
            self.graph["imports"][sm.file_path].append({"source": sm.get("import.source"), "name": "*", "alias": None,
                                                        "file": src_file})
            if src_file and sm.file_path.endswith(".py"):
                # a module that star-imports another re-exports everything it defines
                entry = self.graph["reexports"].setdefault(sm.file_path, {"star": [], "names": {}})
                if src_file not in entry["star"]:
                    entry["star"].append(src_file)
            return

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
            **({"static": True} if sm.get("import.static") else {}),
        })

        # A Python module that imports a name re-exports it (importing binds the name in the
        # module's namespace): `from .core.engine import boot` in pkg/__init__.py makes
        # `from pkg import boot` reach engine.py, and `from .exceptions import
        # TemplateSyntaxError` in template/base.py makes `from .base import
        # TemplateSyntaxError` reach exceptions.py (400 django call sites hit this).
        if sm.file_path.endswith(".py") and resolved_file and sm.get("import.name"):
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

    _BUILTIN_FUNCTION_NAMES = None

    @classmethod
    def builtin_function_names(cls):
        """Bare names the language provides: Python builtins (len, isinstance, ValueError,
        super, ...) and the JS/browser/Node globals. A call to one of these is never a
        project function; labelling it keeps it out of "unresolved" counts and out of the
        completeness block of a project function that happens to share the name (open)."""
        if cls._BUILTIN_FUNCTION_NAMES is None:
            import builtins
            names = {n for n in dir(builtins) if not n.startswith("_")}
            names |= {"require", "parseInt", "parseFloat", "isNaN", "isFinite", "setTimeout", "setInterval",
                      "clearTimeout", "clearInterval", "setImmediate", "queueMicrotask", "fetch", "alert",
                      "encodeURIComponent", "decodeURIComponent", "encodeURI", "decodeURI", "escape", "unescape",
                      "Symbol", "Promise", "Array", "Object", "String", "Number", "Boolean", "Date", "RegExp", "Error",
                      "TypeError", "RangeError", "Map", "Set", "WeakMap", "WeakSet", "Proxy", "Reflect", "BigInt",
                      "structuredClone", "Function", "Uint8Array", "Float32Array", "Float64Array", "ArrayBuffer",
                      "describe", "it", "test", "expect", "beforeEach", "afterEach", "beforeAll", "afterAll",
                      "suite", "context", "specify", "jest", "vi"}
            cls._BUILTIN_FUNCTION_NAMES = frozenset(names)
        return cls._BUILTIN_FUNCTION_NAMES

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

    def infer_types_from_returns(self):
        """`def session(): return Session()` types `s` in `s = session()`; `return self`
        types fluent chains; `return x` with a typed local x too. Return types are learned
        from the `returns` records, then applied to every `v = f(...)` / `v = obj.f(...)`
        assignment whose call already resolved. Runs inside the finalize fixpoint, so a
        variable typed here can resolve calls that type further variables next round."""
        import re as _re
        from semantic_core.symbol_resolver import SymbolResolver
        owner_class = {}
        nested = {}  # (file, inner name) -> enclosing def
        for f, fns in self.graph["functions"].items():
            for fn in fns:
                if isinstance(fn, dict) and fn.get("class"):
                    owner_class.setdefault((f, fn["name"]), set()).add(fn["class"])
                if isinstance(fn, dict) and fn.get("parent"):
                    nested[(f, fn["name"])] = fn["parent"]
        ret = {}
        # declared / documented return types win over inference (`-> Axes`, numpydoc Returns)
        declared = {}
        for f, fns in self.graph["functions"].items():
            for fn in fns:
                if isinstance(fn, dict) and fn.get("return_type") and self.resolve_class_file(f, fn["return_type"]):
                    declared.setdefault((f, fn["name"]), set()).add(fn["return_type"])
        for k, v in declared.items():
            if len(v) == 1:
                ret[k] = set(v)
        tuples = {}  # (file, fn) -> [type or None per position] for `return fig, ax`
        for r in self.graph.get("returns", []):
            f, fn, val = r.get("file"), r.get("function"), (r.get("value") or "").strip()
            if not fn or not val:
                continue
            if (f, fn) in declared:
                continue
            if "," in val and "(" not in val and "[" not in val and "{" not in val:
                parts = [p.strip() for p in val.split(",")]
                if all(_re.match(r"^[A-Za-z_]\w*$", p) for p in parts):
                    tuples[(f, fn)] = [self.symbol_table.resolve_type(f, fn, p) for p in parts]
                continue
            t = SymbolResolver.extract_instantiated_class(val)
            cs = owner_class.get((f, fn)) or set()
            own = next(iter(cs)) if len(cs) == 1 else None
            if not t and (val in ("self", "this") or _re.match(r"^(?:self\.__class__|type\(self\)|cls)\s*\(", val)):
                # `return self` (fluent APIs), `return self.__class__(...)` / `type(self)(...)`
                # (QuerySet._clone), `return cls(...)` (classmethod constructors)
                t = own
            if not t and _re.match(r"^[A-Za-z_$][\w$]*$", val):
                t = self.symbol_table.resolve_type(f, fn, val)
                if not t and (f, val) in nested and nested[(f, val)] == fn:
                    # `return make` where make is a def nested in this function: the caller
                    # gets a callable; what IT returns is looked up when it is called
                    t = f"callable:{f}:{val}"
            if not t:
                m = _re.match(r"^(?:self|this)\.([A-Za-z_$][\w$]*)\s*\(", val)
                if m and own:
                    # `return self._chain()`: the sibling method's return type (previous round)
                    prev = getattr(self, "_return_types", None) or {}
                    t = prev.get((f, m.group(1)))
            if not t and ("(" in val or "." in val):
                # `return figure().add_subplot()` / `return fig.legend()`: chain typing from the
                # previous round's return types
                t = self._expr_type(f, fn, val)
                if t and t.startswith(("callable:", "class:")):
                    t = None
            if t:
                ret.setdefault((f, fn), set()).add(t)
        ret = {k: next(iter(v)) for k, v in ret.items() if len(v) == 1}
        self._return_types = ret
        self._return_tuples = tuples
        if not ret and not tuples:
            return 0
        call_target, class_target = {}, {}
        for f, calls in self.graph["calls"].items():
            for c in calls:
                rf = c.get("resolved_function")
                if isinstance(rf, dict) and c.get("function") and rf.get("kind") != "class":
                    call_target.setdefault((f, c.get("caller_function") or "GLOBAL_SCOPE", c["function"]),
                                           (c.get("resolved_file"), rf.get("name")))
                elif isinstance(rf, dict) and c.get("function") and rf.get("kind") == "class" and c.get("receiver") in ("self", "this", "cls"):
                    class_target.setdefault((f, c.get("caller_function") or "GLOBAL_SCOPE", c["function"]), rf.get("name"))
        n = 0
        for vs in self.graph.get("variable_states", []):
            var, val, f, fn = vs.get("variable"), vs.get("value") or "", vs.get("file"), vs.get("function") or "GLOBAL_SCOPE"
            scope = "GLOBAL" if fn == "GLOBAL_SCOPE" else fn
            if var and "," in var:
                # `fig, ax = plt.subplots()`: positional types from the callee's `return fig, axs`
                targets = [t.strip() for t in var.split(",")]
                target_fn = self._callee_of_expr(f, fn, val.strip())
                types = self._return_tuples.get(target_fn) if target_fn else None
                if types:
                    for name, t in zip(targets, types):
                        if t and name and not self.symbol_table.resolve_type(f, scope, name):
                            self.symbol_table.register_type(f, scope, name, t)
                            n += 1
                continue
            if not var or self.symbol_table.resolve_type(f, scope, var):
                continue
            m = _re.match(r"^(?:await\s+)?(?:[\w$]+\.)*([\w$]+)\s*\(", val)
            if not m:
                continue
            callee = m.group(1)
            t = None
            if "." not in val.split("(")[0]:
                # `app_ = make_app(...)` where make_app is a variable / parameter typed as a
                # callable (a factory fixture): the value is what the inner function returns
                ct = self.symbol_table.resolve_type(f, scope, callee)
                if ct and ct.startswith("callable:"):
                    _, cf, cfn = ct.split(":", 2)
                    ts = {ret.get((cf, x)) for x in cfn.split("|")} - {None}
                    t = next(iter(ts)) if len(ts) == 1 else None
                elif ct and ct.startswith("class:"):
                    names = ct[6:].split("|")
                    if len(names) == 1:
                        t = names[0]
                    else:
                        self.param_candidates[(f, scope, var)] = sorted(names)
            if not t:
                t = ret.get(call_target.get((f, fn, callee), (None, None)))
            if not t:
                t = class_target.get((f, fn, callee))  # `v = self.cls()` resolved to a class node
            if not t:
                t = self._expr_type(f, scope, val)  # chains: figure().add_subplot(), fig.legend()
            if t and not t.startswith(("callable:", "class:")):
                self.symbol_table.register_type(f, scope, var, t)
                n += 1
        return n

    def _callee_of_expr(self, file_path, caller, expr):
        """(file, function name) of the function a call expression invokes, or None."""
        head, name, _args = self._split_call(expr)
        if name is None:
            return None
        if head is None:
            for c in self.graph["calls"].get(file_path, []):
                if c.get("function") == name and (c.get("caller_function") or "GLOBAL_SCOPE") == caller and c.get("resolved_function") \
                        and not c.get("receiver"):
                    return (c.get("resolved_file"), c["resolved_function"].get("name"))
            return None
        recv_t = self._expr_type(file_path, "GLOBAL" if caller == "GLOBAL_SCOPE" else caller, head)
        if recv_t and not recv_t.startswith(("callable:", "class:")):
            cf, cm = self.resolve_method(file_path, recv_t, name)
            if cm:
                return (cf, cm["name"])
        if not recv_t and head[:1].isupper() and "." not in head and self.resolve_class_file(file_path, head):
            # `Visit.builder()` / `Lexer.lex(src)`: the receiver is the class -> static method
            cf, cm = self.resolve_method(file_path, head, name, _want_static=True)
            if cm:
                return (cf, cm["name"])
        # module alias: plt.subplots()
        imp = self.symbol_table.resolve_import(file_path, head)
        if imp:
            f2, m2, _ = self.resolve_through_reexports(imp, name)
            if m2:
                return (f2, m2["name"])
        return None

    @staticmethod
    def _split_call(expr):
        """'a.b(c).d(e)' -> ('a.b(c)', 'd', 'e'); 'f(x)' -> (None, 'f', 'x'); else (None, None, None)."""
        expr = expr.strip()
        if expr.startswith("await "):
            expr = expr[6:].strip()
        if not expr.endswith(")"):
            return None, None, None
        depth, i = 0, len(expr) - 1
        while i >= 0:
            ch = expr[i]
            if ch == ")":
                depth += 1
            elif ch == "(":
                depth -= 1
                if depth == 0:
                    break
            i -= 1
        if i <= 0:
            return None, None, None
        args = expr[i + 1:-1]
        callee = expr[:i]
        j = len(callee) - 1
        while j >= 0 and (callee[j].isalnum() or callee[j] in "_$"):
            j -= 1
        name = callee[j + 1:]
        if not name:
            return None, None, None
        head = callee[:j].strip() if j >= 0 and callee[j] == "." else (None if j < 0 else callee[:j + 1].strip() or None)
        if head is not None and head.startswith("new ") is False and j >= 0 and callee[j] != ".":
            return None, None, None
        return head, name, args

    def _expr_type(self, file_path, scope, expr, _depth=0):
        """Best-effort type of a Python/JS expression used as a receiver or value:
        name / self.field / X(...) / f(...) / a.b(...).c(...) chains."""
        if not expr or _depth > 6:
            return None
        import re as _re
        from semantic_core.symbol_resolver import SymbolResolver
        expr = expr.strip()
        if expr.startswith("await "):
            expr = expr[6:].strip()
        if expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1].strip()
        if _re.match(r"^[A-Za-z_$][\w$]*$", expr):
            t = self.symbol_table.resolve_type(file_path, scope, expr)
            return t
        m = _re.match(r"^(?:self|this)\.([A-Za-z_]\w*)$", expr)
        if m:
            cls = None
            for f, fns in self.graph["functions"].items():
                if f == file_path:
                    for fn in fns:
                        if isinstance(fn, dict) and fn["name"] == scope and fn.get("class"):
                            cls = fn["class"]
                            break
            return self.resolve_field_type(file_path, cls, m.group(1)) if cls else None
        head, name, _args = self._split_call(expr)
        if name is not None:
            inst = SymbolResolver.extract_instantiated_class(expr if head is None else f"{name}()")
            if head is None and inst and self.resolve_class_file(file_path, inst):
                return inst
            if head is not None and name[:1].isupper() and self.resolve_class_file(file_path, name):
                return name  # mod.Class(...)
            callee = self._callee_of_expr(file_path, "GLOBAL_SCOPE" if scope == "GLOBAL" else scope, expr)
            ret = getattr(self, "_return_types", None) or {}
            if callee:
                t = ret.get(callee)
                if t:
                    return t
            if head is None:
                ct = self.symbol_table.resolve_type(file_path, scope, name)
                if ct and ct.startswith("callable:"):
                    _, cf, names = ct.split(":", 2)
                    ts = {ret.get((cf, x)) for x in names.split("|")} - {None}
                    return next(iter(ts)) if len(ts) == 1 else None
            return None
        m = _re.match(r"^(.+)\.([A-Za-z_]\w*)$", expr)
        if m:
            t = self._expr_type(file_path, scope, m.group(1), _depth + 1)
            return self.resolve_field_type(file_path, t, m.group(2)) if t else None
        return None

    def infer_fixture_param_types(self):
        """pytest injects fixtures by parameter NAME: `def test_x(app):` gets whatever the
        fixture `app` returns/yields. Every sphinx/pytest/xarray test drives the code under
        test through such a parameter, so without this the tests are dead ends in the graph.
        A fixture's type is its inferred return type; the nearest definition wins (same
        file, then a conftest.py up the tree, then a unique one anywhere)."""
        ret = getattr(self, "_return_types", None) or {}
        fixtures = {}  # name -> [(file, type)]
        for f, fns in self.graph["functions"].items():
            for fn in fns:
                if isinstance(fn, dict) and fn.get("fixture"):
                    t = ret.get((f, fn["name"]))
                    if t:
                        injected = fn["fixture"] if isinstance(fn["fixture"], str) else fn["name"]
                        fixtures.setdefault(injected, []).append((f, t))
        if not fixtures:
            return 0
        import posixpath
        n = 0
        for f, entries in self.graph.get("parameters", {}).items():
            if not f.endswith(".py"):
                continue
            for entry in entries:
                fn = entry.get("function")
                for param in entry.get("params") or []:
                    if param not in fixtures or param in ("self", "cls"):
                        continue
                    if self.symbol_table.resolve_type(f, fn, param):
                        continue
                    cands = fixtures[param]
                    same = [t for ff, t in cands if ff == f]
                    if same:
                        t = same[0]
                    else:
                        d = posixpath.dirname(f)
                        conf = None
                        while True:
                            hit = [t for ff, t in cands if ff == posixpath.join(d, "conftest.py") or (not d and ff == "conftest.py")]
                            if hit:
                                conf = hit[0]
                                break
                            if not d:
                                break
                            d = posixpath.dirname(d)
                        if conf:
                            t = conf
                        elif len({t for _, t in cands}) == 1:
                            t = cands[0][1]
                        else:
                            continue
                    self.symbol_table.register_type(f, fn, param, t)
                    n += 1
        return n

    _DICT_ENTRY_RE = re.compile(r"""(?:[\"']([^\"']+)[\"']|([A-Za-z_]\w*))\s*:\s*([A-Za-z_$][\w$.]*)\s*(?=[,}\n])""")

    def _callable_target(self, file_path, owner_class, ref):
        """(file, metadata) for a function reference in a dict literal: `and_`, `self.f`,
        `Cls.m`, `mod.f`; None if the name is not a function we know."""
        if "(" in ref:
            return None
        if ref.startswith(("self.", "this.", "cls.")) and owner_class:
            return self.resolve_method(file_path, owner_class, ref.split(".", 1)[1])
        if "." in ref:
            head, name = ref.rsplit(".", 1)
            if head[:1].isupper() and self.resolve_class_file(file_path, head):
                return self.resolve_method(file_path, head, name, _want_static=True)
            f = self.symbol_table.resolve_import(file_path, head)
            if f:
                f2, m2, _ = self.resolve_through_reexports(f, name)
                return (f2, m2) if m2 else None
            return None
        meta = self.function_index.resolve_function(file_path, ref)
        if meta and meta.get("kind") != "class":
            return file_path, meta
        f = self.symbol_table.resolve_import(file_path, ref)
        if f:
            f2, m2, _ = self.resolve_through_reexports(f, self.symbol_table.resolve_imported_name(file_path, ref) or ref)
            return (f2, m2) if m2 else None
        for src in self.symbol_table.star_imports.get(file_path, []):
            f2, m2, _ = self.resolve_through_reexports(src, ref)
            if m2:
                return f2, m2
        return None

    def build_dispatch_tables(self):
        """(file, name) -> [(file, metadata)] for every dict literal whose values are ALL
        function references (at least two): `_ops = {'&': and_, '|': or_}`,
        `self.handlers = {"a": self.on_a, "b": self.on_b}`."""
        tables = {}
        class_of_fn = {}
        for f, fns in self.graph["functions"].items():
            for fn in fns:
                if isinstance(fn, dict) and fn.get("class"):
                    class_of_fn.setdefault((f, fn["name"]), fn["class"])
        for vs in self.graph.get("variable_states", []):
            val = (vs.get("value") or "").strip()
            var = vs.get("variable")
            if not var or not val.startswith("{") or ":" not in val:
                continue
            entries = self._DICT_ENTRY_RE.findall(val)
            if len(entries) < 2:
                continue
            f = vs["file"]
            owner = class_of_fn.get((f, vs.get("function")))
            targets = []
            for _k1, _k2, ref in entries:
                t = self._callable_target(f, owner, ref)
                if not t or not t[1]:
                    targets = None
                    break
                targets.append(t)
            if targets:
                name = var.split(".")[-1]
                tables.setdefault((f, name), []).extend(x for x in targets if x not in tables.get((f, name), []))
        self._dispatch_tables = tables
        return tables

    def resolve_dispatch_calls(self):
        """Link computed-callee calls: dispatch tables to every value they hold
        (confidence="dispatch"), getattr(self, "prefix_"+x)() to every method of the class
        with that prefix (confidence="dynamic"). Consumers can weigh or drop these."""
        tables = self.build_dispatch_tables()
        edges = self.graph["execution_edges"]
        first_new = len(edges)
        replaced = set()
        for file_path, calls in self.graph["calls"].items():
            for call in calls:
                d = call.get("dispatch")
                if not d or call.get("resolved_function"):
                    continue
                targets, conf = [], None
                if d["kind"] == "dispatch":
                    t = tables.get((file_path, d["table"]))
                    if not t and d.get("table"):
                        # a table imported from another module
                        f = self.symbol_table.resolve_import(file_path, d["table"])
                        if f:
                            t = tables.get((f, d["table"]))
                    targets, conf = list(t or []), "dispatch"
                elif d["kind"] == "dynamic":
                    recv, prefix = call.get("receiver"), d.get("prefix") or ""
                    cls = None
                    if recv in ("self", "cls") and call.get("caller_class"):
                        cls = call["caller_class"]
                    elif recv:
                        cls = self.symbol_table.resolve_type(file_path, call.get("caller_function") or "GLOBAL", recv)
                    if cls and prefix:
                        cf = self.resolve_class_file(file_path, cls) or file_path
                        for fn in self.graph["functions"].get(cf, []):
                            if isinstance(fn, dict) and fn.get("class") == cls and fn["name"].startswith(prefix):
                                targets.append((cf, fn))
                    conf = "dynamic"
                if not targets:
                    continue
                from_node = {"type": "FUNCTION", "file": file_path,
                             "function": call.get("caller_function") or "GLOBAL_SCOPE"}
                if call.get("caller_class"):
                    from_node["class"] = call["caller_class"]
                call.update({"resolved_file": targets[0][0], "resolved_function": targets[0][1],
                             "resolved_class": targets[0][1].get("class"), "resolution": conf,
                             "candidates": [{"file": tf, "function": tm["name"], "class": tm.get("class")} for tf, tm in targets]})
                if call.get("call_id"):
                    replaced.add(call["call_id"])
                for tf, tm in targets:
                    self.add_execution_edge(from_node=dict(from_node),
                                            to_node={"type": "FUNCTION", "file": tf, "function": tm["name"],
                                                     **({"class": tm["class"]} if tm.get("class") else {})},
                                            edge_type="FUNCTION_CALL", is_test=bool(call.get("is_test")), call_id=call.get("call_id"))
                    self.graph["execution_edges"][-1]["confidence"] = conf
        if replaced:
            self.graph["execution_edges"] = [e for i, e in enumerate(self.graph["execution_edges"])
                                             if i >= first_new or e.get("call_id") not in replaced]

    def _orm_queryset_class(self, file_path):
        """"QuerySet" when the project defines exactly one class of that name (Django itself,
        or an app vendoring the ORM); None otherwise so nothing is guessed elsewhere."""
        cache = getattr(self, "_qs_cache", None)
        if cache is None:
            owners = [(f, c) for f, cs in self.graph["classes"].items() for c in cs if c == "QuerySet"]
            cache = self._qs_cache = "QuerySet" if len(owners) == 1 else None
        return cache

    def infer_class_attribute_injection(self):
        """pylint's test pattern: a base class does `self.checker = self.CHECKER_CLASS(...)`
        and each subclass sets `CHECKER_CLASS = VariablesChecker`. For every class C with
        such an attribute, the field assigned from `self.ATTR(...)` anywhere up C's
        superclass chain gets C's value of ATTR as its type. Also links the base class's
        `self.ATTR(...)` call site to every subclass value's constructor (candidates)."""
        import re as _re
        classes = self.graph.get("classes") or {}
        # (file, class) -> {field: attr} from `self.field = self.ATTR(...)` in its methods
        inject = {}
        pat = _re.compile(r"^\s*(?:self|this)\.([A-Za-z_]\w*)\s*\(")
        for vs in self.graph.get("variable_states", []):
            var, cls = vs.get("variable") or "", vs.get("class")
            if not cls or not var.startswith(("self.", "this.")):
                continue
            m = pat.match(vs.get("value") or "")
            if m:
                inject.setdefault((vs["file"], cls), {})[var.split(".", 1)[1]] = m.group(1)
        def chain(file, cls, depth=0):
            out = [(file, cls)]
            entry = (classes.get(file) or {}).get(cls) or {}
            sup = entry.get("superclass")
            if sup and depth < 8:
                sf = self.resolve_class_file(file, sup) or file
                out += chain(sf, sup, depth + 1)
            return out

        n = 0
        for f, cs in classes.items():
            for cname, entry in cs.items():
                attrs = entry.get("attrs") or {}
                if not attrs:
                    continue
                for bf, bc in chain(f, cname):
                    for field, attr in inject.get((bf, bc), {}).items():
                        val = attrs.get(attr)
                        val = _re.sub(r"^(?:staticmethod|classmethod)\(\s*(.+?)\s*\)$", r"\1", val or "")
                        if not val or not _re.match(r"^[A-Za-z_][\w.]*$", val) or val == "None":
                            continue
                        tname = val.split(".")[-1]
                        if not self.resolve_class_file(f, tname):
                            continue
                        fields = entry.setdefault("fields", {})
                        if fields.get(field) != tname:
                            fields[field] = tname
                            n += 1
        # `self.ATTR(...)` where ATTR is a class attribute holding a class (in this class or a
        # subclass): every such value is a possible callee
        if True:
            sub_values = {}  # (attr) -> {(file, class name of value)}
            for f, cs in classes.items():
                for cname, entry in cs.items():
                    for attr, val in (entry.get("attrs") or {}).items():
                        val = _re.sub(r"^(?:staticmethod|classmethod)\(\s*(.+?)\s*\)$", r"\1", val or "")
                        if val and _re.match(r"^[A-Za-z_][\w.]*$", val) and val != "None":
                            tname = val.split(".")[-1]
                            cf = self.resolve_class_file(f, tname)
                            if cf:
                                sub_values.setdefault(attr, set()).add((cf, tname))
            for file_path, calls in self.graph["calls"].items():
                for call in calls:
                    if call.get("resolved_function") or call.get("receiver") not in ("self", "this"):
                        continue
                    targets = sub_values.get(call.get("function"))
                    if not targets:
                        continue
                    from_node = {"type": "FUNCTION", "file": file_path, "function": call.get("caller_function") or "GLOBAL_SCOPE"}
                    if call.get("caller_class"):
                        from_node["class"] = call["caller_class"]
                    cands = []
                    for cf, tname in sorted(targets):
                        meta = self.function_index.resolve_function(cf, tname)
                        if not meta:
                            continue
                        cands.append((cf, meta))
                        self.add_execution_edge(from_node=dict(from_node), to_node={"type": "FUNCTION", "file": cf, "function": tname},
                                                edge_type="FUNCTION_CALL", is_test=bool(call.get("is_test")), call_id=call.get("call_id"))
                        self.graph["execution_edges"][-1]["confidence"] = "candidates"
                        self._constructor_edge(from_node, cf, meta, bool(call.get("is_test")), call.get("call_id"))
                    if cands:
                        call.update({"resolved_file": cands[0][0], "resolved_function": cands[0][1], "resolution": "candidates",
                                     "candidates": [{"file": cf, "function": m["name"]} for cf, m in cands]})
        return n

    _JS_GLOBAL_NAMES = frozenset({"Object", "Array", "Promise", "Reflect", "JSON", "Math", "Number", "String", "Boolean",
                                  "Symbol", "Date", "Map", "Set", "WeakMap", "WeakSet", "Error", "TypeError", "RangeError",
                                  "RegExp", "Function", "Proxy", "BigInt", "Intl", "console", "process", "globalThis",
                                  "window", "document", "navigator", "Buffer", "Atomics", "ArrayBuffer", "Uint8Array",
                                  # test runners' globals (vitest / jest / jasmine / mocha / cypress / sinon)
                                  "vi", "jest", "jasmine", "expect", "cy", "sinon", "chai", "assert"})

    _JAVA_LANG_NAMES = frozenset({"String", "Integer", "Long", "Short", "Byte", "Double", "Float", "Boolean", "Character",
                                  "Math", "Objects", "System", "Thread", "StringBuilder", "StringBuffer", "Object",
                                  "Class", "Enum", "Exception", "RuntimeException", "Throwable", "Runtime", "Iterable"})

    _JAVA_MAPPINGS = {"GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT", "DeleteMapping": "DELETE",
                      "PatchMapping": "PATCH", "RequestMapping": "ANY"}

    def _java_route_from_annotations(self, sm, function_name, owner_class, annotations):
        """`@GetMapping("/owners/new")` on OwnerController.initCreationForm -> a route record
        (method, path with the class-level @RequestMapping prefix, handler) plus the
        ROUTE -> handler edge, same shape as the Express routes."""
        for ann, method in self._JAVA_MAPPINGS.items():
            if ann not in annotations:
                continue
            path = annotations.get(ann) or ""
            prefix = ""
            if owner_class:
                centry = self.graph["classes"].get(sm.file_path, {}).get(owner_class) or {}
                prefix = (centry.get("annotations") or {}).get("RequestMapping") or ""
            full = (prefix.rstrip("/") + "/" + path.lstrip("/")).rstrip("/") or "/"
            self.ensure_file("routes", sm.file_path)
            route = {"path": full, "method": method, "handler": {"function": function_name, "class": owner_class},
                     "file": sm.file_path, "framework": "spring"}
            self.graph["routes"][sm.file_path].append(route)
            self.add_execution_edge(from_node={"type": "ROUTE", "route": full, "method": method, "file": sm.file_path},
                                    to_node={"type": "FUNCTION", "file": sm.file_path, "function": function_name, "class": owner_class},
                                    edge_type="ROUTE_CALL")

    _JAVA_TEST_REQUEST_RE = re.compile(
        r"(?<![\w])(?:MockMvcRequestBuilders\.)?(get|post|put|delete|patch|options|head|multipart|getForObject|getForEntity|postForObject|postForEntity|"
        r"postForLocation|exchange|uri)\s*\(\s*\"(/[^\"]*)\"")

    def link_java_routes(self):
        """Convention rule (like the pytest fixture one): a Spring test drives a controller
        by URL -- `mockMvc.perform(get("/owners/new"))`, `restTemplate.getForObject("/vets", ..)`
        -- so the handler is never named. For every test method in a .java test file, each
        `<verb>("/path")` in its body is matched against the registered routes (method +
        path template, `{var}` = one segment, query string ignored) and an edge
        test -> handler is added, confidence="convention". Idempotent."""
        routes = []
        for f, rs in self.graph.get("routes", {}).items():
            for r in rs:
                if r.get("framework") != "spring":
                    continue
                tmpl = re.escape(r["path"])
                tmpl = re.sub(r"\\\{[^}]*\\\}", r"[^/]+", tmpl)  # `{ownerId}` -> one segment
                tmpl = re.sub(r"\\\*\\\*", r".*", tmpl)
                tmpl = re.sub(r"\\\*", r"[^/]*", tmpl)
                routes.append((re.compile("^" + tmpl + "/?$"), r["method"], f, r["handler"], r["path"].count("{") + r["path"].count("*")))
        if not routes:
            return 0
        have = set()
        for e in self.graph.get("execution_edges", []):
            if e.get("via") == "route":
                have.add((e["from"].get("file"), e["from"].get("function"), e["to"].get("file"), e["to"].get("function")))
        root = getattr(self, "project_root", None) or ""
        verbs = {"get": "GET", "getForObject": "GET", "getForEntity": "GET", "post": "POST", "postForObject": "POST",
                 "postForEntity": "POST", "postForLocation": "POST", "put": "PUT", "delete": "DELETE", "patch": "PATCH",
                 "options": "OPTIONS", "head": "HEAD", "multipart": "POST"}
        n = 0
        for f, fns in self.graph["functions"].items():
            if not f.endswith(".java"):
                continue
            tests = [fn for fn in fns if isinstance(fn, dict) and fn.get("is_test") and fn.get("kind") != "class" and fn.get("start_line")]
            if not tests:
                continue
            try:
                with open(os.path.join(root, f), "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().split("\n")
            except OSError:
                continue
            for fn in tests:
                body = "\n".join(lines[fn["start_line"] - 1:fn.get("end_line") or fn["start_line"]])
                for verb, url in self._JAVA_TEST_REQUEST_RE.findall(body):
                    method = verbs.get(verb)  # None for uri()/exchange(): any method
                    path = url.split("?", 1)[0]
                    hits = [(wild, rf, handler) for rx, rmethod, rf, handler, wild in routes
                            if rx.match(path) and (not method or rmethod in ("ANY", method))]
                    if not hits:
                        continue
                    best = min(w for w, _, _ in hits)  # Spring: literal segments beat {variables}
                    for wild, rf, handler in hits:
                        if wild != best:
                            continue
                        key = (f, fn["name"], rf, handler["function"])
                        if key in have:
                            continue
                        have.add(key)
                        from_node = {"type": "FUNCTION", "file": f, "function": fn["name"]}
                        if fn.get("class"):
                            from_node["class"] = fn["class"]
                        to_node = {"type": "FUNCTION", "file": rf, "function": handler["function"]}
                        if handler.get("class"):
                            to_node["class"] = handler["class"]
                        self.add_execution_edge(from_node=from_node, to_node=to_node, edge_type="FUNCTION_CALL", is_test=True)
                        self.graph["execution_edges"][-1]["confidence"] = "convention"
                        self.graph["execution_edges"][-1]["via"] = "route"
                        n += 1
        return n

    _CONSTRUCTOR_NAMES = frozenset({"__init__", "__new__", "constructor"})

    def link_implementations(self):
        """A call through a base type lands on the base's method; the code that runs is the
        override in a subclass / implementation: Java `owners.findPet(n)` on an
        `OwnerRepository`, django `ops.quote()` on a `BaseDatabaseOperations`, Chart.js
        `element.draw()` on an `Element`. Edge `Base.m -> Sub.m` for every class Sub that
        declares m and lists Base as its superclass / interface, confidence="dispatch",
        via="implementation". Constructors are not overrides (`Sub()` already resolves to
        Sub.__init__ directly). Idempotent; only declared parents, no name-based guessing."""
        parents = []  # (impl file, impl class, parent name)
        for f, cs in self.graph["classes"].items():
            for cname, entry in cs.items():
                for p in [entry.get("superclass")] + list(entry.get("interfaces") or []):
                    if p:
                        parents.append((f, cname, p))
        if not parents:
            return 0
        have = set()
        for e in self.graph.get("execution_edges", []):
            if e.get("via") == "implementation":
                have.add((e["from"].get("file"), e["from"].get("class"), e["from"].get("function"), e["to"].get("file"), e["to"].get("class")))
        n = 0
        for f, cname, p in parents:
            pf = self.resolve_class_file(f, p)
            if not pf:
                continue
            for fn in self.graph["functions"].get(f, []):
                if not isinstance(fn, dict) or fn.get("class") != cname or fn.get("kind") == "class":
                    continue
                m = fn["name"]
                if m == cname or m in self._CONSTRUCTOR_NAMES:
                    continue  # constructors are not overrides
                pmeta = self.function_index.resolve_function(pf, f"{p}.{m}")
                if not pmeta:
                    continue
                key = (pf, p, m, f, cname)
                if key in have:
                    continue
                have.add(key)
                self.add_execution_edge(from_node={"type": "FUNCTION", "file": pf, "function": m, "class": p},
                                        to_node={"type": "FUNCTION", "file": f, "function": m, "class": cname},
                                        edge_type="FUNCTION_CALL", is_test=False)
                self.graph["execution_edges"][-1]["confidence"] = "dispatch"
                self.graph["execution_edges"][-1]["via"] = "implementation"
                n += 1
        return n

    def link_constant_uses(self):
        """Edge function -> constant for every module-level constant a function body reads,
        in its own file or imported by name (`from dj.global_settings import
        FILE_UPLOAD_PERMISSIONS`). confidence="uses". A changed regex or setting then reaches
        the tests through the functions that use it. One regex scan per file that can see
        at least one constant; idempotent."""
        consts = {}  # file -> {name}
        for f, fns in self.graph["functions"].items():
            for fn in fns:
                if isinstance(fn, dict) and fn.get("kind") == "constant":
                    consts.setdefault(f, set()).add(fn["name"])
        if not consts:
            return 0
        visible = {}  # file -> {local name: (const file, const name)}
        for f in self.graph["functions"]:
            vis = {}
            for n in consts.get(f, ()):
                vis[n] = (f, n)
            for imp in self.graph.get("imports", {}).get(f, []):
                src, nm = imp.get("file"), imp.get("name")
                if src and nm and nm in consts.get(src, ()):
                    vis[imp.get("alias") or nm] = (src, nm)
            if vis:
                visible[f] = vis
        have = set()
        for e in self.graph.get("execution_edges", []):
            if e.get("confidence") == "uses":
                have.add((e["from"].get("file"), e["from"].get("function"), e["from"].get("class"), e["to"].get("file"), e["to"].get("function")))
        root = getattr(self, "project_root", None) or ""
        n = 0
        for f, vis in visible.items():
            fns = [fn for fn in self.graph["functions"].get(f, []) if isinstance(fn, dict) and fn.get("kind") not in ("constant", "class", "value") and fn.get("start_line")]
            if not fns:
                continue
            try:
                with open(os.path.join(root, f), "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().split("\n")
            except OSError:
                continue
            rx = re.compile(r"(?<![\w.])(" + "|".join(re.escape(k) for k in sorted(vis, key=len, reverse=True)) + r")(?![\w])")
            for fn in fns:
                body = "\n".join(lines[fn["start_line"]:fn.get("end_line") or fn["start_line"]])  # after the def line
                for name in set(rx.findall(body)):
                    cf, cn = vis[name]
                    key = (f, fn["name"], fn.get("class"), cf, cn)
                    if key in have:
                        continue
                    have.add(key)
                    from_node = {"type": "FUNCTION", "file": f, "function": fn["name"]}
                    if fn.get("class"):
                        from_node["class"] = fn["class"]
                    self.add_execution_edge(from_node=from_node, to_node={"type": "FUNCTION", "file": cf, "function": cn},
                                            edge_type="FUNCTION_CALL", is_test=bool(fn.get("is_test")))
                    self.graph["execution_edges"][-1]["confidence"] = "uses"
                    n += 1
        return n

    def link_nested_functions(self):
        """A function defined inside another (a callback passed to forEach, a jasmine
        matcher's `compare`, an event handler) runs when the enclosing code hands it over,
        which the graph cannot see. Edge parent -> nested, confidence="nested", so the
        blast radius of the inner function includes whoever owns it. Idempotent."""
        have = set()
        for e in self.graph.get("execution_edges", []):
            have.add((e["from"].get("file"), e["from"].get("function"), e["to"].get("file"), e["to"].get("function")))
        n = 0
        for f, fns in self.graph["functions"].items():
            for fn in fns:
                if not isinstance(fn, dict) or not fn.get("parent") or fn.get("kind") == "class":
                    continue
                key = (f, fn["parent"], f, fn["name"])
                if key in have:
                    continue
                have.add(key)
                to_node = {"type": "FUNCTION", "file": f, "function": fn["name"]}
                if fn.get("class"):
                    to_node["class"] = fn["class"]
                is_test = bool(fn.get("is_test"))
                self.add_execution_edge(from_node={"type": "FUNCTION", "file": f, "function": fn["parent"]}, to_node=to_node,
                                        edge_type="FUNCTION_CALL", is_test=is_test)
                self.graph["execution_edges"][-1]["confidence"] = "nested"
                n += 1
        return n

    def _resolve_marker_call(self, file_path, call, caller, ct, replaced):
        """A bare call `name(...)` where `name` is typed as
          callable:<file>:<fn>[|<fn>...]   a stored function / bound method (factory fixture,
                                          `init_func = self._init_from_list`)
          class:<A>[|<B>...]               a stored class (`plotter = _ScatterPlotter`)
          <Class>                          an instance -> its __call__
        Links the call to every target (candidates when more than one). True if linked."""
        from_node = {"type": "FUNCTION", "file": file_path, "function": caller if caller != "GLOBAL" else "GLOBAL_SCOPE"}
        if call.get("caller_class"):
            from_node["class"] = call["caller_class"]
        targets = []  # (file, meta, class-or-None, ctor?)
        if ct.startswith("callable:"):
            _, cf, names = ct.split(":", 2)
            for cfn in names.split("|"):
                cm = self.function_index.resolve_function(cf, cfn)
                if cm:
                    targets.append((cf, cm, cm.get("class"), False))
        elif ct.startswith("class:"):
            for cname in ct[6:].split("|"):
                cf = self.resolve_class_file(file_path, cname)
                cm = self.function_index.resolve_function(cf, cname) if cf else None
                if cm:
                    targets.append((cf, cm, None, True))
        else:
            cf, cm = self.resolve_method(file_path, ct, "__call__")
            if cm:
                targets.append((cf, cm, cm.get("class") or ct, False))
                call["implicit"] = "__call__"
        if not targets:
            return False
        how = "typed" if len(targets) == 1 else "candidates"
        call.update({"resolved_file": targets[0][0], "resolved_function": targets[0][1],
                     "resolved_class": targets[0][2], "resolution": how})
        if len(targets) > 1:
            call["candidates"] = [{"file": tf, "function": tm["name"], "class": tc} for tf, tm, tc, _ in targets]
        if call.get("call_id"):
            replaced.add(call["call_id"])
        for tf, tm, tc, is_ctor in targets:
            to_node = {"type": "FUNCTION", "file": tf, "function": tm["name"]}
            if tc:
                to_node["class"] = tc
            self.add_execution_edge(from_node=dict(from_node), to_node=to_node, edge_type="FUNCTION_CALL",
                                    is_test=bool(call.get("is_test")), call_id=call.get("call_id"))
            if how == "candidates":
                self.graph["execution_edges"][-1]["confidence"] = "candidates"
            if is_ctor:
                self._constructor_edge(from_node, tf, tm, bool(call.get("is_test")), call.get("call_id"))
        return True

    def infer_stored_callables(self):
        """Functions and classes held in variables before being called:
          init_func = self._init_from_list      (astropy Table.__init__, if/elif chain)
          plotter = _ScatterPlotter             (seaborn relplot)     -> class:_ScatterPlotter
          handler = a if cond else b            -> both candidates
          for search in (GridSearchCV(), RandomizedSearchCV()):  -> candidates on the loop target
        Registers callable:/class: markers (several assignments to one name in one scope
        become `|`-joined candidates); loop targets over tuples of instantiations become
        param_candidates so `search.fit()` resolves to every class."""
        import re as _re
        from semantic_core.symbol_resolver import SymbolResolver
        groups = {}
        for vs in self.graph.get("variable_states", []):
            var, f, fn = vs.get("variable"), vs.get("file"), vs.get("function") or "GLOBAL_SCOPE"
            val = (vs.get("value") or "").strip()
            if not var or "." in var or not val:
                continue
            groups.setdefault((f, fn, var), []).append((val, vs.get("class")))
        n = 0
        for (f, fn, var), vals in groups.items():
            scope = "GLOBAL" if fn == "GLOBAL_SCOPE" else fn
            existing = self.symbol_table.resolve_type(f, scope, var)
            if existing and not existing.startswith(("callable:", "class:")):
                continue
            methods, classes, insts = [], [], []
            for val, owner in vals:
                parts = [v.strip() for v in _re.split(r"\s+if\s+.+?\s+else\s+", val)] if " if " in val and " else " in val else [val]
                for part in parts:
                    m = _re.match(r"^(?:self|this)\.([A-Za-z_]\w*)$", part)
                    if m and owner:
                        mf, mm = self.resolve_method(f, owner, m.group(1))
                        if mm:
                            q = f"{mm.get('class') or owner}.{m.group(1)}"
                            if q not in methods:
                                methods.append(q)
                        continue
                    m = _re.match(r"^(?:staticmethod|classmethod)\(\s*(_*[A-Z]\w*)\s*\)$", part) or _re.match(r"^(_*[A-Z]\w*)$", part)
                    if m and self.resolve_class_file(f, m.group(1)):
                        if m.group(1) not in classes:
                            classes.append(m.group(1))
                        continue
                    if part.startswith(("(", "[")):
                        for inst in _re.findall(r"(?:^|[\[(,]\s*)((?:[a-z_]\w*\.)*_*[A-Z]\w*)\s*\(", part):
                            c = SymbolResolver.extract_instantiated_class(inst + "()")
                            if c and self.resolve_class_file(f, c) and c not in insts:
                                insts.append(c)
            if methods:
                self.symbol_table.register_type(f, scope, var, f"callable:{f}:" + "|".join(methods)); n += 1
            elif classes:
                self.symbol_table.register_type(f, scope, var, "class:" + "|".join(classes)); n += 1
            elif len(insts) == 1:
                self.symbol_table.register_type(f, scope, var, insts[0]); n += 1
            elif insts:
                self.param_candidates[(f, scope, var)] = sorted(insts); n += 1
        return n

    def _is_parameter(self, file_path, function_name, name):
        if not function_name or not name:
            return False
        for entry in self.graph.get("parameters", {}).get(file_path, []):
            if entry.get("function") == function_name:
                return name in (entry.get("params") or [])
        return False

    def _return_type_of_call(self, file_path, caller, recv_expr):
        """Type of the value a call expression evaluates to (see _expr_type)."""
        t = self._expr_type(file_path, caller, recv_expr)
        return None if (t and t.startswith(("callable:", "class:"))) else t

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
        edges = self.graph["execution_edges"]
        first_new_edge = len(edges)
        replaced = set()  # call_ids re-resolved in this pass: their earlier edges go
        for file_path, calls in self.graph["calls"].items():
            # local aliases of imports that reach NO project file: `import * as R from 'ramda'`,
            # `const fs = require('fs')`, `import json`, `from os import path`
            external = {}
            star_external = []  # Java `import static org.assertj...Assertions.*`: any bare name
            is_java = file_path.endswith(".java")
            for imp in self.graph["imports"].get(file_path, []):
                src = imp.get("source") or ""
                if is_java:
                    if not src or imp.get("file") is not None:
                        continue
                    label = ".".join(src.split(".")[:2])  # org.junit / java.util / org.springframework
                    if imp.get("name") == "*":
                        star_external.append(label)
                    else:
                        external[src.split(".")[-1]] = label
                    continue
                alias = imp.get("alias") or imp.get("name") or (src.split(".")[0] if src and not src.startswith(".") else None)
                if alias and src and imp.get("file") is None:
                    # package name: `lodash/fp` -> lodash, scoped `@nestjs/common/x` -> @nestjs/common
                    parts = src.split("/")
                    external[alias] = "/".join(parts[:2]) if src.startswith("@") and len(parts) > 1 else parts[0]
            if is_java:
                for n in self._JAVA_LANG_NAMES:
                    external.setdefault(n, "java.lang")
            is_js = file_path.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"))
            if is_js:
                # `Object.create(..)`, `Promise.resolve(..)`, `vi.spyOn(..)`, `expect(x).toBe(..)`:
                # a global the project never defines is a builtin, not an unresolved call
                for n in self._JS_GLOBAL_NAMES:
                    if n not in external and not self.function_index.resolve_function(file_path, n) \
                            and not self.resolve_class_file(file_path, n):
                        external[n] = "builtin"
            for call in calls:
                if call.get("resolved_function"):
                    continue
                recv = call.get("receiver")
                func = call.get("function")
                if not recv and func and not call.get("dispatch"):
                    caller0 = call.get("caller_function") or "GLOBAL"
                    ct = self.symbol_table.resolve_type(file_path, caller0, func)
                    if ct and self._resolve_marker_call(file_path, call, caller0, ct, replaced):
                        continue
                    # bare call that nothing defined: a language builtin, or a name imported
                    # from a package outside the project -> say so instead of leaving None
                    if func in self.builtin_function_names():
                        call["external"] = "builtin"
                    elif func in external:
                        call["external"] = external[func]
                    elif star_external and not self.function_index.resolve_function(file_path, func):
                        # `assertThat(..)` under `import static ...Assertions.*`
                        call["external"] = star_external[0] if len(star_external) == 1 else "static-import"
                    continue
                if not recv or not func or recv in ("this", "super", "self"):
                    continue
                root = recv.split(".")[0].split("[")[0].split("(")[0]
                if root in external:
                    # a library call (R.compose, fs.readFile): unresolvable by design, and
                    # saying so is more useful than a silent None
                    call["external"] = external[root]
                    continue
                caller = call.get("caller_function") or "GLOBAL"
                if (is_java or is_js) and "(" not in recv:
                    # a variable whose DECLARED type is a library class (`List<Owner> results`
                    # -> results.isEmpty(), `MockMvc mockMvc` -> mockMvc.perform(..)): the
                    # call is in the library, say so
                    rt = self.symbol_table.resolve_type(file_path, caller, root) if root == recv else None
                    if not rt and recv.startswith("this.") and recv.count(".") == 1 and call.get("caller_class"):
                        rt = self.resolve_field_type(file_path, call["caller_class"], recv.split(".", 1)[1])
                    if rt and rt in external and not self.resolve_class_file(file_path, rt):
                        call["external"] = external[rt]
                        continue
                elif is_java or is_js:
                    # a chain that STARTS outside the project stays outside: `status().isOk()`,
                    # `get("/x").param(..)`, `mockMvc.perform(..).andExpect(..)`
                    head = re.match(r"^([A-Za-z_$][\w$]*)\s*(\(|\.)", recv)
                    root0 = head.group(1) if head else None
                    label = None
                    if root0 and head.group(2) == "(" and not self.function_index.resolve_function(file_path, root0) \
                            and not self.resolve_class_file(file_path, root0):
                        label = external.get(root0) or (star_external[0] if len(star_external) == 1 else ("static-import" if star_external else None))
                        if not label and is_js and root0 in self.builtin_function_names():
                            label = "builtin"  # `expect(x).toBe(..)` / `require('x').y()`
                    elif root0 and head.group(2) == ".":
                        rt = self.symbol_table.resolve_type(file_path, caller, root0)
                        if rt and rt in external and not self.resolve_class_file(file_path, rt):
                            label = external[rt]
                    if label:
                        call["external"] = label
                        continue
                typed_file = typed_meta = typed_class = None
                if "(" in recv and recv.endswith(")"):
                    # `session().get()` / `self.factory().run()`: the receiver is a call whose
                    # return type infer_types_from_returns learned
                    t = self._return_type_of_call(file_path, caller, recv)
                    if t:
                        typed_file, typed_meta = self.resolve_method(file_path, t, func)
                        typed_class, how = t, "typed"
                if not typed_meta and recv.startswith(("self.", "this.")) and recv.count(".") == 1 and call.get("caller_class"):
                    # `self.checker.visit(...)`: the field's type may only be known now
                    # (assigned in a base class from a subclass attribute, see
                    # infer_class_attribute_injection)
                    t = self.resolve_field_type(file_path, call["caller_class"], recv.split(".", 1)[1])
                    if t:
                        typed_file, typed_meta = self.resolve_method(file_path, t, func)
                        typed_class, how = t, "typed"
                if not typed_meta and recv.endswith(".objects") and recv.count(".") == 1:
                    # Django: `Model.objects.filter(...)`. The manager's methods are
                    # QuerySet's (Manager.from_queryset builds them at import time), so a
                    # static graph must treat `objects` as a QuerySet.
                    t = self._orm_queryset_class(file_path)
                    if t:
                        typed_file, typed_meta = self.resolve_method(file_path, t, func)
                        typed_class, how = t, "typed"
                if not typed_meta and "." not in recv:
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
                            if call.get("call_id"):
                                replaced.add(call["call_id"])
                            for cf, cm, c in resolved:
                                self.add_execution_edge(from_node=dict(from_node),
                                                        to_node={"type": "FUNCTION", "file": cf, "function": func, "class": cm.get("class") or c},
                                                        edge_type="FUNCTION_CALL", is_test=bool(call.get("is_test")), call_id=call.get("call_id"))
                                self.graph["execution_edges"][-1]["confidence"] = "candidates"
                            continue
                if not typed_meta and re.match(r"^expect(Async)?\s*[.(]", recv):
                    # `expect(x).toRender(html)`: a custom matcher registered with
                    # jasmine.addMatchers / expect.extend -- the project function of that name
                    owners_m = [(f, fn) for f, fns in self.graph["functions"].items() for fn in fns
                                if isinstance(fn, dict) and fn["name"] == func and fn.get("is_test") and fn.get("kind") != "class"]
                    if len({f for f, _ in owners_m}) == 1:
                        cf, cm = owners_m[0]
                        call.update({"resolved_file": cf, "resolved_function": cm, "resolved_class": cm.get("class"), "resolution": "convention"})
                        from_node = {"type": "FUNCTION", "file": file_path, "function": caller if caller != "GLOBAL" else "GLOBAL_SCOPE"}
                        if call.get("caller_class"):
                            from_node["class"] = call["caller_class"]
                        if call.get("call_id"):
                            replaced.add(call["call_id"])
                        self.add_execution_edge(from_node=from_node, to_node={"type": "FUNCTION", "file": cf, "function": func},
                                                edge_type="FUNCTION_CALL", is_test=bool(call.get("is_test")), call_id=call.get("call_id"))
                        self.graph["execution_edges"][-1]["confidence"] = "convention"
                        continue
                if not typed_meta and call.get("implicit"):
                    continue  # an implicit dunder call resolves only through a typed receiver
                if not typed_meta and root[:1].isupper() and root == recv and self.resolve_class_file(file_path, root):
                    # the receiver IS a project class we know, and it has no such method
                    # (defined dynamically, e.g. Object.defineProperties(Chart, {register}));
                    # guessing another class's `register` would be wrong, so stay unresolved
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
                if call.get("call_id"):
                    replaced.add(call["call_id"])
                self.add_execution_edge(
                    from_node=from_node,
                    to_node={"type": "FUNCTION", "file": typed_file, "function": func, "class": typed_meta.get("class") or typed_class},
                    edge_type="FUNCTION_CALL", is_test=is_test, call_id=call.get("call_id"),
                )
                if how == "name-unique":
                    self.graph["execution_edges"][-1]["confidence"] = "name-unique"
        if replaced:
            # drop the edges those calls had before (import-resolved to a file without the
            # function): one call, one edge
            self.graph["execution_edges"] = [e for i, e in enumerate(edges)
                                             if i >= first_new_edge or e.get("call_id") not in replaced]

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
        # incremental update: the callers of this file's values live in files that are not
        # in this batch -- their recorded calls count too
        for calls in self.graph.get("calls", {}).values():
            for c in calls:
                if not c.get("receiver") and c.get("function"):
                    called.add(c["function"])
        for sm in semantic_matches:
            if sm.match_type != "VARIABLE_ASSIGNMENT" or sm.owner_function or sm.get("assign.class"):
                continue
            name = sm.get("assign.variable")
            if not name or not re.match(r"^[A-Za-z_]\w*$", name):
                continue
            if self.function_index.resolve_function(sm.file_path, name):
                continue
            # a called module-level value is a function (kind="value"); any other module-level
            # assignment is a constant node (a regex, a setting, a table): a change to it has
            # a blast radius too -- the functions that READ it (see link_constant_uses)
            kind = "value" if name in called else "constant"
            if kind == "constant" and (not sm.file_path.endswith(".py") or name.startswith("__")):
                continue
            self.ensure_file("functions", sm.file_path)
            metadata = {
                "name": name,
                "file": sm.file_path,
                "start_line": sm.start_point[0] + 1,
                "end_line": sm.end_point[0] + 1,
                "kind": kind,
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
        if sm.get("function.fixture"):
            metadata["fixture"] = sm.get("function.fixture")  # True, or the injected name
        if sm.get("function.parent"):
            metadata["parent"] = sm.get("function.parent")  # enclosing def of a nested def
            self.symbol_table.register_scope_parent(sm.file_path, function_name, sm.get("function.parent"))
        if sm.get("function.return_type"):
            metadata["return_type"] = sm.get("function.return_type")  # annotation or docstring
        if getattr(sm, "is_test", False) or sm.get("function.is_test"):
            metadata["is_test"] = True  # test dir, or a JUnit @Test
        if sm.get("function.annotations"):
            metadata["annotations"] = dict(sm.get("function.annotations"))
            self._java_route_from_annotations(sm, function_name, owner_class, metadata["annotations"])

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

    def handle_class_def(self, sm):
        """JS/TS `class X [extends Y]`: a class node (kind="class") so `new X()` resolves to
        it, plus the classes registry entry (superclass for `super` and inheritance)."""
        name = sm.get("class.name")
        if not name:
            return
        entry = self.graph["classes"].setdefault(sm.file_path, {}).setdefault(name, {"superclass": None})
        sup = sm.get("class.superclass")
        if sup and not entry.get("superclass"):
            entry["superclass"] = sup
        if sm.get("class.interfaces"):
            entry["interfaces"] = list(sm.get("class.interfaces"))
        if sm.get("class.interface"):
            entry["interface"] = True
        if sm.get("class.annotations"):
            entry["annotations"] = dict(sm.get("class.annotations"))
        if not self.function_index.resolve_function(sm.file_path, name):
            self.ensure_file("functions", sm.file_path)
            metadata = {"name": name, "file": sm.file_path, "start_line": sm.start_point[0] + 1,
                        "end_line": sm.end_point[0] + 1, "kind": "class"}
            if getattr(sm, "is_test", False):
                metadata["is_test"] = True
            self.function_index.register_function(file_path=sm.file_path, function_name=name, metadata=metadata)
            self.graph["functions"][sm.file_path].append(dict(metadata))

    def _constructor_edge(self, from_node, resolved_file, resolved_function, is_test, call_id):
        """A call that resolves to a class node is a call of its constructor: add the edge to
        `X.__init__` / `X.constructor` (walking superclasses) so a change to a constructor
        reaches every instantiation. Flagged via="constructor"."""
        if not isinstance(resolved_function, dict) or resolved_function.get("kind") != "class":
            return
        cls = resolved_function.get("name")
        for ctor in ("__init__", "constructor"):
            cf, cm = self.resolve_method(resolved_file, cls, ctor)
            if cm:
                self.add_execution_edge(from_node=dict(from_node),
                                        to_node={"type": "FUNCTION", "file": cf, "function": ctor, "class": cm.get("class") or cls},
                                        edge_type="FUNCTION_CALL", is_test=is_test, call_id=call_id)
                self.graph["execution_edges"][-1]["via"] = "constructor"
                return

    _DISPATCH_TABLE_RE = re.compile(r"^\s*(?:self\.|this\.|cls\.)?([A-Za-z_$][\w$]*)\s*(?:\[|\.get\s*\()")
    _GETATTR_RE = re.compile(r"^\s*getattr\s*\(\s*([A-Za-z_][\w.]*)\s*,\s*(?:f?[\"']([A-Za-z_][\w]*?)(?:\{|[\"']\s*\+))")

    def handle_dispatch_call(self, sm):
        """A call whose callee is computed: `_ops[op](...)`, `handlers.get(k)(...)`,
        `getattr(self, "visit_" + name)(...)`. Recorded now (with the callee text); the
        targets are linked in resolve_dispatch_calls once every definition is known."""
        expr = (sm.get("call.dispatch") or "").strip()
        m = self._GETATTR_RE.match(expr)
        kind = table = prefix = recv = None
        if m:
            kind, recv, prefix = "dynamic", m.group(1), m.group(2)
        else:
            m2 = self._DISPATCH_TABLE_RE.match(expr)
            if m2:
                kind, table = "dispatch", m2.group(1)
                recv = expr.split(table)[0].strip().rstrip(".") or None
        if not kind:
            return
        self.ensure_file("calls", sm.file_path)
        self.graph["calls"][sm.file_path].append({
            "call_id": self.build_call_id(sm), "object": None, "receiver": recv,
            "function": table or f"getattr:{prefix}*", "resolved_file": None, "resolved_function": None,
            "caller_function": sm.owner_function, "caller_class": getattr(sm, "owner_class", None),
            "is_test": bool(getattr(sm, "is_test", False)),
            "dispatch": {"kind": kind, "table": table, "prefix": prefix, "expr": expr[:120]},
        })

    _PROTO = (("call.proto_iter", "__iter__"), ("call.proto_getitem", "__getitem__"), ("call.proto_enter", "__enter__"),
              ("call.proto_len", "__len__"))

    def handle_call(self, sm):
        if sm.get("call.dispatch") and not sm.get("call.func_name"):
            return self.handle_dispatch_call(sm)
        for key, dunder in self._PROTO:
            if sm.get(key) is not None:
                recv = (sm.get(key) or "").strip()
                if key == "call.proto_enter" and " as " in recv:
                    recv = recv.split(" as ", 1)[0].strip()
                # only receivers we could ever type: a name, self.field, or an instantiation
                if not re.match(r"^(?:[A-Za-z_][\w.]*|[A-Za-z_][\w.]*\([^()]*\))$", recv):
                    return
                sm.captures["call.obj_name"] = recv
                sm.captures["call.func_name"] = dunder
                sm.captures["call.implicit"] = dunder
                break
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
        ) or sm.get("call.new_class")
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
                    "caller_class": getattr(sm, "owner_class", None), "is_test": bool(getattr(sm, "is_test", False)),
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
        elif not raw_object_name and sm.file_path.endswith(".java") and getattr(sm, "owner_class", None) \
                and not self.symbol_table.resolve_import(sm.file_path, func):
            # Java implicit `this`: a bare `getPets()` inside class Owner is `this.getPets()`
            # (walking superclasses); a static import of the same name wins
            typed_file, typed_meta = self.resolve_method(sm.file_path, sm.owner_class, func)
            typed_class = sm.owner_class
        elif isinstance(raw_object_name, str) and raw_object_name[:1].isupper() and "." not in raw_object_name \
                and self.resolve_class_file(sm.file_path, raw_object_name):
            # `Lexer.lex(src)`: the receiver is the class -> static method preferred
            typed_file, typed_meta = self.resolve_method(sm.file_path, raw_object_name, func, _want_static=True)
            typed_class = raw_object_name
        elif isinstance(raw_object_name, str) and "(" in raw_object_name:
            # `requests.Request('GET', url).prepare()` / `new Lexer(opts).lex()`: the receiver
            # is an instantiation expression -> a method of that class
            from semantic_core.symbol_resolver import SymbolResolver
            inst = SymbolResolver.extract_instantiated_class(raw_object_name)
            if inst and self.resolve_class_file(sm.file_path, inst):
                typed_file, typed_meta = self.resolve_method(sm.file_path, inst, func)
                typed_class = inst
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
                "caller_class": getattr(sm, "owner_class", None),
                "is_test": bool(getattr(sm, "is_test", False)),
            })
            self.add_execution_edge(
                from_node=self._from_node(sm),
                to_node={"type": "FUNCTION", "file": typed_file, "function": func,
                         "class": typed_meta.get("class") or typed_class},
                edge_type="FUNCTION_CALL",
                is_test=getattr(sm, "is_test", False),
                call_id=call_id,
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
        # FALLBACK 2b — `from x import *`
        # ==============================================
        if not resolved_function and not obj:
            for src in self.symbol_table.star_imports.get(sm.file_path, []):
                f2, m2, orig = self.resolve_through_reexports(src, func)
                if m2:
                    resolved_file, resolved_function, target_name = f2, m2, orig
                    break

        # ==============================================
        # FALLBACK 3 — LOCAL DEFINITION
        # ==============================================
        if not resolved_function and not obj and not self._is_parameter(sm.file_path, sm.owner_function, func):
            # nearest module-level definition before the call site: a bundle defines
            # `edit$1` twice and last-wins picked the wrong one (JS precision audit).
            # Not when the name is a PARAMETER of the calling function: `make_app(...)`
            # inside a fixture that takes `make_app` calls whatever was injected, not the
            # same-named fixture function in this file.
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
            **({"implicit": sm.get("call.implicit")} if sm.get("call.implicit") else {}),
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
            _cid = self.graph["calls"][sm.file_path][-1].get("call_id")
            self.add_execution_edge(
                from_node=self._from_node(sm),
                to_node=to_node,
                edge_type="FUNCTION_CALL",
                is_test=getattr(sm, "is_test", False),
                call_id=_cid,
            )
            self._constructor_edge(self._from_node(sm), resolved_file, resolved_function,
                                   bool(getattr(sm, "is_test", False)), _cid)

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
                entry = self.graph["classes"].setdefault(sm.file_path, {}).setdefault(name, {"superclass": None})
                sup = sm.get("contract.superclass")
                if sup and not entry.get("superclass") and sup.strip() not in ("object", "metaclass"):
                    # `class IndexVariable(Variable): pass` -- no methods, so handle_function_def
                    # never records the base; method lookups must still walk to Variable
                    entry["superclass"] = sup.strip().split("=")[-1].split(".")[-1].split("[")[0]
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
        call_id=None,
    ):
        edge = {
            "from": from_node,
            "to": to_node,
            "type": edge_type
        }
        if call_id:
            # the call this edge came from: a later pass that re-resolves the call replaces
            # the edge instead of adding a second, contradictory one
            edge["call_id"] = call_id
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
                "class": getattr(sm, "owner_class", None),

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
                "class": getattr(sm, "owner_class", None),

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
        if sm.get("assign.class") and variable and not sm.owner_function:
            # class attribute: keep the raw value so `self.ATTR(...)` and subclass overrides
            # (`CHECKER_CLASS = VariablesChecker`) can be resolved later
            entry = self.graph["classes"].setdefault(sm.file_path, {}).setdefault(sm.get("assign.class"), {"superclass": None})
            entry.setdefault("attrs", {})[variable] = (value or "").strip()
            if sm.get("field.type"):
                # Java `private final OwnerRepository owners;` -> `this.owners.x()` is typed
                entry.setdefault("fields", {})[variable] = sm.get("field.type")
        
        class_name = sm.get("assign.type") or sm.get("assign.value_type") or sm.get("field.type")
        if class_name == "var":
            class_name = None  # Java `var x = new Owner()`: the value decides
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



