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

  java-di-field   spring-petclinic: `private final OwnerRepository owners;` used as
                  `this.owners.findByLastName(..)` / bare `owners.save(..)`; the type is an interface.
  java-inheritance petclinic model chain `Pet extends NamedEntity extends BaseEntity`, and
                  `JpaOwnerRepository implements OwnerRepository` reached through the interface.

  java-fluent-chain `owner.getPet("Max").getType().getName()`, a builder chain, a local typed
                  from a call (`Owner found = owners.findById(1)`), `for (Pet pet : getPets())`.

  java-routes     @WebMvcTest drives controllers by URL: `mockMvc.perform(get("/owners/new"))`
                  -> the @GetMapping("/owners/new") handler (class @RequestMapping prefix, {vars}).

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


# --------------------------------------------------------------------------- doc-return-types
# matplotlib: `fig, ax = plt.subplots()` (tuple unpacking), pyplot wrappers `return gca().hist()`
# (a call-expression receiver), and types that exist only in numpydoc "Returns" sections
pattern("doc-return-types", {
    "pyproject.toml": "[project]\nname = 'pat'\n",
    "src/mpl/__init__.py": "",
    "src/mpl/axes.py": textwrap.dedent("""        class Axes:
            def plot(self, *args):
                return self._plot(args)

            def _plot(self, args):
                return args

            def hist(self, x):
                return self._hist(x)

            def _hist(self, x):
                return x

            def get_xlim(self) -> tuple:
                return (0, 1)


        class Axes3D:
            # same method names as Axes: nothing here may resolve by unique name
            def plot(self, *args):
                return self._plot3d(args)

            def _plot3d(self, args):
                return args

            def hist(self, x):
                return x

            def set_draggable(self, state):
                return state
        """),
    "src/mpl/figure.py": textwrap.dedent("""        from .axes import Axes


        class Figure:
            def add_subplot(self, *args):
                \"\"\"Add an Axes to the figure.

                Returns
                -------
                `~.axes.Axes`
                    The new Axes.
                \"\"\"
                return self._make(args)

            def _make(self, args):
                return args

            def subplots(self, nrows=1):
                \"\"\"Create subplots.

                Returns
                -------
                ax : `~.axes.Axes` or array of Axes
                \"\"\"
                return self.add_subplot()

            def legend(self, *args) -> "Legend":
                return Legend(self)


        class Legend:
            def __init__(self, parent):
                self.parent = parent

            def set_draggable(self, state):
                return self._draggable(state)

            def _draggable(self, state):
                return state
        """),
    "src/mpl/pyplot.py": textwrap.dedent("""        from .figure import Figure


        def figure():
            return Figure()


        def gca():
            return figure().add_subplot()


        def subplots(nrows=1):
            fig = figure()
            axs = fig.subplots(nrows)
            return fig, axs


        def hist(x):
            return gca().hist(x)


        def close(fig):
            return None
        """),
    "tests/test_axes.py": textwrap.dedent("""        from mpl import pyplot as plt


        def test_inverted_limits():
            fig, ax = plt.subplots()
            ax.plot([1, 2])
            ax.get_xlim()
            plt.close(fig)


        def test_hist_range_and_density():
            plt.hist([1, 2, 3])


        def test_subfigure_legend():
            fig = plt.figure()
            leg = fig.legend()
            leg.set_draggable(True)
        """),
}, [
    ("FUNCTION:src/mpl/axes.py:Axes._plot", "test_inverted_limits", 4),
    ("FUNCTION:src/mpl/axes.py:Axes._hist", "test_hist_range_and_density", 4),
    ("FUNCTION:src/mpl/figure.py:Legend._draggable", "test_subfigure_legend", 4),
])


# --------------------------------------------------------------------------- module-constants
# django: the gold patch changes a module-level regex / setting, not a function
# (utils/dateparse.py standard_duration_re, conf/global_settings.py FILE_UPLOAD_PERMISSIONS,
# core/validators.py); the tests reach it through the functions that READ the constant
pattern("module-constants", {
    "pyproject.toml": "[project]\nname = 'pat'\n",
    "src/dj/__init__.py": "",
    "src/dj/dateparse.py": textwrap.dedent("""        import re

        standard_duration_re = re.compile(r"^(?:(?P<days>-?\\d+) (days?, )?)?")
        iso8601_duration_re = re.compile(r"^P")


        def parse_duration(value):
            match = standard_duration_re.match(value) or iso8601_duration_re.match(value)
            return match


        def parse_date(value):
            return value
        """),
    "src/dj/global_settings.py": textwrap.dedent("""        FILE_UPLOAD_PERMISSIONS = None
        FILE_UPLOAD_DIRECTORY_PERMISSIONS = None
        """),
    "src/dj/storage.py": textwrap.dedent("""        from dj.global_settings import FILE_UPLOAD_PERMISSIONS


        class FileSystemStorage:
            def _save(self, name):
                return self.file_permissions_mode()

            def file_permissions_mode(self):
                return FILE_UPLOAD_PERMISSIONS
        """),
    "tests/test_dateparse.py": textwrap.dedent("""        from dj.dateparse import parse_duration, parse_date


        def test_negative():
            assert parse_duration("-1 days") is None or True


        def test_parse_date():
            assert parse_date("x")
        """),
    "tests/test_storage.py": textwrap.dedent("""        from dj.storage import FileSystemStorage


        def test_override_file_upload_permissions():
            FileSystemStorage()._save("f")
        """),
}, [
    ("FUNCTION:src/dj/dateparse.py:standard_duration_re", "test_negative", 4),
    ("FUNCTION:src/dj/global_settings.py:FILE_UPLOAD_PERMISSIONS", "test_override_file_upload_permissions", 4),
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


# --------------------------------------------------------------------------- java-di-field
# spring-petclinic OwnerController: the repository is a constructor-injected FIELD
# (`private final OwnerRepository owners;`) and every use is `this.owners.xxx(...)` or bare
# `owners.xxx(...)`; the field's declared type is an INTERFACE (Spring Data writes the impl).
# The test calls the controller method directly (WebMvc route tests are java-routes).
pattern("java-di-field", {
    "pom.xml": "<project><artifactId>pat</artifactId></project>\n",
    "src/main/java/pat/owner/OwnerRepository.java": textwrap.dedent("""\
        package pat.owner;

        import java.util.List;

        public interface OwnerRepository {

            List<Owner> findByLastName(String lastName);

            Owner save(Owner owner);

        }
        """),
    "src/main/java/pat/owner/Owner.java": textwrap.dedent("""\
        package pat.owner;

        public class Owner {

            private String lastName;

            public String getLastName() {
                return this.lastName;
            }

            public void setLastName(String lastName) {
                this.lastName = lastName;
            }

        }
        """),
    "src/main/java/pat/owner/OwnerController.java": textwrap.dedent("""\
        package pat.owner;

        import java.util.List;

        public class OwnerController {

            private final OwnerRepository owners;

            public OwnerController(OwnerRepository owners) {
                this.owners = owners;
            }

            public String processFindForm(Owner owner) {
                List<Owner> results = this.owners.findByLastName(owner.getLastName());
                if (results.isEmpty()) {
                    return "owners/findOwners";
                }
                return "owners/ownersList";
            }

            public String processCreationForm(Owner owner) {
                owners.save(owner);
                return "redirect:/owners/" + owner.getLastName();
            }

        }
        """),
    "src/test/java/pat/owner/OwnerControllerTests.java": textwrap.dedent("""\
        package pat.owner;

        import org.junit.jupiter.api.Test;

        class OwnerControllerTests {

            @Test
            void processFindFormSuccess() {
                OwnerController controller = new OwnerController(new InMemoryOwners());
                Owner owner = new Owner();
                owner.setLastName("Franklin");
                assertEquals("owners/ownersList", controller.processFindForm(owner));
            }

            @Test
            void processCreationFormSuccess() {
                OwnerController controller = new OwnerController(new InMemoryOwners());
                assertEquals("redirect:/owners/Franklin", controller.processCreationForm(new Owner()));
            }

        }
        """),
}, [
    ("FUNCTION:src/main/java/pat/owner/OwnerRepository.java:OwnerRepository.findByLastName", "processFindFormSuccess", 4),
    ("FUNCTION:src/main/java/pat/owner/OwnerRepository.java:OwnerRepository.save", "processCreationFormSuccess", 4),
    ("FUNCTION:src/main/java/pat/owner/Owner.java:Owner.getLastName", "processFindFormSuccess", 4),
])


# --------------------------------------------------------------------------- java-inheritance
# spring-petclinic model: `Owner extends Person extends NamedEntity extends BaseEntity` -- the
# test calls `owner.getId()` / `pet.setName()` on a subclass instance, the method lives three
# levels up; and `interface OwnerRepository` + `class JpaOwnerRepository implements
# OwnerRepository` -- a call through the interface must reach the implementation.
pattern("java-inheritance", {
    "pom.xml": "<project><artifactId>pat</artifactId></project>\n",
    "src/main/java/pat/model/BaseEntity.java": textwrap.dedent("""\
        package pat.model;

        public class BaseEntity {

            private Integer id;

            public Integer getId() {
                return id;
            }

            public boolean isNew() {
                return this.id == null;
            }

        }
        """),
    "src/main/java/pat/model/NamedEntity.java": textwrap.dedent("""\
        package pat.model;

        public class NamedEntity extends BaseEntity {

            private String name;

            public String getName() {
                return this.name;
            }

            public void setName(String name) {
                this.name = name;
            }

        }
        """),
    "src/main/java/pat/owner/Pet.java": textwrap.dedent("""\
        package pat.owner;

        import pat.model.NamedEntity;

        public class Pet extends NamedEntity {

            private String birthDate;

        }
        """),
    # same method names, unrelated class: a bare-name guess would point here too
    "src/main/java/pat/vet/Vet.java": textwrap.dedent("""\
        package pat.vet;

        public class Vet {

            private String name;

            public void setName(String name) {
                this.name = name.toUpperCase();
            }

            public boolean isNew() {
                return this.name == null;
            }

        }
        """),
    "src/main/java/pat/owner/OwnerRepository.java": textwrap.dedent("""\
        package pat.owner;

        public interface OwnerRepository {

            Pet findPet(String name);

        }
        """),
    "src/main/java/pat/owner/JpaOwnerRepository.java": textwrap.dedent("""\
        package pat.owner;

        import java.util.HashMap;
        import java.util.Map;

        public class JpaOwnerRepository implements OwnerRepository {

            private final Map<String, Pet> pets = new HashMap<>();

            @Override
            public Pet findPet(String name) {
                return pets.get(name);
            }

        }
        """),
    "src/main/java/pat/owner/InMemoryOwnerRepository.java": textwrap.dedent("""\
        package pat.owner;

        public class InMemoryOwnerRepository implements OwnerRepository {

            @Override
            public Pet findPet(String name) {
                Pet pet = new Pet();
                pet.setName(name);
                return pet;
            }

        }
        """),
    "src/main/java/pat/owner/PetService.java": textwrap.dedent("""\
        package pat.owner;

        public class PetService {

            private final OwnerRepository owners;

            public PetService(OwnerRepository owners) {
                this.owners = owners;
            }

            public String petName(String name) {
                Pet pet = owners.findPet(name);
                return pet.getName();
            }

        }
        """),
    "src/test/java/pat/owner/PetTests.java": textwrap.dedent("""\
        package pat.owner;

        import org.junit.jupiter.api.Test;

        class PetTests {

            @Test
            void petIsNewWithoutId() {
                Pet pet = new Pet();
                pet.setName("Max");
                assertTrue(pet.isNew());
            }

            @Test
            void serviceFindsPetByName() {
                PetService service = new PetService(new JpaOwnerRepository());
                assertEquals("Max", service.petName("Max"));
            }

        }
        """),
}, [
    ("FUNCTION:src/main/java/pat/model/NamedEntity.java:NamedEntity.setName", "petIsNewWithoutId", 4),
    ("FUNCTION:src/main/java/pat/model/BaseEntity.java:BaseEntity.isNew", "petIsNewWithoutId", 4),
    ("FUNCTION:src/main/java/pat/owner/JpaOwnerRepository.java:JpaOwnerRepository.findPet", "serviceFindsPetByName", 4),
    ("FUNCTION:src/main/java/pat/owner/InMemoryOwnerRepository.java:InMemoryOwnerRepository.findPet", "serviceFindsPetByName", 4),
])


# --------------------------------------------------------------------------- java-fluent-chain
# spring-petclinic: `owner.getPet("Max").getType().getName()` -- every hop is typed by the
# DECLARED return type of the previous call; `Visit.builder().description(d).build()` -- a
# builder whose setters return `this`; `Owner found = repo.findById(id)` -- a local typed
# from a call, not from `new`; `for (Pet pet : owner.getPets())`. Two classes share the
# method names (`Vet.getName`, `Vet.getType`) so a bare-name guess cannot pass this.
pattern("java-fluent-chain", {
    "pom.xml": "<project><artifactId>pat</artifactId></project>\n",
    "src/main/java/pat/model/NamedEntity.java": textwrap.dedent("""\
        package pat.model;

        public class NamedEntity {

            private String name;

            public String getName() {
                return this.name;
            }

            public void setName(String name) {
                this.name = name;
            }

        }
        """),
    "src/main/java/pat/owner/PetType.java": textwrap.dedent("""\
        package pat.owner;

        import pat.model.NamedEntity;

        public class PetType extends NamedEntity {

        }
        """),
    "src/main/java/pat/owner/Pet.java": textwrap.dedent("""\
        package pat.owner;

        import pat.model.NamedEntity;

        public class Pet extends NamedEntity {

            private PetType type;

            public PetType getType() {
                return this.type;
            }

            public void setType(PetType type) {
                this.type = type;
            }

        }
        """),
    "src/main/java/pat/owner/Owner.java": textwrap.dedent("""\
        package pat.owner;

        import java.util.ArrayList;
        import java.util.List;

        public class Owner {

            private final List<Pet> pets = new ArrayList<>();

            public List<Pet> getPets() {
                return this.pets;
            }

            public Pet getPet(String name) {
                for (Pet pet : getPets()) {
                    if (pet.getName().equals(name)) {
                        return pet;
                    }
                }
                return null;
            }

            public int petCount() {
                int n = 0;
                for (Pet pet : this.pets) {
                    if (pet.getType() != null) {
                        n++;
                    }
                }
                return n;
            }

        }
        """),
    "src/main/java/pat/owner/OwnerRepository.java": textwrap.dedent("""\
        package pat.owner;

        public interface OwnerRepository {

            Owner findById(int id);

        }
        """),
    "src/main/java/pat/owner/Visit.java": textwrap.dedent("""\
        package pat.owner;

        public class Visit {

            private String description;

            public static Builder builder() {
                return new Builder();
            }

            public String getDescription() {
                return this.description;
            }

            public static class Builder {

                private final Visit visit = new Visit();

                public Builder description(String description) {
                    visit.description = description;
                    return this;
                }

                public Visit build() {
                    return visit;
                }

            }

        }
        """),
    "src/main/java/pat/vet/Vet.java": textwrap.dedent("""\
        package pat.vet;

        public class Vet {

            public String getName() {
                return "vet";
            }

            public String getType() {
                return "vet";
            }

            public String getDescription() {
                return "vet";
            }

        }
        """),
    "src/test/java/pat/owner/OwnerTests.java": textwrap.dedent("""\
        package pat.owner;

        import org.junit.jupiter.api.Test;

        class OwnerTests {

            @Test
            void petTypeNameThroughChain() {
                Owner owner = new Owner();
                assertEquals("dog", owner.getPet("Max").getType().getName());
            }

            @Test
            void builderKeepsDescription() {
                Visit visit = Visit.builder().description("checkup").build();
                assertEquals("checkup", visit.getDescription());
            }

            @Test
            void foundOwnerCountsPets(OwnerRepository owners) {
                Owner found = owners.findById(1);
                assertEquals(1, found.petCount());
            }

        }
        """),
}, [
    ("FUNCTION:src/main/java/pat/owner/Pet.java:Pet.getType", "petTypeNameThroughChain", 2),
    ("FUNCTION:src/main/java/pat/model/NamedEntity.java:NamedEntity.getName", "petTypeNameThroughChain", 2),
    ("FUNCTION:src/main/java/pat/owner/Visit.java:Builder.description", "builderKeepsDescription", 2),
    ("FUNCTION:src/main/java/pat/owner/Visit.java:Builder.build", "builderKeepsDescription", 2),
    ("FUNCTION:src/main/java/pat/owner/Visit.java:Visit.getDescription", "builderKeepsDescription", 2),
    ("FUNCTION:src/main/java/pat/owner/Owner.java:Owner.petCount", "foundOwnerCountsPets", 2),
    ("FUNCTION:src/main/java/pat/owner/Pet.java:Pet.getType", "foundOwnerCountsPets", 3),
])


# --------------------------------------------------------------------------- java-routes
# spring-petclinic OwnerControllerTests / PetControllerTests: a @WebMvcTest never names the
# controller method -- it drives it by URL: `mockMvc.perform(get("/owners/new"))`,
# `post("/owners/new").param(..)`, `get("/owners/{ownerId}/pets/new", 1)`. The handler is
# found by its @GetMapping/@PostMapping path (class-level @RequestMapping prefix included).
pattern("java-routes", {
    "pom.xml": "<project><artifactId>pat</artifactId></project>\n",
    "src/main/java/pat/owner/OwnerController.java": textwrap.dedent("""\
        package pat.owner;

        import org.springframework.stereotype.Controller;
        import org.springframework.web.bind.annotation.GetMapping;
        import org.springframework.web.bind.annotation.PostMapping;

        @Controller
        class OwnerController {

            private static final String VIEWS_OWNER_CREATE_OR_UPDATE_FORM = "owners/createOrUpdateOwnerForm";

            @GetMapping("/owners/new")
            public String initCreationForm() {
                return VIEWS_OWNER_CREATE_OR_UPDATE_FORM;
            }

            @PostMapping("/owners/new")
            public String processCreationForm(Owner owner) {
                return "redirect:/owners/" + owner.getId();
            }

            @GetMapping("/owners/{ownerId}")
            public String showOwner(int ownerId) {
                return "owners/ownerDetails";
            }

            @GetMapping("/owners")
            public String processFindForm(Owner owner) {
                return "owners/ownersList";
            }

        }
        """),
    "src/main/java/pat/owner/PetController.java": textwrap.dedent("""\
        package pat.owner;

        import org.springframework.stereotype.Controller;
        import org.springframework.web.bind.annotation.GetMapping;
        import org.springframework.web.bind.annotation.PostMapping;
        import org.springframework.web.bind.annotation.RequestMapping;

        @Controller
        @RequestMapping("/owners/{ownerId}")
        class PetController {

            @GetMapping("/pets/new")
            public String initCreationForm(Owner owner) {
                return "pets/createOrUpdatePetForm";
            }

            @PostMapping("/pets/{petId}/edit")
            public String processUpdateForm(Owner owner, int petId) {
                return "redirect:/owners/" + owner.getId();
            }

        }
        """),
    "src/main/java/pat/owner/Owner.java": textwrap.dedent("""\
        package pat.owner;

        public class Owner {

            private Integer id;

            public Integer getId() {
                return id;
            }

        }
        """),
    "src/test/java/pat/owner/OwnerControllerTests.java": textwrap.dedent("""\
        package pat.owner;

        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
        import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
        import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;

        import org.junit.jupiter.api.Test;
        import org.springframework.beans.factory.annotation.Autowired;
        import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
        import org.springframework.test.web.servlet.MockMvc;

        @WebMvcTest(OwnerController.class)
        class OwnerControllerTests {

            @Autowired
            private MockMvc mockMvc;

            @Test
            void testInitCreationForm() throws Exception {
                mockMvc.perform(get("/owners/new")).andExpect(status().isOk())
                    .andExpect(view().name("owners/createOrUpdateOwnerForm"));
            }

            @Test
            void testProcessCreationFormSuccess() throws Exception {
                mockMvc.perform(post("/owners/new").param("firstName", "Joe").param("lastName", "Bloggs"))
                    .andExpect(status().is3xxRedirection());
            }

            @Test
            void testShowOwner() throws Exception {
                mockMvc.perform(get("/owners/{ownerId}", 1)).andExpect(status().isOk());
            }

            @Test
            void testProcessFindFormSuccess() throws Exception {
                mockMvc.perform(get("/owners?page=1")).andExpect(status().isOk());
            }

        }
        """),
    "src/test/java/pat/owner/PetControllerTests.java": textwrap.dedent("""\
        package pat.owner;

        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
        import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

        import org.junit.jupiter.api.Test;
        import org.springframework.beans.factory.annotation.Autowired;
        import org.springframework.test.web.servlet.MockMvc;

        class PetControllerTests {

            @Autowired
            private MockMvc mockMvc;

            @Test
            void testInitPetCreationForm() throws Exception {
                mockMvc.perform(get("/owners/1/pets/new")).andExpect(status().isOk());
            }

            @Test
            void testProcessPetUpdateFormSuccess() throws Exception {
                mockMvc.perform(post("/owners/1/pets/2/edit").param("name", "Betty"))
                    .andExpect(status().is3xxRedirection());
            }

        }
        """),
}, [
    ("FUNCTION:src/main/java/pat/owner/OwnerController.java:OwnerController.initCreationForm", "testInitCreationForm", 2),
    ("FUNCTION:src/main/java/pat/owner/OwnerController.java:OwnerController.processCreationForm", "testProcessCreationFormSuccess", 2),
    ("FUNCTION:src/main/java/pat/owner/OwnerController.java:OwnerController.showOwner", "testShowOwner", 2),
    ("FUNCTION:src/main/java/pat/owner/OwnerController.java:OwnerController.processFindForm", "testProcessFindFormSuccess", 2),
    ("FUNCTION:src/main/java/pat/owner/PetController.java:PetController.initCreationForm", "testInitPetCreationForm", 2),
    ("FUNCTION:src/main/java/pat/owner/PetController.java:PetController.processUpdateForm", "testProcessPetUpdateFormSuccess", 2),
    ("FUNCTION:src/main/java/pat/owner/Owner.java:Owner.getId", "testProcessCreationFormSuccess", 3),
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
