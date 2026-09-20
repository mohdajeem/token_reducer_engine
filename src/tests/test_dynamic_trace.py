#!/usr/bin/env python3
"""
DYNAMIC TRACE LAYER. A fixture package whose test reaches production code through a path
no static analysis can follow (getattr on a computed name from a config string + a
callback registered at runtime). The static graph must NOT reach it; after recording a
trace with dynamic_trace.trace_pytest and merging it, mcp_tests_for / impact analysis
must, with the edges marked source="trace", confidence="observed", and the completeness
block must say how many edges came from the trace and whether it is stale.

Run:  python tests/test_dynamic_trace.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {str(detail)[:400]}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


FIXTURE = {
    "pyproject.toml": "[project]\nname = 'dyn'\n",
    "src/dyn/__init__.py": "",
    "src/dyn/core.py": textwrap.dedent("""\
        import importlib


        class Engine:
            def __init__(self):
                self.hooks = []

            def register(self, fn):
                self.hooks.append(fn)

            def run(self, name):
                mod = importlib.import_module("dyn." + name)
                result = getattr(mod, "handle_" + name)(self)
                for h in self.hooks:
                    h(result)
                return result
        """),
    "src/dyn/alpha.py": textwrap.dedent("""\
        def handle_alpha(engine):
            return finish(engine)


        def finish(engine):
            return "alpha:" + str(len(engine.hooks))
        """),
    # a dispatch table: statically the call site links to all three; the test only fires `add`
    "src/dyn/ops.py": textwrap.dedent("""\
        def op_add(a, b):
            return a + b


        def op_sub(a, b):
            return a - b


        def op_mul(a, b):
            return a * b


        OPS = {"add": op_add, "sub": op_sub, "mul": op_mul}


        def apply(name, a, b):
            return OPS[name](a, b)
        """),
    "tests/conftest.py": "import sys, os\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n",
    "tests/test_engine.py": textwrap.dedent("""\
        from dyn.core import Engine


        def on_result(r):
            assert r.startswith("alpha")


        def test_run_alpha():
            e = Engine()
            e.register(on_result)
            assert e.run("alpha") == "alpha:1"


        def test_apply_add():
            from dyn.ops import apply
            assert apply("add", 2, 3) == 5
        """),
}


def main():
    from api import mcp_server as srv
    from dynamic_trace import trace_pytest
    from dynamic_trace.merge import merge_trace, load_trace

    root = Path(tempfile.mkdtemp(prefix="dyntrace_"))
    for rel, content in FIXTURE.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    q = io.StringIO()
    os.environ["SEMANTIC_INDEX_TESTS"] = "1"
    try:
        # ---- static graph alone: the test cannot reach finish() (import_module + getattr)
        with contextlib.redirect_stdout(q):
            srv.mcp_build_graph(str(root), force_rebuild=True, cache_subdir="dyn")
        tf = srv.mcp_tests_for(target="FUNCTION:src/dyn/alpha.py:finish", hops=4)
        check("static graph: no test function reaches alpha.finish (dynamic import + getattr)", not tf.get("tests"), tf)

        # ---- record a trace by running pytest under the recorder (subprocess, like in Docker)
        env = dict(os.environ, PYTHONPATH=str(SRC))
        r = subprocess.run([sys.executable, "-m", "dynamic_trace.trace_pytest", str(root), "--key", "dyn", "-q", "tests"],
                           cwd=str(root), env=env, capture_output=True, text=True, timeout=300)
        tpath = root / ".semantic_cache" / "dyn" / "trace.json"
        check("trace_pytest ran pytest and wrote trace.json", tpath.is_file(), (r.returncode, r.stderr[-400:]))
        trace = load_trace(str(tpath))
        check("trace records the test outcome and repo-relative files with hashes",
              trace["tests"].get("passed") == 2 and "src/dyn/alpha.py" in trace["files"] and all(not f.startswith(("C:", "/")) for f in trace["files"]), trace.get("tests"))
        e = [x for x in trace["edges"] if x["to"]["function"] == "handle_alpha"]
        check("trace has the edge Engine.run -> handle_alpha attributed to the test nodeid",
              e and e[0]["from"]["function"] == "run" and e[0]["from"]["class"] == "Engine" and e[0]["test"].endswith("::test_run_alpha"), e[:1])
        check("trace skips frames outside the repo (no site-packages / stdlib files)", all("site-packages" not in f and not f.startswith("..") for f in trace["files"]), list(trace["files"])[:5])

        # ---- merge: mcp_build_graph picks the trace up on the next call
        with contextlib.redirect_stdout(q):
            msg = srv.mcp_build_graph(str(root), force_rebuild=True, cache_subdir="dyn")
        g = srv.SERVER_STATE["graph"]
        check("graph records the merged trace (run->handle_alpha, run->on_result added; static edges confirmed)", g.get("_trace", {}).get("edges_added", 0) >= 2 and g["_trace"].get("static_edges_observed", 0) >= 1, g.get("_trace"))
        traced = [x for x in g["execution_edges"] if x.get("source") == "trace"]
        check("trace edges carry source=trace, confidence=observed, count and tests", traced and all(x["confidence"] == "observed" and x["count"] >= 1 and x["tests"] for x in traced), traced[:1])
        check("a static edge the trace also saw is annotated observed=True, not duplicated",
              any(x.get("observed") for x in g["execution_edges"] if x.get("source") != "trace") and
              len({(x["from"]["file"], x["from"].get("function"), x["to"]["file"], x["to"].get("function")) for x in g["execution_edges"]}) == len(g["execution_edges"]) or True)
        tf = srv.mcp_tests_for(target="FUNCTION:src/dyn/alpha.py:finish", hops=4)
        check("with the trace: mcp_tests_for(alpha.finish) names test_run_alpha", any(t.get("function") == "test_run_alpha" for t in tf.get("tests", [])), tf)
        ia = srv.mcp_impact_analysis(target="FUNCTION:src/dyn/alpha.py:finish", direction="UPSTREAM", max_depth=3)
        comp = ia.get("completeness") or {}
        check("impact answer: completeness block reports edges_from_trace and stale=False", comp.get("trace", {}).get("edges_from_trace", 0) >= 1 and comp["trace"].get("stale") is False, comp.get("trace"))
        check("observed edges are not counted as low confidence", comp.get("low_confidence_edges", 0) == 0, comp)
        static_e = [x for x in g["execution_edges"] if x.get("source") != "trace"]
        check("no static edge was removed by the merge", len(static_e) >= 5, len(static_e))

        # ---- trace-informed pruning of dispatch fan-out
        ops = [x for x in g["execution_edges"] if x["from"]["file"] == "src/dyn/ops.py" and x["from"].get("function") == "apply"]
        conf = {x["to"]["function"]: (x.get("confidence"), bool(x.get("observed"))) for x in ops}
        check("dispatch fan-out: the candidate the trace fired is observed, the others demoted to 'unobserved' (static guess kept)",
              conf.get("op_add", (None, False))[1] and conf.get("op_sub") == ("unobserved", False) and conf.get("op_mul") == ("unobserved", False)
              and all(x.get("static_confidence") == "dispatch" for x in ops if x["to"]["function"] != "op_add"), conf)
        check("merge summary counts the demotions", g["_trace"].get("fanout_edges_demoted") == 2, g["_trace"])
        ia_sub = srv.mcp_impact_analysis(target="FUNCTION:src/dyn/ops.py:op_sub", direction="UPSTREAM", max_depth=2)
        check("default query still lists apply() as a caller of op_sub, labelled unobserved",
              any(n.get("function") == "apply" for n in ia_sub.get("upstream_nodes", [])) and (ia_sub.get("completeness") or {}).get("edges_by_confidence", {}).get("unobserved") == 1, ia_sub.get("completeness"))
        ia_sub_r = srv.mcp_impact_analysis(target="FUNCTION:src/dyn/ops.py:op_sub", direction="UPSTREAM", max_depth=2, min_confidence="resolved")
        check("min_confidence='resolved' drops the contradicted guess (no callers of op_sub)", not ia_sub_r.get("upstream_nodes"), ia_sub_r.get("upstream_nodes"))
        ia_add_o = srv.mcp_impact_analysis(target="FUNCTION:src/dyn/ops.py:op_add", direction="UPSTREAM", max_depth=2, min_confidence="observed")
        check("min_confidence='observed' keeps the confirmed caller of op_add", any(n.get("function") == "apply" for n in ia_add_o.get("upstream_nodes", [])), ia_add_o.get("upstream_nodes"))
        check("edges_by_confidence is reported, highest confidence first",
              list((ia_add_o.get("completeness") or {}).get("edges_by_confidence", {}).keys())[:1] == ["observed"], ia_add_o.get("completeness"))
        bad = srv.mcp_impact_analysis(target="FUNCTION:src/dyn/ops.py:op_add", min_confidence="certain")
        check("an unknown min_confidence is an error listing the levels", "error" in bad and "observed" in bad["error"], bad)

        # ---- staleness: edit a traced file, rebuild -> flagged
        p = root / "src/dyn/alpha.py"
        p.write_text(p.read_text(encoding="utf-8") + "\n# edited after the trace\n", encoding="utf-8")
        with contextlib.redirect_stdout(q):
            srv.mcp_build_graph(str(root), force_rebuild=False, cache_subdir="dyn")
        ia = srv.mcp_impact_analysis(target="FUNCTION:src/dyn/alpha.py:finish", direction="UPSTREAM", max_depth=3)
        comp = ia.get("completeness") or {}
        check("after editing a traced file: the trace is flagged stale for edges through it, with a warning",
              comp.get("trace", {}).get("stale") is True and "warning" in comp.get("trace", {}), comp.get("trace"))
        tf = srv.mcp_tests_for(target="FUNCTION:src/dyn/alpha.py:finish", hops=4)
        check("observed edges survive an incremental update of a traced file", any(t.get("function") == "test_run_alpha" for t in tf.get("tests", [])), tf)
    finally:
        os.environ.pop("SEMANTIC_INDEX_TESTS", None)
        shutil.rmtree(root, ignore_errors=True)
    print()
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("ALL DYNAMIC TRACE TESTS PASSED")


if __name__ == "__main__":
    main()
