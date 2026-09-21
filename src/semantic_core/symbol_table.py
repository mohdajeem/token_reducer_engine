import os

_DIR_CACHE = {}


def isfile_exact(path):
    """os.path.isfile with a case-exact basename check. Windows and macOS file systems are
    case-insensitive, so `from astropy.table import Table` made the candidate
    astropy/table/Table.py "exist" (it matched table.py) and the import resolved to a file
    that has no functions -- every Table(...) call in the tests was lost. The directory
    listing is cached per directory and refreshed when its mtime changes."""
    if not os.path.isfile(path):
        return False
    d, base = os.path.split(path)
    d = d or "."
    try:
        mtime = os.stat(d).st_mtime_ns
    except OSError:
        return False
    cached = _DIR_CACHE.get(d)
    if cached is None or cached[0] != mtime:
        try:
            cached = (mtime, frozenset(os.listdir(d)))
        except OSError:
            return False
        _DIR_CACHE[d] = cached
    return base in cached[1]


class SymbolTable:

    def __init__(self):

        self.imports = {}
        self.aliases = {}
        self.destructured = {}
        self.types = {}
        # file -> {local name -> exported name}: `import { helper as h }` records h -> helper,
        # so a call to h() can be looked up under the name the source module exports.
        self.imported_names = {}
        # file -> [resolved source files] for `from x import *`
        self.star_imports = {}
        # file -> {scope: enclosing scope}: a closure sees the variables of the function it
        # is defined in (`let injector: Injector` in a describe() callback, used inside it())
        self.scope_parents = {}


    @property
    def registry(self):
        """Compatibility property for tests."""
        return self.imports

    _JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")

    def resolve_module_path(self, file_path, import_source):
        """
        Project-relative path of the module `import_source` refers to, as seen from
        file_path. Handles what Node/bundlers handle: an explicit extension, every JS/TS
        extension, and directory imports via index.* -- `import { x } from '../core'`
        resolves to ../core/index.js, which the previous ".js"-append logic turned into
        the nonexistent ../core.js (every barrel import in Chart.js failed that way).
        Returns None for bare package imports ('lodash') and unresolvable paths.
        """
        if not import_source or not import_source.startswith((".", "/")):
            return None
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        project_root = getattr(self, "project_root", None)
        base_dir = os.path.dirname(file_path if os.path.isabs(file_path) or not project_root else os.path.join(project_root, file_path))
        target = os.path.normpath(os.path.join(base_dir, import_source)).replace("\\", "/")
        candidates = []
        stem, ext0 = os.path.splitext(target)
        if ext0 in self._JS_EXTS:
            candidates.append(target)
            # TS under NodeNext/ESM imports the EMITTED name: `from './container.js'` while
            # the source is container.ts (every import in nestjs/nest); .mjs/.cjs -> .mts/.cts
            swap = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}.get(ext0, ())
            candidates += [stem + e for e in swap]
        candidates += [target + ext for ext in self._JS_EXTS]
        candidates += [os.path.join(target, "index" + ext).replace("\\", "/") for ext in self._JS_EXTS]
        for cand in candidates:
            if isfile_exact(cand):
                out = cand
                break
        else:
            # nothing on disk (e.g. tests run without a checkout): keep the historical guess
            out = target if os.path.splitext(target)[1] in self._JS_EXTS else target + (".ts" if file_path.endswith((".ts", ".tsx")) else ".js")
        if project_root and os.path.isabs(out):
            out = os.path.relpath(out, project_root).replace("\\", "/")
        return out

    def forget_file(self, file_path):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        for table in (self.imports, self.aliases, self.destructured, self.types, self.imported_names, self.star_imports,
                      self.scope_parents):
            table.pop(file_path, None)

    def to_state(self):
        return {"imports": self.imports, "aliases": self.aliases, "destructured": self.destructured,
                "types": self.types, "imported_names": self.imported_names, "star_imports": self.star_imports,
                "scope_parents": self.scope_parents}

    def load_state(self, state):
        for key in ("imports", "aliases", "destructured", "types", "imported_names", "star_imports", "scope_parents"):
            setattr(self, key, dict(state.get(key) or {}))

    def register_scope_parent(self, file_path, scope_id, parent_scope):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        if scope_id and parent_scope and scope_id != parent_scope:
            self.scope_parents.setdefault(file_path, {})[scope_id] = parent_scope

    def register_star_import(self, file_path, import_source):
        """`from x import *` -> remember x's file so bare names can be looked up there."""
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        if not file_path.endswith(".py"):
            return None
        resolved = self.resolve_python_module(file_path, import_source)
        if resolved:
            lst = self.star_imports.setdefault(file_path, [])
            if resolved not in lst:
                lst.append(resolved)
        return resolved

    _PY_ROOTS_CACHE = {}

    def _python_search_roots(self, abs_file):
        """Directories a dotted module path is resolved against: the project root, src/,
        and the directory above the file's top-level package (found by walking up while
        __init__.py exists). Cached per directory."""
        d = os.path.dirname(abs_file)
        if d in self._PY_ROOTS_CACHE:
            return self._PY_ROOTS_CACHE[d]
        roots = []
        project_root = getattr(self, "project_root", None)
        cur = d
        while os.path.isfile(os.path.join(cur, "__init__.py")):
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        roots.append(cur)
        if project_root:
            for r in (project_root, os.path.join(project_root, "src"), os.path.join(project_root, "lib")):
                if os.path.isdir(r) and r not in roots:
                    roots.append(r)
        self._PY_ROOTS_CACHE[d] = roots
        return roots

    def resolve_python_module(self, file_path, import_source, import_name=None):
        """
        Project-relative file for a Python import, or None when it is not project code
        (stdlib, third-party). `from M import N` tries the submodule M/N first, then M.
          from ..util import helper   -> <pkg>/util.py
          from . import parts         -> <dir>/parts.py
          from pkg.core import engine -> pkg/core/engine.py   (N is a submodule)
          from pkg import boot        -> pkg/__init__.py      (N is a symbol; re-exports follow)
        """
        if not import_source:
            return None
        project_root = getattr(self, "project_root", None)
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        abs_file = file_path if os.path.isabs(file_path) or not project_root else os.path.join(project_root, file_path)
        src = import_source.strip()
        if src.startswith("."):
            dots = len(src) - len(src.lstrip("."))
            rest = src[dots:]
            base = os.path.dirname(abs_file)
            for _ in range(dots - 1):
                base = os.path.dirname(base)
            bases = [base]
            parts = [p for p in rest.split(".") if p]
        else:
            bases = self._python_search_roots(abs_file)
            parts = src.split(".")
        candidates = []
        for b in bases:
            if import_name:
                candidates.append(os.path.join(b, *parts, import_name + ".py"))
                candidates.append(os.path.join(b, *parts, import_name, "__init__.py"))
            if parts:
                candidates.append(os.path.join(b, *parts) + ".py")
                candidates.append(os.path.join(b, *parts, "__init__.py"))
        for cand in candidates:
            if isfile_exact(cand):
                out = os.path.normpath(cand).replace("\\", "/")
                if project_root and os.path.isabs(out):
                    out = os.path.relpath(out, project_root).replace("\\", "/")
                return out
        return None

    def resolve_imported_name(self, file_path, local_name):
        """The exported name behind a local import alias (h -> helper), or None."""
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        return self.imported_names.get(file_path, {}).get(local_name)

    # ======================================================
    # REGISTER IMPORT
    # ======================================================

    def register_import(
        self,
        file_path,
        import_name,
        import_source,
        exported_name=None,
    ):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")

        if file_path not in self.imports:

            self.imports[file_path] = {}

        project_root = getattr(self, "project_root", None)
        if project_root and not os.path.isabs(file_path):
            abs_file_path = os.path.normpath(os.path.join(project_root, file_path)).replace("\\", "/")
        else:
            abs_file_path = file_path

        normalized = os.path.normpath(
            os.path.join(
                os.path.dirname(abs_file_path),
                import_source
            )
        ).replace("\\",'/')

        if file_path.endswith(".py"):
            if import_name is None and import_source and not import_source.startswith("."):
                # `import pytest` / `import a.b.c`: the local names are `pytest`, and both
                # `a` (the package) and `a.b.c` (the module, as written at call sites)
                top = import_source.split(".")[0]
                if "." in import_source:
                    top_file = self.resolve_python_module(file_path, top)
                    self.imports[file_path][top] = top_file
                import_name = import_source
            resolved = self.resolve_python_module(file_path, import_source, exported_name)
            if resolved is None:
                # stdlib / third-party: remember nothing resolvable; callers see "external"
                self.imports[file_path][import_name] = None
                if exported_name and exported_name != import_name:
                    self.imported_names.setdefault(file_path, {})[import_name] = exported_name
                return None
            normalized = resolved
        elif file_path.endswith(".java"):
            # Java import: com.example.service.UserService
            import_source_parts = import_source.split(".")
            import_class = import_source_parts[-1]
            if not import_name:
                import_name = import_class
            package_path = "/".join(import_source_parts) + ".java"
            
            curr_dir = os.path.dirname(abs_file_path)
            resolved = None
            for _ in range(10):
                candidate = os.path.normpath(os.path.join(curr_dir, package_path)).replace("\\", "/")
                if isfile_exact(candidate):
                    if project_root:
                        resolved = os.path.relpath(candidate, project_root).replace("\\", "/")
                    else:
                        resolved = candidate
                    break
                parent = os.path.dirname(curr_dir)
                if parent == curr_dir:
                    break
                curr_dir = parent
                
            if resolved:
                normalized = resolved
            else:
                # JDK / Spring / JUnit: no project file. Record None so the graph marks the
                # import (and every call through it) external instead of inventing a
                # `<dir>/Test.java` that does not exist.
                self.imports[file_path][import_name] = None
                return None
        else:
            resolved = self.resolve_module_path(file_path, import_source)
            if resolved is None:
                # bare package import: keep the historical shape in the table so callers
                # see a string, but report None so the graph marks the import external
                self.imports[file_path][import_name] = normalized + (".ts" if file_path.endswith((".ts", ".tsx")) else ".js")
                if exported_name and exported_name != import_name:
                    self.imported_names.setdefault(file_path, {})[import_name] = exported_name
                return None
            normalized = resolved

        if project_root and os.path.isabs(normalized):
            normalized = os.path.relpath(normalized, project_root).replace("\\", "/")

        self.imports[file_path][
            import_name
        ] = normalized
        if exported_name and exported_name != import_name:
            self.imported_names.setdefault(file_path, {})[import_name] = exported_name
        return normalized
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

    # ======================================================
    # REGISTER TYPE MAPPING
    # ======================================================

    def register_type(self, file_path, scope_id, variable_name, type_name):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        if file_path not in self.types:
            self.types[file_path] = {}
        if scope_id not in self.types[file_path]:
            self.types[file_path][scope_id] = {}
        self.types[file_path][scope_id][variable_name] = type_name

    # ======================================================
    # RESOLVE TYPE MAPPING
    # ======================================================

    def resolve_type(self, file_path, scope_id, variable_name):
        file_path = os.path.normpath(str(file_path)).replace("\\", "/")
        if file_path not in self.types:
            return None
        
        # Check in local scope, then the enclosing scopes (a closure sees the variables of
        # the function it is defined in: `let injector: Injector` in a describe() callback,
        # used inside it())
        scopes = self.types[file_path]
        parents = self.scope_parents.get(file_path) or {}
        seen = set()
        while scope_id and scope_id not in seen and len(seen) < 12:
            seen.add(scope_id)
            if scope_id in scopes and variable_name in scopes[scope_id]:
                return scopes[scope_id][variable_name]
            scope_id = parents.get(scope_id)
            
        # Fallback to GLOBAL scope
        if "GLOBAL" in self.types[file_path] and variable_name in self.types[file_path]["GLOBAL"]:
            return self.types[file_path]["GLOBAL"][variable_name]
            
        return None
