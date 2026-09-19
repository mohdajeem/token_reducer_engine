"""
Type-checker sidecar: resolves the calls the builder could not, using a real analyzer.

  Python      jedi  (pip install jedi)            -- inference over untyped code, stubs for stdlib
  JavaScript  the TypeScript compiler in checkJs  -- needs node + a `typescript` package;
              mode via tests/ts_resolve_oracle.js    set TS_MODULE to its node_modules path if not
                                                     resolvable from the repo

Opt-in: SEMANTIC_TYPE_SIDECAR=1 (or =py / =js). Off by default because it costs seconds to
minutes per repo (jedi is ~10-50 ms per call site). Only calls that are still unresolved,
not external, not builtin-method names are sent; results are written back as
resolution="sidecar" and edges get confidence="sidecar". The builder's own resolutions are
never overwritten -- the audit shows them at 97-100% precision.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")


def enabled(ext: str) -> bool:
    mode = os.environ.get("SEMANTIC_TYPE_SIDECAR", "").strip().lower()
    if mode in ("", "0", "false", "no", "off"):
        return False
    if mode in ("1", "true", "yes", "all", "on"):
        return True
    return (ext == ".py" and mode == "py") or (ext != ".py" and mode == "js")


def _pending(builder, lang_exts, is_test_path):
    """(file, call) pairs worth asking the analyzer about."""
    bm = builder.builtin_method_names()
    out = []
    for f, calls in builder.graph.get("calls", {}).items():
        if not f.endswith(lang_exts) or is_test_path(f):
            continue
        for c in calls:
            if c.get("resolved_function") or c.get("external"):
                continue
            recv = c.get("receiver")
            if not recv or not c.get("call_id") or c.get("function") in bm:
                continue
            if recv in ("this", "self", "cls", "super") or "(" in recv or "[" in recv:
                continue
            out.append((f, c))
    return out


def _by_span(builder):
    """(file, start_line) -> function metadata, to map an analyzer's declaration line back to a node."""
    idx = {}
    for f, fns in builder.graph.get("functions", {}).items():
        for fn in fns:
            if isinstance(fn, dict) and fn.get("start_line"):
                idx.setdefault((f, fn["start_line"]), fn)
    return idx


def _accept(builder, file_path, call, target_file, target_line, span_idx):
    meta = span_idx.get((target_file, target_line))
    if meta is None:
        # the analyzer may point at a decorator / docstring line; look a few lines around
        for d in (1, 2, -1, 3, -2):
            meta = span_idx.get((target_file, target_line + d))
            if meta is not None:
                break
    if meta is None or meta.get("name") != call.get("function"):
        return False
    call.update({"resolved_file": target_file, "resolved_function": meta,
                 "resolved_class": meta.get("class"), "resolution": "sidecar"})
    from_node = {"type": "FUNCTION", "file": file_path,
                 "function": call.get("caller_function") or "GLOBAL_SCOPE"}
    if call.get("caller_class"):
        from_node["class"] = call["caller_class"]
    to_node = {"type": "FUNCTION", "file": target_file, "function": meta["name"]}
    if meta.get("class"):
        to_node["class"] = meta["class"]
    builder.add_execution_edge(from_node=from_node, to_node=to_node, edge_type="FUNCTION_CALL",
                               is_test=bool(call.get("is_test")))
    builder.graph["execution_edges"][-1]["confidence"] = "sidecar"
    return True


def run_python(builder, repo_root: str, is_test_path) -> dict:
    try:
        import jedi
    except ImportError:
        return {"skipped": "jedi not installed"}
    pending = _pending(builder, (".py",), is_test_path)
    if not pending:
        return {"pending": 0}
    span_idx = _by_span(builder)
    root = Path(repo_root)
    project = jedi.Project(path=str(root), added_sys_path=[str(root / "src")] if (root / "src").is_dir() else [])
    filled = 0
    cache = {}
    for f, c in pending:
        try:
            start = int(c["call_id"].split(":")[-2])
        except Exception:
            continue
        src = cache.get(f)
        if src is None:
            try:
                src = (root / f).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            cache[f] = src
        head = src[:start]
        line = head.count("\n") + 1
        col = len(head.split("\n")[-1])
        callee = src[start:start + 200].split("(")[0]
        off = callee.rfind(c["function"])
        if off < 0:
            continue
        try:
            defs = jedi.Script(code=src, path=str(root / f), project=project).goto(line, col + off + 1, follow_imports=True)
        except Exception:
            continue
        for d in defs:
            if not d.module_path:
                continue
            try:
                rel = os.path.relpath(str(d.module_path), root).replace("\\", "/")
            except ValueError:
                continue
            if rel.startswith(".."):
                continue  # stdlib / site-packages
            if _accept(builder, f, c, rel, d.line, span_idx):
                filled += 1
                break
    return {"pending": len(pending), "filled": filled}


def run_javascript(builder, repo_root: str, is_test_path) -> dict:
    pending = _pending(builder, (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"), is_test_path)
    if not pending:
        return {"pending": 0}
    oracle = Path(__file__).resolve().parents[1] / "tests" / "ts_resolve_oracle.js"
    if not oracle.exists():
        return {"skipped": "ts_resolve_oracle.js missing"}
    reqs = []
    for f, c in pending:
        try:
            reqs.append({"file": f, "offset": int(c["call_id"].split(":")[-2]), "name": c["function"]})
        except Exception:
            pass
    tmp = Path(tempfile.mkdtemp()) / "req.json"
    tmp.write_text(json.dumps(reqs), encoding="utf-8")
    try:
        proc = subprocess.run(["node", str(oracle), str(repo_root), str(tmp)], capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"skipped": f"node unavailable: {e}"}
    if proc.returncode != 0:
        return {"skipped": f"oracle failed: {proc.stderr[-300:]}"}
    results = {(r["file"], r["offset"]): r for r in json.loads(proc.stdout or "[]")}
    span_idx = _by_span(builder)
    filled = 0
    for (f, c), req in zip(pending, reqs):
        r = results.get((f, req["offset"]))
        for d in (r or {}).get("decls", []):
            if d["file"].startswith("..") or "node_modules" in d["file"]:
                continue
            if _accept(builder, f, c, d["file"], d["line"], span_idx):
                filled += 1
                break
    return {"pending": len(pending), "filled": filled}
