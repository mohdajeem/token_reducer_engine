import os
class SymbolTable:

    def __init__(self):

        self.imports = {}
        self.aliases = {}
        self.destructured = {}
        self.types = {}
        # file -> {local name -> exported name}: `import { helper as h }` records h -> helper,
        # so a call to h() can be looked up under the name the source module exports.
        self.imported_names = {}


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
        if os.path.splitext(target)[1] in self._JS_EXTS:
            candidates.append(target)
        candidates += [target + ext for ext in self._JS_EXTS]
        candidates += [os.path.join(target, "index" + ext).replace("\\", "/") for ext in self._JS_EXTS]
        for cand in candidates:
            if os.path.isfile(cand):
                out = cand
                break
        else:
            # nothing on disk (e.g. tests run without a checkout): keep the historical guess
            out = target if os.path.splitext(target)[1] in self._JS_EXTS else target + (".ts" if file_path.endswith((".ts", ".tsx")) else ".js")
        if project_root and os.path.isabs(out):
            out = os.path.relpath(out, project_root).replace("\\", "/")
        return out

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
            if os.path.isfile(cand):
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
                if os.path.exists(candidate):
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
                fallback = os.path.normpath(os.path.join(os.path.dirname(abs_file_path), import_class + ".java")).replace("\\", "/")
                if project_root:
                    normalized = os.path.relpath(fallback, project_root).replace("\\", "/")
                else:
                    normalized = fallback
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
        
        # Check in local scope
        if scope_id in self.types[file_path] and variable_name in self.types[file_path][scope_id]:
            return self.types[file_path][scope_id][variable_name]
            
        # Fallback to GLOBAL scope
        if "GLOBAL" in self.types[file_path] and variable_name in self.types[file_path]["GLOBAL"]:
            return self.types[file_path]["GLOBAL"][variable_name]
            
        return None
