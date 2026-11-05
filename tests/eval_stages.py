#!/usr/bin/env python3
"""Eval results by stage, so a fix shows where it helped, not only that the total moved.

Usage:
  python3 tests/eval_stages.py result.json [more.json ...] [--cases]

result.json is the file `claude plugin eval ... --json result.json` writes. Every grader carries
a `stage:` in its front matter (tests/check_skill.py makes sure of it):

  route    the right mode and reference for the question (near misses: en-route-*)
  script   the numbers come from the skill's script, not from the model
  answer   what the runner reads: the numbers, the advice, the plan
  conduct  asks before writing or deciding, asks for missing or conflicting input

Prints, per stage and arm (with / without the plugin), how many graded runs passed. A grader
that only fires with the plugin (with-only) still counts in the "with" arm here, because the
point is to see whether the script was run. --cases adds one line per case and stage.
"""
import json
import pathlib
import sys

EVALS = pathlib.Path(__file__).resolve().parent.parent / "skills" / "running-coach" / "evals"
STAGES = ("route", "script", "answer", "conduct")


def stage_of(case, grader):
    path = EVALS / case / "stages.json"
    return json.loads(path.read_text()).get(grader, "?") if path.exists() else "?"


def tally(paths):
    totals, per_case = {}, {}
    for p in paths:
        data = json.loads(pathlib.Path(p).read_text())
        for case in data["cases"]:
            for arm, runs in case["arms"].items():
                for run in runs:
                    for g in run.get("graders", []):
                        if g.get("passed") is None:
                            continue
                        stage = stage_of(case["name"], g["name"])
                        for bucket in (totals.setdefault((stage, arm), [0, 0]),
                                       per_case.setdefault((case["name"], stage, arm), [0, 0])):
                            bucket[0] += bool(g["passed"])
                            bucket[1] += 1
    return totals, per_case


def cell(counts):
    if not counts:
        return "–"
    ok, n = counts
    return f"{ok}/{n} ({round(100 * ok / n)} %)"


def main(argv):
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 2
    totals, per_case = tally(paths)
    arms = sorted({arm for _, arm in totals}, key=lambda a: (a != "with", a))
    stages = [s for s in STAGES if any((s, a) in totals for a in arms)]
    stages += sorted({s for s, _ in totals} - set(STAGES))
    print("stage     " + "".join(f"{a:<18}" for a in arms))
    for s in stages:
        print(f"{s:<10}" + "".join(f"{cell(totals.get((s, a))):<18}" for a in arms))
    if "--cases" in argv:
        print()
        for case in sorted({c for c, _, _ in per_case}):
            for s in stages:
                row = [per_case.get((case, s, a)) for a in arms]
                if any(row):
                    print(f"{case:<34}{s:<10}" + "".join(f"{cell(r):<18}" for r in row))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
