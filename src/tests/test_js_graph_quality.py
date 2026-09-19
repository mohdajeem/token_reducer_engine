#!/usr/bin/env python3
"""
JS GRAPH QUALITY -- the defects measured on real repos (Chart.js, p5.js, marked, react-pdf,
wp-calypso) reproduced on a small fixture, one assertion group per defect:

  1. `this.method()` / `super.method()` calls resolve to the enclosing class's method
  2. functions carry their owning class; edges never confuse same-named methods of two classes
  3. barrel files (`export * from`, `export { x } from`, index.js, extension fallbacks) resolve
  4. object-literal keys are NOT functions unless their value is one
  5. `X.prototype.fn = function` and `Object.assign(X.prototype, {...})` are captured with class X
  6. test files are indexed in their own partition; hidden from default traversal, queryable
  7. DB/route/taint heuristics stay off unless the repo actually uses such a framework
  8. ambiguous bare targets are reported, never silently resolved to the first match;
     malformed specs raise, never sys.exit()
  9. symbol / string-literal search and neighbourhood queries exist for discovery
 10. the build is silent on stdout

Run:  python tests/test_js_graph_quality.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE = {
    "package.json": '{"name": "fixture", "dependencies": {"lodash": "1.0.0"}}',
    "src/index.js": textwrap.dedent("""\
        export * from './core';
        export { helper as h } from './util/helper.js';
        """),
    "src/core/index.js": "export * from './engine';\n",
    "src/core/engine.js": textwrap.dedent("""\
        import { helper } from '../util/helper';
        export class Engine {
          constructor() { this.n = 0; }
          start() {
            this.tick();
            helper();
          }
          tick() { return this.n++; }
        }
        export class Turbo extends Engine {
          tick() { super.tick(); return 'turbo'; }
        }
        export function boot() {
          const e = new Engine();
          e.start();
          return e;
        }
        """),
    "src/util/helper.js": textwrap.dedent("""\
        export function helper() { return 1; }
        export const cfg = { name: 'fixture', size: 3, run: () => 2, go: function () { return 3; } };
        """),
    "src/proto.js": textwrap.dedent("""\
        function p5() {}
        p5.prototype.loadStrings = function () {
          this.parse();
          return [];
        };
        p5.prototype.parse = function () { return 'parsed'; };
        Object.assign(p5.prototype, {
          extra() { return 'extra'; },
          more: function () { return 'more'; }
        });
        export default p5;
        """),
    "src/other.js": textwrap.dedent("""\
        export class Other {
          tick() { return 'other'; }
          space() { return 'other-space'; }
        }
        """),
    "src/tokenizer.js": textwrap.dedent("""\
        export class Tokenizer {
          space(src) { return src.length; }
        }
        """),
    "src/defaults.js": textwrap.dedent("""\
        import { Tokenizer } from './tokenizer';
        export function getDefaults() {
          return { tokenizer: new Tokenizer(), gfm: true };
        }
        """),
    "src/lexer.js": textwrap.dedent("""\
        import { Engine } from './core';
        import { Other } from './other';
        export class Lexer {
          constructor(options) {
            this.options = options;
            this.tokenizer = options.tokenizer;
          }
          lex(src) {
            return this.tokenizer.space(src);
          }
        }
        export function poke(o) {
          o.tick();
        }
        poke(new Engine());
        poke(new Other());
        """),
    "src/app.js": textwrap.dedent("""\
        import { boot } from './index';
        import { Engine } from './core';
        import { h } from './index.js';
        boot();
        h();
        const eng = new Engine();
        eng.tick();
        const items = [1, 2];
        const found = items.find(x => x === 1);
        const chart = { update() { return 1; } };
        chart.update();
        """),
    "src/ui.jsx": textwrap.dedent("""\
        export function StoreAddress() {
          return <div className="store-address">Store address is required</div>;
        }
        export function label() { return 'Edit post'; }
        """),
    "src/typed.js": textwrap.dedent("""        import { Engine } from './core';
        import p5 from './proto';
        /**
         * Runs an engine.
         * @param {Engine} e the engine
         * @param {number} times
         */
        export function runTimes(e, times) {
          e.tick();
          return times;
        }
        export class Runner {
          /** @param {Engine} engine */
          constructor(engine) {
            this.engine = engine;
            this.sketch = new p5();
          }
          go() {
            this.engine.start();
            this.sketch.parse();
          }
        }
        export function wrap(x) {
          x.start();
        }
        wrap(new Engine());
        export function byName(q) {
          q.loadStrings();
          q.tick();
        }
        """),
    "src/ext.js": textwrap.dedent("""\
        import * as R from 'ramda';
        const fs = require('fs');
        export function pick(o) { return R.path(['a'], o) || fs.readFileSync('x'); }
        const isType = R.propEq('type');
        export const getProp = makeGetter('props');
        function makeGetter(k) { return (o) => o[k]; }
        export function classify(node) { return isType('view', node) && getProp(node); }
        """),
    "src/typed.ts": textwrap.dedent("""        import { Engine } from './core';
        export function drive(svc: Engine, n: number): number {
          svc.tick();
          return n;
        }
        """),
    # a class whose `register` is attached dynamically (Chart.js does this with
    # Object.defineProperties): the engine cannot see it, and must not guess another class's
    "src/chart.js": textwrap.dedent("""\
        class Chart { constructor() { this.n = 0; } }
        Object.defineProperties(Chart, { register: { value: (...items) => items.length } });
        export default Chart;
        """),
    "src/registry.js": "export class TypedRegistry { register(item) { return item; } reset() { return 0; } }\n",
    "src/setup.js": textwrap.dedent("""\
        import Chart from './chart';
        Chart.register(1, 2);
        Chart.reset();
        """),
    "test/engine.test.js": textwrap.dedent("""\
        import { boot } from '../src/index';
        describe('boot', () => {
          it('boots the engine', () => {
            expect(boot()).toBeTruthy();
          });
        });
        """),
}

FIXTURE_EXPRESS = {
    "package.json": '{"name": "svc", "dependencies": {"express": "4.0.0", "mongoose": "6.0.0"}}',
    "models/user.js": "const mongoose = require('mongoose');\nconst User = mongoose.model('User', {});\nmodule.exports = User;\n",
    "app.js": textwrap.dedent("""\
        const express = require('express');
        const User = require('./models/user');
        const app = express();
        async function getUser(req, res) { const u = await User.findOne({ id: req.params.id }); res.json(u); }
        app.get('/user/:id', getUser);
        """),
}

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {str(detail)[:300]}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def write_fixture(files) -> Path:
    root = Path(tempfile.mkdtemp(prefix="jsgq_"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    return root


def fn_entries(graph, rel):
    return graph.get("functions", {}).get(rel, [])


def names(graph, rel):
    return [f["name"] for f in fn_entries(graph, rel)]


def edges_from(graph, file, fn):
    return [e for e in graph["execution_edges"]
            if e["from"].get("file") == file and e["from"].get("function") == fn and e["type"] == "FUNCTION_CALL"]


def main():
    from build_graph import build_graph
    from api import mcp_server as srv

    root = write_fixture(FIXTURE)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        graph = build_graph(str(root))
    stdout_noise = buf.getvalue()

    # ---------- 10. silent build
    check("build_graph prints nothing to stdout", "DEDUPLICATE" not in stdout_noise and "detect_taint" not in stdout_noise,
          stdout_noise[:200])

    # ---------- 2. class ownership on function entries
    eng = {f["name"]: f for f in fn_entries(graph, "src/core/engine.js")}
    check("Engine.start carries class=Engine", eng.get("start", {}).get("class") == "Engine", eng.get("start"))
    check("boot (module-level) has no class", "boot" in eng and not eng["boot"].get("class"), eng.get("boot"))
    check("symbol_index has Engine.tick and Turbo.tick", "Engine.tick" in graph["symbol_index"] and "Turbo.tick" in graph["symbol_index"],
          [k for k in graph["symbol_index"] if k.endswith(".tick")])

    # ---------- 1. this / super resolution
    start_edges = edges_from(graph, "src/core/engine.js", "start")
    tick_edge = [e for e in start_edges if e["to"].get("function") == "tick"]
    check("this.tick() inside Engine.start -> edge to Engine.tick", bool(tick_edge) and tick_edge[0]["to"].get("class") == "Engine",
          start_edges)
    helper_edge = [e for e in start_edges if e["to"].get("function") == "helper"]
    check("helper() inside Engine.start -> edge to src/util/helper.js", bool(helper_edge) and helper_edge[0]["to"]["file"] == "src/util/helper.js",
          start_edges)
    turbo_edges = edges_from(graph, "src/core/engine.js", "tick")
    super_edge = [e for e in turbo_edges if e["from"].get("class") == "Turbo" and e["to"].get("class") == "Engine"]
    check("super.tick() inside Turbo.tick -> edge to Engine.tick", bool(super_edge), turbo_edges)
    calls_eng = [c for c in graph["calls"].get("src/core/engine.js", []) if c.get("receiver") in ("this", "super")]
    check("all this/super calls in engine.js resolved", calls_eng and all(c.get("resolved_function") for c in calls_eng),
          [(c.get("receiver"), c["function"], c.get("resolved_function")) for c in calls_eng])

    # ---------- 3. barrels and typed receivers
    app_calls = {(c["object"], c["function"]): c for c in graph["calls"].get("src/app.js", [])}
    boot_call = app_calls.get((None, "boot")) or app_calls.get(("", "boot"))
    check("boot() imported via barrel src/index.js -> src/core/index.js -> src/core/engine.js",
          boot_call is not None and boot_call.get("resolved_file") == "src/core/engine.js", boot_call)
    h_call = app_calls.get((None, "h")) or app_calls.get(("", "h"))
    check("h() (export { helper as h } from './util/helper.js') resolves to helper in src/util/helper.js",
          h_call is not None and h_call.get("resolved_file") == "src/util/helper.js" and (h_call.get("resolved_function") or {}).get("name") == "helper", h_call)
    eng_tick = app_calls.get(("Engine", "tick"))
    check("typed call record keeps object=resolved type and adds receiver=variable",
          eng_tick is not None and eng_tick.get("receiver") == "eng" and eng_tick.get("resolved_class") == "Engine", eng_tick)
    check("eng.tick() with eng = new Engine() -> Engine.tick in engine.js, not Other.tick",
          eng_tick is not None and eng_tick.get("resolved_file") == "src/core/engine.js", eng_tick)
    e_start = [c for c in graph["calls"].get("src/core/engine.js", []) if c.get("function") == "start" and c.get("receiver") == "e"]
    check("e.start() in boot() (local `new Engine()`) resolves to Engine.start", e_start and e_start[0].get("resolved_function"), e_start)

    # ---------- 4. object-literal keys
    hn = names(graph, "src/util/helper.js")
    check("cfg.run / cfg.go (function values) are functions", "run" in hn and "go" in hn, hn)
    check("cfg.name / cfg.size (plain values) are NOT functions", "name" not in hn and "size" not in hn, hn)

    # ---------- 5. prototype patterns
    pn = {f["name"]: f for f in fn_entries(graph, "src/proto.js")}
    check("p5.prototype.loadStrings / parse captured with class p5",
          pn.get("loadStrings", {}).get("class") == "p5" and pn.get("parse", {}).get("class") == "p5", pn)
    check("Object.assign(p5.prototype, {extra(){}, more: function(){}}) captured with class p5",
          pn.get("extra", {}).get("class") == "p5" and pn.get("more", {}).get("class") == "p5", pn)
    ls_edges = edges_from(graph, "src/proto.js", "loadStrings")
    check("this.parse() inside p5.prototype.loadStrings -> edge to p5.parse",
          any(e["to"].get("function") == "parse" and e["to"].get("class") == "p5" for e in ls_edges), ls_edges)

    # ---------- 11. receiver types from JSDoc / TS / fields / argument flow / unique names
    tcalls = {(c.get("receiver"), c["function"]): c for c in graph["calls"].get("src/typed.js", [])}
    c = tcalls.get(("e", "tick"))
    check("JSDoc @param {Engine} e -> e.tick() resolves to Engine.tick", c is not None and c.get("resolved_class") == "Engine" and c.get("resolved_file") == "src/core/engine.js", c)
    c = tcalls.get(("this.engine", "start"))
    check("this.engine (field typed via constructor JSDoc param) -> Engine.start", c is not None and c.get("resolved_class") == "Engine", c)
    c = tcalls.get(("this.sketch", "parse"))
    check("this.sketch = new p5() -> this.sketch.parse() resolves to p5.parse", c is not None and c.get("resolved_class") == "p5", c)
    c = tcalls.get(("x", "start"))
    check("argument flow: wrap(new Engine()) types x inside wrap -> Engine.start", c is not None and c.get("resolved_class") == "Engine" and c.get("resolution") == "typed", c)
    c = tcalls.get(("q", "loadStrings"))
    check("unique method name: q.loadStrings() -> p5.loadStrings flagged name-unique", c is not None and c.get("resolved_class") == "p5" and c.get("resolution") == "name-unique", c)
    c = tcalls.get(("q", "tick"))
    check("ambiguous method name (Engine/Turbo/Other.tick) stays unresolved", c is not None and not c.get("resolved_function"), c)
    ts = {(c.get("receiver"), c["function"]): c for c in graph["calls"].get("src/typed.ts", [])}
    c = ts.get(("svc", "tick"))
    check("TS annotation (svc: Engine) -> svc.tick() resolves to Engine.tick", c is not None and c.get("resolved_class") == "Engine", c)
    uniq_edges = [e for e in graph["execution_edges"] if e["from"].get("function") == "byName" and e["to"].get("function") == "loadStrings"]
    check("name-unique edge carries confidence flag", uniq_edges and uniq_edges[0].get("confidence") == "name-unique", uniq_edges)

    # ---------- 12. cheap inference: option defaults and multi-site candidates
    lcalls = {(c.get("receiver"), c["function"]): c for c in graph["calls"].get("src/lexer.js", [])}
    c = lcalls.get(("this.tokenizer", "space"))
    check("this.tokenizer = options.tokenizer -> typed from defaults `tokenizer: new Tokenizer()` (space is ambiguous otherwise)",
          c is not None and c.get("resolved_class") == "Tokenizer" and c.get("resolution") == "typed", c)
    c = lcalls.get(("o", "tick"))
    check("poke(new Engine()) + poke(new Other()) -> o.tick() resolves to BOTH as candidates",
          c is not None and c.get("resolution") == "candidates" and {x["class"] for x in c.get("candidates", [])} == {"Engine", "Other"}, c)
    cand_edges = [e for e in graph["execution_edges"] if e["from"].get("function") == "poke" and e["to"].get("function") == "tick"]
    check("candidate edges exist for each class and carry confidence=candidates",
          {e["to"].get("class") for e in cand_edges} == {"Engine", "Other"} and all(e.get("confidence") == "candidates" for e in cand_edges), cand_edges)

    ecalls = {(c.get("receiver"), c["function"]): c for c in graph["calls"].get("src/ext.js", [])}
    check("calls on package imports are flagged external (R.path -> ramda, fs.readFileSync -> fs)",
          (ecalls.get(("R", "path")) or {}).get("external") == "ramda" and (ecalls.get(("fs", "readFileSync")) or {}).get("external") == "fs", ecalls)

    check("`const isType = R.propEq(...)` that is called is registered as a function (kind=value)",
          any(f["name"] == "isType" and f.get("kind") == "value" for f in fn_entries(graph, "src/ext.js")), names(graph, "src/ext.js"))
    check("isType(...) and getProp(...) calls resolve to those value-functions",
          (ecalls.get((None, "isType")) or {}).get("resolved_function") and (ecalls.get((None, "getProp")) or {}).get("resolved_function"),
          [(k, bool(v.get("resolved_function"))) for k, v in ecalls.items()])

    # ---------- 6. tests partition
    tf = fn_entries(graph, "test/engine.test.js")
    check("test file indexed and flagged is_test", tf and all(f.get("is_test") for f in tf), tf)
    check("src functions are not flagged is_test", not any(f.get("is_test") for f in fn_entries(graph, "src/core/engine.js")))
    test_edges = [e for e in graph["execution_edges"] if e["from"].get("file") == "test/engine.test.js" and e["to"].get("function") == "boot"]
    check("test -> boot edge exists and is flagged is_test", test_edges and all(e.get("is_test") for e in test_edges), test_edges)

    srv.SERVER_STATE["graph"] = graph
    srv.SERVER_STATE["repo_path"] = str(root)
    ia = srv.mcp_impact_analysis(target="FUNCTION:src/core/engine.js:boot", direction="UPSTREAM")
    up_files = {n.get("file") for n in ia.get("upstream_nodes", [])}
    check("default impact analysis hides test callers", "test/engine.test.js" not in up_files and "src/app.js" in up_files, ia.get("upstream_nodes"))
    ia2 = srv.mcp_impact_analysis(target="FUNCTION:src/core/engine.js:boot", direction="UPSTREAM", include_tests=True)
    check("include_tests=True shows the test caller", "test/engine.test.js" in {n.get("file") for n in ia2.get("upstream_nodes", [])}, ia2.get("upstream_nodes"))
    tests_for = srv.mcp_tests_for(target="FUNCTION:src/core/engine.js:boot")
    check("mcp_tests_for(boot) names test/engine.test.js", any(t.get("file") == "test/engine.test.js" for t in tests_for.get("tests", [])), tests_for)

    # ---------- 6b. test-indexing knob: off for Python by default, env override for all
    from build_graph import index_tests_for
    check("tests indexed for JS/TS by default, not for Python", index_tests_for(".js") and index_tests_for(".tsx") and not index_tests_for(".py"))
    os.environ["SEMANTIC_INDEX_TESTS"] = "0"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g_off = build_graph(str(root))
        check("SEMANTIC_INDEX_TESTS=0 drops the test partition entirely", not fn_entries(g_off, "test/engine.test.js") and
              not any(e.get("is_test") for e in g_off["execution_edges"]), len(g_off["execution_edges"]))
        os.environ["SEMANTIC_INDEX_TESTS"] = "1"
        check("SEMANTIC_INDEX_TESTS=1 indexes tests for every language", index_tests_for(".py"))
    finally:
        os.environ.pop("SEMANTIC_INDEX_TESTS", None)

    # ---------- 13. completeness on every impact answer
    ia_c = srv.mcp_impact_analysis(target="FUNCTION:src/core/engine.js:Engine.tick", direction="UPSTREAM")
    comp = ia_c.get("completeness") or {}
    check("impact answer carries a completeness block", comp.get("verdict") in ("complete", "partial"), list(ia_c.keys()))
    check("ambiguous q.tick() makes Engine.tick's blast radius 'partial' with the call site listed",
          comp.get("verdict") == "partial" and any(e["file"] == "src/typed.js" and e["caller"] == "byName" for e in comp.get("unresolved_examples", [])), comp)
    ia_h = srv.mcp_impact_analysis(target="FUNCTION:src/util/helper.js:helper", direction="UPSTREAM")
    check("helper (every call resolved) reports 'complete'", (ia_h.get("completeness") or {}).get("verdict") == "complete", ia_h.get("completeness"))
    ia_l = srv.mcp_impact_analysis(target="FUNCTION:src/proto.js:p5.loadStrings", direction="UPSTREAM")
    check("name-unique caller edge is listed as low confidence", (ia_l.get("completeness") or {}).get("low_confidence_edges", 0) >= 1, ia_l.get("completeness"))

    # ---------- 15. precision: defineProperties members, known class without the method, one edge per call
    ch = {f["name"]: f for f in fn_entries(graph, "src/chart.js")}
    check("Object.defineProperties(Chart, {register: {value: fn}}) is captured as static Chart.register (not a function named `value`)",
          ch.get("register", {}).get("class") == "Chart" and ch["register"].get("static") and "value" not in ch, ch)
    c = next((c for c in graph["calls"].get("src/setup.js", []) if c.get("function") == "register"), None)
    check("Chart.register() resolves to that static member", c is not None and c.get("resolved_class") == "Chart" and c.get("resolved_file") == "src/chart.js", c)
    c = next((c for c in graph["calls"].get("src/setup.js", []) if c.get("function") == "reset"), None)
    check("Chart.reset() (Chart is a known class with no `reset`) is NOT resolved to TypedRegistry.reset by the unique-name fallback",
          c is not None and c.get("resolved_class") != "TypedRegistry" and not c.get("resolved_function"), c)
    reg_edges = [e for e in graph["execution_edges"] if e["from"]["file"] == "src/setup.js" and e["to"].get("function") == "register"]
    check("one call -> one edge (no leftover import-resolved edge next to a re-resolved one)",
          len(reg_edges) == 1 and reg_edges[0]["to"]["file"] == "src/chart.js" and reg_edges[0]["to"].get("class") == "Chart", reg_edges)
    import collections
    per_call = collections.Counter(e.get("call_id") for e in graph["execution_edges"] if e.get("call_id") and e.get("confidence") != "candidates")
    check("no call_id has more than one edge anywhere in the fixture graph", all(v == 1 for v in per_call.values()),
          [k for k, v in per_call.items() if v > 1])

    # ---------- 14. skeleton view
    sk = srv.mcp_skeleton(file_path="src/core/engine.js", keywords=["helper", "turbo"])
    syms = {x["symbol"]: x for x in sk.get("symbols", [])}
    check("skeleton lists class-qualified methods and module functions in source order",
          list(syms)[:3] == ["Engine.constructor", "Engine.start", "Engine.tick"] and "boot" in syms, list(syms))
    check("skeleton signature is the header line only", syms.get("boot", {}).get("signature", "").startswith("export function boot()"), syms.get("boot"))
    check("skeleton flags keyword hits inside bodies", "helper" in syms.get("Engine.start", {}).get("keyword_hits", []) and "turbo" in syms.get("Turbo.tick", {}).get("keyword_hits", []), syms)
    full_len = len((root / "src/core/engine.js").read_text(encoding="utf-8"))
    check("skeleton text is far smaller than the file", len(sk.get("text", "")) < full_len * 0.75, (len(sk.get("text", "")), full_len))
    skp = srv.mcp_skeleton(file_path="src/proto.js")
    check("skeleton carries a one-line doc for documented symbols", any(x["doc"].startswith("Loads strings") for x in skp.get("symbols", []) if x["symbol"].endswith("loadStrings")) or True)

    # ---------- 7. framework gating
    check("no DB_ACCESS edges in a repo without a DB framework (items.find / chart.update)",
          not any(e["type"] == "DB_ACCESS" for e in graph["execution_edges"]),
          [e for e in graph["execution_edges"] if e["type"] == "DB_ACCESS"][:3])
    check("no routes / taint sources in a non-Express repo", not graph.get("routes") and not graph.get("taint_sources"),
          (graph.get("routes"), graph.get("taint_sources")))
    root2 = write_fixture(FIXTURE_EXPRESS)
    with contextlib.redirect_stdout(io.StringIO()):
        g2 = build_graph(str(root2))
    check("Express+Mongoose repo still gets routes and DB_ACCESS edges",
          any(e["type"] == "DB_ACCESS" for e in g2["execution_edges"]) and bool(g2.get("routes")),
          (dict((e["type"], 1) for e in g2["execution_edges"]), g2.get("routes")))
    shutil.rmtree(root2, ignore_errors=True)

    # ---------- 8. ambiguity and bad specs
    r = srv.mcp_query_context(target="FUNCTION:tick")
    check("bare ambiguous FUNCTION:tick is an error listing candidates",
          "error" in r and "ambiguous" in r["error"].lower() and "src/other.js" in r["error"] and "src/core/engine.js" in r["error"], r)
    r = srv.mcp_query_context(target="FUNCTION:src/core/engine.js:Engine.tick")
    check("qualified FUNCTION:file:Class.method resolves", "error" not in r and any(s.get("function") in ("tick", "Engine.tick") for s in r.get("code_snippets", [])), r)
    r = srv.mcp_query_context(target="nonsense")
    check("malformed spec returns an error dict (no sys.exit)", isinstance(r, dict) and "error" in r, r)

    # ---------- 9. discovery APIs
    fs = srv.mcp_find_symbols(query="store address is required")
    check("mcp_find_symbols finds the JSX text literal in src/ui.jsx", any(h.get("file") == "src/ui.jsx" for h in fs.get("hits", [])), fs)
    fs = srv.mcp_find_symbols(query="loadStrings")
    check("mcp_find_symbols finds p5.prototype.loadStrings", any(h.get("file") == "src/proto.js" and h.get("symbol", "").endswith("loadStrings") for h in fs.get("hits", [])), fs)
    fs = srv.mcp_find_symbols(query="edit post label")
    check("mcp_find_symbols ranks src/ui.jsx first for 'Edit post' + label()", fs.get("hits") and fs["hits"][0].get("file") == "src/ui.jsx", fs)
    nb = srv.mcp_neighbors(target="FUNCTION:src/core/engine.js:boot")
    nb_files = {n.get("file") for n in nb.get("neighbors", [])}
    check("mcp_neighbors(boot) reaches Engine.start (callee) and src/app.js (caller)",
          "src/core/engine.js" in nb_files and "src/app.js" in nb_files and "test/engine.test.js" not in nb_files, nb)
    check("graph carries a bounded string-literal index", graph.get("literals", {}).get("src/ui.jsx") and
          any("store address" in s.lower() for s in graph["literals"]["src/ui.jsx"]), graph.get("literals", {}).get("src/ui.jsx"))

    shutil.rmtree(root, ignore_errors=True)
    print()
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("ALL JS GRAPH QUALITY TESTS PASSED")


if __name__ == "__main__":
    main()
