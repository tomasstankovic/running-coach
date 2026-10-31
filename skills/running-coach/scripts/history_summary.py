#!/usr/bin/env python3
"""Condense 1-2 years of training into seasons, peaks, breaks, likely races and best efforts.

Usage:
  history_summary.py --fitness fitness.json [--fitness older.json ...] [--peaks peaks.json ...]
  history_summary.py --weeks weeks.json      # weekly totals, e.g. built from Strava activities

--fitness   tp_get_fitness output with start_date/end_date (daily tss/ctl/atl/tsb); several files
            (e.g. one per year) are merged.
--peaks     tp_get_peaks output (e.g. pr_type speed10K / speedHalfMarathon, days 730).
--weeks     [{"week_start": "2025-11-03", "minutes": 240, "km": 40, "long_min": 90}, ...]

Prints: monthly table, peak fitness, build blocks, breaks, likely races and best efforts, and
where the runner is now relative to their peak. That's the long view onboarding needs ("how did I
run last spring?") without reading hundreds of workouts.
"""
import argparse
import json
from collections import OrderedDict
from datetime import date, timedelta


def load_fitness(paths):
    days = {}
    for p in paths:
        with open(p) as f:
            data = json.load(f)
        for row in data.get("daily_data", data if isinstance(data, list) else []):
            days[row["date"][:10]] = row
    return [days[k] for k in sorted(days)]


def fmt_pace(speed):
    if not speed:
        return "--"
    sec = round(1000 / speed)
    return f"{sec // 60}:{sec % 60:02d}"


def summarize_fitness(rows):
    if not rows:
        return
    print("## Monthly overview (TrainingPeaks fitness)")
    print(f"{'month':<8} {'TSS/wk':>7} {'CTL start→end':>14} {'CTL max':>8} {'days off':>9}")
    months = OrderedDict()
    for r in rows:
        months.setdefault(r["date"][:7], []).append(r)
    for m, rs in months.items():
        weeks = len(rs) / 7
        tss = sum(r.get("tss") or 0 for r in rs)
        off = sum(1 for r in rs if not r.get("tss"))
        print(f"{m:<8} {tss / weeks:>7.0f} {rs[0]['ctl']:>6.1f} → {rs[-1]['ctl']:<5.1f} "
              f"{max(r['ctl'] for r in rs):>8.1f} {off:>5}/{len(rs)}")

    peak = max(rows, key=lambda r: r["ctl"])
    now = rows[-1]
    print()
    print(f"Peak fitness: CTL {peak['ctl']:.1f} on {peak['date']}")
    print(f"Now ({now['date']}): CTL {now['ctl']:.1f} = {now['ctl'] / peak['ctl'] * 100:.0f} % of peak")

    # build blocks: CTL rising >= 10 points from a local low within <= 16 weeks
    print("\n## Build blocks (CTL +10 or more)")
    i, found = 0, False
    while i < len(rows):
        low = rows[i]
        j_best = None
        for j in range(i + 1, min(i + 112, len(rows))):
            if rows[j]["ctl"] < low["ctl"] - 2:
                break
            if rows[j]["ctl"] - low["ctl"] >= 10 and (j_best is None or rows[j]["ctl"] > rows[j_best]["ctl"]):
                j_best = j
        if j_best:
            hi = rows[j_best]
            wks = (date.fromisoformat(hi["date"]) - date.fromisoformat(low["date"])).days / 7
            ramp = (hi["ctl"] - low["ctl"]) / max(wks, 1)
            print(f"  {low['date']} → {hi['date']}: CTL {low['ctl']:.0f} → {hi['ctl']:.0f} "
                  f"over {wks:.0f} weeks ({ramp:+.1f}/week)")
            found = True
            i = j_best + 1
        else:
            i += 1
    if not found:
        print("  none")

    # breaks: 7+ consecutive days without training
    print("\n## Breaks (7+ days without training)")
    run, start, found = 0, None, False
    for r in rows + [{"date": "9999-12-31", "tss": 1}]:
        if not r.get("tss"):
            run += 1
            start = start or r["date"]
        else:
            if run >= 7:
                print(f"  {start}: {run} days")
                found = True
            run, start = 0, None
    if not found:
        print("  none")

    # likely races: a big day (>= 120 TSS and >= 2.5x the 6-week average daily load) reached fresh
    print("\n## Likely races (big effort after a taper)")
    found = False
    for k in range(1, len(rows)):
        r, prev = rows[k], rows[k - 1]
        window = rows[max(0, k - 42):k]
        avg = sum(x.get("tss") or 0 for x in window) / max(len(window), 1)
        if (r.get("tss") or 0) >= max(120, 2.5 * avg) and prev["tsb"] >= 5:
            print(f"  {r['date']}: TSS {r['tss']:.0f}, TSB before {prev['tsb']:+.0f}, CTL {r['ctl']:.0f}")
            found = True
    if not found:
        print("  none detected")


def summarize_peaks(paths):
    for p in paths:
        with open(p) as f:
            data = json.load(f)
        recs = data.get("records", [])
        if not recs:
            continue
        print(f"\n## Best efforts: {data.get('pr_type', '?')} (last {data.get('days', '?')} days)")
        for r in recs[:8]:
            print(f"  {r['date']}  {fmt_pace(r['value'])}/km  {r.get('workout_title', '')}")


def summarize_weeks(path):
    with open(path) as f:
        weeks = sorted(json.load(f), key=lambda w: w["week_start"])
    if not weeks:
        return
    print("## Monthly overview (weekly totals)")
    print(f"{'month':<8} {'h/week':>7} {'km/week':>8} {'longest':>8} {'weeks off':>10}")
    months = OrderedDict()
    for w in weeks:
        months.setdefault(w["week_start"][:7], []).append(w)
    for m, ws in months.items():
        mins = [w.get("minutes", 0) for w in ws]
        print(f"{m:<8} {sum(mins) / len(ws) / 60:>7.1f} {sum(w.get('km', 0) for w in ws) / len(ws):>8.0f} "
              f"{max(w.get('long_min', 0) for w in ws):>6.0f}m {sum(1 for x in mins if x == 0):>6}/{len(ws)}")
    peak = max(weeks, key=lambda w: w.get("minutes", 0))
    recent = weeks[-4:]
    now = sum(w.get("minutes", 0) for w in recent) / len(recent)
    print(f"\nBiggest week: {peak['week_start']} ({peak.get('minutes', 0) / 60:.1f} h, {peak.get('km', 0):.0f} km)")
    print(f"Last 4 weeks average: {now / 60:.1f} h = {now / max(peak.get('minutes', 1), 1) * 100:.0f} % of the biggest week")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fitness", action="append", default=[])
    ap.add_argument("--peaks", action="append", default=[])
    ap.add_argument("--weeks")
    args = ap.parse_args()
    if not (args.fitness or args.weeks or args.peaks):
        ap.error("pass --fitness, --weeks and/or --peaks")
    if args.fitness:
        summarize_fitness(load_fitness(args.fitness))
    if args.weeks:
        summarize_weeks(args.weeks)
    if args.peaks:
        summarize_peaks(args.peaks)


if __name__ == "__main__":
    main()
