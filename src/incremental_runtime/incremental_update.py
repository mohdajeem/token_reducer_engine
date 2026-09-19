"""
Incremental graph update that produces the same graph a full rebuild would.

The previous incremental path started a fresh GraphBuilder (empty symbol table / function
index) on top of the cached graph, re-ran a subset of the passes for the changed file, and
saved. Measured on Chart.js after a one-line edit: the edited file kept 32 of its 68 resolved
calls and 14 of 36 cross-file edges, lost its string literals, and the whole thing took 4.2 s
against 5.2 s for a full build -- most of it writing 14.5 MB of indented JSON.

This module keeps (or restores) the builder that built the graph, so the re-parsed file
resolves cross-file exactly as in the original build:

  1. forget the file everywhere: graph sections, function index, symbol table, classes,
     re-exports, literals, edges it owns and edges into it
  2. re-index the file AND its dependents (files with calls that resolved into it) with
     build_graph.index_file -- the same code path as the full build
  3. ingest the matches through every per-match pass, then run the graph-wide passes once
  4. rebuild the symbol index and refresh the persisted builder state

Deleted files go through step 1 only. If there is no builder state to restore (a snapshot
older than this module), the caller must do a full rebuild -- a wrong graph is worse than a
slow one.
"""
import os

_FILE_SECTIONS = ("functions", "imports", "routes", "calls", "database", "errors", "contracts",
                  "parameters", "arguments", "classes", "reexports", "literals")
_DERIVED_LISTS = ("data_flow", "taint_sources", "security_sinks", "security_findings", "sanitizers")


def _norm(p):
    return os.path.normpath(str(p)).replace("\\", "/")


def forget_file(builder, graph, rel, drop_incoming=True):
    """Remove every trace of `rel`. drop_incoming=False keeps edges INTO the file: used for
    an unchanged dependent that is only re-ingested so its own calls re-resolve -- its
    definitions come back identical, so its callers' edges stay valid."""
    rel = _norm(rel)
    for section in _FILE_SECTIONS:
        sec = graph.get(section)
        if isinstance(sec, dict):
            sec.pop(rel, None)
    graph["execution_edges"] = [e for e in graph.get("execution_edges", [])
                                if e.get("from", {}).get("file") != rel
                                and (not drop_incoming or e.get("to", {}).get("file") != rel)]
    for key in ("variable_states", "returns"):
        if key in graph:
            graph[key] = [x for x in graph[key] if x.get("file") != rel]
    builder.function_index.forget_file(rel)
    builder.symbol_table.forget_file(rel)
    builder.param_candidates = {k: v for k, v in builder.param_candidates.items() if k[0] != rel}


def _definitions(graph, rel):
    """What other files can resolve against in `rel`: its functions (name, class, kind, lines,
    static, test flag), classes and re-exports. If this is unchanged after an edit, every
    call record and edge pointing into the file is still exact and its callers need no work."""
    def _sig(fn):
        return (fn.get("name"), fn.get("class"), fn.get("kind"), fn.get("start_line"), fn.get("end_line"),
                bool(fn.get("static")), bool(fn.get("is_test")))
    fns = sorted((_sig(x) for x in graph.get("functions", {}).get(rel, []) if isinstance(x, dict)), key=str)
    classes = graph.get("classes", {}).get(rel)
    reex = graph.get("reexports", {}).get(rel)
    return (fns, _stable(classes), _stable(reex))


def _stable(x):
    if isinstance(x, dict):
        return tuple(sorted((k, _stable(v)) for k, v in x.items()))
    if isinstance(x, (list, tuple, set)):
        return tuple(sorted((_stable(v) for v in x), key=str))
    return x


def _ingest(builder, graph, work, literals, reindexed):
    """ONE ingest for every re-indexed file: build() is multi-pass over its whole match list
    (definitions before calls), so ingesting file by file would resolve a call in file A
    before file B's definitions exist -- an ordering the full build never sees."""
    all_matches = []
    for rel, (matches, lits, defaults, fws) in work:
        builder.frameworks |= fws
        if lits:
            literals[rel] = lits
        for k, t in defaults.items():
            builder.option_defaults.setdefault(k, t)
        all_matches.extend(matches)
        reindexed.append(rel)
    if all_matches:
        builder.ingest(all_matches)


def apply_update(builder, graph, directory, changed_files):
    """Update `graph` in place for `changed_files` (relative paths; missing files = deleted).
    Returns a small report."""
    from build_graph import index_file, build_symbol_index, builder_state
    directory = os.path.abspath(directory)
    builder.graph = graph
    builder.project_root = directory
    builder.symbol_table.project_root = directory
    reindexed, deleted = [], []
    literals = graph.setdefault("literals", {})
    changed = set(_norm(r) for r in changed_files)

    # ---- phase 1: the changed files themselves. Edges INTO them are kept for now; they are
    # only stale if the file's definitions moved, which phase 2 decides.
    before = {rel: _definitions(graph, rel) for rel in changed}
    work = []
    for rel in sorted(changed):
        abs_path = os.path.join(directory, rel)
        if not os.path.isfile(abs_path):
            forget_file(builder, graph, rel, drop_incoming=True)
            deleted.append(rel)
            continue
        indexed = index_file(directory, rel)
        if indexed is None:
            forget_file(builder, graph, rel, drop_incoming=True)  # became unindexable (e.g. minified)
            continue
        work.append((rel, indexed))
    for rel, _ in work:
        forget_file(builder, graph, rel, drop_incoming=False)
    _ingest(builder, graph, work, literals, reindexed)

    # ---- phase 2: files whose definitions changed (renamed / moved / deleted symbols)
    # invalidate their callers. Those callers are re-ingested through the real handle_call
    # pipeline -- the only way to get byte-identical results. An edit that keeps every
    # definition where it was (the common case: a body change) skips this entirely.
    moved = {rel for rel in changed if _definitions(graph, rel) != before[rel]}
    dependents = set()
    if moved:
        for f, calls in graph.get("calls", {}).items():
            if f not in changed and any(c.get("resolved_file") in moved for c in calls):
                dependents.add(f)
        # a call record can be re-pointed by a later pass (name-unique) while the
        # import-resolved edge stays: edges are the authoritative dependency list
        for e in graph.get("execution_edges", []):
            if e.get("to", {}).get("file") in moved:
                f = e.get("from", {}).get("file")
                if f and f not in changed:
                    dependents.add(f)
        graph["execution_edges"] = [e for e in graph["execution_edges"] if e.get("to", {}).get("file") not in moved
                                    or e.get("from", {}).get("file") in changed]
        dep_work = []
        for rel in sorted(dependents):
            indexed = index_file(directory, rel)
            if indexed is not None:
                dep_work.append((rel, indexed))
        for rel, _ in dep_work:
            forget_file(builder, graph, rel, drop_incoming=False)  # unchanged: its own definitions come back identical
        _ingest(builder, graph, dep_work, literals, reindexed)

    # graph-wide passes are recomputed from scratch: they append, so clear their outputs first
    for key in _DERIVED_LISTS:
        graph[key] = []
    builder.finalize()
    build_symbol_index(graph)
    graph["frameworks"] = sorted(builder.frameworks)
    graph["_builder"] = builder_state(builder, directory)
    return {"reindexed": reindexed, "deleted": deleted, "moved": sorted(moved), "dependents": sorted(dependents)}
