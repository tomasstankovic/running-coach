#!/usr/bin/env python3
"""The numbers the eval graders expect, checked against the scripts.

Run from the repository root:  python3 -m unittest discover -s tests -v
Standard library only.

A grader says "about 414 km, 24 key sessions on target"; those numbers come from running a
script on the case's files. A case that depends on such numbers keeps them beside its data in
evals/<case>/expected.json (outside files/, so the model under test never sees it):

  {
    "why":    "what the graders rely on",
    "script": "block_report.py",
    "args":   ["plan.json", "--phase", "base", "--json"],
    "input":  {...},            optional: written to _input.json; "@name.json" values are
                                replaced by that file's content from files/
    "exit":   0,                optional: expected exit code (default 0)
    "json":   {...},            optional: must match the JSON output (dicts by key, lists in order)
    "text":   ["..."]           optional: substrings of the text output
  }

If a script or a fixture changes so that the numbers move, this test fails before the graders
quietly start grading against the wrong numbers. English copies (en-*) carry the same file and
must expect the same numbers as their Slovak source.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "running-coach"
SCRIPTS = SKILL / "scripts"
EVALS = SKILL / "evals"


def cases():
    return sorted(p.parent for p in EVALS.glob("*/expected.json"))


def resolve(value, files):
    if isinstance(value, str) and value.startswith("@"):
        return json.loads((files / value[1:]).read_text())
    if isinstance(value, dict):
        return {k: resolve(v, files) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, files) for v in value]
    return value


def mismatches(expected, actual, path="$"):
    """Where `actual` differs from `expected`; extra keys in `actual` are fine."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected an object, got {actual!r}"]
        out = []
        for key, value in expected.items():
            if key not in actual:
                out.append(f"{path}.{key}: missing")
            else:
                out += mismatches(value, actual[key], f"{path}.{key}")
        return out
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [f"{path}: expected {len(expected)} items, got {actual!r}"]
        out = []
        for i, (e, a) in enumerate(zip(expected, actual)):
            out += mismatches(e, a, f"{path}[{i}]")
        return out
    return [] if expected == actual else [f"{path}: expected {expected!r}, got {actual!r}"]


def run_case(case):
    spec = json.loads((case / "expected.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        shutil.copytree(case / "files", work, dirs_exist_ok=True)
        if "input" in spec:
            (work / "_input.json").write_text(json.dumps(resolve(spec["input"], work)))
        proc = subprocess.run([sys.executable, str(SCRIPTS / spec["script"]), *spec["args"]],
                              cwd=work, capture_output=True, text=True)
    return spec, proc


class EvalFixtures(unittest.TestCase):
    def test_there_are_cases(self):
        self.assertGreaterEqual(len(cases()), 4)

    def test_scripts_give_the_numbers_the_graders_expect(self):
        for case in cases():
            with self.subTest(case=case.name):
                spec, proc = run_case(case)
                self.assertEqual(proc.returncode, spec.get("exit", 0),
                                 f"{spec['script']} exit {proc.returncode}:\n{proc.stderr[-500:]}")
                if "json" in spec:
                    problems = mismatches(spec["json"], json.loads(proc.stdout))
                    self.assertFalse(problems, "\n".join(problems))
                for text in spec.get("text", []):
                    self.assertIn(text, proc.stdout)

    def test_english_copies_expect_the_same(self):
        for case in cases():
            if not case.name.startswith("en-"):
                continue
            with self.subTest(case=case.name):
                sources = [c for c in cases() if not c.name.startswith("en-")
                           and (EVALS / f"en-{c.name}") == case]
                for src in sources:
                    en = json.loads((case / "expected.json").read_text())
                    sk = json.loads((src / "expected.json").read_text())
                    self.assertEqual(en, sk)


if __name__ == "__main__":
    unittest.main()
