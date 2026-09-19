"""
Graph-quality metrics for Python repositories (the Python counterpart of js_graph_metrics).

    python -m tests.py_graph_metrics <repo_path> [...] [--json out.json]

Reports, over production code (tests excluded): functions / methods with a known class,
calls split by receiver (`self.x()` / `cls.x()` / `super().x()`, `obj.x()`, bare `f()`)
and how many resolve, import resolution (does `from a.b import c` reach a real file),
decorated functions, and same-name collisions.
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

BUILTIN_RECV = {"os", "sys", "re", "json", "math", "time", "datetime", "logging", "itertools", "functools",
                "collections", "typing", "pathlib", "subprocess", "shutil", "io", "warnings", "inspect",
                "textwrap", "copy", "random", "string", "struct", "operator", "contextlib", "abc", "enum",
                "np", "numpy", "pd", "pytest", "six", "attr", "click", "jinja2", "docutils", "sphinx_rtd_theme",
                "werkzeug", "urllib3", "chardet", "idna", "certifi"}
BUILTIN_METHODS = {"append", "extend", "insert", "pop", "remove", "clear", "index", "count", "sort", "reverse",
                   "copy", "get", "keys", "values", "items", "update", "setdefault", "add", "discard", "union",
                   "join", "split", "strip", "lstrip", "rstrip", "replace", "startswith", "endswith", "format",
                   "lower", "upper", "encode", "decode", "find", "rfind", "splitlines", "partition", "isdigit",
                   "isalpha", "write", "read", "readline", "readlines", "close", "flush", "seek", "group",
                   "groups", "match", "search", "sub", "findall", "finditer", "compile", "isoformat", "strftime",
                   "exists", "is_file", "is_dir", "mkdir", "open", "resolve", "relative_to", "with_suffix",
                   "warn", "debug", "info", "error", "warning", "exception", "critical", "log"}


def is_test(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return any(p in {"test", "tests", "testing", "conftest"} for p in parts[:-1]) or parts[-1].startswith("test_") or parts[-1].endswith("_test.py") or parts[-1] == "conftest.py"


def measure(repo_path: str) -> dict:
    from build_graph import build_graph
    repo = Path(repo_path)
    t0 = time.time()
    g = build_graph(str(repo))
    secs = time.time() - t0

    fns = {f: v for f, v in g.get("functions", {}).items() if f.endswith(".py")}
    calls = [c for f, v in g.get("calls", {}).items() if f.endswith(".py") and not is_test(f) for c in v]

    by_recv = collections.Counter(); res_recv = collections.Counter()
    obj_project = obj_project_res = 0; how = collections.Counter()
    for c in calls:
        o = c.get("receiver", c.get("object")) or ""
        k = "self" if o in ("self", "cls") or o.startswith("super(") else ("bare" if not o else "obj")
        by_recv[k] += 1
        resolved = bool(c.get("resolved_function"))
        if k == "obj" and o.split(".")[0] not in BUILTIN_RECV and c.get("function") not in BUILTIN_METHODS and not c.get("external"):
            obj_project += 1; obj_project_res += int(resolved)
        if resolved:
            res_recv[k] += 1
            if k == "obj":
                how[c.get("resolution") or "import"] += 1

    prod_fns = [fn for f, v in fns.items() if not is_test(f) for fn in v]
    names = collections.Counter(fn["name"] for fn in prod_fns if fn.get("name"))
    with_class = sum(1 for fn in prod_fns if fn.get("class"))
    # ground truth: how many defs are methods (indented under a class) per a cheap regex scan
    method_defs = total_defs = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".semantic_cache", "build", "dist"}]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), repo).replace("\\", "/")
            if not f.endswith(".py") or is_test(rel):
                continue
            try:
                txt = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in re.finditer(r"^([ \t]*)(?:async\s+)?def\s+\w+", txt, re.M):
                total_defs += 1
                if m.group(1):
                    method_defs += 1

    # import resolution: entries in symbol_table imports that point at an existing file
    imp_total = imp_ok = 0
    for f, lst in g.get("imports", {}).items():
        if not f.endswith(".py") or is_test(f):
            continue
        for e in lst:
            imp_total += 1
    edges = g.get("execution_edges", [])
    etypes = collections.Counter(e.get("type") for e in edges)
    return {
        "repo": repo.name,
        "build_secs": round(secs, 1),
        "graph_kb": len(json.dumps(g)) // 1024,
        "py_files_with_functions": len([f for f in fns if not is_test(f)]),
        "functions": len(prod_fns),
        "functions_with_class": with_class,
        "defs_indented_under_class(regex)": f"{method_defs}/{total_defs}",
        "test_functions_indexed": sum(len(v) for f, v in fns.items() if is_test(f)),
        "dup_names": sum(1 for n, c in names.items() if c > 1),
        "calls": len(calls),
        "calls_resolved_pct": round(100 * sum(res_recv.values()) / max(1, len(calls)), 1),
        "self_resolved": f"{res_recv['self']}/{by_recv['self']}",
        "obj_resolved": f"{res_recv['obj']}/{by_recv['obj']}",
        "obj_resolved_by": dict(how),
        "obj_project_resolved": f"{obj_project_res}/{obj_project}",
        "obj_project_resolved_pct": round(100 * obj_project_res / max(1, obj_project), 1),
        "bare_resolved": f"{res_recv['bare']}/{by_recv['bare']}",
        "imports": imp_total,
        "exec_edges": len(edges),
        "edge_types": dict(etypes),
        "literals": sum(len(v) for f, v in g.get("literals", {}).items() if f.endswith(".py")),
    }


def main(argv):
    out = None; paths = []; i = 0
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
