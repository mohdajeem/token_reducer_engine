#!/usr/bin/env python3
"""
JAVA GRAPH QUALITY -- the breaking points found by hand on spring-petclinic (14% of calls
resolved before), reproduced on a small fixture, one assertion group per defect:

  1. receivers: `this.owners.find(..)`, bare `owners.save(..)`, chained `a.b().c()`,
     `new X().m()`, implicit-this `getPets()` inside a class
  2. declared types: fields, locals (`Owner o = repo.find(1)`, generics, `var`), for-each,
     parameters, method return types
  3. `extends` / `implements` on the class entry; interface methods carry their class;
     interface -> implementation dispatch edges (confidence=dispatch, via=implementation)
  4. annotations: @Test marks a test, @GetMapping/@RequestMapping register Spring routes,
     `mockMvc.perform(get("/path"))` links the test to the handler (via=route)
  5. imports outside the project are external (no phantom `<dir>/Test.java`); JUnit/AssertJ
     static imports, java.lang names and library-typed receivers are labelled, not "unresolved"
  6. the build is silent on stdout

Run:  python tests/test_java_graph_quality.py
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
    "pom.xml": "<project><artifactId>fixture</artifactId></project>\n",
    "src/main/java/fx/model/BaseEntity.java": textwrap.dedent("""\
        package fx.model;

        public class BaseEntity {
            private Integer id;
            public Integer getId() { return id; }
            public boolean isNew() { return this.id == null; }
        }
        """),
    "src/main/java/fx/model/NamedEntity.java": textwrap.dedent("""\
        package fx.model;

        public class NamedEntity extends BaseEntity {
            private String name;
            public String getName() { return this.name; }
            public void setName(String name) { this.name = name; }
        }
        """),
    "src/main/java/fx/owner/Pet.java": textwrap.dedent("""\
        package fx.owner;

        import fx.model.NamedEntity;

        public class Pet extends NamedEntity {
            private PetType type;
            public PetType getType() { return this.type; }
        }
        """),
    "src/main/java/fx/owner/PetType.java": textwrap.dedent("""\
        package fx.owner;

        import fx.model.NamedEntity;

        public class PetType extends NamedEntity {
        }
        """),
    "src/main/java/fx/owner/Owner.java": textwrap.dedent("""\
        package fx.owner;

        import java.util.ArrayList;
        import java.util.List;

        public class Owner {
            private final List<Pet> pets = new ArrayList<>();
            public List<Pet> getPets() { return this.pets; }
            public Pet getPet(String name) {
                for (Pet pet : getPets()) {
                    if (pet.getName().equals(name)) { return pet; }
                }
                return null;
            }
            public int petCount() {
                var n = 0;
                for (Pet pet : this.pets) { if (pet.getType() != null) { n++; } }
                return n;
            }
        }
        """),
    "src/main/java/fx/owner/OwnerRepository.java": textwrap.dedent("""\
        package fx.owner;

        import java.util.List;

        public interface OwnerRepository {
            List<Owner> findByLastName(String lastName);
            Owner findById(int id);
        }
        """),
    "src/main/java/fx/owner/JpaOwnerRepository.java": textwrap.dedent("""\
        package fx.owner;

        import java.util.List;
        import java.util.Objects;

        public class JpaOwnerRepository implements OwnerRepository {
            @Override
            public List<Owner> findByLastName(String lastName) { return List.of(); }
            @Override
            public Owner findById(int id) { return Objects.requireNonNull(new Owner()); }
        }
        """),
    "src/main/java/fx/owner/OwnerController.java": textwrap.dedent("""\
        package fx.owner;

        import java.util.List;
        import org.springframework.stereotype.Controller;
        import org.springframework.web.bind.annotation.GetMapping;
        import org.springframework.web.bind.annotation.PostMapping;
        import org.springframework.web.bind.annotation.RequestMapping;

        @Controller
        @RequestMapping("/owners")
        public class OwnerController {
            private final OwnerRepository owners;
            public OwnerController(OwnerRepository owners) { this.owners = owners; }

            @GetMapping("/find")
            public String processFindForm(Owner owner) {
                List<Owner> results = this.owners.findByLastName(String.valueOf(owner.getPet("x").getType().getName()));
                if (results.isEmpty()) { return "owners/findOwners"; }
                return "owners/ownersList";
            }

            @PostMapping("/{ownerId}/edit")
            public String processUpdateForm(int ownerId) {
                Owner found = owners.findById(ownerId);
                var vet = new Vet();
                return "redirect:/owners/" + found.petCount() + vet.getName() + new Owner().petCount();
            }
        }
        """),
    "src/main/java/fx/owner/Vet.java": textwrap.dedent("""\
        package fx.owner;

        public class Vet {
            public String getName() { return "vet"; }
            public String getType() { return "vet"; }
        }
        """),
    "src/test/java/fx/owner/OwnerControllerTests.java": textwrap.dedent("""\
        package fx.owner;

        import static org.assertj.core.api.Assertions.*;
        import static org.junit.jupiter.api.Assertions.assertEquals;
        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
        import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

        import org.junit.jupiter.api.Test;
        import org.springframework.beans.factory.annotation.Autowired;
        import org.springframework.test.web.servlet.MockMvc;

        class OwnerControllerTests {
            @Autowired
            private MockMvc mockMvc;

            @Test
            void findForm() throws Exception {
                mockMvc.perform(get("/owners/find?lastName=x")).andExpect(status().isOk());
            }

            @Test
            void updateForm() throws Exception {
                mockMvc.perform(post("/owners/1/edit").param("name", "Betty")).andExpect(status().is3xxRedirection());
            }

            @Test
            void direct() {
                OwnerController c = new OwnerController(new JpaOwnerRepository());
                assertEquals("owners/findOwners", c.processFindForm(new Owner()));
                assertThat(c).isNotNull();
            }

            void helper() { }
        }
        """),
}

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {str(detail)[:300]}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def write_fixture(files):
    root = Path(tempfile.mkdtemp(prefix="javaq_"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    return root


def calls(graph, file, fn=None):
    return [c for c in graph["calls"].get(file, []) if fn is None or c.get("caller_function") == fn]


def call(graph, file, fn, name, recv=None):
    for c in calls(graph, file, fn):
        if c["function"] == name and (recv is None or c.get("receiver") == recv):
            return c
    return None


def resolved_to(c, file, name, cls=None):
    return bool(c) and c.get("resolved_file") == file and (c.get("resolved_function") or {}).get("name") == name \
        and (cls is None or (c.get("resolved_function") or {}).get("class") == cls)


def main():
    from api import mcp_server as srv
    os.environ["SEMANTIC_INDEX_TESTS"] = "1"
    root = write_fixture(FIXTURE)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        srv.mcp_build_graph(str(root), force_rebuild=True, cache_subdir="javaq")
    graph = srv.SERVER_STATE["graph"]
    noise = buf.getvalue()
    CTL = "src/main/java/fx/owner/OwnerController.java"
    OWN = "src/main/java/fx/owner/Owner.java"
    REPO = "src/main/java/fx/owner/OwnerRepository.java"
    JPA = "src/main/java/fx/owner/JpaOwnerRepository.java"
    TST = "src/test/java/fx/owner/OwnerControllerTests.java"

    # ---------- 6. silent build
    check("build prints nothing to stdout", "DEDUPLICATE" not in noise and "detect_taint" not in noise, noise[:200])

    # ---------- 1. receivers
    c = call(graph, CTL, "processFindForm", "findByLastName")
    check("this.owners.findByLastName(..) -> OwnerRepository.findByLastName (field declared type)",
          c and c.get("receiver") == "this.owners" and resolved_to(c, REPO, "findByLastName", "OwnerRepository"), c)
    c = call(graph, CTL, "processUpdateForm", "findById")
    check("bare owners.findById(..) (field without this.) -> OwnerRepository.findById", resolved_to(c, REPO, "findById"), c)
    c = call(graph, CTL, "processFindForm", "getType")
    check("chained owner.getPet(\"x\").getType() -> Pet.getType via getPet's declared return type",
          resolved_to(c, "src/main/java/fx/owner/Pet.java", "getType", "Pet"), c)
    c = call(graph, CTL, "processFindForm", "getName")
    check("...getType().getName() -> NamedEntity.getName (PetType extends NamedEntity), not Vet.getName",
          resolved_to(c, "src/main/java/fx/model/NamedEntity.java", "getName", "NamedEntity"), c)
    c = call(graph, CTL, "processUpdateForm", "petCount", recv="new Owner()")
    check("new Owner().petCount() -> Owner.petCount", resolved_to(c, OWN, "petCount", "Owner"), c)
    c = call(graph, OWN, "getPet", "getPets")
    check("implicit-this getPets() inside Owner -> Owner.getPets", resolved_to(c, OWN, "getPets", "Owner"), c)

    # ---------- 2. declared types
    c = call(graph, CTL, "processUpdateForm", "petCount", recv="found")
    check("Owner found = owners.findById(..) -> found.petCount() typed by the DECLARED local type", resolved_to(c, OWN, "petCount"), c)
    c = call(graph, CTL, "processUpdateForm", "getName", recv="vet")
    check("var vet = new Vet() -> vet.getName() -> Vet.getName (value types a `var`)",
          resolved_to(c, "src/main/java/fx/owner/Vet.java", "getName", "Vet"), c)
    c = call(graph, OWN, "petCount", "getType")
    check("for (Pet pet : this.pets) -> pet.getType() -> Pet.getType", resolved_to(c, "src/main/java/fx/owner/Pet.java", "getType"), c)
    c = call(graph, CTL, "processFindForm", "getPet")
    check("parameter `Owner owner` -> owner.getPet(..) -> Owner.getPet (typed, not name-unique)",
          resolved_to(c, OWN, "getPet") and c.get("resolution") == "typed", c)
    fns = {f["name"]: f for f in graph["functions"].get(OWN, []) if isinstance(f, dict)}
    check("Owner.getPet carries return_type=Pet; getPets carries List (raw type, not the type argument)",
          fns.get("getPet", {}).get("return_type") == "Pet" and fns.get("getPets", {}).get("return_type") == "List", fns)

    # ---------- 3. inheritance / interfaces
    cls = graph["classes"]
    check("Pet has superclass NamedEntity; NamedEntity has BaseEntity",
          cls.get("src/main/java/fx/owner/Pet.java", {}).get("Pet", {}).get("superclass") == "NamedEntity"
          and cls.get("src/main/java/fx/model/NamedEntity.java", {}).get("NamedEntity", {}).get("superclass") == "BaseEntity", cls)
    check("JpaOwnerRepository lists interfaces=[OwnerRepository]; OwnerRepository is flagged interface",
          cls.get(JPA, {}).get("JpaOwnerRepository", {}).get("interfaces") == ["OwnerRepository"]
          and cls.get(REPO, {}).get("OwnerRepository", {}).get("interface") is True, cls.get(JPA))
    check("interface methods carry class=OwnerRepository",
          all(f.get("class") == "OwnerRepository" for f in graph["functions"].get(REPO, []) if isinstance(f, dict) and f.get("kind") != "class"),
          graph["functions"].get(REPO))
    impl = [e for e in graph["execution_edges"] if e.get("via") == "implementation"]
    check("dispatch edges OwnerRepository.findById -> JpaOwnerRepository.findById (confidence=dispatch, via=implementation)",
          any(e["from"].get("class") == "OwnerRepository" and e["from"].get("function") == "findById" and e["to"].get("file") == JPA
              and e.get("confidence") == "dispatch" for e in impl), impl)
    r = srv.mcp_tests_for(target=f"FUNCTION:{JPA}:JpaOwnerRepository.findById", hops=4)
    check("mcp_tests_for(JpaOwnerRepository.findById) reaches updateForm through the interface + the route",
          any(t.get("function") == "updateForm" for t in r.get("tests", [])), r)

    # ---------- 4. annotations
    tfns = {f["name"]: f for f in graph["functions"].get(TST, []) if isinstance(f, dict)}
    check("@Test methods are is_test; the un-annotated helper in the same test file is too (test partition)",
          tfns.get("findForm", {}).get("is_test") and tfns.get("helper", {}).get("is_test"), tfns)
    check("@Test is recorded in the method's annotations", "Test" in (tfns.get("findForm", {}).get("annotations") or {}), tfns.get("findForm"))
    routes = graph.get("routes", {}).get(CTL, [])
    check("routes: GET /owners/find and POST /owners/{ownerId}/edit (class @RequestMapping prefix applied)",
          {(r["method"], r["path"]) for r in routes} == {("GET", "/owners/find"), ("POST", "/owners/{ownerId}/edit")}, routes)
    rt = [e for e in graph["execution_edges"] if e.get("via") == "route"]
    check("findForm -> processFindForm by URL (query string ignored), confidence=convention",
          any(e["from"].get("function") == "findForm" and e["to"].get("function") == "processFindForm" and e.get("confidence") == "convention" for e in rt), rt)
    check("updateForm -> processUpdateForm (POST /owners/1/edit matches {ownerId})",
          any(e["from"].get("function") == "updateForm" and e["to"].get("function") == "processUpdateForm" for e in rt), rt)
    check("no test -> handler edge for a method the test never requests",
          not any(e["from"].get("function") == "direct" for e in rt), rt)
    r = srv.mcp_tests_for(target=f"FUNCTION:{CTL}:OwnerController.processFindForm", hops=2)
    check("mcp_tests_for(processFindForm) names findForm (route) and direct (call)",
          {t.get("function") for t in r.get("tests", [])} >= {"findForm", "direct"}, r)

    # ---------- 5. externals
    imps = graph["imports"].get(TST, [])
    check("no import in the test file resolves to a phantom project file",
          all(i.get("file") is None for i in imps), [(i.get("source"), i.get("file")) for i in imps])
    c = call(graph, TST, "direct", "assertEquals")
    check("assertEquals (static import) external=org.junit", c and c.get("external") == "org.junit", c)
    c = call(graph, TST, "direct", "assertThat")
    check("assertThat (static star import) external=org.assertj", c and c.get("external") == "org.assertj", c)
    c = call(graph, TST, "findForm", "perform")
    check("mockMvc.perform(..) (field typed MockMvc from Spring) external=org.springframework",
          c and c.get("external") == "org.springframework", c)
    c = call(graph, CTL, "processFindForm", "isEmpty")
    check("results.isEmpty() (local typed List<Owner>) external=java.util", c and c.get("external") == "java.util", c)
    c = call(graph, CTL, "processFindForm", "valueOf")
    check("String.valueOf(..) external=java.lang", c and c.get("external") == "java.lang", c)
    c = call(graph, JPA, "findById", "requireNonNull")
    check("Objects.requireNonNull(..) external=java.util (imported)", c and c.get("external") == "java.util", c)
    unresolved = [(c.get("caller_function"), c.get("receiver"), c["function"]) for f in (CTL, OWN, JPA, TST)
                  for c in graph["calls"].get(f, []) if not c.get("resolved_function") and not c.get("external")]
    check("every call in the fixture is resolved or labelled external (only `.equals` on a String is left)",
          all(fn in ("equals",) for _, _, fn in unresolved), unresolved)
    c = call(graph, TST, "findForm", "isOk")
    check("status().isOk() -- a chain that starts at a static import -- external=org.springframework", c and c.get("external") == "org.springframework", c)
    c = call(graph, TST, "findForm", "andExpect")
    check("mockMvc.perform(..).andExpect(..) external=org.springframework", c and c.get("external") == "org.springframework", c)

    from incremental_runtime.snapshot_manager import SnapshotManager
    SnapshotManager(str(root / ".semantic_cache" / "javaq")).wait()
    shutil.rmtree(root, ignore_errors=True)
    os.environ.pop("SEMANTIC_INDEX_TESTS", None)
    print()
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("ALL JAVA GRAPH QUALITY TESTS PASSED")


if __name__ == "__main__":
    main()
