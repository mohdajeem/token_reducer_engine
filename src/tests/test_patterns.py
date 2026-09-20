#!/usr/bin/env python3
"""
PATTERN FIXTURES: one mini repo per code shape that made a real SWE-bench test unreachable,
copied (trimmed) from the repo that fooled us. Each fixture asks the one question that
matters -- "if I change X, does mcp_tests_for name test Y?" -- and prints a pass/fail table.
A pattern that passes here is also asserted in the permanent suites so it cannot regress.

  stored-method   astropy Table.__init__: `init_func = self._init_from_list` in an if/elif
                  chain, called later as `init_func(data)`; seaborn `plotter = _ScatterPlotter`
                  then `plotter(...)`; sklearn `for search in (GridSearchCV(), RandomizedSearchCV())`;
                  xarray `cls = staticmethod(IndexVariable)` then `self.cls()`.
  dunder-call     sphinx `for msg in catalog` -> Catalog.__iter__; requests `auth(r)` ->
                  HTTPDigestAuth.__call__; `catalog[0]` -> __getitem__; `with Session() as s`
                  -> __enter__.

Run:  python tests/test_patterns.py [pattern ...]
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

PATTERNS = {}


def pattern(name, files, expectations):
    """expectations: list of (target spec, test function name that must be reached, hops)."""
    PATTERNS[name] = (files, expectations)


# --------------------------------------------------------------------------- stored-method
pattern("stored-method", {
    "pyproject.toml": "[project]\nname = 'pat'\n",
    "src/pat/__init__.py": "",
    # astropy/table/table.py, Table.__init__ (trimmed)
    "src/pat/table.py": textwrap.dedent("""\
        class Table:
            def __init__(self, data=None, kind="list"):
                if kind == "list":
                    init_func = self._init_from_list
                elif kind == "dict":
                    init_func = self._init_from_dict
                else:
                    init_func = self._init_from_ndarray
                init_func(data)

            def _init_from_list(self, data):
                self._convert_data_to_col(data)

            def _init_from_dict(self, data):
                self._convert_data_to_col(list(data.values()))

            def _init_from_ndarray(self, data):
                return data

            def _convert_data_to_col(self, data):
                return list(data)
        """),
    # seaborn/relational.py relplot (trimmed): a class held in a variable, chosen by kind
    "src/pat/relational.py": textwrap.dedent("""\
        class _ScatterPlotter:
            def __init__(self, data):
                self.data = data

            def add_legend_data(self, ax):
                return locator_to_legend_entries(ax)


        class _LinePlotter:
            def __init__(self, data):
                self.data = data

            def add_legend_data(self, ax):
                return locator_to_legend_entries(ax)


        def locator_to_legend_entries(ax):
            return [ax]


        def relplot(data, kind="scatter"):
            if kind == "scatter":
                plotter = _ScatterPlotter
            else:
                plotter = _LinePlotter
            p = plotter(data)
            p.add_legend_data(1)
            return p
        """),
    # sklearn/model_selection/tests/test_search.py (trimmed): loop over instances
    "src/pat/search.py": textwrap.dedent("""\
        class BaseSearchCV:
            def fit(self, X):
                return self._run_search(X)

            def _run_search(self, X):
                return X


        class GridSearchCV(BaseSearchCV):
            pass


        class RandomizedSearchCV(BaseSearchCV):
            pass
        """),
    # xarray/tests/test_variable.py (trimmed): a class stored on the test class
    "src/pat/variable.py": textwrap.dedent("""\
        class Variable:
            def copy(self):
                return self._replace()

            def _replace(self):
                return Variable()


        class IndexVariable(Variable):
            pass
        """),
    "tests/test_table.py": textwrap.dedent("""\
        from pat.table import Table


        def test_structured_masked_column():
            t = Table([1, 2])
            assert t
        """),
    "tests/test_relational.py": textwrap.dedent("""\
        from pat.relational import relplot


        def test_legend_has_no_offset():
            assert relplot({"x": 1})
        """),
    "tests/test_search.py": textwrap.dedent("""\
        from pat.search import GridSearchCV, RandomizedSearchCV


        def test_search_cv_timing():
            for search in (GridSearchCV(), RandomizedSearchCV()):
                search.fit([1])
        """),
    "tests/test_variable.py": textwrap.dedent("""\
        from pat.variable import IndexVariable


        class TestIndexVariable:
            cls = staticmethod(IndexVariable)

            def test_copy(self):
                v = self.cls()
                v.copy()
        """),
}, [
    ("FUNCTION:src/pat/table.py:Table._convert_data_to_col", "test_structured_masked_column", 4),
    ("FUNCTION:src/pat/relational.py:locator_to_legend_entries", "test_legend_has_no_offset", 4),
    ("FUNCTION:src/pat/search.py:BaseSearchCV._run_search", "test_search_cv_timing", 4),
    ("FUNCTION:src/pat/variable.py:Variable._replace", "test_copy", 4),
])


# --------------------------------------------------------------------------- dunder-call
pattern("dunder-call", {
    "pyproject.toml": "[project]\nname = 'pat'\n",
    "src/pat/__init__.py": "",
    # sphinx/builders/gettext.py Catalog (trimmed)
    "src/pat/gettext.py": textwrap.dedent("""\
        class Catalog:
            def __init__(self):
                self.messages = []
                self.metadata = {}

            def add(self, msg, origin):
                if msg not in self.metadata:
                    self.messages.append(msg)
                    self.metadata[msg] = []
                self.metadata[msg].append(origin)

            def __iter__(self):
                for message in self.messages:
                    yield self._entry(message)

            def __getitem__(self, i):
                return self._entry(self.messages[i])

            def __len__(self):
                return self._count()

            def _entry(self, message):
                return (message, self.metadata[message])

            def _count(self):
                return len(self.messages)
        """),
    # requests/auth.py HTTPDigestAuth (trimmed): the auth object is CALLED
    "src/pat/auth.py": textwrap.dedent("""\
        class HTTPDigestAuth:
            def __init__(self, username, password):
                self.username = username
                self.password = password

            def build_digest_header(self, method, url):
                return "Digest " + self.username

            def __call__(self, r):
                r.headers["Authorization"] = self.build_digest_header(r.method, r.url)
                return r


        class Session:
            def __enter__(self):
                return self._open()

            def __exit__(self, *a):
                return self._close()

            def _open(self):
                return self

            def _close(self):
                return None
        """),
    "tests/test_gettext.py": textwrap.dedent("""\
        from pat.gettext import Catalog


        def test_Catalog_duplicated_message():
            catalog = Catalog()
            catalog.add("hello", ("origin", 1))
            assert len(catalog) == 1
            for msg, origins in catalog:
                assert msg == "hello"
            assert catalog[0]
        """),
    "tests/test_auth.py": textwrap.dedent("""\
        from pat.auth import HTTPDigestAuth, Session


        class Req:
            method = "GET"
            url = "/"
            headers = {}


        def test_DIGESTAUTH_QUOTES_QOP_VALUE():
            auth = HTTPDigestAuth("user", "pass")
            r = auth(Req())
            assert r.headers["Authorization"]


        def test_session_context():
            with Session() as s:
                assert s
        """),
}, [
    ("FUNCTION:src/pat/gettext.py:Catalog.__iter__", "test_Catalog_duplicated_message", 2),
    ("FUNCTION:src/pat/gettext.py:Catalog._entry", "test_Catalog_duplicated_message", 3),
    ("FUNCTION:src/pat/gettext.py:Catalog._count", "test_Catalog_duplicated_message", 3),
    ("FUNCTION:src/pat/auth.py:HTTPDigestAuth.build_digest_header", "test_DIGESTAUTH_QUOTES_QOP_VALUE", 3),
    ("FUNCTION:src/pat/auth.py:Session._open", "test_session_context", 3),
])


# --------------------------------------------------------------------------- js-generated-titles
# markedjs/marked test/specs/marked/marked-spec.js: tests are generated from a JSON spec in a
# loop, titled with a template string; the failing id is "Marked Table cells should pass example 9"
pattern("js-generated-titles", {
    "package.json": '{"name": "pat"}',
    "src/marked.js": textwrap.dedent("""        import { Lexer } from './lexer';
        export function marked(src) {
          const tokens = Lexer.lex(src);
          return tokens.join('');
        }
        """),
    "src/lexer.js": textwrap.dedent("""        export class Lexer {
          static lex(src) {
            const lexer = new Lexer();
            return lexer.token(src);
          }
          token(src) {
            return src.split('|');
          }
        }
        """),
    "test/specs/marked-spec.js": textwrap.dedent("""        import { marked } from '../../src/marked';
        const spec = [{ example: 5, markdown: 'a|b' }, { example: 9, markdown: 'c' }];
        describe('Marked Table cells', () => {
          spec.forEach((example) => {
            it(`should pass example ${example.example}`, () => {
              expect(marked(example.markdown)).toBeTruthy();
            });
          });
        });
        """),
}, [
    ("FUNCTION:src/lexer.js:Lexer.token", "should pass example ${example.example}", 4),
])


# --------------------------------------------------------------------------- js-shared-fixture-var
# processing/p5.js test/unit/*.js: the object under test is created in beforeEach and used in
# every `it`; the variable lives in the describe callback, not in the test function
pattern("js-shared-fixture-var", {
    "package.json": '{"name": "pat"}',
    "src/p5.js": textwrap.dedent("""        export class p5 {
          constructor(sketch) { this.sketch = sketch; }
          loadStrings(path) { return this._load(path); }
          _load(path) { return [path]; }
          remove() { return null; }
        }
        """),
    "test/unit/io/files_input.js": textwrap.dedent("""        import { p5 } from '../../../src/p5';
        describe('Files', () => {
          let myp5;
          beforeEach(() => {
            myp5 = new p5(() => {});
          });
          afterEach(() => {
            myp5.remove();
          });
          describe('p5.prototype.loadStrings', () => {
            it('should include empty strings', () => {
              const strings = myp5.loadStrings('empty_lines.txt');
              expect(strings.length).toBe(1);
            });
          });
        });
        """),
}, [
    ("FUNCTION:src/p5.js:p5._load", "should include empty strings", 4),
])


# --------------------------------------------------------------------------- js-custom-matcher
# markedjs/marked test/specs/run-spec.js + test/helpers/helpers.js (2020+): the runner is
# chosen at runtime `(spec.only ? fit : it)('should ' + passFail + example, ...)`, and the
# code under test runs inside a jasmine matcher `expectAsync(spec).toRender(html)` whose
# `compare` closure is registered with addAsyncMatchers
pattern("js-custom-matcher", {
    "package.json": '{"name": "pat"}',
    "src/marked.js": textwrap.dedent("""        import { Lexer } from './lexer';
        export function marked(src, opt) {
          return Lexer.lex(src).join('');
        }
        """),
    "src/lexer.js": textwrap.dedent("""        export class Lexer {
          static lex(src) {
            return new Lexer().inlineTokens(src);
          }
          inlineTokens(src) {
            return src.split('~');
          }
        }
        """),
    "test/helpers/helpers.js": textwrap.dedent("""        const marked = require('../../src/marked.js');
        beforeEach(() => {
          jasmine.addAsyncMatchers({
            toRender: () => {
              return {
                compare: async (spec, expected) => {
                  const actual = marked(spec.markdown, spec.options);
                  return { pass: actual === expected };
                }
              };
            }
          });
        });
        """),
    "test/specs/run-spec.js": textwrap.dedent("""        const specs = [{ example: 3, markdown: 'a~b', html: 'ab' }];
        describe('New', () => {
          specs.forEach((spec) => {
            const example = (spec.example ? ' example ' + spec.example : '');
            const passFail = (spec.shouldFail ? 'fail' : 'pass');
            (spec.only ? fit : (spec.skip ? xit : it))('should ' + passFail + example, async () => {
              await expectAsync(spec).toRender(spec.html);
            });
          });
        });
        """),
}, [
    ("FUNCTION:src/lexer.js:Lexer.inlineTokens", "should ${passFail}${example}", 6),
])


def write(files):
    root = Path(tempfile.mkdtemp(prefix="pattern_"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    return root


def main(argv):
    from api import mcp_server as srv
    wanted = argv or list(PATTERNS)
    os.environ["SEMANTIC_INDEX_TESTS"] = "1"
    fails = []
    print(f"{'pattern':16} {'target':58} {'test':36} result")
    for name in wanted:
        files, expectations = PATTERNS[name]
        root = write(files)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                srv.mcp_build_graph(str(root), force_rebuild=True, cache_subdir="pat")
            for target, test_fn, hops in expectations:
                res = srv.mcp_tests_for(target=target, hops=hops)
                ok = any(t.get("function") == test_fn for t in res.get("tests", []))
                if not ok:
                    fails.append((name, target, test_fn))
                print(f"{name:16} {target[9:]:58} {test_fn:36} {'PASS' if ok else 'FAIL' + ('  (' + res['error'] + ')' if 'error' in res else '')}")
        finally:
            from incremental_runtime.snapshot_manager import SnapshotManager
            SnapshotManager(str(root / ".semantic_cache" / "pat")).wait()  # background writer
            shutil.rmtree(root, ignore_errors=True)
    os.environ.pop("SEMANTIC_INDEX_TESTS", None)
    print()
    if fails:
        print(f"{len(fails)} FAILED")
        sys.exit(1)
    print("ALL PATTERN FIXTURES PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
