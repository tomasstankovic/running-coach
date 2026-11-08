#!/usr/bin/env python3
"""Daily readiness from HRV, resting HR and sleep, compared with the runner's own baseline.

Usage:
  readiness.py metrics.json [--date 2026-10-31] [--stress 1-5]

metrics.json is either the raw tp_get_metrics output (pass 35-60 days), or a simple list:
  [{"date": "2026-10-30", "hrv": 46, "rhr": 50, "sleep_h": 7.6}, ...]

HRV follows the HRV-guided training studies (Vesterinen 2016, Nuuttila 2022; references/sources.md):
the 7-day rolling mean of ln(nightly HRV) is compared with the runner's normal band, the baseline
mean +- 0.5 SD over the 28-60 days before the week. Inside the band: train as planned. Below it:
no quality today; still below after 3 more days: cut volume ~25 % for 3-4 days. A single low night
counts only together with another sign. At least 21 baseline days are needed before HRV is judged.

Output: text (default), --brief (one line for a morning message), --json, or --trend DAYS
(JSON rows for the plan page's readiness chart; "reasons" are flag codes the page translates:
hrv_low_4d, hrv_low, hrv_night_low, rhr_spike, rhr_high, sleep_short, sleep_very_short, sleep_debt,
life_stress).

Resting HR: the 7-day mean above baseline + 1 SD is a flag; a single day +8 bpm or more is a flag
(practice-based). Sleep under 6 h (or 5 h) is a flag. Sleep debt: 3 or more of the last 4 nights
under 6 h is a flag even when last night was fine, so a recovered HRV does not hide several bad
nights. --stress is the runner's own 1-5 rating of load outside running (work, travel, heat,
family; 1 = calm, 5 = very heavy); 4 or 5 is a flag. Prints GREEN / AMBER / RED with reasons.
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


def assess(rows, target, stress=None):
    """Verdict, flags and the numbers behind them for one day."""
    today = next((r for r in rows if r["date"] == target), None)
    if today is None:
        return None
    base = [r for r in rows if r["date"] < target][-28:]

    flags, notes, codes = [], [], []

    def flag(level, code, message):
        flags.append((level, message))
        codes.append(code)
    hrv_info, rhr7 = (None, None), None

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
    hrv_info = (mean7, b)
    if "hrv" in today and state is not None:
        mean, sd, n = b
        notes.append(f"HRV {today['hrv']:.0f}; 7-day mean {math.exp(mean7):.0f} vs normal band "
                     f"{math.exp(mean - BAND_SD * sd):.0f}-{math.exp(mean + BAND_SD * sd):.0f} ({n} baseline days)")
        earlier = [hrv_state((date.fromisoformat(target) - timedelta(days=k)).isoformat())[0] for k in (1, 2, 3)]
        if state == -1 and all(e == -1 for e in earlier):
            flag("red", "hrv_low_4d", "HRV 7-day mean below the normal band for 4+ days: cut volume ~25 % for 3-4 days, no quality")
        elif state == -1:
            flag("amber", "hrv_low", "HRV 7-day mean below the normal band: no quality today")
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
        rhr7 = mean7
        notes.append(f"resting HR {today['rhr']:.0f} (7-day {mean7:.0f}) vs baseline {mean:.0f} ± {sd:.0f}")
        if diff >= 8:
            flag("amber", "rhr_spike", f"resting HR {diff:+.0f} bpm today")
        elif mean7 > mean + sd:
            flag("amber", "rhr_high", "resting HR 7-day mean above baseline + 1 SD")

    if "sleep_h" in today:
        notes.append(f"sleep {today['sleep_h']:.1f} h")
        if today["sleep_h"] < 5:
            flag("amber", "sleep_very_short", "very short sleep")
        elif today["sleep_h"] < 6:
            flag("amber", "sleep_short", "short sleep")

    nights = window("sleep_h", target, 4)
    short_nights = sum(1 for h in nights if h < 6)
    if short_nights >= 3:
        flag("amber", "sleep_debt", f"{short_nights} of the last {len(nights)} nights under 6 h (sleep debt)")

    if stress is not None:
        notes.append(f"life stress {stress}/5 (runner's rating)")
        if stress >= 4:
            flag("amber", "life_stress", f"heavy load outside running ({stress}/5): work, travel, heat or family")

    if single_low and any(not m.startswith("HRV") for _, m in flags):
        flag("amber", "hrv_night_low", "HRV last night more than 1 SD below baseline (counts with the other signs)")
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

    mean7, b = hrv_info
    band = (math.exp(b[0] - BAND_SD * b[1]), math.exp(b[0] + BAND_SD * b[1])) if b else (None, None)
    return {"date": target, "verdict": verdict.split(" ")[0], "verdict_text": verdict,
            "flags": flags, "reasons": codes, "notes": notes, "hrv": today.get("hrv"),
            "hrv_state": {-1: "below", 0: "inside", 1: "above"}.get(state),
            "hrv7": round(math.exp(mean7), 1) if mean7 else None,
            "band_lo": round(band[0], 1) if band[0] else None, "band_hi": round(band[1], 1) if band[1] else None,
            "rhr": today.get("rhr"), "rhr7": round(rhr7, 1) if rhr7 else None,
            "sleep_h": round(today["sleep_h"], 1) if today.get("sleep_h") else None, "stress": stress}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("metrics_json")
    ap.add_argument("--date", help="day to assess (default: latest day in the file)")
    ap.add_argument("--brief", action="store_true", help="one line for a morning message")
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    ap.add_argument("--stress", type=int, choices=range(1, 6), metavar="1-5",
                    help="the runner's rating of load outside running today (4-5 is a flag)")
    ap.add_argument("--trend", type=int, metavar="DAYS",
                    help="JSON rows for the last DAYS judged days (plan page trends)")
    args = ap.parse_args()

    rows = load(args.metrics_json)
    if not rows:
        sys.exit("no metrics found")
    if args.trend:
        out = [a for a in (assess(rows, r["date"]) for r in rows[-args.trend:]) if a and a["hrv7"]]
        print(json.dumps([{k: a[k] for k in ("date", "verdict", "reasons", "hrv", "hrv7", "hrv_state", "band_lo",
                                              "band_hi", "rhr", "rhr7", "sleep_h")} for a in out]))
        return
    target = args.date or rows[-1]["date"]
    a = assess(rows, target, args.stress)
    if a is None:
        sys.exit(f"no metrics for {target}")
    if args.json:
        print(json.dumps(a, ensure_ascii=False))
    elif args.brief:
        reasons = "; ".join(m for _, m in a["flags"]) or "all within your normal range"
        nums = []
        if a["hrv7"]:
            nums.append(f"HRV 7d {a['hrv7']:.0f} (band {a['band_lo']:.0f}-{a['band_hi']:.0f})")
        if a["rhr"]:
            nums.append(f"RHR {a['rhr']:.0f}")
        if a["sleep_h"]:
            nums.append(f"sleep {a['sleep_h']:.1f} h")
        print(f"{target} {a['verdict']}: {reasons} [{', '.join(nums)}]")
    else:
        print(f"{target}: {a['verdict_text']}")
        for lvl, msg in a["flags"]:
            print(f"  {lvl.upper():<5} {msg}")
        for n in a["notes"]:
            print(f"  ·     {n}")


if __name__ == "__main__":
    main()
