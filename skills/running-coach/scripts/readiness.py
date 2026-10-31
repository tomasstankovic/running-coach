#!/usr/bin/env python3
"""Daily readiness from HRV, resting HR and sleep, compared with the runner's own baseline.

Usage:
  readiness.py metrics.json [--date 2026-10-31]

metrics.json is either the raw tp_get_metrics output (pass 35-60 days), or a simple list:
  [{"date": "2026-10-30", "hrv": 46, "rhr": 50, "sleep_h": 7.6}, ...]

HRV follows the HRV-guided training studies (Vesterinen 2016, Nuuttila 2022; references/sources.md):
the 7-day rolling mean of ln(nightly HRV) is compared with the runner's normal band, the baseline
mean +- 0.5 SD over the 28-60 days before the week. Inside the band: train as planned. Below it:
no quality today; still below after 3 more days: cut volume ~25 % for 3-4 days. A single low night
counts only together with another sign. At least 21 baseline days are needed before HRV is judged.

Resting HR: the 7-day mean above baseline + 1 SD is a flag; a single day +8 bpm or more is a flag
(practice-based). Sleep under 6 h (or 5 h) is a flag. Prints GREEN / AMBER / RED with reasons.
"""
import argparse
import json
import math
import statistics
import sys
from datetime import date, timedelta

MIN_BASELINE_DAYS = 21
BAND_SD = 0.5

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

    def window(key, end_iso, days):
        end = date.fromisoformat(end_iso)
        lo = (end - timedelta(days=days - 1)).isoformat()
        return [r[key] for r in rows if key in r and lo <= r["date"] <= end_iso]

    def band(key, week_start, log=False):
        """Baseline mean and SD from the 28-60 days before `week_start`."""
        hi = date.fromisoformat(week_start) - timedelta(days=1)
        lo = (hi - timedelta(days=59)).isoformat()
        vals = [r[key] for r in rows if key in r and lo <= r["date"] <= hi.isoformat() and r[key] > 0]
        vals = [math.log(v) for v in vals] if log else vals
        if len(vals) < MIN_BASELINE_DAYS:
            return None
        return statistics.mean(vals), statistics.pstdev(vals) or 0.01, len(vals)

    def hrv_state(day):
        """-1 below the band, 0 inside, 1 above; None if not enough data."""
        week_start = (date.fromisoformat(day) - timedelta(days=6)).isoformat()
        b = band("hrv", week_start, log=True)
        last7 = [math.log(v) for v in window("hrv", day, 7) if v > 0]
        if not b or len(last7) < 4:
            return None, None, None
        mean7 = statistics.mean(last7)
        lo, hi = b[0] - BAND_SD * b[1], b[0] + BAND_SD * b[1]
        return (-1 if mean7 < lo else 1 if mean7 > hi else 0), mean7, b

    single_low = False
    state, mean7, b = hrv_state(target)
    if "hrv" in today and state is not None:
        mean, sd, n = b
        notes.append(f"HRV {today['hrv']:.0f}; 7-day mean {math.exp(mean7):.0f} vs normal band "
                     f"{math.exp(mean - BAND_SD * sd):.0f}-{math.exp(mean + BAND_SD * sd):.0f} ({n} baseline days)")
        earlier = [hrv_state((date.fromisoformat(target) - timedelta(days=k)).isoformat())[0] for k in (1, 2, 3)]
        if state == -1 and all(e == -1 for e in earlier):
            flags.append(("red", "HRV 7-day mean below the normal band for 4+ days: cut volume ~25 % for 3-4 days, no quality"))
        elif state == -1:
            flags.append(("amber", "HRV 7-day mean below the normal band: no quality today"))
        elif state == 1:
            notes.append("HRV 7-day mean above the band: fine, unless the runner feels very tired (then treat as amber)")
        single_low = today["hrv"] > 0 and math.log(today["hrv"]) < mean - sd
    elif "hrv" in today:
        notes.append(f"HRV {today['hrv']:.0f} (fewer than {MIN_BASELINE_DAYS} baseline days, not judged yet)")

    b = band("rhr", (date.fromisoformat(target) - timedelta(days=6)).isoformat())
    if "rhr" in today and b:
        mean, sd, n = b
        diff = today["rhr"] - mean
        last7 = window("rhr", target, 7)
        mean7 = statistics.mean(last7) if last7 else today["rhr"]
        notes.append(f"resting HR {today['rhr']:.0f} (7-day {mean7:.0f}) vs baseline {mean:.0f} ± {sd:.0f}")
        if diff >= 8:
            flags.append(("amber", f"resting HR {diff:+.0f} bpm today"))
        elif mean7 > mean + sd:
            flags.append(("amber", "resting HR 7-day mean above baseline + 1 SD"))

    if "sleep_h" in today:
        notes.append(f"sleep {today['sleep_h']:.1f} h")
        if today["sleep_h"] < 5:
            flags.append(("amber", "very short sleep"))
        elif today["sleep_h"] < 6:
            flags.append(("amber", "short sleep"))

    if single_low and any(not m.startswith("HRV") for _, m in flags):
        flags.append(("amber", "HRV last night more than 1 SD below baseline (counts with the other signs)"))
    elif single_low:
        notes.append("HRV last night low, but no other sign: train as planned, recheck tomorrow")

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

    print(f"{target}: {verdict}")
    for lvl, msg in flags:
        print(f"  {lvl.upper():<5} {msg}")
    for n in notes:
        print(f"  ·     {n}")


if __name__ == "__main__":
    main()
