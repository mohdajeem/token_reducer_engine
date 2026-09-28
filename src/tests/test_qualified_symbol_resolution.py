#!/usr/bin/env python3
"""
TEST: QUALIFIED SYMBOL RESOLUTION
Confirmed live: resolve_target_node discarded the class qualifier in a 2-part
FUNCTION:ClassName.method spec and matched purely by bare method name, so any repo
with the same method name in more than one class could silently return the wrong
function's blast-radius data (impact_analysis). Reproduces that exact collision
against a real, freshly-built graph.

Also confirmed live, and caught by strengthening this exact test rather than just
checking resolve_target_node's returned dict shape: execution_edges store ONLY bare
function names, so an early version of the fix that returned the qualified name in
target_node["function"] resolved to the right FILE but matched ZERO edges during the
actual traversal -- looked correct in isolation, did nothing in practice. These tests
run the real end-to-end impact walk (GraphTraversal + PolicyTraversalEngine), not just
resolve_target_node, specifically so that class of bug can't hide again.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from build_graph import build_graph
from main import resolve_target_node
from impact_engine import GraphTraversal, TraversalPolicy, PolicyTraversalEngine


def _build_fixture_graph(fixture_dir):
    return build_graph(str(fixture_dir))


def _downstream_functions(graph, target_node):
    """Runs the real impact walk and returns the set of downstream function names."""
    traversal = GraphTraversal(graph)
    engine = PolicyTraversalEngine(traversal)
    impact = engine.resolve_impact(target_node=target_node, policy=TraversalPolicy.DEFAULT, max_depth=None, direction="BOTH", include_types=None)
    return {edge["to"].get("function") for edge in impact.get("downstream", [])}


def test_cross_file_collision():
    """Same method name, two DIFFERENT files, each calling a DIFFERENT helper -- the
    original motivating case. Runs the real impact walk, not just resolve_target_node,
    so a fix that resolves the right file but the wrong edges can't pass silently."""
    tmp = Path(tempfile.mkdtemp(prefix="qualified_symbol_test_"))
    (tmp / "a.py").write_text(
        "class Alpha:\n"
        "    def shared_method(self):\n"
        "        return alpha_only_helper()\n"
        "\n"
        "def alpha_only_helper():\n"
        "    return 'ALPHA'\n",
        encoding="utf-8",
    )
    (tmp / "b.py").write_text(
        "class Beta:\n"
        "    def shared_method(self):\n"
        "        return beta_only_helper()\n"
        "\n"
        "def beta_only_helper():\n"
        "    return 'BETA'\n",
        encoding="utf-8",
    )
    graph = _build_fixture_graph(tmp)

    alpha_node = resolve_target_node(graph, "FUNCTION:Alpha.shared_method", repo_root=str(tmp))
    beta_node = resolve_target_node(graph, "FUNCTION:Beta.shared_method", repo_root=str(tmp))

    ok = True
    if not (alpha_node and alpha_node["file"].endswith("a.py")):
        print(f"  [FAIL] Alpha.shared_method resolved to {alpha_node}, expected a.py")
        ok = False
    if not (beta_node and beta_node["file"].endswith("b.py")):
        print(f"  [FAIL] Beta.shared_method resolved to {beta_node}, expected b.py")
        ok = False

    alpha_downstream = _downstream_functions(graph, alpha_node) if alpha_node else set()
    beta_downstream = _downstream_functions(graph, beta_node) if beta_node else set()

    if alpha_downstream != {"alpha_only_helper"}:
        print(f"  [FAIL] Alpha.shared_method's real impact walk found {alpha_downstream}, expected {{'alpha_only_helper'}}")
        ok = False
    if beta_downstream != {"beta_only_helper"}:
        print(f"  [FAIL] Beta.shared_method's real impact walk found {beta_downstream}, expected {{'beta_only_helper'}}")
        ok = False

    if ok:
        print("  [PASS] cross-file collision: each class's method resolves to its own file AND its own real impact edges")

    shutil.rmtree(tmp, ignore_errors=True)
    return ok


def test_same_file_collision():
    """Same method name, two classes in the SAME file (e.g. requests' auth.py with
    four __call__ methods -- the real case that originally motivated bypassing this
    engine for code lookups in the benchmarking harness). DOWNSTREAM is disambiguated
    via function_line (the specific occurrence's own definition line, carried through
    from resolve_target_node -> target_node -> node_equals); UPSTREAM remains a known,
    documented limitation (needs real type inference at call sites to know which
    occurrence a remote `some_obj.method()` call actually targets -- not attempted)."""
    tmp = Path(tempfile.mkdtemp(prefix="qualified_symbol_test_"))
    (tmp / "auth.py").write_text(
        "class Gamma:\n"
        "    def shared_method(self):\n"
        "        return gamma_only_helper()\n"
        "\n"
        "class Delta:\n"
        "    def shared_method(self):\n"
        "        return delta_only_helper()\n"
        "\n"
        "def gamma_only_helper():\n"
        "    return 'GAMMA'\n"
        "\n"
        "def delta_only_helper():\n"
        "    return 'DELTA'\n",
        encoding="utf-8",
    )
    graph = _build_fixture_graph(tmp)

    gamma_node = resolve_target_node(graph, "FUNCTION:Gamma.shared_method", repo_root=str(tmp))
    delta_node = resolve_target_node(graph, "FUNCTION:Delta.shared_method", repo_root=str(tmp))

    ok = True
    if not (gamma_node and gamma_node["file"].endswith("auth.py") and delta_node and delta_node["file"].endswith("auth.py")):
        print(f"  [FAIL] same-file case did not even resolve to the right file: gamma={gamma_node} delta={delta_node}")
        shutil.rmtree(tmp, ignore_errors=True)
        return False

    if gamma_node.get("function_line") == delta_node.get("function_line"):
        print(f"  [FAIL] gamma and delta resolved to the SAME function_line ({gamma_node.get('function_line')}) -- can't be, they're different methods")
        ok = False

    gamma_downstream = _downstream_functions(graph, gamma_node)
    delta_downstream = _downstream_functions(graph, delta_node)

    if gamma_downstream != {"gamma_only_helper"}:
        print(f"  [FAIL] Gamma.shared_method's downstream impact = {gamma_downstream}, expected {{'gamma_only_helper'}} only")
        ok = False
    if delta_downstream != {"delta_only_helper"}:
        print(f"  [FAIL] Delta.shared_method's downstream impact = {delta_downstream}, expected {{'delta_only_helper'}} only")
        ok = False

    if ok:
        print("  [PASS] same-file collision: DOWNSTREAM correctly disambiguated via function_line")
        print(f"         (Gamma at line {gamma_node.get('function_line')}, Delta at line {delta_node.get('function_line')})")
        print("  [INFO] UPSTREAM ('who calls this specific occurrence') remains a known,")
        print("         documented limitation -- needs real type inference at call sites")
        print("         to resolve a remote some_obj.shared_method() call to the right")
        print("         class. Not attempted; out of scope.")

    shutil.rmtree(tmp, ignore_errors=True)
    return ok


def test_unqualified_lookup_unaffected():
    """Regression check: a bare (unqualified) function name must behave exactly as
    before -- this fix must not change behavior for the common, unambiguous case."""
    tmp = Path(tempfile.mkdtemp(prefix="qualified_symbol_test_"))
    (tmp / "solo.py").write_text(
        "def standalone_function():\n"
        "    return 'STANDALONE_VALUE'\n",
        encoding="utf-8",
    )
    graph = _build_fixture_graph(tmp)

    node_with_root = resolve_target_node(graph, "FUNCTION:standalone_function", repo_root=str(tmp))
    node_without_root = resolve_target_node(graph, "FUNCTION:standalone_function")

    ok = (
        node_with_root and node_with_root["file"].endswith("solo.py")
        and node_without_root and node_without_root["file"].endswith("solo.py")
    )
    if ok:
        print("  [PASS] unqualified lookup unaffected, with and without repo_root")
    else:
        print(f"  [FAIL] unqualified lookup broke: with_root={node_with_root} without_root={node_without_root}")

    shutil.rmtree(tmp, ignore_errors=True)
    return bool(ok)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST: QUALIFIED SYMBOL RESOLUTION")
    print("=" * 80)

    results = []
    print("\n[1] Cross-file collision (same method name, different files) -- real impact walk")
    results.append(test_cross_file_collision())

    print("\n[2] Same-file collision (same method name, two classes, one file)")
    results.append(test_same_file_collision())

    print("\n[3] Unqualified lookup regression check")
    results.append(test_unqualified_lookup_unaffected())

    print("\n" + "=" * 80)
    passed = sum(1 for r in results if r)
    print(f"[RESULTS] {passed}/{len(results)} passed")
    print("=" * 80)

    sys.exit(0 if all(results) else 1)
