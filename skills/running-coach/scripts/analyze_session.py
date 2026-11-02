#!/usr/bin/env python3
"""Turn one completed run into numbers a coach can judge: reps or steady-state drift.

Usage:
  analyze_session.py analysis.json [--lthr 174] [--threshold-pace 4:10] [--easy-cap 145] [--rftp 420]
  analyze_session.py analysis.json --json      # one row for the plan page's "sessions" collection

analysis.json is TrainingPeaks' tp_analyze_workout output: either the tool's response saved to a
file, or the file it writes itself (its "data_file", e.g. /tmp/tp-mcp/analysis/workout_<id>.json,
which also holds the time series). GPS positions in it are never read or printed.

Structured sessions (laps marked by the watch's workout: Warmup/Active/Rest/Cooldown):
- laps the watch split inside one workout step (auto-lap every km during a 10-min rep) are joined
  back into one rep;
- Active steps run easy (below 85 % of threshold speed, or 30 % slower than the hardest step when
  no threshold is given; e.g. a 10-min Z2 build-up) are easy parts, not reps;
- reps are grouped by kind (similar distance or time), so 2 km and 2 x 400 m are judged
  separately and nested sets (4 x (4 x 30 s)) are judged as one kind.
Per kind: distance, time, pace, graded pace (NGP), average and max HR, % of threshold speed,
evenness (coefficient of variation on graded pace), first-to-last change, HR vs LTHR and HR drop
in the recoveries. Reps under a minute skip the HR checks: heart rate lags behind short efforts.
Compare the reps with the planned paces yourself (the workout description): TrainingPeaks'
"Structure" channel follows the planned timing, not the laps actually run, so it is not used.

Steady runs get aerobic decoupling (TrainingPeaks' Pa:Hr, plus our own from the time series after
a 10-minute warm-up, on grade-adjusted pace), efficiency factor (NGP speed in m/min per beat),
heart-rate drift, and time above the easy HR cap. Unstructured runs (no workout on the watch) are
always read as steady.

Thresholds are in the constants below and the reasoning in references/analysis.md.
"""
import argparse
import json
import statistics
import sys

DECOUPLING_GOOD, DECOUPLING_HIGH = 5.0, 10.0     # % (Friel / TrainingPeaks convention)
MIN_STEADY_MIN = 60                              # decoupling means little on shorter runs
WARMUP_SKIP_S = 600
DURABILITY_MIN_S = 5400          # durability only for runs of 90+ min
DURABILITY_OK, DURABILITY_HIGH = 3.0, 6.0   # % efficiency lost late in the run (practice, cf. [S23])
REP_CV_EVEN, REP_CV_UNEVEN = 2.0, 4.0            # % pace CV across reps (practice-based)
REP_FADE = 3.0                                   # % slower last rep vs first = fading
REP_FASTER = 2.0                                 # % faster last rep vs first = pushed the end
REST_KINDS = ("Rest", "Recovery")
WORK_KINDS = ("Active", "Interval")
EASY_PCT = 85                                    # % of threshold speed: Active steps run slower are easy parts
EASY_GAP = 30                                    # % slower than the hardest step, when no threshold is given
SAME_REP = 0.10                                  # reps of one kind: within 10 % in distance or in time
SHORT_REP_S = 60                                 # under a minute HR lags the effort
LONG_REP_S = 1200                                # a rep this long also gets its own HR drift
STALE_MIN_REP_S = 180                            # stale-threshold hint only from reps of 3 min or more
STRIDES_MAX_S = 240                              # short reps adding up to 4 min at most: strides, read as steady


def parse_pace(text):
    m, s = str(text).split(":")
    return int(m) * 60 + int(s)


def fmt_pace(sec_per_km):
    if not sec_per_km or sec_per_km <= 0 or sec_per_km > 1800:
        return "--"
    s = round(sec_per_km)
    return f"{s // 60}:{s % 60:02d}"


def fmt_time(sec):
    sec = int(round(sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def load(path, raw=False):
    with open(path) as f:
        d = json.load(f)
    if raw:
        return d
    totals = d.get("totals") or {}
    if isinstance(totals, list):  # the saved data_file stores totals as a list
        totals = {t["name"]: {"value": t.get("value"), "unit": t.get("unit")} for t in totals}
    total = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in totals.items()}
    laps = [l for l in d.get("lapData", []) if (l.get("TotalDistance") or 0) >= 0.05
            and (l.get("TotalTimerTime") or 0) >= 15]
    series = d.get("data") if isinstance(d.get("data"), list) else []
    return total, laps, series


def structured(laps):
    """True when the watch ran a workout: laps carry step indexes or warm-up/rest/cool-down marks."""
    return any(l.get("WorkoutStepIndex") is not None or l.get("Intensity") in ("Warmup", "Cooldown") + REST_KINDS
               for l in laps)


def combine(laps):
    """One segment from consecutive laps: totals, time-weighted averages, graded pace."""
    t = sum(l.get("TotalTimerTime") or 0 for l in laps)
    d = sum(l.get("TotalDistance") or 0 for l in laps)
    if all((l.get("AveragePace") or 0) > 0 and l.get("TotalTimerTime") for l in laps):
        d = sum(l["TotalTimerTime"] / l["AveragePace"] for l in laps)  # lap distances are rounded to 10 m

    def avg(key):
        pts = [(l["TotalTimerTime"], l[key]) for l in laps if l.get(key) and l.get("TotalTimerTime")]
        w = sum(p[0] for p in pts)
        return sum(a * b for a, b in pts) / w if w else None

    graded = [l for l in laps if (l.get("NormalizedGradedPace") or 0) > 0 and l.get("TotalTimerTime")]
    ngp = (sum(l["TotalTimerTime"] for l in graded)
           / sum(l["TotalTimerTime"] / l["NormalizedGradedPace"] for l in graded)) if graded else None
    return {"time": t, "dist": d, "pace": t / d if d else None, "ngp": ngp,
            "hr": avg("AverageHeartRate"), "power": avg("AveragePower"),
            "hr_max": max((l.get("MaximumHeartRate") or 0) for l in laps),
            "hr_min": min((l["MinimumHeartRate"] for l in laps if l.get("MinimumHeartRate")), default=None),
            "start": laps[0].get("startOffsetSeconds"), "stop": laps[-1].get("stopOffsetSeconds")}


def segments(laps):
    """Join laps the watch split inside one workout step (auto-lap) into one segment per step."""
    segs = []
    for l in laps:
        kind = "rest" if l.get("Intensity") in REST_KINDS else l.get("Intensity")
        step = l.get("WorkoutStepIndex")
        prev = segs[-1] if segs else None
        if prev and prev["kind"] == kind and (kind == "rest" or (step is not None and step == prev["step"])):
            prev["laps"].append(l)
        else:
            segs.append({"kind": kind, "step": step, "laps": [l]})
    for i, s in enumerate(segs):
        s.update(combine(s["laps"]), i=i)
    return segs


def effort(seg):
    """Graded pace when the watch file has it (fair on hills), else plain pace."""
    return seg["ngp"] or seg["pace"]


def split_work(active, thr):
    """Reps are the Active steps run hard; the others are easy parts of the session."""
    fastest = min(effort(s) for s in active)
    work, easy = [], []
    for s in active:
        hard = thr / effort(s) * 100 >= EASY_PCT if thr else effort(s) <= fastest * (1 + EASY_GAP / 100)
        (work if hard else easy).append(s)
    return work, easy


def rep_groups(work):
    """Reps of one kind: similar distance or similar time."""
    groups = []
    for s in work:
        for g in groups:
            r = g[0]
            if abs(s["dist"] - r["dist"]) <= SAME_REP * r["dist"] or abs(s["time"] - r["time"]) <= SAME_REP * r["time"]:
                g.append(s)
                break
        else:
            groups.append([s])
    return groups


def workout(laps, thr):
    """(segments, rep groups, easy parts) of a structured session, or None for a steady read."""
    if not structured(laps):
        return None
    segs = segments(laps)
    active = [s for s in segs if s["kind"] in WORK_KINDS and effort(s)]
    if not active:
        return None
    work, easy = split_work(active, thr)
    if not work:
        return None
    return segs, rep_groups(work), easy


def is_short(group):
    return statistics.mean(r["time"] for r in group) < SHORT_REP_S


def is_strides(group):
    return is_short(group) and sum(r["time"] for r in group) <= STRIDES_MAX_S


def strides_only(plan):
    """An easy run with strides: a few short reps only. Read it as steady too."""
    return all(is_strides(g) for g in plan[1])


def series_halves(series, start=0, stop=None, skip=WARMUP_SKIP_S):
    pts = []
    for p in series:
        t, hr, ngp = p.get("time"), p.get("HeartRate"), p.get("NGP")
        if t is None or not hr or not ngp or ngp <= 0 or ngp > 15 or t < start + skip or (stop and t >= stop):
            continue
        pts.append((t, 1000 / (ngp * 60), hr))  # m/s from NGP in min/km
    if len(pts) < 20:
        return None
    mid = (pts[0][0] + pts[-1][0]) / 2
    a = [p for p in pts if p[0] < mid]
    b = [p for p in pts if p[0] >= mid]
    ra = statistics.mean(p[1] for p in a) / statistics.mean(p[2] for p in a)
    rb = statistics.mean(p[1] for p in b) / statistics.mean(p[2] for p in b)
    return (ra - rb) / ra * 100, statistics.mean(p[2] for p in a), statistics.mean(p[2] for p in b)


def durability(series, skip=WARMUP_SKIP_S):
    """Efficiency late in a long run vs. early: (% EF lost, early HR, late HR, early pace, late pace).
    Early = after the warm-up to 40 % of the run; late = the last 25 %. The drop shows how well the
    runner holds pace for the same heart rate when tired (durability [S23]); runs under 90 min: None."""
    pts = []
    for p in series:
        t, hr, ngp = p.get("time"), p.get("HeartRate"), p.get("NGP")
        if t is None or not hr or not ngp or ngp <= 0 or ngp > 15 or t < skip:
            continue
        pts.append((t, 1000 / (ngp * 60), hr))
    if len(pts) < 40 or pts[-1][0] < DURABILITY_MIN_S:
        return None
    end = pts[-1][0]
    early = [q for q in pts if q[0] <= skip + (end - skip) * 0.4]
    late = [q for q in pts if q[0] >= end * 0.75]
    if len(early) < 10 or len(late) < 10:
        return None
    ef = lambda xs: statistics.mean(q[1] for q in xs) / statistics.mean(q[2] for q in xs)
    pace = lambda xs: 1000 / statistics.mean(q[1] for q in xs)
    return ((ef(early) - ef(late)) / ef(early) * 100, statistics.mean(q[2] for q in early),
            statistics.mean(q[2] for q in late), pace(early), pace(late))


def describe(group):
    dist = statistics.mean(r["dist"] for r in group)
    secs = statistics.mean(r["time"] for r in group)
    return f"{len(group)} x {dist:.2f} km (~{fmt_time(secs)})"


def analyze_group(n, group, segs, series, args, thr):
    if is_strides(group):
        mean = statistics.mean(effort(r) for r in group)
        print(f"Strides: {describe(group)}, mean graded pace {fmt_pace(mean)}"
              + (f" = {thr / mean * 100:.0f} % of threshold speed" if thr else "")
              + " (short accelerations; GPS pace over 20-30 s is rough, so no evenness check)")
        return
    print(f"Reps, kind {n}: {describe(group)}")
    power = args.rftp and all(r["power"] for r in group)
    print(f"{'rep':>3} {'dist':>6} {'time':>7} {'pace':>6} {'NGP':>6} {'avgHR':>6} {'maxHR':>6} {'%thr':>5}"
          + (f" {'W':>5} {'%rFTP':>6}" if power else ""))
    for i, r in enumerate(group, 1):
        pct = f"{thr / effort(r) * 100:.0f}" if thr else "--"
        print(f"{i:>3} {r['dist']:>5.2f}k {fmt_time(r['time']):>7} {fmt_pace(r['pace']):>6} {fmt_pace(r['ngp']):>6} "
              f"{r['hr'] or 0:>6.0f} {r['hr_max']:>6} {pct:>5}"
              + (f" {r['power']:>5.0f} {r['power'] / args.rftp * 100:>5.0f}%" if power else ""))
    paces = [effort(r) for r in group]
    mean = statistics.mean(paces)
    short = is_short(group)
    line = f"mean graded pace {fmt_pace(mean)}"
    if thr:
        line += f" = {thr / mean * 100:.0f} % of threshold speed"
    print(line)
    if len(paces) >= 2:
        cv = statistics.pstdev(paces) / mean * 100
        change = (paces[-1] - paces[0]) / paces[0] * 100
        label = "even" if cv < REP_CV_EVEN else "acceptable" if cv < REP_CV_UNEVEN else "uneven"
        print(f"{'OK' if cv < REP_CV_UNEVEN else 'NOTE'} pace variation {cv:.1f} % ({label})")
        if change > REP_FADE:
            print(f"NOTE last rep {change:.1f} % slower than the first: fading (too fast a start, or fatigue)")
        elif change < -REP_FASTER:
            print(f"NOTE last rep {-change:.1f} % faster than the first: the end was pushed; "
                  "fine if planned, otherwise the reps were too easy or the athlete raced them")
        else:
            print(f"OK first to last rep {change:+.1f} %")
    if short:
        print("note: reps under a minute; heart rate lags behind them, so judge them by pace (or power), not HR")
        return
    if args.lthr:
        over = [i for i, r in enumerate(group, 1) if r["hr_max"] > args.lthr + 3]
        print(f"{'NOTE' if over else 'OK'} HR at the end of reps vs LTHR {args.lthr}: "
              f"last rep max {group[-1]['hr_max']}" + (f"; reps {over} went > LTHR + 3, i.e. above threshold" if over else ""))
        if thr and mean < thr and not over and statistics.mean(r["time"] for r in group) >= STALE_MIN_REP_S:
            print("NOTE reps faster than threshold pace without HR above LTHR: the threshold may be stale "
                  "(raise a retest)")
    drops = []
    for r in group:
        nxt = segs[r["i"] + 1] if r["i"] + 1 < len(segs) else None
        if nxt and nxt["kind"] == "rest" and nxt["hr_min"] and nxt["time"] >= 45:
            drops.append(r["hr_max"] - nxt["hr_min"])
    if drops:
        print(f"recovery HR drop per rest: {', '.join(str(x) for x in drops)} bpm"
              + (" (a shrinking drop through the session means accumulating fatigue)" if len(drops) > 1 else ""))
    for i, r in enumerate(group, 1):
        if r["time"] >= LONG_REP_S and series:
            own = series_halves(series, r["start"] or 0, r["stop"], skip=180)
            if own:
                print(f"rep {i}: HR drift within the rep {own[0]:.1f} % (after its first 3 min; "
                      f"HR {own[1]:.0f} -> {own[2]:.0f})")


def analyze_workout(plan, series, args, thr):
    segs, groups, easy = plan
    print(f"Structured session: {sum(len(g) for g in groups)} reps in {len(groups)} kind(s)")
    for part in easy:
        print(f"easy part: {part['dist']:.1f} km in {fmt_time(part['time'])} at {fmt_pace(part['pace'])}/km, "
              f"HR {part['hr'] or 0:.0f} (not a rep)")
    for n, g in enumerate(groups, 1):
        print()
        analyze_group(n, g, segs, series, args, thr)


def analyze_steady(total, laps, series, args):
    dur = total.get("Duration") or sum(l.get("TotalTimerTime", 0) for l in laps)
    dist = total.get("Distance") or sum(l.get("TotalDistance", 0) for l in laps)
    ngp = total.get("NGP")  # min/km as a decimal number
    hr = total.get("Avg heart rate")
    gain = total.get("El. Gain") or 0
    print(f"Steady run: {fmt_time(dur)}, {dist:.1f} km, NGP {fmt_pace(ngp * 60) if ngp else '--'}/km, "
          f"avg HR {hr}, gain {gain:.0f} m ({gain / dist:.0f} m/km)" if dist else "Steady run")
    if ngp and hr:
        ef = (1000 / ngp) / hr
        print(f"efficiency factor {ef:.2f} (NGP m/min per beat; compare with the runner's own similar runs, "
              f"higher = fitter)")
    tp_dec = total.get("Pa:Hr")
    if total.get("Pw:Hr") is not None:
        notes_pw = f"TrainingPeaks Pw:Hr (power-based) {total['Pw:Hr']:.1f} %"
        if gain / max(dist, 1) >= 10:
            notes_pw += " (on hills power is the fairer measure of effort than graded pace)"
        print(notes_pw)
    if args.rftp and total.get("NP"):
        print(f"normalized power {total['NP']:.0f} W = {total['NP'] / args.rftp * 100:.0f} % of rFTP")
    own = series_halves(series) if series else None
    if dur / 60 < MIN_STEADY_MIN:
        print(f"NOTE {dur / 60:.0f} min is short for decoupling; read it loosely")
    for name, value in (("TrainingPeaks Pa:Hr", tp_dec), ("decoupling after warm-up", own[0] if own else None)):
        if value is None:
            continue
        verdict = ("OK", "good aerobic durability") if value < DECOUPLING_GOOD else \
            ("NOTE", "moderate drift") if value < DECOUPLING_HIGH else ("NOTE", "large drift")
        print(f"{verdict[0]} {name} {value:.1f} % ({verdict[1]})")
    if own:
        print(f"HR first half {own[1]:.0f} -> second half {own[2]:.0f} bpm")
    dura = durability(series) if series else None
    if dura:
        drop, h1, h2, p1, p2 = dura
        verdict = "OK" if drop < DURABILITY_OK else "NOTE"
        what = "holds well when tired" if drop < DURABILITY_OK else "moderate fade late" if drop < DURABILITY_HIGH \
            else "large fade late: a marathon limiter"
        print(f"{verdict} durability: efficiency {drop:+.1f} % lost in the last quarter vs. early "
              f"({fmt_pace(p1)}/km at {h1:.0f} bpm -> {fmt_pace(p2)}/km at {h2:.0f} bpm; {what})")
    if (own or tp_dec) and gain / max(dist, 1) >= 10:
        print("note: hilly route; NGP corrects pace for gradient, but descents and heat still distort drift")
    if args.easy_cap and series:
        hrs = [p.get("HeartRate") for p in series if p.get("HeartRate")]
        above = sum(1 for h in hrs if h > args.easy_cap) / len(hrs) * 100 if hrs else 0
        print(f"{'OK' if above < 10 else 'NOTE'} {above:.0f} % of the run above the easy cap {args.easy_cap}")


def summary_row(path, args):
    """Date, type and the key numbers of one session, for the plan page."""
    d = load(path, raw=True)
    total, laps, series = load(path)
    thr = parse_pace(args.threshold_pace) if args.threshold_pace else None
    row = {"date": str(d.get("startTimestamp", ""))[:10], "km": round(total.get("Distance") or 0, 1),
           "minutes": round((total.get("Duration") or 0) / 60)}
    plan = workout(laps, thr)
    main = max(plan[1], key=lambda g: sum(r["time"] for r in g)) if plan and not strides_only(plan) else None
    if main:
        paces = [r["pace"] for r in main]
        graded = [effort(r) for r in main]
        row.update(kind="intervals", reps=len(main), rep_km=round(statistics.mean(r["dist"] for r in main), 2),
                   rep_pace=round(statistics.mean(paces)),
                   rep_cv=round(statistics.pstdev(graded) / statistics.mean(graded) * 100, 1),
                   rep_max_hr=max(r["hr_max"] for r in main))
    else:
        own = series_halves(series) if series else None
        ngp, hr = total.get("NGP"), total.get("Avg heart rate")
        dura = durability(series) if series else None
        row.update(kind="steady", ef=round((1000 / ngp) / hr, 2) if ngp and hr else None,
                   durability=round(dura[0], 1) if dura else None,
                   decoupling=round(own[0], 1) if own else total.get("Pa:Hr"),
                   avg_hr=hr, gain_per_km=round((total.get("El. Gain") or 0) / max(row["km"], 1)))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("analysis")
    ap.add_argument("--lthr", type=int)
    ap.add_argument("--threshold-pace", help="threshold pace, e.g. 4:10")
    ap.add_argument("--easy-cap", type=int, help="easy-run HR cap, e.g. 145")
    ap.add_argument("--rftp", type=float, help="running FTP in watts (adds power columns)")
    ap.add_argument("--json", action="store_true", help="one summary row (plan page sessions)")
    ap.add_argument("--title", help="session title to include in the --json row")
    args = ap.parse_args()
    if args.json:
        row = summary_row(args.analysis, args)
        if args.title:
            row["title"] = args.title
        print(json.dumps(row, ensure_ascii=False))
        return
    try:
        total, laps, series = load(args.analysis)
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"error: {e}")
    thr = parse_pace(args.threshold_pace) if args.threshold_pace else None
    plan = workout(laps, thr)
    if not plan:
        analyze_steady(total, laps, series, args)
        return
    analyze_workout(plan, series, args, thr)
    if strides_only(plan):
        print()
        analyze_steady(total, laps, series, args)


if __name__ == "__main__":
    main()
