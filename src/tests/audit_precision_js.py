"""
Precision audit for JavaScript call resolution, against the TypeScript compiler (checkJs)
as an independent oracle -- see ts_resolve_oracle.js.

    python -m tests.audit_precision_js <repo_path> [--sample 300] [--seed 1] [--ts-module <path to node_modules/typescript>]

Same reading as the Python audit: a mismatch is a disagreement to read, not proof of a wrong
edge; tsc returns nothing for a lot of untyped JS, which is reported as "unknown".
"""
import argparse
import collections
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def is_test(rel):
    parts = rel.replace("\\", "/").split("/")
    return any(p in {"test", "tests", "__tests__", "spec"} for p in parts[:-1]) or ".test." in parts[-1] or ".spec." in parts[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--sample", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ts-module", default=os.environ.get("TS_MODULE", ""))
    args = ap.parse_args()
    from build_graph import build_graph

    repo = Path(args.repo).resolve()
    g = build_graph(str(repo))
    resolved = [(f, c) for f, calls in g["calls"].items() if not is_test(f)
                for c in calls if c.get("resolved_function") and c.get("call_id") and c.get("resolved_file")]
    random.seed(args.seed)
    sample = random.sample(resolved, min(args.sample, len(resolved)))
    reqs = []
    for f, c in sample:
        try:
            reqs.append({"file": f, "offset": int(c["call_id"].split(":")[-2]), "name": c["function"]})
        except Exception:
            pass
    tmp = Path(tempfile.mkdtemp()) / "req.json"
    tmp.write_text(json.dumps(reqs), encoding="utf-8")
    env = dict(os.environ)
    if args.ts_module:
        env["TS_MODULE"] = args.ts_module
    t0 = time.time()
    proc = subprocess.run(["node", str(Path(__file__).parent / "ts_resolve_oracle.js"), str(repo), str(tmp)],
                          capture_output=True, text=True, env=env, timeout=1800)
    if proc.returncode != 0:
        print("oracle failed:", proc.stderr[-2000:]); sys.exit(1)
    oracle = {(r["file"], r["offset"]): r for r in json.loads(proc.stdout)}
    secs = time.time() - t0

    agree = collections.Counter(); total = collections.Counter(); unknown = collections.Counter()
    disagreements = []
    for (f, c), req in zip(sample, reqs):
        kind = c.get("resolution") or "import"
        total[kind] += 1
        o = oracle.get((f, req["offset"]))
        decls = [d for d in (o or {}).get("decls", []) if not d["file"].startswith("..") and "node_modules" not in d["file"]]
        if not decls:
            unknown[kind] += 1
            continue
        ours_file = c["resolved_file"]
        ours_line = (c["resolved_function"] or {}).get("start_line")
        ok = any(d["file"] == ours_file and abs(d["line"] - (ours_line or 0)) <= 3 for d in decls) or \
             (any(d["file"] == ours_file for d in decls) and ours_line is None)
        if ok:
            agree[kind] += 1
        else:
            disagreements.append({"file": f, "call": f"{c.get('receiver') or ''}{'.' if c.get('receiver') else ''}{c['function']}",
                                  "kind": kind, "ours": (ours_file, ours_line), "tsc": [(d["file"], d["line"]) for d in decls[:3]]})
    print(f"repo={repo.name} resolved_calls={len(resolved)} sampled={len(sample)} tsc_secs={secs:.0f}")
    for kind in sorted(total):
        judged = total[kind] - unknown[kind]
        prec = 100 * agree[kind] / judged if judged else float("nan")
        print(f"  {kind:12} sampled={total[kind]:4} tsc_unknown={unknown[kind]:4} judged={judged:4} agree={agree[kind]:4} precision={prec:5.1f}%")
    judged = sum(total.values()) - sum(unknown.values())
    print(f"  {'ALL':12} judged={judged} precision={100*sum(agree.values())/max(1,judged):.1f}%")
    print("\nDISAGREEMENTS (first 25):")
    for d in disagreements[:25]:
        print(f"  {d['file']} {d['call']:34} [{d['kind']}] ours={d['ours']} tsc={d['tsc']}")
    Path(__file__).parent.joinpath(f"audit_precision_js_{repo.name}.json").write_text(
        json.dumps({"agree": agree, "total": total, "unknown": unknown, "disagreements": disagreements}, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
