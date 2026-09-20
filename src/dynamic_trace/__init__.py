"""Dynamic call tracing: the second layer on top of the static graph.

`trace_pytest` runs a repo's pytest suite under a sys.setprofile recorder and writes the
observed caller -> callee edges (per test) to `.semantic_cache/<key>/trace.json`;
`merge` folds them into a built graph as edges with source="trace", confidence="observed".
Pure standard library plus pytest, so it runs unchanged inside the SWE-bench eval images.
"""
