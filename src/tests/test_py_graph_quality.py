#!/usr/bin/env python3
"""
PYTHON GRAPH QUALITY -- measured on pytest / flask / requests / sphinx at SWE-bench base
commits, the Python graph resolved 3-8% of calls: imports were resolved by appending
".js", `self.x()` never resolved (0/2746 on sphinx) and no method knew its class.
Reproduced on a small package fixture, one assertion group per defect:

  1. module resolution: absolute dotted, relative (`.`/`..`), `src/` layout, package
     `__init__.py`, `from pkg import name` re-exported through `__init__.py`
  2. methods carry their class; `self.x()` / `cls.x()` / `super().x()` resolve
  3. receiver types from annotations and `self.f = Foo()`; unique-name fallback
  4. stdlib / third-party calls are flagged external, never guessed
  5. tests partition off by default for Python, on with SEMANTIC_INDEX_TESTS=1

Run:  python tests/test_py_graph_quality.py
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE = {
    "pyproject.toml": "[project]\nname = 'fixture'\n",
    "src/pkg/__init__.py": textwrap.dedent("""\
        from .core.engine import Engine, boot
        from .util import helper as h
        """),
    "src/pkg/util.py": textwrap.dedent("""\
        import os
        def helper():
            return os.getcwd()
        """),
    "src/pkg/core/__init__.py": "",
    "src/pkg/core/engine.py": textwrap.dedent("""\
        from ..util import helper
        from . import parts


        class Engine:
            def __init__(self, gear: "parts.Gear"):
                self.n = 0
                self.gear = gear
                self.cache = parts.Cache()

            def start(self):
                self.tick()
                helper()
                self.gear.spin()
                self.cache.put(1)

            def tick(self):
                self.n += 1
                return self.n

            @classmethod
            def build(cls):
                return cls(parts.Gear())


        class Turbo(Engine):
            def tick(self):
                super().tick()
                return "turbo"


        def boot():
            e = Engine(parts.Gear())
            e.start()
            return e
        """),
    "src/pkg/core/parts.py": textwrap.dedent("""\
        class Gear:
            def spin(self):
                return "spin"


        class Cache:
            def put(self, v):
                return v

            def warm_up(self):
                return 'warm'

            def spin(self):
                return "cache-spin"
        """),
    "src/pkg/app.py": textwrap.dedent("""\
        import json
        import pkg.core.parts
        from pkg import boot, h
        from pkg.core.parts import Gear
        from pkg.core import engine as eng_mod


        def run(gear: Gear):
            gear.spin()
            boot()
            h()
            eng_mod.boot()
            return json.dumps({})


        def by_name(x):
            x.put(2)
            x.warm_up()
            x.spin()
            return pkg.core.parts.Gear()


        def session():
            return eng_mod.Engine(Gear())


        def use_factory():
            s = session()
            s.start()
            with eng_mod.Engine(Gear()) as ctx:
                ctx.tick()
            eng_mod.Engine(Gear()).start()
            n = session().tick()
            return s
        """),
    # `from pkg.table import Table` where the module is table.py: on a case-insensitive file
    # system the candidate pkg/table/Table.py "exists" and used to win over table.py
    "src/pkg/table/__init__.py": "from .table import Table\n",
    "src/pkg/table/table.py": textwrap.dedent("""\
        class Table:
            def __init__(self, data):
                self.cols = self._convert(data)

            def _convert(self, data):
                return list(data)
        """),
    "src/pkg/use_table.py": textwrap.dedent("""\
        from pkg.table import Table


        def make():
            t = Table([1, 2])
            return t.cols
        """),
    # a tiny ORM shaped like Django's: `Model.objects` is a Manager whose methods are really
    # QuerySet's; QuerySet methods return clones (`self.__class__(...)`, `self._chain()`);
    # the package re-exports everything with `from .query import *`
    "src/orm/__init__.py": "from .query import *\nfrom .aggregates import *\n",
    "src/orm/query.py": textwrap.dedent("""\
        class QuerySet:
            def __init__(self, model=None):
                self.model = model

            def _clone(self):
                c = self.__class__(model=self.model)
                return c

            def _chain(self):
                obj = self._clone()
                return obj

            def filter(self, **kw):
                clone = self._chain()
                return clone

            def order_by(self, *fields):
                return self._chain()

            def values_list(self, *fields):
                return list(fields)


        class Manager:
            pass


        class Model:
            objects = Manager()
        """),
    "src/orm/aggregates.py": textwrap.dedent("""\
        class Count:
            def __init__(self, expr):
                self.expr = expr
        """),
    "src/app_models.py": textwrap.dedent("""\
        from orm import Model, Count


        class Book(Model):
            pass


        def newest_titles():
            qs = Book.objects.filter(year=2020)
            ordered = qs.order_by('-year')
            n = Count('id')
            return ordered.values_list('title')
        """),
    # dispatch tables and getattr-built method names (astropy's _operators, django's visitors)
    "src/pkg/dispatch.py": textwrap.dedent("""\
        def and_(a, b):
            return a and b


        def or_(a, b):
            return a or b


        _ops = {'&': and_, '|': or_}


        def apply(op, a, b):
            return _ops[op](a, b)


        def apply_get(op, a, b):
            return _ops.get(op)(a, b)


        class Visitor:
            def __init__(self):
                self.handlers = {"num": self.visit_num, "name": self.visit_name}

            def visit_num(self, node):
                return 1

            def visit_name(self, node):
                return 2

            def other(self, node):
                return 3

            def dispatch(self, node):
                return self.handlers[node.kind](node)

            def dynamic(self, node):
                return getattr(self, "visit_" + node.kind)(node)

            def dynamic_f(self, node):
                return getattr(self, f"visit_{node.kind}")(node)
        """),
    # a plain module re-exports what it imports (django/template/base.py re-exports
    # TemplateSyntaxError from .exceptions); builtins and package names are labelled
    "src/pkg/errors.py": "class PkgError(Exception):\n    pass\n",
    "src/pkg/base.py": "from .errors import PkgError\n\n\ndef base_fn():\n    return 1\n",
    "src/pkg/raise_it.py": textwrap.dedent("""\
        from .base import PkgError
        from numpy import polyval


        def check(items):
            if len(items) > 2:
                raise PkgError()
            return polyval(items, 1)
        """),
    "tests/test_engine.py": textwrap.dedent("""\
        from pkg import boot

        def test_boot():
            assert boot()
        """),
    # pytest fixtures: `app` is injected by NAME; the fixture yields an Engine
    "tests/conftest.py": textwrap.dedent("""\
        import pytest
        from pkg.core.engine import Engine
        from pkg.core.parts import Gear


        @pytest.fixture
        def app():
            engine = Engine(Gear())
            yield engine


        @pytest.fixture(name="eng")
        def _make_engine():
            return Engine(Gear())
        """),
    "tests/test_fixture.py": textwrap.dedent("""\
        import pytest
        from pkg.core.parts import Gear


        def test_start(app):
            app.start()


        def test_named(eng):
            eng.tick()


        class TestWithFixture:
            @pytest.fixture
            def gear(self):
                return Gear()

            def test_spin(self, gear):
                gear.spin()
        """),
}

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {str(detail)[:300]}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def write_fixture(files):
    root = Path(tempfile.mkdtemp(prefix="pygq_"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    return root


def fns(graph, rel):
    return graph.get("functions", {}).get(rel, [])


def calls(graph, rel):
    return {(c.get("receiver"), c["function"]): c for c in graph.get("calls", {}).get(rel, [])}


def main():
    from build_graph import build_graph
    from api import mcp_server as srv

    root = write_fixture(FIXTURE)
    with contextlib.redirect_stdout(io.StringIO()):
        graph = build_graph(str(root))
    E = "src/pkg/core/engine.py"

    # ---------- 2. class ownership + self/cls/super
    eng = {f["name"]: f for f in fns(graph, E)}
    check("Engine.start carries class=Engine", eng.get("start", {}).get("class") == "Engine", eng.get("start"))
    check("boot (module-level) has no class", "boot" in eng and not eng["boot"].get("class"))
    check("Turbo registered with superclass Engine", (graph["classes"].get(E, {}).get("Turbo") or {}).get("superclass") == "Engine", graph["classes"].get(E))
    ec = calls(graph, E)
    c = ec.get(("self", "tick"))
    check("self.tick() inside Engine.start -> Engine.tick", c is not None and c.get("resolved_class") == "Engine" and c.get("resolved_file") == E, c)
    c = ec.get(("super()", "tick"))
    check("super().tick() inside Turbo.tick -> Engine.tick", c is not None and c.get("resolved_class") == "Engine", c)
    c = ec.get(("cls", "__init__")) or ec.get(("cls", "Engine"))
    # cls(...) is a constructor call; accept either shape but require no crash
    check("cls(...) in a classmethod does not break the build", True)

    # ---------- 1. module resolution
    c = ec.get((None, "helper"))
    check("relative import `from ..util import helper` -> src/pkg/util.py", c is not None and c.get("resolved_file") == "src/pkg/util.py", c)
    ac = calls(graph, "src/pkg/app.py")
    c = ac.get((None, "boot"))
    check("`from pkg import boot` re-exported via src/pkg/__init__.py -> engine.py", c is not None and c.get("resolved_file") == E, c)
    c = ac.get((None, "h"))
    check("`from pkg import h` (aliased re-export) -> util.helper", c is not None and c.get("resolved_file") == "src/pkg/util.py"
          and (c.get("resolved_function") or {}).get("name") == "helper", c)
    c = ac.get(("eng_mod", "boot"))
    check("`from pkg.core import engine as eng_mod` -> eng_mod.boot() resolves", c is not None and c.get("resolved_file") == E, c)
    c = ac.get(("gear", "spin"))
    check("annotation `gear: Gear` (imported class) -> gear.spin() resolves to parts.Gear.spin", c is not None and c.get("resolved_class") == "Gear" and c.get("resolved_file") == "src/pkg/core/parts.py", c)

    # ---------- 3. field types, string annotations, unique-name fallback
    c = ec.get(("self.gear", "spin"))
    check("self.gear typed from string annotation 'parts.Gear' -> Gear.spin", c is not None and c.get("resolved_class") == "Gear", c)
    c = ec.get(("self.cache", "put"))
    check("self.cache = parts.Cache() -> self.cache.put() resolves to Cache.put", c is not None and c.get("resolved_class") == "Cache", c)
    c = ac.get(("x", "warm_up"))
    check("unique repo-specific method name x.warm_up() -> Cache.warm_up flagged name-unique", c is not None and c.get("resolved_class") == "Cache" and c.get("resolution") == "name-unique", c)
    c = ac.get(("x", "put"))
    check("x.put() is NOT guessed from repo uniqueness (put is also a Queue/dict-style builtin method)", c is not None and not c.get("resolved_function"), c)
    c = ac.get(("x", "spin"))
    check("ambiguous x.spin() (Gear/Cache) stays unresolved", c is not None and not c.get("resolved_function"), c)

    # ---------- 3b. constructors, plain `import pkg`, cls(...)
    c = ec.get((None, "Engine")) or ec.get((None, "parts.Gear"))
    check("Engine(...) constructor call in boot() resolves to the Engine class node", c is not None and (c.get("resolved_function") or {}).get("kind") == "class", c)
    gc = ec.get(("parts", "Gear")) or ec.get(("parts", "Cache"))
    check("parts.Gear() via `from . import parts` resolves to the class node in parts.py", gc is not None and gc.get("resolved_file") == "src/pkg/core/parts.py", gc)
    c = ec.get((None, "cls"))
    check("cls(...) inside a classmethod resolves to the owning class", c is not None and c.get("resolved_class") == "Engine", c)
    check("classes registry knows Gear and Cache from class definitions", {"Gear", "Cache"} <= set(graph["classes"].get("src/pkg/core/parts.py", {})), graph["classes"].get("src/pkg/core/parts.py"))

    c = ac.get(("pkg.core.parts", "Gear"))
    check("`import pkg.core.parts` then pkg.core.parts.Gear() resolves", c is not None and c.get("resolved_file") == "src/pkg/core/parts.py", c)

    # ---------- 3c. blast radius through constructors, factories and `with ... as`
    ctor = [e for e in graph["execution_edges"] if e.get("via") == "constructor" and e["to"].get("function") == "__init__" and e["to"].get("class") == "Engine"]
    check("Engine(...) also gets an edge to Engine.__init__ (via=constructor)", len(ctor) >= 1, ctor[:2])
    srv.SERVER_STATE["graph"] = graph; srv.SERVER_STATE["repo_path"] = str(root)
    ia = srv.mcp_impact_analysis(target=f"FUNCTION:{E}:Engine.__init__", direction="UPSTREAM", max_depth=1)
    check("impact of Engine.__init__ lists boot() which instantiates Engine", any(n.get("function") == "boot" for n in ia.get("upstream_nodes", [])), ia.get("upstream_nodes"))
    c = ac.get(("s", "start"))
    check("s = session() where session() returns Engine(...) -> s.start() resolves to Engine.start (return-type inference)",
          c is not None and c.get("resolved_class") == "Engine" and c.get("resolution") == "typed", c)
    c = ac.get(("ctx", "tick"))
    check("`with eng_mod.Engine() as ctx` -> ctx.tick() resolves to Engine.tick", c is not None and c.get("resolved_class") == "Engine", c)
    c = next((x for x in calls(graph, "src/pkg/app.py").values() if x.get("function") == "start" and "(" in str(x.get("receiver"))), None)
    check("eng_mod.Engine(Gear()).start() (instantiation-expression receiver) resolves to Engine.start", c is not None and c.get("resolved_class") == "Engine", c)
    c = next((x for x in calls(graph, "src/pkg/app.py").values() if x.get("function") == "tick" and str(x.get("receiver")).startswith("session(")), None)
    check("session().tick() (call-expression receiver, factory return type) resolves to Engine.tick", c is not None and c.get("resolved_class") == "Engine", c)

    # ---------- 3d. case-insensitive file systems must not resolve Table -> pkg/table/Table.py
    uc = calls(graph, "src/pkg/use_table.py")
    c = uc.get((None, "Table"))
    check("`from pkg.table import Table` resolves to src/pkg/table/table.py (case-exact), not Table.py",
          c is not None and c.get("resolved_file") == "src/pkg/table/table.py" and (c.get("resolved_function") or {}).get("kind") == "class", c)
    ia = srv.mcp_impact_analysis(target="FUNCTION:src/pkg/table/table.py:Table._convert", direction="UPSTREAM", max_depth=2)
    check("blast radius of Table._convert reaches make() through Table.__init__", any(n.get("function") == "make" for n in ia.get("upstream_nodes", [])), ia.get("upstream_nodes"))

    # ---------- 3e. Django-shaped ORM chains, star re-exports, clone-returning methods
    mc = calls(graph, "src/app_models.py")
    c = mc.get(("Book.objects", "filter"))
    check("Book.objects.filter() -> QuerySet.filter (manager methods are QuerySet's)", c is not None and c.get("resolved_class") == "QuerySet", c)
    c = mc.get(("qs", "order_by"))
    check("qs = Book.objects.filter(); qs.order_by() -> QuerySet.order_by (filter returns a clone typed via self._chain/self.__class__)",
          c is not None and c.get("resolved_class") == "QuerySet", c)
    c = mc.get(("ordered", "values_list"))
    check("ordered = qs.order_by(); ordered.values_list() -> QuerySet.values_list", c is not None and c.get("resolved_class") == "QuerySet", c)
    c = mc.get((None, "Count"))
    check("Count(...) via `from orm import Count` where orm/__init__ does `from .aggregates import *` -> class node in aggregates.py",
          c is not None and c.get("resolved_file") == "src/orm/aggregates.py" and (c.get("resolved_function") or {}).get("kind") == "class", c)
    ia = srv.mcp_impact_analysis(target="FUNCTION:src/orm/query.py:QuerySet._clone", direction="UPSTREAM", max_depth=4)
    check("blast radius of QuerySet._clone reaches newest_titles() through _chain/filter", any(n.get("function") == "newest_titles" for n in ia.get("upstream_nodes", [])), [n.get("function") for n in ia.get("upstream_nodes", [])])

    # ---------- 3f. dispatch tables and getattr(self, "prefix_" + x)()
    D = "src/pkg/dispatch.py"
    def edges_to(fn_name):
        return [(e["from"].get("function"), e.get("confidence")) for e in graph["execution_edges"] if e["to"].get("file") == D and e["to"].get("function") == fn_name]
    check("_ops[op](a, b) links to BOTH and_ and or_ flagged confidence=dispatch",
          ("apply", "dispatch") in edges_to("and_") and ("apply", "dispatch") in edges_to("or_"), (edges_to("and_"), edges_to("or_")))
    check("_ops.get(op)(a, b) links the same way", ("apply_get", "dispatch") in edges_to("and_"), edges_to("and_"))
    check("self.handlers[k](node) links to visit_num and visit_name but NOT other",
          ("dispatch", "dispatch") in edges_to("visit_num") and ("dispatch", "dispatch") in edges_to("visit_name") and not any(f == "dispatch" for f, _ in edges_to("other")),
          (edges_to("visit_num"), edges_to("other")))
    check("getattr(self, 'visit_' + kind)(node) links to every visit_* method flagged dynamic",
          ("dynamic", "dynamic") in edges_to("visit_num") and ("dynamic", "dynamic") in edges_to("visit_name") and not any(f == "dynamic" for f, _ in edges_to("other")),
          (edges_to("visit_num"), edges_to("other")))
    check("getattr(self, f'visit_{kind}')(node) (f-string prefix) links the same way", ("dynamic_f", "dynamic") in edges_to("visit_num"), edges_to("visit_num"))
    dc = [c for c in graph["calls"].get(D, []) if c.get("dispatch")]
    check("dispatch call records carry resolution + candidates", dc and all(c.get("resolution") in ("dispatch", "dynamic") and c.get("candidates") for c in dc), dc[:2])
    ia = srv.mcp_impact_analysis(target=f"FUNCTION:{D}:Visitor.visit_name", direction="UPSTREAM", max_depth=1)
    check("impact of visit_name lists dispatch/dynamic callers with low confidence noted",
          {n.get("function") for n in ia.get("upstream_nodes", [])} >= {"dispatch", "dynamic", "dynamic_f"} and (ia.get("completeness") or {}).get("low_confidence_edges", 0) >= 3, ia)

    # ---------- 3g. re-exports through plain modules; builtin / package bare calls labelled
    rc = calls(graph, "src/pkg/raise_it.py")
    c = rc.get((None, "PkgError"))
    check("`from .base import PkgError` where base.py merely imports it from .errors -> class node in errors.py",
          c is not None and c.get("resolved_file") == "src/pkg/errors.py" and (c.get("resolved_function") or {}).get("kind") == "class", c)
    c = rc.get((None, "len"))
    check("len(...) is labelled external='builtin', not left unresolved", c is not None and c.get("external") == "builtin", c)
    c = rc.get((None, "polyval"))
    check("polyval(...) imported from numpy is labelled external='numpy'", c is not None and c.get("external") == "numpy", c)

    # ---------- 4. external
    c = ac.get(("json", "dumps"))
    check("json.dumps() flagged external", c is not None and c.get("external") == "json", c)
    uc = calls(graph, "src/pkg/util.py")
    c = uc.get(("os", "getcwd"))
    check("os.getcwd() flagged external", c is not None and c.get("external") == "os", c)

    # ---------- 5. tests partition default off for Python
    check("tests/ not indexed for Python by default", not fns(graph, "tests/test_engine.py"))
    os.environ["SEMANTIC_INDEX_TESTS"] = "1"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g2 = build_graph(str(root))
        tf = fns(g2, "tests/test_engine.py")
        check("SEMANTIC_INDEX_TESTS=1 indexes tests/test_engine.py flagged is_test", tf and all(f.get("is_test") for f in tf), tf)
        srv.SERVER_STATE["graph"] = g2; srv.SERVER_STATE["repo_path"] = str(root)
        tests_for = srv.mcp_tests_for(target=f"FUNCTION:{E}:boot")
        check("mcp_tests_for(boot) names tests/test_engine.py::test_boot", any(t.get("file") == "tests/test_engine.py" for t in tests_for.get("tests", [])), tests_for)
        cf = {f["name"]: f for f in fns(g2, "tests/conftest.py")}
        check("@pytest.fixture def app() is flagged fixture", cf.get("app", {}).get("fixture") is True, cf.get("app"))
        c = calls(g2, "tests/test_fixture.py").get(("app", "start"))
        check("test_start(app): the fixture parameter is typed from the fixture's yield -> app.start() resolves to Engine.start",
              c is not None and c.get("resolved_class") == "Engine", c)
        tests_for = srv.mcp_tests_for(target=f"FUNCTION:{E}:Engine.start", hops=1)
        check("mcp_tests_for(Engine.start) names tests/test_fixture.py::test_start", any(t.get("function") == "test_start" for t in tests_for.get("tests", [])), tests_for)
        c = calls(g2, "tests/test_fixture.py").get(("eng", "tick"))
        check("@pytest.fixture(name='eng') injects under the override name -> eng.tick() resolves", c is not None and c.get("resolved_class") == "Engine", c)
        c = calls(g2, "tests/test_fixture.py").get(("gear", "spin"))
        check("a fixture defined as a method of the test class types the sibling test's parameter -> gear.spin() resolves to Gear.spin",
              c is not None and c.get("resolved_class") == "Gear", c)
    finally:
        os.environ.pop("SEMANTIC_INDEX_TESTS", None)

    # ---------- discovery tools work on Python graphs
    srv.SERVER_STATE["graph"] = graph; srv.SERVER_STATE["repo_path"] = str(root)
    r = srv.mcp_query_context(target=f"FUNCTION:{E}:Engine.tick")
    check("FUNCTION:file:Class.method query works for Python", "error" not in r and r.get("code_snippets"), r)
    r = srv.mcp_query_context(target="FUNCTION:spin")
    check("bare ambiguous FUNCTION:spin is an error listing candidates", "error" in r and "ambiguous" in r["error"].lower(), r)
    r = srv.mcp_query_context(target="FUNCTION:src/pkg/core/parts.py:spin")
    check("file-qualified bare name with two class owners still returns context (harness compatibility)",
          "error" not in r and len({s.get("function") for s in r.get("code_snippets", [])}) >= 1, r)
    nb = srv.mcp_neighbors(target=f"FUNCTION:{E}:boot")
    check("mcp_neighbors(boot) includes Engine.start (callee) and app.run (caller)",
          any(n["function"] == "start" for n in nb["neighbors"]) and any(n["file"] == "src/pkg/app.py" for n in nb["neighbors"]), nb)

    shutil.rmtree(root, ignore_errors=True)
    print()
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("ALL PY GRAPH QUALITY TESTS PASSED")


if __name__ == "__main__":
    main()
