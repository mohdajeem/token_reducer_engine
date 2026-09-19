"""
Graph-quality metrics for JavaScript repositories.

Builds the semantic graph for each repo path given and prints the numbers that decide
whether the graph is useful to an editing agent: how many calls resolve to a target
function, split by receiver (`this.x()`, `obj.x()`, bare `x()`), prototype-definition
coverage, object-literal noise in the function index, DB/route false positives, and
name-collision counts.

    python -m tests.js_graph_metrics <repo_path> [<repo_path> ...] [--json out.json]

Run before and after a graph change; the diff is the evidence.
"""
import collections
import json
import os
import re
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_PROTO_RE = re.compile(r"^\s*[A-Za-z_$][\w$]*\.prototype\.([\w$]+)\s*=\s*(?:function\b|\(?[\w$, ]*\)?\s*=>)", re.M)
_SRC_EXTS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _iter_source(repo: Path):
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build", ".semantic_cache", "coverage"}]
        for f in files:
            if f.endswith(_SRC_EXTS) and not f.endswith(".d.ts"):
                yield Path(root, f)


def measure(repo_path: str) -> dict:
    from build_graph import build_graph
    repo = Path(repo_path)
    t0 = time.time()
    g = build_graph(str(repo))
    secs = time.time() - t0

    fns = g.get("functions", {})
    is_test = lambda p: any(part in {"test", "tests", "__tests__", "spec"} for part in p.split("/")[:-1]) or ".test." in p or ".spec." in p
    # production code only: test files call expect()/describe()/it() thousands of times and
    # those never resolve, so including them makes the ratio incomparable across runs
    calls = [c for f, v in g.get("calls", {}).items() if not is_test(f) for c in v]
    edges = g.get("execution_edges", [])

    # receivers that are never project code: JS/DOM builtins and canvas/console handles
    BUILTIN = {"Math", "Object", "Array", "JSON", "Date", "Number", "String", "Boolean", "Promise", "Symbol",
               "Reflect", "Map", "Set", "WeakMap", "WeakSet", "console", "window", "document", "globalThis",
               "process", "Buffer", "Error", "RegExp", "Intl", "ctx", "context", "canvas", "navigator",
               "localStorage", "performance", "requestAnimationFrame", "setTimeout", "Function", "Proxy",
               "ArrayBuffer", "Uint8Array", "Float32Array", "Float64Array", "Int32Array", "Uint32Array",
               "TextEncoder", "TextDecoder", "URL", "fs", "path", "gl", "self", "location", "history", "atob", "btoa"}
    # methods of String/Array/Object/Map/Promise/DOM: calls to these on an untyped receiver
    # are not project code either (`src.match()`, `tokens.push()`, `el.addEventListener()`)
    BUILTIN_METHODS = {"push", "pop", "shift", "unshift", "slice", "splice", "map", "forEach", "filter", "reduce",
                       "reduceRight", "find", "findIndex", "some", "every", "indexOf", "lastIndexOf", "includes",
                       "join", "split", "replace", "replaceAll", "match", "matchAll", "test", "exec", "trim",
                       "trimStart", "trimEnd", "toLowerCase", "toUpperCase", "charAt", "charCodeAt", "codePointAt",
                       "substring", "substr", "startsWith", "endsWith", "padStart", "padEnd", "repeat", "concat",
                       "sort", "reverse", "flat", "flatMap", "fill", "keys", "values", "entries", "hasOwnProperty",
                       "toString", "toFixed", "valueOf", "apply", "call", "bind", "then", "catch", "finally",
                       "get", "set", "has", "delete", "add", "clear", "size", "at", "from", "of", "assign",
                       "freeze", "create", "defineProperty", "getOwnPropertyNames", "isArray", "parse",
                       "stringify", "addEventListener", "removeEventListener", "dispatchEvent", "querySelector",
                       "querySelectorAll", "getAttribute", "setAttribute", "appendChild", "removeChild",
                       "createElement", "getBoundingClientRect", "preventDefault", "stopPropagation", "focus",
                       "blur", "getContext", "toDataURL", "log", "warn", "error", "info", "debug", "next", "done",
                       "resolve", "reject", "all", "race", "now", "getTime", "abs", "min", "max", "floor", "ceil",
                       "round", "sqrt", "pow", "random", "sin", "cos", "tan", "atan2", "PI", "length", "localeCompare"}
    by_recv = collections.Counter()
    res_recv = collections.Counter()
    how = collections.Counter()
    obj_project = obj_project_res = 0
    for c in calls:
        o = c.get("receiver", c.get("object"))
        k = "this" if o in ("this", "super") else ("bare" if not o else "obj")
        by_recv[k] += 1
        resolved = bool(c.get("resolved_function"))
        if k == "obj" and o.split(".")[0] not in BUILTIN and o.split("[")[0] not in BUILTIN and c.get("function") not in BUILTIN_METHODS and not c.get("external"):
            obj_project += 1
            obj_project_res += int(resolved)
        if resolved:
            res_recv[k] += 1
            if k == "obj":
                how[c.get("resolution") or "import"] += 1

    names = collections.Counter(fn["name"] for f, v in fns.items() if not is_test(f) for fn in v if fn.get("name"))
    src_files = [p for p in _iter_source(repo)]
    src_rel = [p.relative_to(repo).as_posix() for p in src_files]
    non_test_src = [p for p in src_rel if not is_test(p)]
    files_with_fns = {f for f in fns if fns[f]}

    proto_defs = 0
    proto_hit = 0
    qualified = {fn.get("class") + "." + fn["name"] for v in fns.values() for fn in v if fn.get("class") and fn.get("name")}
    for p in src_files:
        rel = p.relative_to(repo).as_posix()
        if is_test(rel):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in _PROTO_RE.finditer(txt):
            proto_defs += 1
            if any(fn["name"] == m.group(1) for fn in fns.get(rel, [])):
                proto_hit += 1

    etypes = collections.Counter(e.get("type") for e in edges)
    with_class = sum(1 for v in fns.values() for fn in v if fn.get("class"))
    test_fns = sum(len(v) for f, v in fns.items() if is_test(f))
    literals = g.get("literals", {})

    return {
        "repo": repo.name,
        "build_secs": round(secs, 1),
        "graph_kb": len(json.dumps(g)) // 1024,
        "src_files_non_test": len(non_test_src),
        "src_files_with_functions": len([f for f in files_with_fns if not is_test(f)]),
        "functions": sum(len(v) for f, v in fns.items() if not is_test(f)),
        "functions_with_class": with_class,
        "test_functions_indexed": test_fns,
        "unique_names": len(names),
        "dup_names": sum(1 for n, c in names.items() if c > 1),
        "calls": len(calls),
        "calls_resolved_pct": round(100 * sum(res_recv.values()) / max(1, len(calls)), 1),
        "this_resolved": f"{res_recv['this']}/{by_recv['this']}",
        "obj_resolved": f"{res_recv['obj']}/{by_recv['obj']}",
        "obj_resolved_by": dict(how),
        "obj_external_calls": sum(1 for c in calls if c.get("external")),
        "obj_project_resolved": f"{obj_project_res}/{obj_project}",
        "obj_project_resolved_pct": round(100 * obj_project_res / max(1, obj_project), 1),
        "bare_resolved": f"{res_recv['bare']}/{by_recv['bare']}",
        "proto_defs_in_src": proto_defs,
        "proto_defs_in_graph": proto_hit,
        "exec_edges": len(edges),
        "edge_types": dict(etypes),
        "db_access_edges": etypes.get("DB_ACCESS", 0),
        "literal_files": len(literals),
        "literals": sum(len(v) for v in literals.values()),
    }


def main(argv):
    out = None
    paths = []
    i = 0
    while i < len(argv):
        if argv[i] == "--json":
            out = argv[i + 1]; i += 2
        else:
            paths.append(argv[i]); i += 1
    results = [measure(p) for p in paths]
    for r in results:
        print(json.dumps(r, indent=1))
    if out:
        Path(out).write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
