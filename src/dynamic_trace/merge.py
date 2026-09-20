"""
Fold a recorded trace.json into a built graph.

Every trace edge whose endpoints the graph knows becomes an execution edge with
source="trace", confidence="observed", the number of times it fired and the tests that
fired it. Static edges are never removed; when the static graph already has the same
edge it is annotated observed=True instead of duplicated. The graph records what was
merged in graph["_trace"] (recorded_at, counts, and which traced files changed since the
recording -- those edges are kept but flagged stale).
"""
import hashlib
import json
import os


def _norm(p):
    return os.path.normpath(str(p)).replace("\\", "/")


def load_trace(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def stale_files(trace, repo_root):
    """Traced files whose content changed since the recording (or disappeared)."""
    out = []
    for rel, digest in (trace.get("files") or {}).items():
        p = os.path.join(repo_root, rel)
        try:
            with open(p, "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() != digest:
                    out.append(rel)
        except OSError:
            out.append(rel)
    return sorted(out)


def _node_index(graph):
    """(file, name) -> set of classes defined for that name (None for module-level)."""
    idx = {}
    for f, fns in (graph.get("functions") or {}).items():
        for fn in fns:
            if isinstance(fn, dict) and fn.get("name"):
                idx.setdefault((f, fn["name"]), set()).add(fn.get("class"))
    return idx


def _edge_key(e):
    return (e["from"].get("file"), e["from"].get("function"), e["from"].get("class"),
            e["to"].get("file"), e["to"].get("function"), e["to"].get("class"))


def _known(idx, file, name, cls):
    classes = idx.get((file, name))
    if classes is None:
        return None, False
    if cls in classes:
        return cls, True
    if None in classes and cls is not None:
        # traced with a runtime class (e.g. a subclass instance) but defined module-level /
        # on a base class the graph names differently: keep the graph's node
        return None, True
    if len(classes) == 1:
        return next(iter(classes)), True
    return cls, False


def merge_trace(graph, trace, repo_root=None, max_tests_per_edge=5):
    """Add trace edges to graph in place. Returns the summary stored at graph["_trace"]."""
    idx = _node_index(graph)
    test_files = {f for f, fns in (graph.get("functions") or {}).items()
                  if any(isinstance(x, dict) and x.get("is_test") for x in fns)}
    existing = {}
    for e in graph.get("execution_edges", []):
        existing.setdefault(_edge_key(e), e)
    stale = set(stale_files(trace, repo_root)) if repo_root else set()
    added = annotated = skipped = 0
    merged = {}  # key -> new edge (aggregating tests/counts across per-test records)
    for te in trace.get("edges", []):
        a, b = te["from"], te["to"]
        fa, fb = _norm(a["file"]), _norm(b["file"])
        ca, ok_a = _known(idx, fa, a.get("function"), a.get("class"))
        cb, ok_b = _known(idx, fb, b.get("function"), b.get("class"))
        if not (ok_a and ok_b):
            skipped += 1
            continue
        key = (fa, a["function"], ca, fb, b["function"], cb)
        if key[:3] == key[3:]:
            continue  # recursion
        if key in existing:
            se = existing[key]
            if se.get("source") == "trace":
                # already merged (re-merge after an incremental update / a fresh recording):
                # idempotent, but the staleness verdict follows the CURRENT trace
                if fa in stale or fb in stale:
                    se["stale"] = True
                else:
                    se.pop("stale", None)
                continue
            if not se.get("observed"):
                se["observed"] = True
                annotated += 1
            se["observed_count"] = se.get("observed_count", 0) + int(te.get("count", 1))
            if te.get("test") and len(se.setdefault("observed_in", [])) < max_tests_per_edge and te["test"] not in se["observed_in"]:
                se["observed_in"].append(te["test"])
            continue
        e = merged.get(key)
        if e is None:
            e = {"from": {"type": "FUNCTION", "file": fa, "function": a["function"], **({"class": ca} if ca else {})},
                 "to": {"type": "FUNCTION", "file": fb, "function": b["function"], **({"class": cb} if cb else {})},
                 "type": "FUNCTION_CALL", "source": "trace", "confidence": "observed", "count": 0, "tests": []}
            if fa in test_files:
                e["is_test"] = True
            if fa in stale or fb in stale:
                e["stale"] = True
            merged[key] = e
            added += 1
        e["count"] = e.get("count", 0) + int(te.get("count", 1))
        if te.get("test") and te["test"] not in e["tests"] and len(e["tests"]) < max_tests_per_edge:
            e["tests"].append(te["test"])
    graph.setdefault("execution_edges", []).extend(merged.values())
    demoted = prune_fanout(graph)
    summary = {"recorded_at": trace.get("recorded_at"), "tests": trace.get("tests"),
               "edges_added": added, "static_edges_observed": annotated, "edges_skipped_unknown_node": skipped,
               "fanout_edges_demoted": demoted, "stale_files": sorted(stale)}
    graph["_trace"] = summary
    return summary


def prune_fanout(graph):
    """A dispatch-table / getattr call site links to every candidate (confidence dispatch
    or dynamic). When the trace saw that call site fire -- at least one candidate edge of
    the same call_id is observed -- the candidates it did NOT fire are demoted to
    confidence="unobserved" (the static guess is kept under static_confidence). A call
    site the trace never executed is left alone: no evidence, no demotion. Idempotent."""
    groups = {}
    for e in graph.get("execution_edges", []):
        if e.get("call_id") and (e.get("confidence") in ("dispatch", "dynamic", "candidates") or e.get("static_confidence")):
            groups.setdefault(e["call_id"], []).append(e)
    demoted = 0
    for cid, edges in groups.items():
        if not any(x.get("observed") for x in edges):
            continue
        for x in edges:
            if x.get("observed"):
                continue
            if x.get("confidence") != "unobserved":
                x["static_confidence"] = x.get("confidence")
                x["confidence"] = "unobserved"
                demoted += 1
    return demoted


def trace_path_for(cache_dir):
    return os.path.join(cache_dir, "trace.json")
