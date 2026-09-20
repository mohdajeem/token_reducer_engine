#!/usr/bin/env python3
"""
Record the calls a pytest run actually makes, per test, as graph edges.

    python -m dynamic_trace.trace_pytest <repo_root> [pytest args ...] [--out FILE] [--key KEY]

Runs pytest IN-PROCESS with a plugin that installs a sys.setprofile recorder around every
test call. For each Python call event whose caller and callee frames both live inside the
repo (site-packages, the stdlib and pytest itself are skipped) it records

    {"from": {"file", "function", "class"}, "to": {"file", "function", "class"},
     "test": "<pytest nodeid>", "count": N}

with repo-relative file paths. Output (default `<repo>/.semantic_cache/<key>/trace.json`):

    {"version": 1, "recorded_at": ISO-8601 UTC, "repo": <abs path>, "python": ..., "pytest_args": [...],
     "tests": {"collected": n, "passed": n, "failed": n, "errors": n},
     "files": {rel: sha256, ...},        # every repo file that appeared in an edge, for staleness checks
     "edges": [ ... ]}

Pure standard library + pytest: copy this package into the SWE-bench eval image and run it
there, then ship trace.json back (see docs/dynamic_trace.md). The recorder costs roughly
2-4x on the test run; it never changes test outcomes.
"""
import argparse
import hashlib
import json
import os
import sys
import time


def _norm(p):
    return os.path.normpath(p).replace("\\", "/")


class Recorder:
    """sys.setprofile callback. One instance per session; `current_test` is set by the
    pytest plugin around each test call."""

    def __init__(self, repo_root, skip_dirs=(".semantic_cache", "site-packages", "dist-packages", "node_modules", ".venv", "venv", "__pycache__")):
        self.root = _norm(os.path.abspath(repo_root))
        self.prefix = self.root + "/"
        self.skip = tuple(f"/{d}/" for d in skip_dirs)
        self.current_test = None
        self.edges = {}       # (from_key, to_key, test) -> count
        self.files = set()
        self._rel_cache = {}

    def _rel(self, filename):
        r = self._rel_cache.get(filename)
        if r is not None:
            return r or None
        if not filename or filename.startswith("<"):
            self._rel_cache[filename] = ""
            return None
        f = _norm(filename)
        if not f.startswith(self.prefix) or any(s in f for s in self.skip):
            self._rel_cache[filename] = ""
            return None
        rel = f[len(self.prefix):]
        self._rel_cache[filename] = rel
        return rel

    @staticmethod
    def _class_of(frame):
        loc = frame.f_locals
        try:
            if "self" in loc:
                return type(loc["self"]).__name__
            if "cls" in loc and isinstance(loc["cls"], type):
                return loc["cls"].__name__
        except Exception:  # noqa: BLE001 - exotic __class__ / __getattr__ implementations
            return None
        return None

    def __call__(self, frame, event, arg):
        if event != "call":
            return
        to_file = self._rel(frame.f_code.co_filename)
        if not to_file:
            return
        caller = frame.f_back
        if caller is None:
            return
        from_file = self._rel(caller.f_code.co_filename)
        if not from_file:
            return
        to_name, from_name = frame.f_code.co_name, caller.f_code.co_name
        if to_name.startswith("<") or from_name.startswith("<"):
            return  # <module>, <lambda>, <listcomp>: not graph nodes
        key = ((from_file, from_name, self._class_of(caller)), (to_file, to_name, self._class_of(frame)), self.current_test)
        self.edges[key] = self.edges.get(key, 0) + 1
        self.files.add(from_file)
        self.files.add(to_file)

    def dump(self, out_path, pytest_args, stats):
        files = {}
        for rel in sorted(self.files):
            try:
                with open(os.path.join(self.root, rel), "rb") as fh:
                    files[rel] = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                continue
        edges = [{"from": {"file": a[0], "function": a[1], "class": a[2]},
                  "to": {"file": b[0], "function": b[1], "class": b[2]},
                  "test": t, "count": n}
                 for (a, b, t), n in sorted(self.edges.items(), key=lambda kv: (kv[0][2] or "", kv[0][0], kv[0][1]))]
        data = {"version": 1, "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "repo": self.root, "python": sys.version.split()[0], "pytest_args": list(pytest_args),
                "tests": stats, "files": files, "edges": edges}
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, separators=(",", ":"))
        os.replace(tmp, out_path)
        return data


class TracePlugin:
    """pytest plugin: profile only while a test body runs (setup/teardown of fixtures is
    attributed to the test too, since fixtures are how pytest tests reach the code)."""

    def __init__(self, recorder):
        self.rec = recorder
        self.stats = {"collected": 0, "passed": 0, "failed": 0, "errors": 0}

    def pytest_collection_finish(self, session):
        self.stats["collected"] = len(session.items)

    def pytest_runtest_protocol(self, item, nextitem):
        self.rec.current_test = item.nodeid
        sys.setprofile(self.rec)
        return None  # let pytest run the default protocol under the profiler

    def pytest_runtest_logfinish(self, nodeid, location):
        sys.setprofile(None)
        self.rec.current_test = None

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.passed:
                self.stats["passed"] += 1
            elif report.failed:
                self.stats["failed"] += 1
        elif report.failed:
            self.stats["errors"] += 1


def run(repo_root, pytest_args, out_path=None, key="trace"):
    import pytest  # imported late: the module must import without pytest for the merge side
    repo_root = os.path.abspath(repo_root)
    out_path = out_path or os.path.join(repo_root, ".semantic_cache", key, "trace.json")
    rec = Recorder(repo_root)
    plugin = TracePlugin(rec)
    cwd = os.getcwd()
    os.chdir(repo_root)
    try:
        args = list(pytest_args) or ["-q", "-p", "no:cacheprovider"]
        if "-p" not in args:
            args += ["-p", "no:cacheprovider"]
        code = pytest.main(args, plugins=[plugin])
    finally:
        sys.setprofile(None)
        os.chdir(cwd)
    data = rec.dump(out_path, pytest_args, plugin.stats)
    print(f"[dynamic_trace] pytest exit={code} tests={plugin.stats} edges={len(data['edges'])} files={len(data['files'])} -> {out_path}",
          file=sys.stderr)
    return out_path, data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo_root")
    ap.add_argument("--out", default=None, help="trace.json path (default <repo>/.semantic_cache/<key>/trace.json)")
    ap.add_argument("--key", default="trace", help="cache sub-directory the graph is built with (mcp_build_graph cache_subdir)")
    ns, rest = ap.parse_known_args(argv)
    run(ns.repo_root, rest, ns.out, ns.key)


if __name__ == "__main__":
    main()
