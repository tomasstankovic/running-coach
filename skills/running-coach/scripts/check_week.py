#!/usr/bin/env python3
"""Check a planned training week against load-progression rules.

Input is one JSON file:

{
  "week_role": "build",            # base | build | peak | deload | taper | race | return
  "today": "2026-10-31",           # optional, defaults to today's date
  "cautious": false,               # novice, or injured in the last 12 months: +10 % weekly limit
  "history": [ ...workouts... ],   # last 4-8 weeks of workouts, raw tool output is fine
  "history_weeks": [ ... ],        # OR weekly totals when there is no per-run data
  "plan":    [ ...workouts... ]    # the week being planned (Mon-Sun)
}

Workout shapes accepted in "history" and "plan" (tool output can be pasted as-is):
  simple:          date, minutes (or hours), km
  TrainingPeaks:   date, duration_actual / duration_planned (hours),
                   distance_actual_km / distance_planned_km, sport
  Strava:          start_date_local, moving_time (s), distance (m), sport_type
"history" may also be the raw tool response ({"workouts": [...]} or {"activities": [...]}).
TrainingPeaks workouts that were planned but never done (no duration_actual) are ignored,
except those still ahead of "today" in the current week, which count as planned volume.

"history_weeks" items: {"week_start": "2026-10-19", "minutes": 190, "km": 32, "long_min": 85}
(use this for runners without connected data: build it from what they told you).

Plan workouts carry "type": rest | recovery | easy | long | strides | tempo | threshold |
intervals | hills | race | cross | strength. Optional "quality_minutes" is the time spent at
X/Z3 or harder (defaults to a rough estimate per type). Strength and cross-training don't count
as running volume.

Checks (references/methodology.md §4, references/sources.md):
  - every run vs the longest run of the previous 30 days: > +10 % is a FAIL (Frandsen 2025)
  - weekly volume: OK <= +15 %, WARN to +20 %, FAIL above +20 % or +30 % over two weeks
    (+10 % when "cautious"); small absolute steps (<= 30 min) are fine at low volume
  - deload rhythm, long-run share, hard days, strength placement, intensity share, rest days

Output: one line per check, prefixed OK / WARN / FAIL. Exit code 1 if any FAIL.
"""
import json
import sys
from collections import defaultdict
from datetime import date, timedelta

HARD_TYPES = {"tempo", "threshold", "intervals", "hills", "race"}
SESSION_TYPES = HARD_TYPES | {"easy", "recovery", "long", "strides", "rest", "cross", "strength"}
NON_RUN_TYPES = {"rest", "cross", "strength"}
TP_STATUS = {"completed", "planned"}
# Rough share of a session spent at X/Z3 or harder when quality_minutes is missing.
DEFAULT_QUALITY_SHARE = {"tempo": 0.4, "threshold": 0.4, "intervals": 0.3, "hills": 0.2, "race": 0.8, "strides": 0.03}


def minutes(w):
    if w.get("minutes") is not None:
        return float(w["minutes"])
    if w.get("hours") is not None:
        return float(w["hours"]) * 60
    for key in ("duration_actual", "duration_planned"):
        if w.get(key):
            return float(w[key]) * 60
    for key in ("moving_time", "elapsed_time"):  # Strava, seconds
        if w.get(key):
            return float(w[key]) / 60
    return 0.0


def km(w):
    if w.get("km") is not None:
        return float(w["km"])
    for key in ("distance_actual_km", "distance_planned_km", "distance_km"):
        if w.get(key):
            return float(w[key])
    if w.get("distance"):  # Strava, metres
        return float(w["distance"]) / 1000
    return 0.0


def is_run(w):
    kind = w.get("type")
    if kind in NON_RUN_TYPES:
        return False
    sport = w.get("sport") or w.get("sport_type")
    if sport is None and kind not in (None, *SESSION_TYPES, *TP_STATUS):
        sport = kind  # Strava's older "type" field ("Run", "Ride", ...)
    return sport is None or "Run" in str(sport)


def monday(d):
    return d - timedelta(days=d.weekday())


def workout_date(w):
    for key in ("date", "start_date_local", "start_date"):
        if w.get(key):
            return date.fromisoformat(str(w[key])[:10])
    raise ValueError(f"workout without a date: {w}")


def counts_as_done(w, today):
    """A TrainingPeaks workout without actual data was skipped, unless it's still ahead."""
    if "duration_actual" in w and not w.get("duration_actual"):
        return workout_date(w) >= today
    return True


def weekly_history(data, plan_start, today):
    weeks = defaultdict(lambda: {"min": 0.0, "km": 0.0, "long": 0.0})
    for wk in data.get("history_weeks", []):
        start = monday(date.fromisoformat(wk["week_start"][:10]))
        weeks[start] = {"min": float(wk.get("minutes", 0)), "km": float(wk.get("km", 0)),
                        "long": float(wk.get("long_min", 0))}

    history = data.get("history", [])
    if isinstance(history, dict):  # raw tool output
        history = history.get("workouts") or history.get("activities") or []
    for w in history:
        if not is_run(w) or not counts_as_done(w, today):
            continue
        start = monday(workout_date(w))
        if start >= plan_start:
            continue
        wk = weeks[start]
        wk["min"] += minutes(w)
        wk["km"] += km(w)
        wk["long"] = max(wk["long"], minutes(w))

    if not weeks:
        return []
    # weeks without any run (illness, post-race rest) are real data points: keep them as zeros
    start = min(weeks)
    while start < plan_start:
        weeks[start]  # defaultdict creates the empty week
        start += timedelta(days=7)
    return [weeks[k] | {"start": k} for k in sorted(weeks) if k < plan_start]


def done_runs(data, before, today):
    """(date, km, minutes) of completed runs before `before`, from per-run history."""
    history = data.get("history", [])
    if isinstance(history, dict):
        history = history.get("workouts") or history.get("activities") or []
    out = []
    for w in history:
        if is_run(w) and counts_as_done(w, today) and workout_date(w) < before:
            out.append((workout_date(w), km(w), minutes(w)))
    return out


def spike_checks(data, plan, plan_start, prior, today, report):
    """Each planned run vs the longest run of the 30 days before it (planned ones included)."""
    runs = done_runs(data, plan_start, today)
    by_km = bool(runs) and all(r[1] > 0 for r in runs)
    if not runs:
        if prior:  # weekly totals only: compare with the longest run of the last 4 weeks
            ref = max(p["long"] for p in prior[-4:])
            longest = max((minutes(w) for w in plan if is_run(w)), default=0)
            if ref and longest > ref * 1.10 + 5:
                report("FAIL", f"longest run {longest:.0f} min is {longest / ref * 100 - 100:.0f} % above the "
                               f"recent longest ({ref:.0f} min); keep each run within +10 %")
        return
    seen = list(runs)
    flagged = False
    for w in sorted((w for w in plan if is_run(w)), key=workout_date):
        d = workout_date(w)
        if w.get("type") == "race":
            continue
        window = [r for r in seen if 0 < (d - r[0]).days <= 30]
        if window:
            val = km(w) if by_km else minutes(w)
            ref = max((r[1] if by_km else r[2]) for r in window)
            tolerance = 1.0 if by_km else 5
            if ref and val > ref * 1.10 + tolerance:
                unit = "km" if by_km else "min"
                report("FAIL", f"{d}: {val:.0f} {unit} is {val / ref * 100 - 100:.0f} % longer than the longest run "
                               f"of the last 30 days ({ref:.0f} {unit}); keep every run within +10 %")
                flagged = True
        seen.append((d, km(w), minutes(w)))
    if not flagged:
        report("OK", "no run is more than 10 % longer than the longest of the previous 30 days")


def main(path):
    with open(path) as f:
        data = json.load(f)
    role = data.get("week_role", "build")
    today = date.fromisoformat(data["today"]) if data.get("today") else date.today()
    plan = data["plan"]
    plan_start = monday(min(workout_date(w) for w in plan))
    prior = weekly_history(data, plan_start, today)
    results = []

    def report(level, msg):
        results.append((level, msg))

    # ---- plan totals --------------------------------------------------------
    runs = [w for w in plan if is_run(w)]
    total_min = sum(minutes(w) for w in runs)
    total_km = sum(km(w) for w in runs)
    long_min = max((minutes(w) for w in runs), default=0)
    long_km = max((km(w) for w in runs), default=0)

    print(f"Planned week from {plan_start}: {len(runs)} runs, {total_km:.1f} km, "
          f"{total_min:.0f} min, longest {long_min:.0f} min / {long_km:.1f} km  (role: {role})")
    if prior:
        print("Previous weeks: " + ", ".join(
            f"{p['start'].strftime('%d.%m')} {p['km']:.0f} km/{p['min']:.0f} min" for p in prior[-6:]))
    print()

    # ---- volume progression ----------------------------------------------
    if prior:
        last = prior[-1]
        recent = prior[-3:]
        avg3 = sum(p["min"] for p in recent) / len(recent)
        base = max(last["min"], 1)
        change = (total_min - base) / base * 100
        change_avg = (total_min - avg3) / max(avg3, 1) * 100
        if role in ("deload", "taper", "race", "return"):
            if total_min > base * 0.9 and role in ("deload", "taper"):
                report("WARN", f"{role} week but volume is {change:+.0f} % vs last week; aim for −20 to −40 %")
            else:
                report("OK", f"{role} week volume {change:+.0f} % vs last week")
        else:
            small = total_min - base <= 30  # small absolute jumps are fine at low volume
            # coming back from a lighter week: compare with the last normal week instead
            reference = max(p["min"] for p in recent)
            if last["min"] < 0.85 * reference:
                base_ref = reference
                change_ref = (total_min - base_ref) / max(base_ref, 1) * 100
                note = f" (last week was lighter; {change_ref:+.0f} % vs the {base_ref:.0f}-min week before)"
                change, small = change_ref, total_min - base_ref <= 30
            else:
                note = ""
            cautious = bool(data.get("cautious"))
            warn_at, fail_at = (10, 15) if cautious else (15, 20)
            two_weeks = (total_min - prior[-2]["min"]) / max(prior[-2]["min"], 1) * 100 if len(prior) >= 2 else 0
            if change > fail_at and not small:
                report("FAIL", f"volume {change:+.0f} % ({base:.0f} → {total_min:.0f} min){note}; "
                               f"keep ≤ +{warn_at} % (hard limit +{fail_at} %)")
            elif two_weeks > 30 and not small and not note:
                report("FAIL", f"volume {two_weeks:+.0f} % over two weeks; keep two-week growth ≤ +30 %")
            elif change > warn_at and not small:
                report("WARN", f"volume {change:+.0f} %{note}; +{warn_at} % is the usual ceiling")
            else:
                report("OK", f"volume {change:+.0f} %{note}, {change_avg:+.0f} % vs 3-week average")

        # deload rhythm: three weeks of rising load in a row, with no lighter week
        if role in ("build", "peak", "base") and len(prior) >= 3:
            last3 = [p["min"] for p in prior[-3:]]
            peak_before = max(p["min"] for p in prior[:-3]) if len(prior) > 3 else 0
            no_lighter = min(last3) >= 0.85 * max(max(last3), peak_before)
            rising = last3[-1] >= 1.05 * last3[0] and total_min >= last3[-1]
            if no_lighter and rising:
                report("WARN", "3 weeks of rising load without a lighter week; consider making this a deload")

    else:
        report("WARN", "no history given; cannot check progression (pass history or history_weeks)")

    # ---- single-run spikes ---------------------------------------------------
    spike_checks(data, plan, plan_start, prior, today, report)

    # ---- long run share ------------------------------------------------------
    if total_min > 0 and role not in ("race", "taper"):
        share = long_min / total_min * 100
        limit = 45 if len(runs) <= 4 else (40 if total_min < 300 else 35)
        report("WARN" if share > limit else "OK", f"long run is {share:.0f} % of weekly time (limit ~{limit} % for {len(runs)} runs)")

    # ---- hard days -----------------------------------------------------------
    hard_dates = sorted({workout_date(w) for w in plan if w.get("type") in HARD_TYPES})
    max_hard = 3 if role == "peak" else 2
    if role in ("deload", "return"):
        max_hard = 1
    report("WARN" if len(hard_dates) > max_hard else "OK",
           f"{len(hard_dates)} hard days (max {max_hard} for a {role} week)")
    for a, b in zip(hard_dates, hard_dates[1:]):
        if (b - a).days == 1:
            report("FAIL", f"hard days back to back: {a} and {b}")
    long_dates = [workout_date(w) for w in plan if w.get("type") == "long"]
    for ld in long_dates:
        for hd in hard_dates:
            if abs((ld - hd).days) == 1:
                report("WARN", f"long run {ld} is next to a hard day {hd}")

    # ---- strength placement --------------------------------------------------
    key_days = set(hard_dates) | set(long_dates)
    for w in plan:
        if w.get("type") == "strength":
            d = workout_date(w)
            if d + timedelta(days=1) in key_days:
                report("WARN", f"strength on {d} is the day before a hard session or long run")

    # ---- intensity distribution ---------------------------------------------
    quality = 0.0
    for w in runs:
        if w.get("quality_minutes") is not None:
            quality += float(w["quality_minutes"])
        else:
            quality += minutes(w) * DEFAULT_QUALITY_SHARE.get(w.get("type"), 0)
    if total_min > 0:
        q_share = quality / total_min * 100
        report("WARN" if q_share > 25 else "OK", f"~{q_share:.0f} % of time at X/Z3 or harder (target ≤ 20 %, warn > 25 %)")

    # ---- rest ----------------------------------------------------------------
    rest_days = 7 - len({workout_date(w) for w in runs})
    report("WARN" if rest_days < 1 else "OK", f"{rest_days} day(s) without running")

    for level, msg in results:
        print(f"{level:<4}  {msg}")
    return 1 if any(level == "FAIL" for level, _ in results) else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
