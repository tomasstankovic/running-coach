#!/usr/bin/env python3
"""Daily readiness from HRV, resting HR and sleep, compared with the runner's own baseline.

Usage:
  readiness.py metrics.json [--date 2026-10-31]

metrics.json is either the raw tp_get_metrics output (pass 21-28 days), or a simple list:
  [{"date": "2026-10-30", "hrv": 46, "rhr": 50, "sleep_h": 7.6}, ...]

Baseline = the days before the checked date (up to 28). Prints GREEN / AMBER / RED with reasons.
Needs at least 7 baseline days for HRV and resting HR; otherwise it says so.
"""
import argparse
import json
import statistics
import sys

TP_LABELS = {"HRV": "hrv", "Pulse": "rhr", "Sleep Hours": "sleep_h"}


def load(path):
    with open(path) as f:
        data = json.load(f)
    days = {}
    if isinstance(data, dict) and "metrics" in data:  # tp_get_metrics
        for entry in data["metrics"]:
            d = entry["timeStamp"][:10]
            row = days.setdefault(d, {"date": d})
            for det in entry.get("details", []):
                key = TP_LABELS.get(det.get("label"))
                if key and isinstance(det.get("value"), (int, float)):
                    row[key] = float(det["value"])
    else:
        for row in data:
            days[row["date"][:10]] = dict(row)
    return [days[k] for k in sorted(days)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("metrics_json")
    ap.add_argument("--date", help="day to assess (default: latest day in the file)")
    args = ap.parse_args()

    rows = load(args.metrics_json)
    if not rows:
        sys.exit("no metrics found")
    target = args.date or rows[-1]["date"]
    today = next((r for r in rows if r["date"] == target), None)
    if today is None:
        sys.exit(f"no metrics for {target}")
    base = [r for r in rows if r["date"] < target][-28:]

    flags, notes = [], []

    def baseline(key):
        vals = [r[key] for r in base if key in r]
        if len(vals) < 7:
            return None
        return statistics.mean(vals), statistics.pstdev(vals) or 1.0, len(vals)

    # HRV: today and the 3-day average against the baseline's normal range (mean ± 1 SD)
    b = baseline("hrv")
    if "hrv" in today and b:
        mean, sd, n = b
        recent = [r["hrv"] for r in base[-2:] if "hrv" in r] + [today["hrv"]]
        avg3 = statistics.mean(recent)
        z = (today["hrv"] - mean) / sd
        notes.append(f"HRV {today['hrv']:.0f} (3-day {avg3:.0f}) vs baseline {mean:.0f} ± {sd:.0f} ({n} days)")
        if z < -2:
            flags.append(("red", "HRV far below normal"))
        elif z < -1 or avg3 < mean - sd:
            flags.append(("amber", "HRV below normal range"))
    elif "hrv" in today:
        notes.append(f"HRV {today['hrv']:.0f} (fewer than 7 baseline days, not judged)")

    b = baseline("rhr")
    if "rhr" in today and b:
        mean, sd, n = b
        diff = today["rhr"] - mean
        notes.append(f"resting HR {today['rhr']:.0f} vs baseline {mean:.0f} ({diff:+.0f})")
        if diff >= 8:
            flags.append(("red", "resting HR clearly elevated"))
        elif diff >= 5:
            flags.append(("amber", "resting HR elevated"))

    if "sleep_h" in today:
        notes.append(f"sleep {today['sleep_h']:.1f} h")
        if today["sleep_h"] < 5:
            flags.append(("amber", "very short sleep"))
        elif today["sleep_h"] < 6:
            flags.append(("amber", "short sleep"))

    reds = [m for lvl, m in flags if lvl == "red"]
    ambers = [m for lvl, m in flags if lvl == "amber"]
    if reds or len(ambers) >= 3:
        verdict = "RED"
    elif len(ambers) == 2:
        verdict = "AMBER (2 flags)"
    elif ambers:
        verdict = "AMBER (1 flag)"
    else:
        verdict = "GREEN"

    # trend: HRV 7-day mean vs the baseline mean, for "load too high" over 1-2 weeks
    hrv_vals = [r["hrv"] for r in rows if "hrv" in r and r["date"] <= target]
    if len(hrv_vals) >= 21:
        last7, prev = statistics.mean(hrv_vals[-7:]), statistics.mean(hrv_vals[:-7])
        if last7 < prev * 0.93:
            notes.append(f"HRV 7-day mean {last7:.0f} is {100 - last7 / prev * 100:.0f} % below the earlier weeks: watch the load")

    print(f"{target}: {verdict}")
    for lvl, msg in flags:
        print(f"  {lvl.upper():<5} {msg}")
    for n in notes:
        print(f"  ·     {n}")


if __name__ == "__main__":
    main()
