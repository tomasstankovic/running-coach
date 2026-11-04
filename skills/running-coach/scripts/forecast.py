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
  "ctl": 28,                                   # optional: CTL today (tp_get_fitness); enables the projection
  "weekly_tss": 290,                           # optional: mean weekly run TSS, last 8 weeks (calibrates the plan's TSS)
  "history": [                                 # optional: earlier best races and the volume behind them
    {"date": "2025-04-27", "km": 21.0975, "time": "1:31:40", "weekly_km": 55, "ctl": 44},
    {"date": "2025-05-25", "km": 42.195, "time": "3:22:47", "weekly_km": 58, "ctl": 48,
     "steady_pace": "4:38"}                    # marathon only, if it faded: pace to km 30
  ],                                           # ctl: CTL on race day (tp_get_fitness for that date)
  "checks": [                                  # optional without a plan: each race's milestones
    {"race": "2027-04-25", "date": "2027-03-07", "name": "30 km, 3 x 4 km at M", "result": "held"},
    {"race": "2027-03-21", "date": "2027-02-12", "name": "2 x 5 km at HM pace", "result": "partly"}
  ],                                           # result: held | partly | faded | planned
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
- Projection to race day ("if the plan happens"): shown next to the forecast, never mixed into it.
  It needs "ctl", the plan's weekly "tss" and at least one history result with its "ctl". The
  plan's TSS, rescaled to the runner's own TSS per km ("weekly_tss"; without it the plan's own
  estimate is used, as CTL lags behind the load in a build), is run forward through the CTL
  formula (42-day average) to the race day. The runner's own results against their CTL then give
  their personal slope (how much faster per point of CTL), on a log scale, in two ways: with
  today's level as one point, and from the earlier results alone. They differ when the runner has
  changed since (today faster at a lower CTL than before: the first is flatter), so the middle
  uses their mean, the fast end the steeper and the slow end the flatter. Slopes are held between
  0.05 and 0.4 % per CTL point, and CTL beyond 15 % above the highest the runner has raced at is
  not extrapolated. The fast end assumes the whole plan, the slow end 80 % of its load. For the
  marathon the projected half goes through the runner's own marathon/half ratio, corrected for
  the planned volume with Vickers model 1, or through Vickers model 1 alone without that history.
  When that marathon faded ("steady_pace", the pace to km 30), it gives two ratios: as run (the
  fade comes back: slow end) and at the steady pace (no fade: fast end). The middle starts with
  half of the fade.
- Checks: each race's milestones move the middle, with evidence instead of hope. With a plan they
  are its key sessions marked as milestones of that race ("race": its date; season_plan.py roads),
  their result the review's "check" (held / partly / faded), else the verdict (on target or better:
  held, under: partly; missed ones don't count); without a plan, "checks" in the input. A
  marathon's checks (long runs with marathon pace) move the share of the fade:
  every one held takes a share of it away, every one faded adds it back, so a block of checks all
  held ends at the no-fade time. The checks of a race up to 25 km (threshold test, sessions at race
  pace) move the middle between the flatter and the steeper slope the same way, for that race and
  for the half a marathon is built on. A test or tune-up race also goes in as a result: that moves
  the whole forecast.
  It is the runner's history applied to the plan, not evidence of fitness: re-run it every week,
  and trust the forecast when the two disagree.
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
FADE_START = 0.5                       # share of an earlier marathon's fade assumed before the checks show otherwise
SLOPE_START = 0.5                      # where the middle sits between the flatter and the steeper slope, before checks
CHECK_CREDIT = {"held": 1.0, "partly": 0.5, "faded": -1.0, "planned": 0.0}
CTL_DAYS = 42                          # TrainingPeaks CTL time constant
SLOPE_RANGE = (0.0005, 0.004)          # personal gain per CTL point on log time: 0.05-0.4 % (guardrail)
SLOPE_DEFAULT = 0.0015                 # used when the history gives no usable slope
CTL_STRETCH = 1.15                     # no extrapolation beyond 15 % above the highest raced CTL
PLAN_SHORTFALL = 0.8                   # slow end of the projection: 80 % of the planned load
PROJ_SPREAD = 1.0                      # % either side of the projection, at least
TSS_SCALE = (0.7, 1.4)                 # how far the runner's own TSS per km may rescale the plan's estimate
HALF = 21.0975


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


def tss_scale(inp, plan):
    """The plan's TSS is a rough estimate per hour; rescale it to the runner's own TSS per km
    (weekly_tss, or CTL x 7 as the recent daily load) so the projected CTL is on their scale."""
    weeks = [w for w in plan.get("weeks", []) if w.get("tss") and w.get("km")]
    km = inp.get("weekly_km")
    own = inp.get("weekly_tss")
    if weeks and km and not own:
        return 1.0, "no weekly_tss: the plan's own TSS estimate is used"
    if not weeks or not km:
        return 1.0, None
    planned = sum(w["tss"] for w in weeks) / sum(w["km"] for w in weeks)
    raw = own / km / planned
    scale = min(max(raw, TSS_SCALE[0]), TSS_SCALE[1])
    if abs(scale - 1) < 0.05:
        return 1.0, None
    return scale, f"plan TSS x {scale:.2f} to match your own {own / km:.1f} TSS per km"


def project_ctl(plan, ctl, today, until, share=1.0):
    """CTL on `until` if `share` of each planned week's TSS is done from tomorrow on."""
    weekly = {date.fromisoformat(w["week_start"]): w.get("tss") or 0 for w in plan.get("weeks", [])}
    d = today
    while d < until:
        d += timedelta(days=1)
        tss = weekly.get(d - timedelta(days=d.weekday()), 0) * share / 7
        ctl += (tss - ctl) / CTL_DAYS
    return ctl


def fit_slope(points):
    """Least-squares slope of log(time) on CTL as a positive gain per CTL point, within SLOPE_RANGE;
    None when the points are too few or all at about the same CTL."""
    if len(points) < 2:
        return None
    xs, ys = [c for c, _ in points], [math.log(t) for _, t in points]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 25:  # all at about the same CTL: nothing to learn from
        return None
    gain = -sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return min(max(gain, SLOPE_RANGE[0]), SLOPE_RANGE[1])


def personal_slopes(now_point, history):
    """(flat, steep, note): the slope with today's level as a point and from the earlier results
    alone. A runner who is faster today at a lower CTL than before makes the first one flatter."""
    found = [g for g in (fit_slope([now_point] + history), fit_slope(history)) if g is not None]
    if not found:
        return SLOPE_DEFAULT, SLOPE_DEFAULT, "history at a similar CTL: default slope"
    flat, steep = min(found), max(found)
    note = (f"personal slope {flat * 100:.2f}-{steep * 100:.2f} % per CTL point (with today's level / earlier races alone)"
            if steep - flat > 0.0001 else f"personal slope {flat * 100:.2f} % per CTL point")
    return flat, steep, note


def projection(inp, race, plan, today):
    """Race-day time if the plan happens, from the runner's own results against their CTL.
    Returns (low, mid, high, notes) or None when the inputs are missing."""
    km = race.get("distance_km") or race.get("km")
    ctl_now = inp.get("ctl")
    hist = [h for h in inp.get("history", []) if h.get("ctl") is not None]
    if ctl_now is None or not plan or not hist or not any(w.get("tss") for w in plan.get("weeks", [])):
        return None
    rdate = date.fromisoformat(race["date"])
    ref = km if km <= 25 else HALF               # the curve is built on the half (or the race distance up to 25 km)
    now = level(inp, ref, today)
    if not now:
        return None
    earlier = [(h["ctl"], riegel(parse_time(h["time"]), h["km"], ref)) for h in hist if h["km"] <= 25]
    flat, steep, slope_note = personal_slopes((ctl_now, now[1]), earlier)
    cap = max([ctl_now] + [c for c, _ in earlier]) * CTL_STRETCH
    scale, scale_note = tss_scale(inp, plan)
    full = project_ctl(plan, ctl_now, today, rdate, scale)
    short = project_ctl(plan, ctl_now, today, rdate, scale * PLAN_SHORTFALL)
    notes = [f"CTL {ctl_now:.0f} today -> {full:.0f} on race day with the whole plan ({short:.0f} with 80 % of it)",
             slope_note] + ([scale_note] if scale_note else [])
    if full > cap:
        notes.append(f"CTL above {cap:.0f} is beyond your racing history: not extrapolated")
    w, w_note = slope_weight(inp, race["date"])
    if w_note:
        notes.append(w_note)
    at = lambda c, g: now[1] * math.exp(-g * (min(c, cap) - ctl_now))
    fast, mid, slow = at(full, steep), at(full, flat + w * (steep - flat)), at(short, flat)
    if km > 25:
        planned = planned_volume(plan, rdate)
        r = marathon_ratios(inp, mid, planned, notes, race["date"])
        if r is None:
            return None
        fast, mid, slow = fast / mid * r[0], r[1], slow / mid * r[2]
    spread = PROJ_SPREAD / 100
    return min(fast, mid * (1 - spread)), mid, max(slow, mid * (1 + spread)), notes


def race_checks(inp, race_date=None, long=None):
    """Checks for one race (by date), or for all races of one kind (long: marathon, else up to 25 km)."""
    out = []
    for c in inp.get("checks", []):
        if c.get("result") not in CHECK_CREDIT:
            continue
        if race_date is not None and c.get("race") != race_date:
            continue
        if long is not None and ((c.get("race_km") or 0) > 30) != long:
            continue
        out.append(c)
    return out


def check_credit(checks, what):
    """(credit from -1 to 1, note): held +1, partly +0.5, faded -1, planned 0, averaged."""
    if not checks:
        return 0.0, None
    credit = sum(CHECK_CREDIT[c["result"]] for c in checks) / len(checks)
    done = [c["result"] for c in checks if c["result"] != "planned"]
    return credit, f"{what}: {len(done)} of {len(checks)} done ({', '.join(done) or 'none yet'})"


def fade_share(inp, race_date):
    """(share of an earlier marathon's fade assumed on race day, note), from that race's checks."""
    credit, note = check_credit(race_checks(inp, race_date), "marathon checks")
    share = min(max(FADE_START * (1 - credit), 0.0), 1.0)
    return share, (f"{note}: {share * 100:.0f} % of the fade assumed" if note else None)


def slope_weight(inp, race_date=None):
    """Where the middle sits between the flatter (0) and the steeper (1) slope: the checks of the
    race itself when it is up to 25 km, else those of the races up to 25 km (the half under a marathon)."""
    checks = race_checks(inp, race_date) if race_date else []
    if not checks or (checks[0].get("race_km") or 0) > 30:
        checks = race_checks(inp, long=False)
    credit, note = check_credit(checks, "race-pace checks")
    w = min(max(SLOPE_START * (1 + credit), 0.0), 1.0)
    return w, (f"{note}: the middle at {w * 100:.0f} % of the way to the steeper slope" if note else None)


def marathon_ratios(inp, half, planned_km, notes=None, race_date=None):
    """(fast, mid, slow) marathon times from a half-marathon time: the runner's own marathon/half
    ratio at the volume they had then, moved to the planned volume by Vickers model 1. A faded
    marathon ("steady_pace") gives the no-fade ratio for the fast end and, with the share of the
    fade still assumed (fade_share), the middle. Without a marathon in the history: Vickers alone."""
    if not planned_km:
        return None
    miles = lambda km: km / 1.609344
    v_plan = vickers_model1(HALF * 1000, half, miles(planned_km))
    hist = inp.get("history", [])
    for m in sorted((h for h in hist if h["km"] > 40 and h.get("weekly_km")), key=lambda h: h["date"], reverse=True):
        mdate = date.fromisoformat(m["date"])
        halves = [h for h in hist if abs(h["km"] - HALF) < 0.3 and 0 <= (mdate - date.fromisoformat(h["date"])).days <= 70]
        if not halves:
            continue
        h = max(halves, key=lambda h: h["date"])
        actual = parse_time(m["time"]) / parse_time(h["time"])
        move = v_plan / vickers_model1(HALF * 1000, half, miles(m["weekly_km"]))
        steady = parse_pace(m["steady_pace"]) * m["km"] / parse_time(h["time"]) if m.get("steady_pace") else actual
        steady = min(steady, actual)
        share, check_note = fade_share(inp, race_date)
        mid = steady + share * (actual - steady)
        if notes is not None:
            notes.append(f"your marathon/half ratio {actual:.3f} ({m['time']} after {h['time']} at {m['weekly_km']:g} km/week), "
                         f"moved to {planned_km:.0f} km/week")
            if steady < actual:
                notes.append(f"that marathon faded after km 30 ({m['steady_pace']}/km before): {steady:.3f} without the fade; "
                             f"the middle assumes {share * 100:.0f} % of it")
                if check_note:
                    notes.append(check_note)
        return half * steady * move, half * mid * move, half * actual * move
    if notes is not None:
        notes.append(f"no marathon in your history: Vickers model 1 with {planned_km:.0f} km/week")
    return v_plan, v_plan, v_plan


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
    out = {"name": race.get("name", f"{km:g} km"), "date": race["date"], "km": km, "low": low, "mid": mid,
           "high": high, "goal": goal, "verdict": verdict, "notes": notes, "planned_km": planned}
    proj = projection(inp, race, plan, today)
    if proj:
        adj = (adj_lo + adj_hi) / 200
        out.update(proj_low=proj[0] * (1 + adj_lo / 100), proj_mid=proj[1] * (1 + adj), proj_high=proj[2] * (1 + adj_hi / 100),
                   proj_notes=proj[3])
        if goal:
            pl, ph = out["proj_low"], out["proj_high"]
            out["proj_verdict"] = ("inside the projection" if pl <= goal <= ph else
                                   "slower than the projection: safe if the plan happens" if goal > ph else
                                   f"{(pl - goal) / pl * 100:.1f} % faster than the projection's fast end")
    return out


VERDICT_CHECK = {"on": "held", "over": "held", "under": "partly"}


def plan_checks(plan):
    """The plan's milestones as checks: {race, date, name, result}; [] without a plan or roads."""
    out = []
    for w in (plan or {}).get("weeks", []):
        for s in w.get("key_sessions", []):
            if not (s.get("milestone") and s.get("race")):
                continue
            act = s.get("actual") or {}
            result = act.get("check") or VERDICT_CHECK.get(act.get("verdict")) or ("planned" if not act else None)
            if result:
                out.append({"race": s["race"], "date": s["date"], "name": s["title"], "result": result})
    return out


def load(path):
    with open(path) as f:
        inp = json.load(f)
    plan = None
    if inp.get("plan"):
        with open(inp["plan"]) as f:
            plan = json.load(f)
    races = inp.get("races") or (plan or {}).get("spec", {}).get("races", [])
    today = date.fromisoformat(inp["today"]) if inp.get("today") else date.today()
    km_of = {r["date"]: r.get("distance_km") or r.get("km") for r in races}
    from_plan = plan_checks(plan)
    if from_plan:
        inp["checks"] = from_plan
    for c in inp.get("checks", []):
        c["race_km"] = km_of.get(c.get("race"))
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
                  "high": round(f["high"]), "goal": f["goal"],
                  **({k: round(f[k]) for k in ("proj_low", "proj_mid", "proj_high")} if "proj_mid" in f else {})}
                 for f in ahead]
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
        if "proj_mid" in f:
            print(f"  if the plan happens: {fmt_time(f['proj_low'])} - {fmt_time(f['proj_high'])}, "
                  f"likely {fmt_time(f['proj_mid'])} ({fmt_pace(f['proj_mid'] / f['km'])}/km)")
            if f["goal"]:
                print(f"  goal {fmt_time(f['goal'])}: {f['proj_verdict']}")
            for n in f["proj_notes"]:
                print(f"  projection: {n}")
    if ahead:
        print("\nToday's level is the slow end; new races, tests and key sessions move the forecast. "
              "Re-run it in every weekly review.")


if __name__ == "__main__":
    main()
