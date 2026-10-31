#!/usr/bin/env python3
"""Rough season plan: one row per week from now to the A race(s), and re-planning when life happens.

Usage:
  season_plan.py generate spec.json --out plan.json
  season_plan.py replan plan.json --from 2027-01-11 --current-km 32 [--long-km 14]
                 [--busy 2027-02-01:0.6:work deadline] [--note "flu, 5 days off"] --out plan.json
  season_plan.py actuals plan.json --history workouts.json [--today 2027-01-10] --out plan.json
  season_plan.py export plan.json --format markdown          # table for a TP note / profile file
  season_plan.py export plan.json --format batch --out-dir docs [--versions versions.json]
                                                            # plan page database: one JSON file per
                                                            # document + the ArtifactData batch writes

Spec:
{
  "title": "Spring 2027", "lang": "sk",       # labels in sk or en (translate others yourself)
  "start": "2026-11-09",                      # Monday of the first planned week
  "current": {"km": 40, "long_km": 14},       # typical recent week
  "runs_per_week": 5, "easy_pace": "6:00",    # converts km to time
  "races": [{"name": "City HM", "date": "2027-03-14", "distance_km": 21.1, "priority": "B"},
            {"name": "Spring Marathon", "date": "2027-04-25", "distance_km": 42.2, "priority": "A"}],
  "peak_km": 65,                              # optional; default by goal distance
  "rhythm": 3,                                # build weeks before a deload: 3 (3:1) or 2 (2:1)
  "busy": [{"week": "2026-12-21", "factor": 0.6, "note": "Christmas travel"}]
}

Rules (methodology.md §4-6): build weeks grow at most 10 %, every (rhythm+1)th week is a deload
at ~70 %, B races and busy weeks count as lighter weeks, phases are planned backwards from each A
race (base -> build -> specific -> taper), the long run grows <= 2 km a week within its share and
cap and never more than 10 % past the longest recent run. Volume is the plan's spine: the detail is planned week by week later.

The plan keeps its spec, so `replan` re-runs the same rules from a later week with the new
starting point and keeps the weeks before it (and their actuals) untouched.
"""
import argparse
import json
import sys
from datetime import date, timedelta

# (max distance km, specific weeks, build weeks, taper factors incl. race week, recovery factors)
GOALS = [
    (6, 2, 4, [0.7], [0.6]),
    (12, 3, 4, [0.7], [0.6]),
    (25, 3, 5, [0.8, 0.55], [0.5]),
    (45, 4, 6, [0.75, 0.6, 0.45], [0.35, 0.6]),
    (999, 4, 6, [0.75, 0.6, 0.45], [0.35, 0.6]),
]
DEFAULT_PEAK = {6: 40, 12: 45, 25: 50, 45: 65, 999: 75}
LONG_CAP = {6: 14, 12: 16, 25: 21, 45: 32, 999: 35}
TSS_PER_HOUR = {"base": 55, "build": 58, "specific": 60, "taper": 56, "race": 65, "recovery": 48}

LABELS = {
    "en": {
        "base": "strides + short hills", "build": "threshold (cruise intervals)",
        "specific_m": "long run with marathon-pace segments", "specific_hm": "half-marathon pace 2-3 x 5 km",
        "specific_10k": "10k pace 3 x 3 km", "specific_5k": "5k pace 6-8 x 800 m",
        "deload": "short threshold, strides", "taper": "race-pace sharpening",
        "recovery": "easy running only", "busy": "busy week: 1 quality + long run",
        "after_race": "recovery after the race",
        "phase": {"base": "base", "build": "build", "specific": "specific", "taper": "taper",
                  "race": "race", "recovery": "recovery"},
    },
    "sk": {
        "base": "rovinky + krátke kopce", "build": "prah (cruise intervaly)",
        "specific_m": "dlhý beh s úsekmi v maratónskom tempe", "specific_hm": "polmaratónske tempo 2-3 x 5 km",
        "specific_10k": "tempo na 10 km 3 x 3 km", "specific_5k": "tempo na 5 km 6-8 x 800 m",
        "deload": "krátky prah, rovinky", "taper": "ostrenie v závodnom tempe",
        "recovery": "len ľahké behy", "busy": "vyťažený týždeň: 1 kvalita + dlhý beh",
        "after_race": "regenerácia po závode",
        "phase": {"base": "základ", "build": "budovanie", "specific": "špecifická", "taper": "ladenie",
                  "race": "závod", "recovery": "regenerácia"},
    },
}


def monday(d):
    return d - timedelta(days=d.weekday())


def parse_pace(text):
    m, s = str(text).split(":")
    return int(m) * 60 + int(s)


def goal_row(distance):
    for row in GOALS:
        if distance <= row[0]:
            return row
    return GOALS[-1]


def specific_key(distance):
    if distance <= 6:
        return "specific_5k"
    if distance <= 12:
        return "specific_10k"
    if distance <= 25:
        return "specific_hm"
    return "specific_m"


def plan_segment(spec, start, a_race, level, long_km, warnings):
    """Weeks from `start` through the A race week, then its recovery weeks."""
    lab = LABELS.get(spec.get("lang", "en"), LABELS["en"])
    dist = float(a_race["distance_km"])
    limit, n_spec, n_build, taper, recovery = goal_row(dist)
    race_week = monday(date.fromisoformat(a_race["date"]))
    total = (race_week - start).days // 7 + 1
    if total < 1:
        raise ValueError(f"A race {a_race['name']} is before the start week")
    n_taper = min(len(taper), total)
    left = total - n_taper
    n_spec, n_build = min(n_spec, left), min(n_build, max(0, left - n_spec))
    n_base = left - n_spec - n_build
    if left < goal_row(dist)[1] + goal_row(dist)[2]:
        warnings.append(f"{a_race['name']}: only {total} weeks; base skipped, build/specific shortened")
    phases = ["base"] * n_base + ["build"] * n_build + ["specific"] * n_spec + ["taper"] * n_taper

    runs = int(spec.get("runs_per_week", 5))
    base_share = 0.35 if runs >= 5 else 0.45
    # marathon build/specific: the long run matters more than its share (methodology.md §4)
    late_share = 0.5 if dist > 25 else base_share
    cap = LONG_CAP[limit]
    peak = float(spec.get("peak_km") or DEFAULT_PEAK[limit])
    rhythm = int(spec.get("rhythm", 3))
    pace = parse_pace(spec.get("easy_pace", "6:00"))
    busy = {monday(date.fromisoformat(b["week"])): b for b in spec.get("busy", [])}
    others = {monday(date.fromisoformat(r["date"])): r for r in spec.get("races", [])
              if r.get("priority", "C") in ("B", "C")}

    ramp_weeks = sum(1 for i, p in enumerate(phases[: n_base + n_build]) if (i + 1) % (rhythm + 1))
    rate = 1.0
    if ramp_weeks and peak > level:
        rate = min(1.10, (peak / level) ** (1 / ramp_weeks))
        reachable = level * rate ** ramp_weeks
        if reachable < peak * 0.97:
            warnings.append(f"{a_race['name']}: peak {peak:.0f} km not reachable at +10 %/week "
                            f"from {level:.0f} km; plan peaks at ~{reachable:.0f} km")
            peak = reachable

    weeks, since_deload = [], 0
    for i, phase in enumerate(phases):
        wk = start + timedelta(weeks=i)
        race = others.get(wk)
        role, key, km = "build", lab["build"] if phase != "base" else lab["base"], None
        if phase == "specific":
            key = lab[specific_key(dist)]
        if phase == "taper":
            role, key = "taper", lab["taper"]
            km = peak * taper[i - (len(phases) - n_taper)]
        elif wk in busy:
            role, key = "busy", lab["busy"]
            km = level * float(busy[wk].get("factor", 0.6))
            since_deload = 0
        elif race and race.get("priority") == "B":
            role, key = "race-B", f"B: {race['name']}"
            km = max(level * 0.8, float(race.get("distance_km", 0)) * 1.8)
            since_deload = 0
        elif since_deload == rhythm:
            role, key = "deload", lab["deload"]
            km = level * 0.7
            since_deload = 0
        else:
            if phase in ("base", "build"):
                level = min(peak, level * rate)
            km = level
            since_deload += 1
        if race and race.get("priority") == "C":
            key = f"C: {race['name']}"
        share = base_share if phase == "base" else late_share
        if role == "build":
            long_km = min(cap, km * share, long_km * 1.10)  # one run <= +10 % (Frandsen 2025)
            this_long = long_km
        else:
            this_long = min(cap, km * share, long_km * 0.8)
        if role == "race-B":
            this_long = float(race.get("distance_km", this_long))
        if wk == race_week:
            role, phase, key, this_long = "race", "race", f"A: {a_race['name']}", dist
            km = max(km, dist + km * 0.5)
        weeks.append(row(wk, phase, role, km, this_long, key, pace, lab))

    for j, factor in enumerate(recovery):
        wk = race_week + timedelta(weeks=j + 1)
        weeks.append(row(wk, "recovery", "recovery", peak * factor, min(cap, peak * factor * 0.3),
                         lab["after_race"] if j == 0 else lab["recovery"], pace, lab))
    return weeks, peak * 0.7, min(long_km, cap * 0.6)


def row(wk, phase, role, km, long_km, key, pace, lab):
    minutes = km * pace * 0.95 / 60
    return {"week_start": wk.isoformat(), "phase": phase, "phase_label": lab["phase"][phase],
            "role": role, "km": round(km), "minutes": int(round(minutes / 5) * 5),
            "long_km": round(long_km), "key": key,
            "tss": int(round(minutes / 60 * TSS_PER_HOUR[phase] / 5) * 5),
            "actual_km": None, "actual_minutes": None, "note": ""}


def generate(spec):
    warnings = []
    start = monday(date.fromisoformat(spec["start"]))
    level = float(spec["current"]["km"])
    long_km = float(spec["current"].get("long_km", level * 0.3))
    a_races = sorted((r for r in spec["races"] if r.get("priority") == "A"), key=lambda r: r["date"])
    if not a_races:
        raise ValueError("the spec needs at least one race with priority A")
    weeks = []
    for a in a_races:
        if monday(date.fromisoformat(a["date"])) < start:
            continue
        seg, level, long_km = plan_segment(spec, start, a, level, long_km, warnings)
        weeks += seg
        start = date.fromisoformat(seg[-1]["week_start"]) + timedelta(weeks=1)
    for i, w in enumerate(weeks, 1):
        w["n"] = i
    return {"spec": spec, "weeks": weeks, "changes": [], "warnings": warnings}


def cmd_replan(plan, args):
    spec = dict(plan["spec"])
    frm = monday(date.fromisoformat(args.from_))
    spec["start"] = frm.isoformat()
    spec["current"] = {"km": args.current_km, "long_km": args.long_km or args.current_km * 0.3}
    busy = list(spec.get("busy", []))
    for b in args.busy or []:
        wk, factor, *note = b.split(":", 2)
        busy.append({"week": wk, "factor": float(factor), "note": note[0] if note else ""})
    spec["busy"] = busy
    new = generate(spec)
    kept = [w for w in plan["weeks"] if date.fromisoformat(w["week_start"]) < frm]
    old_by_week = {w["week_start"]: w for w in plan["weeks"]}
    for w in new["weeks"]:
        old = old_by_week.get(w["week_start"])
        if old:  # keep actuals and notes already recorded for that week
            w.update({k: old[k] for k in ("actual_km", "actual_minutes", "note") if old.get(k)})
    weeks = kept + new["weeks"]
    for i, w in enumerate(weeks, 1):
        w["n"] = i
    spec["start"] = plan["spec"]["start"]
    changes = plan.get("changes", []) + [{"date": date.today().isoformat(),
                                          "text": args.note or f"re-planned from {frm.isoformat()}"}]
    return {"spec": spec, "weeks": weeks, "changes": changes, "warnings": new["warnings"]}


def cmd_actuals(plan, args):
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from check_week import counts_as_done, is_run, km, minutes, workout_date  # noqa: E402
    with open(args.history) as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("workouts") or data.get("activities") or []
    today = date.fromisoformat(args.today) if args.today else date.today()
    totals = {}
    for w in data:
        if not is_run(w) or not counts_as_done(w, today) or workout_date(w) >= today:
            continue
        wk = monday(workout_date(w)).isoformat()
        t = totals.setdefault(wk, [0.0, 0.0])
        t[0] += km(w)
        t[1] += minutes(w)
    for w in plan["weeks"]:
        if w["week_start"] in totals:
            w["actual_km"] = round(totals[w["week_start"]][0], 1)
            w["actual_minutes"] = int(round(totals[w["week_start"]][1]))
    return plan


def export_batch(plan, out_dir, versions):
    """Write one JSON file per page document and return ArtifactData batch writes (<= 50 each)."""
    import os
    meta = {k: plan["spec"].get(k) for k in ("title", "lang", "start", "runs_per_week", "peak_km")}
    meta.update(races=plan["spec"].get("races", []), unit=plan["spec"].get("unit", "km"),
                updated=date.today().isoformat())
    docs = [("plan", "meta", meta)] + [("weeks", w["week_start"], w) for w in plan["weeks"]]
    docs += [("changes", f"{c['date']}-{i:02d}", c) for i, c in enumerate(plan.get("changes", []))]
    writes = []
    for coll, doc_id, data in docs:
        os.makedirs(os.path.join(out_dir, coll), exist_ok=True)
        path = os.path.abspath(os.path.join(out_dir, coll, f"{doc_id}.json"))
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        write = {"op": "set", "collection": coll, "doc_id": doc_id, "file_path": path}
        if versions.get(f"{coll}/{doc_id}"):
            write["if_version"] = versions[f"{coll}/{doc_id}"]
        writes.append(write)
    return [writes[i:i + 50] for i in range(0, len(writes), 50)]


def export(plan, fmt):
    lines = [f"# Running coach plan: {plan['spec'].get('title', '')}",
             f"start {plan['spec']['start']} · races: " + "; ".join(
                 f"{r['priority']} {r['name']} {r['date']}" for r in plan["spec"]["races"]), "",
             "| # | Week | Phase | Role | km | min | Long | Key | Actual |", "|---|---|---|---|---|---|---|---|---|"]
    for w in plan["weeks"]:
        actual = f"{w['actual_km']:g} km" if w.get("actual_km") is not None else ""
        lines.append(f"| {w['n']} | {w['week_start']} | {w['phase_label']} | {w['role']} | {w['km']} | "
                     f"{w['minutes']} | {w['long_km']} | {w['key']} | {actual} |")
    if plan.get("changes"):
        lines += ["", "## Changes"] + [f"- {c['date']}: {c['text']}" for c in plan["changes"][-8:]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("spec")
    g.add_argument("--out")
    r = sub.add_parser("replan")
    r.add_argument("plan")
    r.add_argument("--from", dest="from_", required=True)
    r.add_argument("--current-km", type=float, required=True)
    r.add_argument("--long-km", type=float)
    r.add_argument("--busy", action="append", help="WEEK:FACTOR[:note], e.g. 2027-02-01:0.6:deadline")
    r.add_argument("--note")
    r.add_argument("--out")
    a = sub.add_parser("actuals")
    a.add_argument("plan")
    a.add_argument("--history", required=True)
    a.add_argument("--today")
    a.add_argument("--out")
    e = sub.add_parser("export")
    e.add_argument("plan")
    e.add_argument("--format", choices=["markdown", "batch"], default="markdown")
    e.add_argument("--out-dir", help="batch: where to write the document files")
    e.add_argument("--versions", help='batch: {"weeks/2026-11-09": 3, ...} from an ArtifactData list')
    args = ap.parse_args()

    try:
        if args.cmd == "generate":
            with open(args.spec) as f:
                result = generate(json.load(f))
        else:
            with open(args.plan) as f:
                plan = json.load(f)
            if args.cmd == "export" and args.format == "batch":
                if not args.out_dir:
                    raise ValueError("--format batch needs --out-dir")
                versions = {}
                if args.versions:
                    with open(args.versions) as f:
                        versions = json.load(f)
                print(json.dumps(export_batch(plan, args.out_dir, versions), indent=1))
                return
            if args.cmd == "export":
                print(export(plan, args.format))
                return
            result = cmd_replan(plan, args) if args.cmd == "replan" else cmd_actuals(plan, args)
    except (ValueError, KeyError) as e:
        sys.exit(f"error: {e}")

    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        print(text)
    weeks = result["weeks"]
    print(f"{len(weeks)} weeks, {weeks[0]['week_start']} -> {weeks[-1]['week_start']}, "
          f"peak {max(w['km'] for w in weeks)} km", file=sys.stderr)
    for w in result.get("warnings", []):
        print(f"WARN {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
