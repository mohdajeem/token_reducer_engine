"""
Precision audit for Python call resolution, against jedi as an independent oracle.

For a random sample of RESOLVED call sites in production code, ask jedi where the called
name is defined (goto on the callee at the call's position) and compare with the graph's
resolved (file, name). Reports precision overall and per resolution kind
(import / typed / name-unique / candidates), plus the disagreements so they can be read.

    python -m tests.audit_precision_py <repo_path> [--sample 300] [--seed 1]

Caveats: jedi is itself an approximation (it may return nothing, or a stub); a mismatch is
"disagreement", not proof of a wrong edge -- the listed cases are for a human to read.
"""
import argparse
import collections
import json
import os
import random
import re
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def is_test(rel):
    parts = rel.replace("\\", "/").split("/")
    return any(p in {"test", "tests", "testing"} for p in parts[:-1]) or parts[-1].startswith("test_") or parts[-1] == "conftest.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--sample", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    import jedi
    from build_graph import build_graph

    repo = Path(args.repo).resolve()
    g = build_graph(str(repo))
    resolved = []
    for f, calls in g["calls"].items():
        if not f.endswith(".py") or is_test(f):
            continue
        for c in calls:
            if c.get("resolved_function") and c.get("call_id"):
                resolved.append((f, c))
    random.seed(args.seed)
    sample = random.sample(resolved, min(args.sample, len(resolved)))
    project = jedi.Project(path=str(repo), added_sys_path=[str(repo / "src")] if (repo / "src").is_dir() else [])

    agree = collections.Counter(); total = collections.Counter(); unknown = collections.Counter()
    disagreements = []
    t0 = time.time()
    file_cache = {}
    for f, c in sample:
        kind = c.get("resolution") or "import"
        total[kind] += 1
        try:
            start = int(c["call_id"].split(":")[-2])
        except Exception:
            unknown[kind] += 1
            continue
        src = file_cache.get(f)
        if src is None:
            src = (repo / f).read_text(encoding="utf-8", errors="ignore")
            file_cache[f] = src
        # position of the callee name: the call's byte start -> line/col of the LAST segment
        head = src[:start]
        line = head.count("\n") + 1
        col = len(head.split("\n")[-1])
        callee_text = src[start:start + 200].split("(")[0]
        name_off = callee_text.rfind(c["function"])
        if name_off < 0:
            unknown[kind] += 1
            continue
        col += name_off + 1
        try:
            script = jedi.Script(code=src, path=str(repo / f), project=project)
            defs = script.goto(line, col, follow_imports=True, follow_builtin_imports=False)
        except Exception:
            unknown[kind] += 1
            continue
        defs = [d for d in defs if d.module_path]
        if not defs:
            unknown[kind] += 1
            continue
        jedi_files = {os.path.relpath(str(d.module_path), repo).replace("\\", "/") for d in defs}
        jedi_lines = {(os.path.relpath(str(d.module_path), repo).replace("\\", "/"), d.line) for d in defs}
        ours = (c["resolved_file"], (c["resolved_function"] or {}).get("start_line"))
        ok = ours in jedi_lines or (c["resolved_file"] in jedi_files and any(abs((ln or 0) - (ours[1] or 0)) <= 3 for _, ln in jedi_lines))
        if ok:
            agree[kind] += 1
        else:
            disagreements.append({"file": f, "line": line, "call": f"{c.get('receiver') or ''}{'.' if c.get('receiver') else ''}{c['function']}",
                                  "kind": kind, "ours": ours, "jedi": sorted(jedi_lines)[:3]})
    secs = time.time() - t0
    print(f"repo={repo.name} resolved_calls={len(resolved)} sampled={len(sample)} jedi_secs={secs:.0f}")
    for kind in sorted(total):
        judged = total[kind] - unknown[kind]
        prec = 100 * agree[kind] / judged if judged else float("nan")
        print(f"  {kind:12} sampled={total[kind]:4} jedi_unknown={unknown[kind]:4} judged={judged:4} agree={agree[kind]:4} precision={prec:5.1f}%")
    judged = sum(total.values()) - sum(unknown.values())
    print(f"  {'ALL':12} judged={judged} precision={100*sum(agree.values())/max(1,judged):.1f}%")
    print("\nDISAGREEMENTS (first 25):")
    for d in disagreements[:25]:
        print(f"  {d['file']}:{d['line']} {d['call']:30} [{d['kind']}] ours={d['ours']} jedi={d['jedi']}")
    out = Path(__file__).parent / f"audit_precision_py_{repo.name}.json"
    out.write_text(json.dumps({"agree": agree, "total": total, "unknown": unknown, "disagreements": disagreements}, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
