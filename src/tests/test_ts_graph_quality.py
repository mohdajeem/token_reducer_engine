#!/usr/bin/env python3
"""
TYPESCRIPT GRAPH QUALITY -- the breaking points found by hand on nestjs/nest packages/core
(23% of calls resolved, 41% "unresolved" before), reproduced on a small fixture:

  1. ESM/NodeNext imports name the EMITTED file: `from './container.js'` -> container.ts
  2. constructor parameter properties (`constructor(private readonly container: Container)`)
     declare typed fields; class fields typed by annotation or by `= new X()`
  3. `interface` is a class node (flagged interface) whose method signatures carry the class;
     `class X implements Y` records interfaces (not a superclass); interface -> implementation
     dispatch edges; `implements` never masquerades as `extends`
  4. typed locals `let x: Injector;` / `const w: W = make()`, also when declared in an
     enclosing describe() callback and used inside it() (scope parents)
  5. JS globals (`Object.create`, `Promise.resolve`, `Reflect.getMetadata`) and test-runner
     globals (`vi.spyOn`, `expect(x).toBe`) are labelled builtin, not left unresolved;
     library-typed receivers (`this.logger.log` with logger: Logger from a package) too
  6. a method signature inside a type literal is not a function node

Run:  python tests/test_ts_graph_quality.py
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
    "package.json": '{"name": "fixture", "type": "module"}',
    "src/injector/instance-wrapper.ts": textwrap.dedent("""\
        export class InstanceWrapper {
          private readonly isTreeStatic: boolean = true;
          public isDependencyTreeStatic(): boolean { return this.isTreeStatic; }
        }
        """),
    "src/injector/container.ts": textwrap.dedent("""\
        import { InstanceWrapper } from './instance-wrapper.js';

        export interface Container {
          getModules(): Map<string, InstanceWrapper>;
        }

        export type Options = { getModules(): void; retries: number };

        export class NestContainer implements Container {
          private readonly modules = new Map<string, InstanceWrapper>();
          public getModules(): Map<string, InstanceWrapper> { return this.modules; }
        }

        export class TestingContainer extends NestContainer implements Container {
          public getModules(): Map<string, InstanceWrapper> { return new Map(); }
        }
        """),
    "src/injector/injector.ts": textwrap.dedent("""\
        import { Logger } from '@nestjs/common';
        import { Container } from './container.js';
        import { InstanceWrapper } from './instance-wrapper.js';

        export class Injector {
          private logger: Logger = new Logger('Injector');
          private readonly wrappers = new Map<string, InstanceWrapper>();
          private fallback = new InstanceWrapper();

          constructor(private readonly container: Container) {}

          public loadInstance(wrapper: InstanceWrapper): number {
            const modules = this.container.getModules();
            this.logger.log('loading');
            this.wrappers.set('x', wrapper);
            if (wrapper.isDependencyTreeStatic() && this.fallback.isDependencyTreeStatic()) {
              return modules.size;
            }
            return Promise.resolve(-1) ? -1 : 0;
          }
        }
        """),
    "src/legacy.ts": textwrap.dedent("""\
        export class Legacy {
          public getModules(): string[] { return []; }
          public isDependencyTreeStatic(): boolean { return false; }
          public loadInstance(wrapper: unknown): number { return 0; }
        }
        """),
    "test/injector/injector.spec.ts": textwrap.dedent("""\
        import { Injector } from '../../src/injector/injector.js';
        import { NestContainer } from '../../src/injector/container.js';
        import { InstanceWrapper } from '../../src/injector/instance-wrapper.js';

        function makeWrapper(): InstanceWrapper { return new InstanceWrapper(); }

        describe('Injector', () => {
          let injector: Injector;
          let container: NestContainer;

          beforeEach(() => {
            container = new NestContainer();
            injector = new Injector(container);
          });

          it('loads the instance', () => {
            const wrapper: InstanceWrapper = makeWrapper();
            vi.spyOn(container, 'getModules');
            expect(injector.loadInstance(wrapper)).toBe(0);
            expect(Object.create(null)).toBeDefined();
            Reflect.getMetadata('x', wrapper);
          });
        });
        """),
}

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {str(detail)[:300]}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def write_fixture(files):
    root = Path(tempfile.mkdtemp(prefix="tsq_"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    return root


def call(graph, file, fn, name, recv=None):
    for c in graph["calls"].get(file, []):
        if c.get("caller_function") == fn and c["function"] == name and (recv is None or c.get("receiver") == recv):
            return c
    return None


def resolved_to(c, file, name, cls=None):
    return bool(c) and c.get("resolved_file") == file and (c.get("resolved_function") or {}).get("name") == name \
        and (cls is None or (c.get("resolved_function") or {}).get("class") == cls)


def main():
    from api import mcp_server as srv
    os.environ["SEMANTIC_INDEX_TESTS"] = "1"
    root = write_fixture(FIXTURE)
    with contextlib.redirect_stdout(io.StringIO()):
        srv.mcp_build_graph(str(root), force_rebuild=True, cache_subdir="tsq")
    graph = srv.SERVER_STATE["graph"]
    INJ, CON, IW, TST = "src/injector/injector.ts", "src/injector/container.ts", "src/injector/instance-wrapper.ts", "test/injector/injector.spec.ts"

    # ---------- 1. .js -> .ts imports
    imps = {i.get("name"): i.get("file") for i in graph["imports"].get(TST, [])}
    check("import from '../../src/injector/injector.js' resolves to injector.ts", imps.get("Injector") == INJ, imps)
    c = call(graph, TST, "makeWrapper", "InstanceWrapper")
    check("new InstanceWrapper() through a .js import -> the class node in instance-wrapper.ts",
          c and c.get("resolved_file") == IW and (c.get("resolved_function") or {}).get("kind") == "class", c)

    # ---------- 2. parameter properties / class fields
    fields = (graph["classes"].get(INJ, {}).get("Injector") or {}).get("fields") or {}
    check("constructor(private readonly container: Container) declares field container: Container", fields.get("container") == "Container", fields)
    check("class fields typed: logger: Logger (annotation), wrappers = new Map() (value), fallback = new InstanceWrapper()",
          fields.get("logger") == "Logger" and fields.get("wrappers") == "Map" and fields.get("fallback") == "InstanceWrapper", fields)
    c = call(graph, INJ, "loadInstance", "getModules")
    check("this.container.getModules() -> Container.getModules (the interface method)", resolved_to(c, CON, "getModules", "Container"), c)
    c = call(graph, INJ, "loadInstance", "isDependencyTreeStatic", recv="this.fallback")
    check("this.fallback.isDependencyTreeStatic() -> InstanceWrapper (field typed by `new`)", resolved_to(c, IW, "isDependencyTreeStatic"), c)

    # ---------- 3. interfaces
    cls = graph["classes"].get(CON, {})
    check("Container is a class node flagged interface", cls.get("Container", {}).get("interface") is True, cls)
    check("NestContainer: interfaces=[Container], no superclass (implements is not extends)",
          cls.get("NestContainer", {}).get("interfaces") == ["Container"] and not cls.get("NestContainer", {}).get("superclass"), cls)
    check("TestingContainer extends NestContainer implements Container: both recorded",
          cls.get("TestingContainer", {}).get("superclass") == "NestContainer" and cls.get("TestingContainer", {}).get("interfaces") == ["Container"], cls)
    fns = [f for f in graph["functions"].get(CON, []) if isinstance(f, dict)]
    check("interface method signature getModules carries class=Container",
          any(f["name"] == "getModules" and f.get("class") == "Container" for f in fns), fns)
    check("the getModules signature inside `type Options = {...}` is NOT a function node",
          sum(1 for f in fns if f["name"] == "getModules") == 3, [(f["name"], f.get("class")) for f in fns])
    impl = [e for e in graph["execution_edges"] if e.get("via") == "implementation"]
    check("dispatch edges Container.getModules -> NestContainer.getModules and -> TestingContainer.getModules",
          {e["to"].get("class") for e in impl if e["from"].get("class") == "Container"} >= {"NestContainer", "TestingContainer"}, impl)

    # ---------- 4. typed locals + scope parents
    c = call(graph, TST, "loads the instance", "loadInstance")
    check("`let injector: Injector` declared in describe(), used in it() -> Injector.loadInstance (typed, not Legacy)",
          resolved_to(c, INJ, "loadInstance", "Injector") and c.get("resolution") == "typed", c)
    c = call(graph, TST, "loads the instance", "isDependencyTreeStatic")
    r = srv.mcp_tests_for(target=f"FUNCTION:{CON}:TestingContainer.getModules", hops=4)
    check("mcp_tests_for(TestingContainer.getModules) reaches 'loads the instance' via the interface dispatch",
          any(t.get("function") == "loads the instance" for t in r.get("tests", [])), r)

    # ---------- 5. globals / externals
    for fn_, name, recv in (("loads the instance", "spyOn", "vi"), ("loads the instance", "create", "Object"),
                            ("loads the instance", "getMetadata", "Reflect"), ("loadInstance", "resolve", "Promise")):
        f_ = TST if fn_ == "loads the instance" else INJ
        c = call(graph, f_, fn_, name, recv=recv)
        check(f"{recv}.{name}(..) labelled builtin", c and c.get("external") == "builtin", c)
    c = call(graph, TST, "loads the instance", "toBe")
    check("expect(..).toBe(..) (chain rooted at a builtin) labelled builtin", c and c.get("external") == "builtin", c)
    c = call(graph, INJ, "loadInstance", "log")
    check("this.logger.log(..) with logger: Logger from @nestjs/common -> external=@nestjs/common", c and c.get("external") == "@nestjs/common", c)
    c = call(graph, INJ, "loadInstance", "set")
    check("this.wrappers.set(..) (Map) labelled builtin", c and c.get("external") == "builtin", c)
    left = [(c.get("caller_function"), c.get("receiver"), c["function"]) for f in (INJ, CON, IW, TST)
            for c in graph["calls"].get(f, []) if not c.get("resolved_function") and not c.get("external")]
    check("every call in the fixture is resolved or labelled external", not left, left)

    from incremental_runtime.snapshot_manager import SnapshotManager
    SnapshotManager(str(root / ".semantic_cache" / "tsq")).wait()
    shutil.rmtree(root, ignore_errors=True)
    os.environ.pop("SEMANTIC_INDEX_TESTS", None)
    print()
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("ALL TS GRAPH QUALITY TESTS PASSED")


if __name__ == "__main__":
    main()
