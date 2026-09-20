# Dynamic trace layer

The static graph is a lower bound: a call the builder cannot resolve (dynamic dispatch,
`getattr` on computed names, fixtures it cannot type, decorators, plugin registries) is a
caller it cannot report. The dynamic trace layer records what a test run *actually* calls
and merges those edges on top of the static graph. Nothing static is removed; every
observed edge is labelled, and every answer says how much of it rests on the trace and
how fresh the trace is.

## What gets recorded

`src/dynamic_trace/trace_pytest.py` runs pytest in-process with a plugin that installs a
`sys.setprofile` recorder around each test. For every Python call whose caller and callee
frames both live inside the repo it records

```json
{"from": {"file": "requests/api.py", "function": "get", "class": null},
 "to":   {"file": "requests/sessions.py", "function": "request", "class": "Session"},
 "test": "test_requests.py::RequestsTestCase::test_HTTP_200_OK_GET",
 "count": 3}
```

Paths are repo-relative. Frames from site-packages, the stdlib, pytest and virtualenvs are
skipped, so are `<module>` / `<lambda>` / comprehension frames. The file also carries the
recording time, the interpreter, the pytest arguments, the test outcome counts and a
`files` map (`rel -> sha256`) of every file that appeared in an edge, which is what
staleness is checked against.

The recorder is pure standard library + pytest. It never changes test outcomes; expect a
2-4x slowdown of the test run.

## Recording inside a SWE-bench eval image

The images already contain the repo at `/testbed`, its test dependencies and pytest.
Copy the package in and run it:

```bash
docker cp src/dynamic_trace <container>:/tmp/dynamic_trace
docker exec -w /testbed <container> env PYTHONPATH=/tmp \
    python -m dynamic_trace.trace_pytest /testbed --key <cache_subdir> -q tests/    # or the F2P test files
docker cp <container>:/testbed/.semantic_cache/<cache_subdir>/trace.json ./traces/<instance_id>.json
```

- `--key` must match the `cache_subdir` the graph is built with (`mcp_build_graph(repo,
  cache_subdir=...)`); the default output is `<repo>/.semantic_cache/<key>/trace.json`,
  `--out` overrides it.
- Everything after the recorder's own options is passed to pytest. Restricting to the
  FAIL_TO_PASS test files keeps the run short; the whole suite gives the fullest graph.
- Record on the **unfixed** code with the test patch applied: failing tests still record
  every frame they executed before failing, which is exactly the path from the test to the
  code that must change.
- Repos that turn warnings into errors in their pytest ini: add
  `-o filterwarnings=ignore -W ignore` so tests reach the code under test.

Locally (no Docker) `swe_bench_js/experiments/record_traces_offline.py` does the same for
SWE-bench Verified instances with a venv that has the repo's test dependencies
(`--python .venv_trace/Scripts/python.exe`); it starts a local httpbin for requests.

## Shipping the trace back and merging

Put `trace.json` at `<repo>/.semantic_cache/<cache_subdir>/trace.json`. The next
`mcp_build_graph(repo, cache_subdir=...)` merges it:

- each trace edge whose endpoints exist in the graph becomes an execution edge with
  `source="trace"`, `confidence="observed"`, `count` and up to 5 `tests` that fired it
  (callers in the test partition get `is_test=True` like static test edges);
- a static edge the trace also saw is annotated `observed=True`, `observed_count`,
  `observed_in`, not duplicated;
- trace edges whose endpoints the graph does not know (e.g. a function defined by `exec`)
  are skipped and counted in `graph["_trace"]["edges_skipped_unknown_node"]`;
- the merge is idempotent: it re-runs after a full rebuild, after an incremental update
  (which drops the edges of a changed file) and whenever `trace.json` itself changes.

`graph["_trace"]` keeps `recorded_at`, the test counts, `edges_added`,
`static_edges_observed` and `stale_files`.

## Where it shows up

- `mcp_impact_analysis` / `mcp_tests_for` traverse observed edges like any other
  `FUNCTION_CALL`; each returned edge carries `source`, `observed`, `stale` when set.
- The `completeness` block of every impact answer has a `trace` entry:
  `{"recorded_at", "edges_from_trace", "stale", "stale_files", "warning"?}`.
  Observed edges are not counted as low-confidence.

## Staleness rules

- A trace is **stale for a file** when that file's sha256 differs from the one recorded
  (or the file is gone). Edges touching a stale file are kept but flagged `stale=True`
  and the completeness block warns: the code may no longer call what it called.
- Edges through unchanged files stay authoritative regardless of the trace's age.
- A trace recorded on a different base commit is not rejected; the per-file hashes decide
  what is stale. Re-record after the fix is applied if the agent's later turns need the
  edges of the changed files.
- Re-recording overwrites `trace.json`; the merge picks the new file up on the next
  `mcp_build_graph` call (mtime change).

## JavaScript (designed, not built)

Same shape, different recorder. Jest: a `setupFilesAfterEach` module that wraps
`beforeEach`/`afterEach` to start and stop `inspector` profiling (`Session.post
('Profiler.start')` with `--cpu-prof`-equivalent sampling is too coarse; use the
`Profiler.startPreciseCoverage` + `takePreciseCoverage` pair for function-level "was
called" bits per test, or `Profiler` sampling at a high rate for caller -> callee edges).
Emit the same `trace.json` (files relative to the repo, `test` = the Jest full title, which
is what the graph names test nodes by). Mocha/Karma repos (Chart.js, p5.js) need the hook
in a `--require` file instead. `merge.py` is language-agnostic.
