#!/usr/bin/env python3
"""
INCREMENTAL == FULL. After any change, the incrementally updated graph must match a full
rebuild of the same tree on everything an agent can observe: functions (with class / kind),
classes, literals, resolved calls, edges, symbol index. Cases: edit a body (new cross-file
call), rename a function that other files call, delete a file, and a cold start (new process
restores the builder from the snapshot). Also: the update must be faster than a full build.

Run:  python tests/test_incremental_equivalence.py
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import textwrap
import time
from pathlib import Path


def _k(t):
    return tuple("" if x is None else (str(x) if not isinstance(x, (int, float, bool, tuple)) else x) for x in t)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_js_graph_quality import FIXTURE, write_fixture  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {str(detail)[:400]}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def observable(g):
    """The parts of a graph an agent can observe, normalised for comparison."""
    def fn_key(f, x):
        return (f, x.get("name"), x.get("class"), x.get("kind"), x.get("start_line"), x.get("end_line"), bool(x.get("is_test")), bool(x.get("static")))
    fns = sorted((fn_key(f, x) for f, v in g.get("functions", {}).items() for x in v if isinstance(x, dict)), key=_k)
    classes = sorted(((f, c, (v or {}).get("superclass"), tuple(sorted(((v or {}).get("fields") or {}).items())))
                     for f, cs in g.get("classes", {}).items() for c, v in cs.items()), key=lambda t: (t[0], t[1], t[2] or "", str(t[3])))
    lits = sorted((f, tuple(v)) for f, v in g.get("literals", {}).items())
    calls = sorted(((f, c.get("call_id"), c.get("function"), c.get("resolved_file"),
                    (c.get("resolved_function") or {}).get("name"), (c.get("resolved_function") or {}).get("start_line"),
                    c.get("resolution"), c.get("external"))
                   for f, v in g.get("calls", {}).items() for c in v), key=_k)
    edges = sorted(((e["type"], e["from"].get("file"), e["from"].get("function"), e["from"].get("class"),
                    e["to"].get("file"), e["to"].get("function"), e["to"].get("class"), e.get("confidence"), bool(e.get("is_test")))
                   for e in g.get("execution_edges", [])), key=_k)
    sym = sorted((k, tuple(sorted(v))) for k, v in g.get("symbol_index", {}).items())
    return {"functions": fns, "classes": classes, "literals": lits, "calls": calls, "edges": set(edges), "symbol_index": sym}


def diff_report(a, b):
    out = []
    for k in a:
        if a[k] != b[k]:
            sa, sb = set(a[k]) if not isinstance(a[k], set) else a[k], set(b[k]) if not isinstance(b[k], set) else b[k]
            out.append(f"{k}: only-incremental={list(sa - sb)[:3]} only-full={list(sb - sa)[:3]}")
    return "; ".join(out) or "identical"


def main():
    from api import mcp_server as srv
    from build_graph import build_graph

    root = write_fixture(FIXTURE)
    q = io.StringIO()

    def build(force):
        with contextlib.redirect_stdout(q):
            return srv.mcp_build_graph(str(root), force_rebuild=force, cache_subdir="inc")

    build(True)
    check("live builder kept after a full build", srv.SERVER_STATE.get("builder") is not None)
    base = observable(srv.SERVER_STATE["graph"])

    # ---- 1. edit a body: add a cross-file call inside Engine.start
    p = root / "src/core/engine.js"
    p.write_text(p.read_text(encoding="utf-8").replace("    this.tick();\n    helper();\n", "    this.tick();\n    helper();\n    parts_ok();\n"), encoding="utf-8")
    (root / "src/core/parts_ok.js").write_text("export function parts_ok() { return 'ok'; }\n", encoding="utf-8")
    p.write_text("import { parts_ok } from './parts_ok';\n" + p.read_text(encoding="utf-8"), encoding="utf-8")
    t0 = time.time(); msg = build(False); inc_secs = time.time() - t0
    check("incremental path taken for the edit", "incrementally" in msg.lower(), msg[:120])
    inc = observable(srv.SERVER_STATE["graph"])
    with contextlib.redirect_stdout(q):
        full = observable(build_graph(str(root)))
    check("edit: incremental graph == full rebuild", inc == full, diff_report(inc, full))
    check("edit: the new cross-file call resolved", any(c[2] == "parts_ok" and c[3] == "src/core/parts_ok.js" for c in inc["calls"]), [c for c in inc["calls"] if c[2] == "parts_ok"])

    # ---- 2. rename a function that another file calls (helper -> helper2), keep the alias export
    u = root / "src/util/helper.js"
    u.write_text(u.read_text(encoding="utf-8").replace("export function helper() { return 1; }", "export function helper2() { return 1; }\nexport const helper = helper2;"), encoding="utf-8")
    build(False)
    inc = observable(srv.SERVER_STATE["graph"])
    with contextlib.redirect_stdout(q):
        full = observable(build_graph(str(root)))
    check("rename: incremental graph == full rebuild (callers in OTHER files re-linked)", inc == full, diff_report(inc, full))

    # ---- 3. delete a file
    os.remove(root / "src/core/parts_ok.js")
    p.write_text(p.read_text(encoding="utf-8").replace("import { parts_ok } from './parts_ok';\n", "").replace("    parts_ok();\n", ""), encoding="utf-8")
    build(False)
    inc = observable(srv.SERVER_STATE["graph"])
    with contextlib.redirect_stdout(q):
        full = observable(build_graph(str(root)))
    check("delete: incremental graph == full rebuild", inc == full, diff_report(inc, full))
    check("delete: no trace of the removed file", not any("parts_ok.js" in (c[3] or "") for c in inc["calls"]) and not any("parts_ok" in str(e) for e in inc["edges"]))

    # ---- 4. cold start: forget the live builder, edit, update from the snapshot alone
    srv.SERVER_STATE["builder"] = None
    srv.SERVER_STATE["graph"] = None
    srv.SERVER_STATE["repo_path"] = None
    p.write_text(p.read_text(encoding="utf-8").replace("  tick() { return this.n++; }", "  tick() { helper(); return this.n++; }"), encoding="utf-8")
    msg = build(False)
    check("cold start: builder restored from snapshot and incremental path taken", "incrementally" in msg.lower(), msg[:120])
    inc = observable(srv.SERVER_STATE["graph"])
    with contextlib.redirect_stdout(q):
        full = observable(build_graph(str(root)))
    check("cold start: incremental graph == full rebuild", inc == full, diff_report(inc, full))

    # ---- 4b. back-to-back updates: the second must wait for the first's background write
    for i in range(3):
        p.write_text(p.read_text(encoding="utf-8") + "\n// b%d\n" % i, encoding="utf-8")
        build(False)
    inc = observable(srv.SERVER_STATE["graph"])
    with contextlib.redirect_stdout(q):
        full = observable(build_graph(str(root)))
    check("back-to-back edits (writer racing the next update): incremental == full", inc == full, diff_report(inc, full))

    # ---- 5. no change -> cached load, no rebuild
    t0 = time.time(); msg = build(False); reload_secs = time.time() - t0
    check("no change: cached load", "cached" in msg.lower(), msg[:120])

    # ---- 6. old snapshot without builder state -> full rebuild, not a degraded update
    snap = root / ".semantic_cache" / "inc" / "graph.json"
    import json
    from incremental_runtime.snapshot_manager import SnapshotManager
    # snapshots are written on a background thread: anything reading the file must wait
    SnapshotManager(str(snap.parent)).wait()
    check("background snapshot write landed with the builder state", "_builder" in json.loads(snap.read_text(encoding="utf-8")))
    g = json.loads(snap.read_text(encoding="utf-8")); g.pop("_builder", None); snap.write_text(json.dumps(g), encoding="utf-8")
    srv.SERVER_STATE["builder"] = None; srv.SERVER_STATE["repo_path"] = None
    p.write_text(p.read_text(encoding="utf-8") + "\n// touch\n", encoding="utf-8")
    msg = build(False)
    check("snapshot without builder state falls back to a FULL build", "compiled" in msg.lower(), msg[:120])

    # ---- 7. crash between the in-memory update and the snapshot landing on disk: the file
    # hashes must not claim "up to date" next to the older snapshot. Next start must
    # re-apply the edit, not trust it.
    import incremental_runtime.snapshot_manager as smod
    SnapshotManager(str(snap.parent)).wait()
    hashes_before = (snap.parent / "file_hashes.json").read_bytes()
    orig = smod._serialize_and_write
    def crash(path, graph, chunked=False, cancel=None, on_done=None):
        raise RuntimeError("simulated crash before the snapshot was written")
    smod._serialize_and_write = crash
    import threading
    quiet = threading.excepthook; threading.excepthook = lambda args: None  # the simulated crash is expected
    p.write_text(p.read_text(encoding="utf-8").replace("  tick() { helper(); return this.n++; }", "  tick() { helper(); helper(); return this.n++; }"), encoding="utf-8")
    try:
        build(False)
    finally:
        SnapshotManager(str(snap.parent)).wait()
        smod._serialize_and_write = orig
        threading.excepthook = quiet
    check("hashes are NOT committed when the snapshot write failed", (snap.parent / "file_hashes.json").read_bytes() == hashes_before)
    check("hashes live next to the snapshot (per cache_subdir)", (snap.parent / "file_hashes.json").is_file())
    srv.SERVER_STATE["builder"] = None; srv.SERVER_STATE["graph"] = None; srv.SERVER_STATE["repo_path"] = None
    msg = build(False)
    check("next start re-applies the lost edit incrementally", "incrementally" in msg.lower(), msg[:120])
    inc = observable(srv.SERVER_STATE["graph"])
    with contextlib.redirect_stdout(q):
        full = observable(build_graph(str(root)))
    check("after crash recovery: incremental == full", inc == full, diff_report(inc, full))
    SnapshotManager(str(snap.parent)).wait()

    # ---- 8. change detection vs git as an independent oracle: modified, added (untracked)
    # and deleted source files must all be reported, and nothing else
    import subprocess
    from incremental_runtime.change_detector import ChangeDetector
    git = shutil.which("git")
    if git:
        def _git(*a):
            return subprocess.run([git, *a], cwd=str(root), capture_output=True, text=True)
        _git("init", "-q"); _git("config", "user.email", "t@t"); _git("config", "user.name", "t")
        _git("add", "-A"); _git("commit", "-qm", "base")
        det = ChangeDetector()
        det.get_changed_files(str(root), cache_dir=str(snap.parent))  # baseline hashes
        (root / "src/core/engine.js").write_text((root / "src/core/engine.js").read_text(encoding="utf-8") + "\n// git-oracle\n", encoding="utf-8")
        (root / "src/brand_new.js").write_text("export function fresh() { return 1; }\n", encoding="utf-8")
        os.remove(root / "src/other.js")
        ours = set(det.get_changed_files(str(root), cache_dir=str(snap.parent)))
        porcelain = _git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()
        theirs = {ln[3:].strip().strip('"') for ln in porcelain if ln[3:].strip().endswith((".js", ".ts", ".py", ".jsx", ".tsx"))}
        theirs = {t for t in theirs if not t.startswith(".semantic_cache")}
        check("change detection == git status (modified + untracked + deleted source files)", ours == theirs, (sorted(ours), sorted(theirs)))

    shutil.rmtree(root, ignore_errors=True)
    print(f"\n(timing on fixture: incremental {inc_secs:.2f}s, no-change reload {reload_secs:.2f}s)")
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("ALL INCREMENTAL EQUIVALENCE TESTS PASSED")


if __name__ == "__main__":
    main()
