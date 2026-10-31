#!/usr/bin/env python3
"""Turn one completed run into numbers a coach can judge: reps or steady-state drift.

Usage:
  analyze_session.py analysis.json [--lthr 174] [--threshold-pace 4:10] [--easy-cap 145] [--rftp 420]
  analyze_session.py analysis.json --json      # one row for the plan page's "sessions" collection

analysis.json is TrainingPeaks' tp_analyze_workout output: either the tool's response saved to a
file, or the file it writes itself (its "data_file", e.g. /tmp/tp-mcp/analysis/workout_<id>.json,
which also holds the time series). GPS positions in it are never read or printed.

Interval sessions (laps marked Active/Rest by the structured workout) get, per rep: distance,
time, pace, NGP, average and max HR, % of threshold speed; then pace evenness (coefficient of
variation), first-to-last change, HR at the end of reps vs LTHR, and HR drop in the recoveries.

Steady runs get aerobic decoupling (TrainingPeaks' Pa:Hr, plus our own from the time series after
a 10-minute warm-up, on grade-adjusted pace), efficiency factor (NGP speed in m/min per beat),
heart-rate drift, and time above the easy HR cap.

Thresholds are in the constants below and the reasoning in references/analysis.md.
"""
import argparse
import json
import statistics
import sys

DECOUPLING_GOOD, DECOUPLING_HIGH = 5.0, 10.0     # % (Friel / TrainingPeaks convention)
MIN_STEADY_MIN = 60                              # decoupling means little on shorter runs
WARMUP_SKIP_S = 600
REP_CV_EVEN, REP_CV_UNEVEN = 2.0, 4.0            # % pace CV across reps (practice-based)
REP_FADE = 3.0                                   # % slower last rep vs first = fading
REP_FASTER = 2.0                                 # % faster last rep vs first = pushed the end


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


def is_interval(laps):
    kinds = [l.get("Intensity") for l in laps]
    return kinds.count("Active") >= 2 and "Rest" in kinds


def analyze_intervals(laps, args):
    thr = parse_pace(args.threshold_pace) if args.threshold_pace else None
    reps = [l for l in laps if l.get("Intensity") == "Active"]
    print(f"Interval session: {len(reps)} reps")
    power = args.rftp and all(r.get("AveragePower") for r in reps)
    print(f"{'rep':>3} {'dist':>6} {'time':>6} {'pace':>6} {'NGP':>6} {'avgHR':>6} {'maxHR':>6} {'%thr':>5}"
          + (f" {'W':>5} {'%rFTP':>6}" if power else ""))
    paces = []
    for i, r in enumerate(reps, 1):
        pace = r.get("AveragePace") or (r["TotalTimerTime"] / r["TotalDistance"])
        paces.append(pace)
        pct = f"{thr / pace * 100:.0f}" if thr else "--"
        print(f"{i:>3} {r['TotalDistance']:>5.2f}k {fmt_time(r['TotalTimerTime']):>6} {fmt_pace(pace):>6} "
              f"{fmt_pace(r.get('NormalizedGradedPace')):>6} {r.get('AverageHeartRate', 0):>6} "
              f"{r.get('MaximumHeartRate', 0):>6} {pct:>5}"
              + (f" {r['AveragePower']:>5.0f} {r['AveragePower'] / args.rftp * 100:>5.0f}%" if power else ""))
    if len(paces) < 2:
        return
    mean = statistics.mean(paces)
    cv = statistics.pstdev(paces) / mean * 100
    change = (paces[-1] - paces[0]) / paces[0] * 100
    print(f"\nmean pace {fmt_pace(mean)}" + (f" ({thr / mean * 100:.0f} % of threshold speed)" if thr else ""))
    label = "even" if cv < REP_CV_EVEN else "acceptable" if cv < REP_CV_UNEVEN else "uneven"
    print(f"{'OK' if cv < REP_CV_UNEVEN else 'NOTE'} pace variation {cv:.1f} % ({label})")
    if change > REP_FADE:
        print(f"NOTE last rep {change:.1f} % slower than the first: fading (too fast a start, or fatigue)")
    elif change < -REP_FASTER:
        print(f"NOTE last rep {-change:.1f} % faster than the first: the end was pushed; "
              "fine if planned, otherwise the reps were too easy or the athlete raced them")
    else:
        print(f"OK first to last rep {change:+.1f} %")
    if args.lthr:
        last_max = reps[-1].get("MaximumHeartRate") or 0
        over = [i for i, r in enumerate(reps, 1) if (r.get("MaximumHeartRate") or 0) > args.lthr + 3]
        print(f"{'NOTE' if over else 'OK'} HR at the end of reps vs LTHR {args.lthr}: "
              f"last rep max {last_max}" + (f"; reps {over} went > LTHR + 3, i.e. above threshold" if over else ""))
        if thr and mean < thr and not over:
            print("NOTE reps faster than threshold pace without HR above LTHR: the threshold may be stale "
                  "(raise a retest)")
    drops = []
    for i, l in enumerate(laps[:-1]):
        nxt = laps[i + 1]
        if l.get("Intensity") == "Active" and nxt.get("Intensity") == "Rest" and nxt.get("MinimumHeartRate"):
            drops.append((l.get("MaximumHeartRate") or 0) - nxt["MinimumHeartRate"])
    if drops:
        print(f"recovery HR drop per rest: {', '.join(str(x) for x in drops)} bpm "
              f"(a shrinking drop through the session means accumulating fatigue)")


def series_halves(series):
    pts = []
    for p in series:
        t, hr, ngp = p.get("time"), p.get("HeartRate"), p.get("NGP")
        if t is None or not hr or not ngp or ngp <= 0 or ngp > 15 or t < WARMUP_SKIP_S:
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
    row = {"date": str(d.get("startTimestamp", ""))[:10], "km": round(total.get("Distance") or 0, 1),
           "minutes": round((total.get("Duration") or 0) / 60)}
    if is_interval(laps):
        reps = [l for l in laps if l.get("Intensity") == "Active"]
        paces = [r.get("AveragePace") or r["TotalTimerTime"] / r["TotalDistance"] for r in reps]
        row.update(kind="intervals", reps=len(reps), rep_pace=round(statistics.mean(paces)),
                   rep_cv=round(statistics.pstdev(paces) / statistics.mean(paces) * 100, 1),
                   rep_max_hr=max((r.get("MaximumHeartRate") or 0) for r in reps))
    else:
        own = series_halves(series) if series else None
        ngp, hr = total.get("NGP"), total.get("Avg heart rate")
        row.update(kind="steady", ef=round((1000 / ngp) / hr, 2) if ngp and hr else None,
                   decoupling=round(own[0], 1) if own else total.get("Pa:Hr"),
                   avg_hr=hr, gain_per_km=round((total.get("El. Gain") or 0) / max(row["km"], 1)))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("analysis")
    ap.add_argument("--lthr", type=int)
    ap.add_argument("--threshold-pace")
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
    if is_interval(laps):
        analyze_intervals(laps, args)
    else:
        analyze_steady(total, laps, series, args)


if __name__ == "__main__":
    main()
