#!/usr/bin/env python3
"""Checks the skill package against the limits that Claude's apps enforce and the repo's own rules.

Run from the repository root:  python3 tests/check_skill.py
Exit code 1 on any failure. Standard library only, so it runs in CI and locally.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "running-coach"
DESCRIPTION_MAX = 1024        # Agent Skills limit; longer descriptions get cut off in claude.ai
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
failures = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


text = (SKILL / "SKILL.md").read_text()
m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
check(m is not None, "SKILL.md starts with a frontmatter block")
front = dict(re.findall(r"^(\w+): (.*)$", m.group(1), re.M)) if m else {}
name, desc = front.get("name", ""), front.get("description", "")
check(bool(NAME_RE.match(name)), f"name '{name}' is lowercase letters, digits and hyphens")
check(0 < len(desc) <= DESCRIPTION_MAX, f"description is {len(desc)} characters (max {DESCRIPTION_MAX})")
check(": " not in desc and " #" not in desc, "description has no ': ' or ' #' (would break unquoted YAML)")
check("<" not in desc and ">" not in desc, "description has no angle brackets")
lines = text.count("\n")
check(lines <= 500, f"SKILL.md is {lines} lines (keep under 500)")

for ref in sorted(set(re.findall(r"`((?:references|scripts|assets)/[\w.-]+)`", text))):
    check((SKILL / ref).exists(), f"{ref} referenced in SKILL.md exists")
for ref in sorted(set(re.findall(r"`(\w[\w-]*\.md)`", text))):
    if ref != "SKILL.md" and not (SKILL / "references" / ref).exists() and ref not in ("athlete-profile.md", "season-plan.md"):
        check(False, f"{ref} mentioned in SKILL.md exists in references/")

defined = set(re.findall(r"^\| (S\d+) ", (SKILL / "references" / "sources.md").read_text(), re.M))
used = set()
for f in (SKILL / "references").glob("*.md"):
    used |= set(re.findall(r"\b(S\d{1,2})\b", f.read_text()))
check(used <= defined, "every source tag used in references/ is defined in sources.md"
      + (f" (missing: {sorted(used - defined)})" if used - defined else ""))

plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
check(bool(re.match(r"^\d+\.\d+\.\d+$", plugin.get("version", ""))), f"plugin version {plugin.get('version')} is semver")
check(plugin.get("name") == name, "plugin name matches the skill name")
tpl = re.search(r'<meta name="running-coach-version" content="([^"]+)">',
                (SKILL / "assets" / "season-plan.html").read_text())
check(bool(tpl) and tpl.group(1) == plugin["version"],
      f"page template version {tpl.group(1) if tpl else None} matches plugin version {plugin['version']}")
check(f"\n## {plugin['version']}\n" in (SKILL / "references" / "whats-new.md").read_text(),
      f"whats-new.md has a section for {plugin['version']}")
check(any(p.get("name") == plugin["name"] for p in market.get("plugins", [])), "marketplace lists the plugin")

for script in sorted((SKILL / "scripts").glob("*.py")):
    try:
        compile(script.read_text(), str(script), "exec")
        check(True, f"{script.name} compiles")
    except SyntaxError as e:
        check(False, f"{script.name} compiles: {e}")

print(f"\n{'FAILED' if failures else 'All checks passed'} ({len(failures)} failure(s))")
sys.exit(1 if failures else 0)
