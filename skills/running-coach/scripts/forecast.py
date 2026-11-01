#!/usr/bin/env python3
"""Race predictions: current form over 5 km, 10 km, half and marathon, and a forecast for each race
in the season, from the runner's results, threshold, training volume and the plan.

Usage:
  forecast.py input.json                 # tables for the conversation
  forecast.py input.json --json          # rows for the plan page's "predictions" collection

input.json:
{
  "today": "2026-11-01",
  "results": [                                 # last ~16 weeks; older ones are ignored
    {"date": "2026-10-04", "km": 21.0975, "time": "1:34:23", "kind": "race", "name": "Autumn HM"},
    {"date": "2026-09-05", "km": 10, "time": "41:16", "kind": "race"},
    {"date": "2026-10-28", "km": 5, "time": "21:10", "kind": "effort"}   # best 5 km inside a workout
  ],                                           # (tp_get_peaks speed5K/10K/HalfMarathon: km / speed)
  "threshold_pace": "4:10",                    # optional
  "weekly_km": 38,                             # mean of the last 8 weeks
  "training_pace": "5:55",                     # optional: mean pace of all runs, last 8 weeks (Tanda)
  "history": [                                 # optional: earlier best races and the volume behind them
    {"date": "2025-04-27", "km": 21.0975, "time": "1:31:40", "weekly_km": 55}
  ],
  "plan": "plan.json",                         # optional: season_plan.py output (races + planned km)
  "races": [                                   # optional when the plan has them
    {"name": "Spring Marathon", "date": "2027-04-25", "distance_km": 42.195, "goal": "3:25:00",
     "course_pct": 1.0, "temp_c": 14}          # course_pct: + % for a slow course (hills, turns),
  ]                                            # - % for a fast one; temp_c: expected temperature
}

How (references/analysis.md "Race predictions"):
- Races give the most: equivalent times by Riegel (exponent 1.06), weighted by how recent the race
  is (full weight up to 8 weeks, half by 16) and how close its distance is.
- Best efforts inside workouts weren't all-out: they only say "at least this fast".
- Threshold pace gives a second view: 5k ~107 %, 10k ~103 %, half ~98 % of threshold speed (the
  same factors as `paces.py race`). A gap of > 3 % between races and threshold means
  one of them is stale.
- Marathon: Riegel is too fast for most recreational runners, so the marathon comes from the
  volume models (Vickers & Vertosick 2016, Tanda 2011) [S25, S26].
- Race day: today's level is the conservative end. The plan's volume moves the marathon models;
  the runner's own earlier result at a similar volume (history) can set the optimistic end. No
  generic "+x % per block" is added. Then the course and the temperature (above 15 °C, 1-2 % per
  5 °C [S39]).
"""
import argparse
import json
import math
import statistics
import sys
from datetime import date, timedelta

from paces import RACE_TO_THRESHOLD, fmt_pace, fmt_time, parse_pace, parse_time, tanda, vickers_model1, vickers_model2

RIEGEL = 1.06
STANDARD = [("5 km", 5.0), ("10 km", 10.0), ("Half marathon", 21.0975), ("Marathon", 42.195)]
FRESH_WEEKS, MAX_WEEKS = 8, 16         # full weight up to 8 weeks old, half at 16, ignored after
THRESHOLD_WEIGHT = 0.5                 # threshold counts half as much as one fresh race
STALE_GAP = 3.0                        # % between race-based and threshold-based: one is stale
MIN_SPREAD = 1.5                       # % either side of the middle, at least
MARATHON_SPREAD = 2.5                  # % either side for the marathon, at least
HEAT_FROM, HEAT_PER_5C = 15, (1.0, 2.0)  # % slower per 5 °C above 15 °C [S39]
HISTORY_VOLUME = 0.9                   # an earlier result counts when the plan reaches 90 % of its volume
TAPER_WEEKS = 1                        # weeks before the race not counted as "planned volume"
VOLUME_WEEKS = 8                       # planned weeks counted before the race (weeks -9 to -2)


def riegel(t, d_from, d_to):
    return t * (d_to / d_from) ** RIEGEL


def threshold_factor(km):
    """Race speed as a share of threshold speed, interpolated on log distance."""
    pts = sorted((d, 1 / f) for d, f in RACE_TO_THRESHOLD.items())
    if km <= pts[0][0]:
        return pts[0][1]
    if km >= pts[-1][0]:
        return pts[-1][1]
    for (d1, f1), (d2, f2) in zip(pts, pts[1:]):
        if d1 <= km <= d2:
            w = math.log(km / d1) / math.log(d2 / d1)
            return f1 + (f2 - f1) * w


def age_weight(days):
    weeks = days / 7
    if weeks > MAX_WEEKS:
        return 0
    return 1.0 if weeks <= FRESH_WEEKS else 1 - 0.5 * (weeks - FRESH_WEEKS) / (MAX_WEEKS - FRESH_WEEKS)


def level(inp, km, today, weekly_km=None):
    """Prediction for one distance from the current inputs: (low, mid, high, notes, sources)."""
    results = [dict(r, secs=parse_time(r["time"])) for r in inp.get("results", [])]
    races = [r for r in results if r.get("kind", "race") == "race"]
    efforts = [r for r in results if r.get("kind") == "effort"]
    est, notes = [], []
    for r in races:
        w = age_weight((today - date.fromisoformat(r["date"])).days) / (1 + abs(math.log(km / r["km"])))
        if w > 0:
            est.append((riegel(r["secs"], r["km"], km), w, f"{r.get('name') or str(r['km']) + ' km'} {r['date']}"))
    race_mid = sum(t * w for t, w, _ in est) / sum(w for _, w, _ in est) if est else None
    thr = parse_pace(inp["threshold_pace"]) if inp.get("threshold_pace") else None
    thr_time = km * thr / threshold_factor(km) if thr else None
    if thr_time:
        est.append((thr_time, THRESHOLD_WEIGHT, f"threshold {inp['threshold_pace']}/km"))
        gap = abs(thr_time - race_mid) / race_mid * 100 if race_mid else 0
        if km <= 25 and gap > STALE_GAP:
            notes.append(f"the threshold predicts {gap:.0f} % {'faster' if thr_time < race_mid else 'slower'} than the "
                         f"races: either the threshold is set {'too fast' if thr_time < race_mid else 'too slow'}, or the "
                         f"races (hills, heat, pacing) {'undersell' if thr_time < race_mid else 'flatter'} the runner")
    floor = None
    for e in efforts:
        if km <= 25 and age_weight((today - date.fromisoformat(e["date"])).days) > 0:
            t = riegel(e["secs"], e["km"], km)  # not for the marathon: Riegel from 5-10 km is too fast there
            floor = t if floor is None else min(floor, t)
    weekly = weekly_km if weekly_km is not None else inp.get("weekly_km")
    if km > 30:
        vol = marathon_models(inp, races, today, weekly)
        if vol:
            riegel_only = race_mid
            est = [(t, 1.0, name) for t, name in vol]
            if riegel_only:
                notes.append(f"Riegel from the races alone says {fmt_time(riegel_only)}: too fast "
                             f"without marathon volume, not used")
            vt = [t for t, _ in vol]
            if len(vt) > 1 and (max(vt) - min(vt)) / min(vt) * 100 > 10:
                notes.append("the volume models disagree by more than 10 %: little marathon-specific evidence yet; "
                             "a half marathon or a long run with marathon-pace segments will narrow it")
        elif est:
            notes.append("no weekly km given: marathon from Riegel only, which is usually too fast")
    if not est:
        if floor:
            return floor * (1 - MIN_SPREAD / 100), floor, floor, ["only workout efforts: at least this fast"], []
        return None
    times = [t for t, _, _ in est]
    mid = sum(t * w for t, w, _ in est) / sum(w for _, w, _ in est)
    if floor and floor < mid:
        notes.append(f"a workout effort equals {fmt_time(floor)}: faster than the races suggest")
        mid = (mid + floor) / 2
        times.append(floor)
    spread = (MARATHON_SPREAD if km > 30 else MIN_SPREAD) / 100
    low, high = min(min(times), mid * (1 - spread)), max(max(times), mid * (1 + spread))
    return low, mid, high, notes, [name for _, _, name in est]


def marathon_models(inp, races, today, weekly_km):
    if not weekly_km:
        return []
    miles = weekly_km / 1.609344
    fresh = sorted((r for r in races if r["km"] < 42 and age_weight((today - date.fromisoformat(r["date"])).days) > 0),
                   key=lambda r: r["date"], reverse=True)
    out = []
    if fresh:
        best = max(fresh, key=lambda r: r["km"])  # the longest recent race says most about the marathon
        out.append((vickers_model1(best["km"] * 1000, best["secs"], miles), f"Vickers 1 ({best['km']:g} km + {weekly_km:g} km/week)"))
        others = [r for r in fresh if abs(r["km"] - best["km"]) > 1]
        if others:
            o = others[0]
            (d1, t1), (d2, t2) = sorted([(o["km"] * 1000, o["secs"]), (best["km"] * 1000, best["secs"])])
            out.append((vickers_model2(d1, t1, d2, t2, miles), "Vickers 2 (two races + volume)"))
    if inp.get("training_pace"):
        out.append((tanda(weekly_km, parse_pace(inp["training_pace"])), f"Tanda ({weekly_km:g} km/week)"))
    return out


def planned_volume(plan, race_date):
    """Mean planned km of the weeks -9 to -2 before the race (the taper week left out)."""
    if not plan:
        return None
    race_monday = race_date - timedelta(days=race_date.weekday())
    weeks = [w for w in plan.get("weeks", [])
             if race_monday - timedelta(weeks=VOLUME_WEEKS + TAPER_WEEKS) <= date.fromisoformat(w["week_start"])
             < race_monday - timedelta(weeks=TAPER_WEEKS)]
    kms = [w.get("km") for w in weeks if w.get("km")]
    return statistics.mean(kms) if kms else None


def race_forecast(inp, race, plan, today):
    km = race.get("distance_km") or race.get("km")
    rdate = date.fromisoformat(race["date"])
    now = level(inp, km, today)
    if not now:
        return None
    low, mid, high, notes, _ = now
    planned = planned_volume(plan, rdate)
    if km > 30 and planned:
        ahead = level(inp, km, today, weekly_km=planned)
        if ahead:
            notes.append(f"with the plan's {planned:.0f} km/week before the race "
                         f"(now {inp.get('weekly_km', '?')}): {fmt_time(ahead[1])}")
            current = inp.get("weekly_km") or planned
            low, mid = min(low, ahead[0]), ahead[1]
            high = high if planned >= current else max(high, ahead[2])
    for h in inp.get("history", []):
        if planned and h.get("weekly_km") and planned >= HISTORY_VOLUME * h["weekly_km"]:
            t = riegel(parse_time(h["time"]), h["km"], km)
            if t < low:
                notes.append(f"your {h['date']} result ({h['time']} over {h['km']:g} km at {h['weekly_km']:g} km/week) "
                             f"is within reach of this volume: {fmt_time(t)}")
                low = t
    adj_lo = adj_hi = race.get("course_pct", 0) or 0
    temp = race.get("temp_c")
    if temp is not None and temp > HEAT_FROM:
        steps = (temp - HEAT_FROM) / 5
        adj_lo += HEAT_PER_5C[0] * steps
        adj_hi += HEAT_PER_5C[1] * steps
        notes.append(f"{temp:g} °C: {HEAT_PER_5C[0] * steps:.1f}-{HEAT_PER_5C[1] * steps:.1f} % slower")
    if race.get("course_pct"):
        notes.append(f"course {race['course_pct']:+g} %")
    low, mid, high = low * (1 + adj_lo / 100), mid * (1 + (adj_lo + adj_hi) / 200), high * (1 + adj_hi / 100)
    goal = parse_time(race["goal"]) if race.get("goal") else None
    verdict = None
    if goal:
        verdict = ("inside the range" if low <= goal <= high else
                   f"{(low - goal) / low * 100:.1f} % faster than the fast end: a stretch" if goal < low and (low - goal) / low <= 0.03 else
                   f"{(low - goal) / low * 100:.1f} % faster than the fast end: out of reach on current evidence" if goal < low else
                   "slower than the range: a safe goal")
    return {"name": race.get("name", f"{km:g} km"), "date": race["date"], "km": km, "low": low, "mid": mid,
            "high": high, "goal": goal, "verdict": verdict, "notes": notes, "planned_km": planned}


def load(path):
    with open(path) as f:
        inp = json.load(f)
    plan = None
    if inp.get("plan"):
        with open(inp["plan"]) as f:
            plan = json.load(f)
    races = inp.get("races") or (plan or {}).get("spec", {}).get("races", [])
    today = date.fromisoformat(inp["today"]) if inp.get("today") else date.today()
    return inp, plan, races, today


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--json", action="store_true", help="rows for the plan page's predictions collection")
    args = ap.parse_args()
    try:
        inp, plan, races, today = load(args.input)
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"error: {e}")
    now = [(name, km, level(inp, km, today)) for name, km in STANDARD]
    ahead = [f for f in (race_forecast(inp, r, plan, today) for r in races if r["date"] >= today.isoformat()) if f]
    if args.json:
        rows = [{"id": f"{today}_now_{km:g}", "date": today.isoformat(), "kind": "now", "name": name, "km": km,
                 "low": round(p[0]), "mid": round(p[1]), "high": round(p[2])} for name, km, p in now if p]
        rows += [{"id": f"{today}_{f['date']}_{f['km']:g}", "date": today.isoformat(), "kind": "race", "name": f["name"],
                  "race_date": f["date"], "km": f["km"], "low": round(f["low"]), "mid": round(f["mid"]),
                  "high": round(f["high"]), "goal": f["goal"]} for f in ahead]
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    print(f"Current form ({today}):")
    print(f"  {'':<14} {'range':>19} {'likely':>8} {'pace':>7}")
    for name, km, p in now:
        if not p:
            print(f"  {name:<14} {'not enough data':>19}")
            continue
        print(f"  {name:<14} {fmt_time(p[0]):>8} - {fmt_time(p[2]):<8} {fmt_time(p[1]):>8} {fmt_pace(p[1] / km):>7}")
    where = {}
    for name, _, p in now:
        for n in (p[3] if p else []):
            where.setdefault(n, []).append(name)
    for n, names in where.items():
        print(f"  note ({', '.join(names)}): {n}")
    sources = {s for _, _, p in now if p for s in p[4]}
    if sources:
        print("  from: " + "; ".join(sorted(sources)))
    for f in ahead:
        print(f"\n{f['name']} {f['date']} ({f['km']:g} km), race-day forecast:")
        print(f"  {fmt_time(f['low'])} - {fmt_time(f['high'])}, likely {fmt_time(f['mid'])} ({fmt_pace(f['mid'] / f['km'])}/km)")
        if f["goal"]:
            print(f"  goal {fmt_time(f['goal'])}: {f['verdict']}")
        for n in f["notes"]:
            print(f"  note: {n}")
    if ahead:
        print("\nToday's level is the slow end; new races, tests and key sessions move the forecast. "
              "Re-run it in every weekly review.")


if __name__ == "__main__":
    main()
