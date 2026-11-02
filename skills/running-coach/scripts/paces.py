#!/usr/bin/env python3
"""Pace / zone calculator for running plans that live in TrainingPeaks.

TrainingPeaks expresses run intensity as a percentage of threshold *speed*
(faster = higher %). So with a 4:10/km threshold, 4:00/km is 104 %, not 96 %.
This script does that conversion so it is never done by hand.

Usage:
  paces.py zones --threshold-pace 4:10 --lthr 174
  paces.py zones --tp-settings settings.json     # output of tp_get_athlete_settings
  paces.py convert --threshold-pace 4:10 4:25 4:00-4:05 95 102-104
  paces.py race --distance 21.0975 --time 1:34:23  # estimate threshold from a race
  paces.py predict --distance 10 --time 48:30      # equivalent times for other distances
  paces.py predict --distance 10 --time 48:30 --weekly-km 45 [--race2-distance 21.1 --race2-time 1:47:00]
                   [--training-pace 5:45]          # + marathon models that use training volume
  paces.py splits --distance 21.0975 --goal 1:35:00 --every 5 --negative 1
  paces.py power --rftp 420 300 95-100              # running power zones, watts <-> % of rFTP
  paces.py power --effort-watts 401 --effort-minutes 94   # estimate rFTP from a hard effort
"""
import argparse
import math
import json
import re
import sys

# Zone boundaries as a fraction of threshold speed / LTHR. These match the
# 7-zone (Z1, Z2, X, Z3, Y, Z4, Z5) set TrainingPeaks generates with its 80/20
# Endurance calculators (Matt Fitzgerald's model; X and Y are the in-between zones
# 80/20 training mostly avoids). Used only when real zones from TrainingPeaks are
# not available.
DEFAULT_SPEED_ZONES = [
    ("Z1", 0.5995, 0.7599),
    ("Z2", 0.7599, 0.8711),
    ("X", 0.8711, 0.9294),
    ("Z3", 0.9294, 1.0000),
    ("Y", 1.0000, 1.0204),
    ("Z4", 1.0204, 1.1521),
    ("Z5", 1.1521, 1.40),
]
DEFAULT_HR_ZONES = [
    ("Z1", 0.718, 0.810),
    ("Z2", 0.810, 0.902),
    ("X", 0.902, 0.948),
    ("Z3", 0.948, 1.000),
    ("Y", 1.000, 1.017),
    ("Z4", 1.017, 1.052),
    ("Z5", 1.052, 1.10),
]

# Running power zones as % of running FTP (the 5-zone model Stryd publishes; TrainingPeaks'
# own run power zones are Coggan-style and also work from rFTP). Watts differ between devices
# (Garmin wrist power reads higher than Stryd), so never mix sources.
POWER_ZONES = [
    ("Easy", 0.65, 0.80, "easy, long and recovery runs"),
    ("Moderate", 0.80, 0.90, "steady, marathon-ish"),
    ("Threshold", 0.90, 1.00, "tempo, cruise intervals, sub-threshold"),
    ("Interval", 1.00, 1.15, "VO2max intervals"),
    ("Repetition", 1.15, 1.30, "short fast reps, strides"),
]
# rFTP ~ power holdable for about an hour; shorter efforts sit above it, longer below
# (practice-based factors, like RACE_TO_THRESHOLD for pace).
EFFORT_TO_RFTP = [(25, 0.95), (35, 0.97), (65, 1.00), (110, 1.04), (240, 1.12)]

# Approximate share of a race's average speed held at threshold, used by the
# `race` command (threshold ≈ the pace you can hold for ~50–60 min).
RACE_TO_THRESHOLD = {5.0: 0.93, 10.0: 0.975, 21.0975: 1.02, 42.195: 1.075}


def parse_pace(text):
    """'4:10' -> 250 seconds per km."""
    m = re.fullmatch(r"\s*(\d+):(\d{1,2})\s*", text)
    if not m:
        raise ValueError(f"not a pace: {text!r} (expected m:ss)")
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_time(text):
    parts = [int(p) for p in text.split(":")]
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return secs


def fmt_pace(sec_per_km):
    if sec_per_km <= 0 or sec_per_km > 3600:
        return "--"
    sec = round(sec_per_km)
    return f"{sec // 60}:{sec % 60:02d}"


def speed_to_pace(speed_ms):
    return 1000.0 / speed_ms if speed_ms > 0 else float("inf")


def pct_from_pace(threshold_sec, pace_sec):
    return threshold_sec / pace_sec * 100.0


def pace_from_pct(threshold_sec, pct):
    return threshold_sec / (pct / 100.0)


def zones_from_tp(path):
    with open(path) as f:
        data = json.load(f)
    settings = data.get("settings", data)
    speed = settings["speedZones"][0]
    hr = settings["heartRateZones"][0]
    thr_speed = speed["threshold"]
    speed_zones = [
        (z["label"].replace("Zone ", "Z").replace("ZX", "X").replace("ZY", "Y"),
         z["minimum"] / thr_speed, min(z["maximum"] / thr_speed, 1.4))
        for z in speed["zones"]
    ]
    lthr = hr["threshold"]
    hr_zones = [
        (z["label"].replace("Zone ", "Z").replace("ZX", "X").replace("ZY", "Y"),
         z["minimum"] / lthr, min(z["maximum"], 230) / lthr)
        for z in hr["zones"]
    ]
    return speed_to_pace(thr_speed), lthr, speed_zones, hr_zones, hr.get("maximumHeartRate")


def cmd_zones(args):
    if args.tp_settings:
        thr_pace, lthr, speed_zones, hr_zones, max_hr = zones_from_tp(args.tp_settings)
        source = "TrainingPeaks settings"
    else:
        if not args.threshold_pace or not args.lthr:
            sys.exit("zones needs --tp-settings or both --threshold-pace and --lthr")
        thr_pace, lthr = parse_pace(args.threshold_pace), args.lthr
        speed_zones, hr_zones, max_hr = DEFAULT_SPEED_ZONES, DEFAULT_HR_ZONES, None
        source = "default 7-zone ratios"

    print(f"Threshold pace {fmt_pace(thr_pace)}/km, LTHR {lthr}"
          + (f", max HR {max_hr}" if max_hr else "") + f"  ({source})")
    print()
    print(f"{'Zone':<5} {'pace /km':<15} {'% thr speed':<13} {'HR':<10}")
    hr_by_label = {label: (lo, hi) for label, lo, hi in hr_zones}
    for label, lo, hi in speed_zones:
        slow, fast = pace_from_pct(thr_pace, lo * 100), pace_from_pct(thr_pace, hi * 100)
        pace_txt = f"{fmt_pace(slow)}–{fmt_pace(fast)}" if hi < 1.39 else f"< {fmt_pace(slow)}"
        pct_txt = f"{lo * 100:.0f}–{hi * 100:.0f} %" if hi < 1.39 else f"> {lo * 100:.0f} %"
        hr_lo, hr_hi = hr_by_label.get(label, (None, None))
        hr_txt = f"{round(hr_lo * lthr)}–{round(hr_hi * lthr)}" if hr_lo else "-"
        if hr_hi and hr_hi * lthr > 220:
            hr_txt = f"> {round(hr_lo * lthr)}"
        print(f"{label:<5} {pace_txt:<15} {pct_txt:<13} {hr_txt:<10}")


def cmd_convert(args):
    thr = parse_pace(args.threshold_pace)
    for item in args.values:
        parts = item.split("-")
        out = []
        for p in parts:
            if ":" in p:
                out.append(f"{fmt_pace(parse_pace(p))}/km = {pct_from_pace(thr, parse_pace(p)):.1f} %")
            else:
                out.append(f"{float(p):.1f} % = {fmt_pace(pace_from_pct(thr, float(p)))}/km")
        print(f"{item:<12} ->  " + "  |  ".join(out))
    print(f"(threshold {fmt_pace(thr)}/km; TrainingPeaks % is of threshold speed, faster = higher)")


def cmd_race(args):
    secs = parse_time(args.time)
    pace = secs / args.distance
    nearest = min(RACE_TO_THRESHOLD, key=lambda d: abs(d - args.distance))
    factor = RACE_TO_THRESHOLD[nearest]
    thr = pace / factor  # factor is threshold speed / race speed
    print(f"Race pace {fmt_pace(pace)}/km over {args.distance} km")
    print(f"Estimated threshold pace ≈ {fmt_pace(thr)}/km "
          f"(factor {factor} for ~{nearest} km; hilly/trail races understate fitness)")


def cmd_power(args):
    if args.effort_watts and args.effort_minutes:
        factor = next((f for limit, f in EFFORT_TO_RFTP if args.effort_minutes <= limit), 1.12)
        est = args.effort_watts * factor
        print(f"Effort {args.effort_watts:.0f} W for {args.effort_minutes:.0f} min -> rFTP ≈ {est:.0f} W "
              f"(factor {factor}; an estimate, the same device only)")
        if not args.rftp:
            args.rftp = est
    if not args.rftp:
        sys.exit("power needs --rftp, or --effort-watts with --effort-minutes")
    print(f"\nRunning power zones, rFTP {args.rftp:.0f} W")
    print(f"{'Zone':<11} {'watts':<12} {'% rFTP':<10} use")
    for name, lo, hi, use in POWER_ZONES:
        print(f"{name:<11} {round(lo * args.rftp)}–{round(hi * args.rftp):<7} {lo * 100:.0f}–{hi * 100:.0f} %   {use}")
    for item in args.values or []:
        parts = item.split("-")
        out = []
        for p in parts:
            v = float(p)
            out.append(f"{v:.0f} % = {v / 100 * args.rftp:.0f} W" if v <= 200 else f"{v:.0f} W = {v / args.rftp * 100:.1f} %")
        print(f"{item:<12} ->  " + "  |  ".join(out))


def fmt_time(secs):
    secs = round(secs)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def vickers_model1(d_m, t_s, miles):
    """Vickers & Vertosick 2016, model 1: one non-marathon race + typical weekly mileage."""
    v_riegel = 42195 / (t_s * (42195 / d_m) ** 1.07)
    v = 0.16018617 + 0.83076202 * v_riegel + 0.06423826 * (miles / 10)
    return 42195 / v


def vickers_model2(d1, t1, d2, t2, miles):
    """Vickers & Vertosick 2016, model 2: two races (d1 < d2) + weekly mileage."""
    k21 = math.log(t2 / t1) / math.log(d2 / d1)
    k_mar = 1.4510756 - 0.23797948 * k21 - 0.01410023 * (miles / 10)
    return t2 * (42195 / d2) ** k_mar


def tanda(weekly_km, training_pace_s):
    """Tanda 2011: marathon pace from mean weekly km and mean training pace (weeks -9 to -1)."""
    pm = 17.1 + 140.0 * math.exp(-0.0053 * weekly_km) + 0.55 * training_pace_s
    return 42.195 * pm


def cmd_predict(args):
    # Riegel: T2 = T1 * (D2 / D1) ^ 1.06. Fine up to the half marathon; for the marathon it is
    # optimistic unless the runner has the volume (Vickers & Vertosick 2016: often 10+ min too fast).
    secs = parse_time(args.time)
    print(f"From {args.distance} km in {fmt_time(secs)} ({fmt_pace(secs / args.distance)}/km):")
    for name, dist in [("5 km", 5.0), ("10 km", 10.0), ("Half marathon", 21.0975), ("Marathon", 42.195)]:
        t = secs * (dist / args.distance) ** 1.06
        note = "  (Riegel; optimistic without marathon volume)" if dist > 30 else ""
        print(f"  {name:<14} {fmt_time(t):>8}  {fmt_pace(t / dist)}/km{note}")
    if not (args.weekly_km or args.training_pace):
        return
    print("\nMarathon with training volume:")
    if args.weekly_km:
        miles = args.weekly_km / 1.609344
        if args.distance < 42:
            t = vickers_model1(args.distance * 1000, secs, miles)
            print(f"  Vickers model 1 {fmt_time(t):>8}  {fmt_pace(t / 42.195)}/km  "
                  f"(race + {args.weekly_km:g} km/week)")
        if args.race2_distance and args.race2_time:
            (d1, t1), (d2, t2) = sorted([(args.distance * 1000, secs),
                                         (args.race2_distance * 1000, parse_time(args.race2_time))])
            t = vickers_model2(d1, t1, d2, t2, miles)
            print(f"  Vickers model 2 {fmt_time(t):>8}  {fmt_pace(t / 42.195)}/km  (two races + volume; most accurate)")
    if args.training_pace and args.weekly_km:
        t = tanda(args.weekly_km, parse_pace(args.training_pace))
        print(f"  Tanda           {fmt_time(t):>8}  {fmt_pace(t / 42.195)}/km  "
              f"(mean pace of all runs, weeks -9 to -1; validated for ~2:47-3:36)")
    print("  Plan from the slowest credible estimate; revisit after the next race or long-run test.")


def cmd_splits(args):
    goal = parse_time(args.goal)
    avg = goal / args.distance
    # negative split: first half slower by `negative` % of avg pace, second half faster by the same
    delta = avg * args.negative / 100
    print(f"Goal {fmt_time(goal)} over {args.distance} km, average {fmt_pace(avg)}/km"
          + (f", negative split ±{args.negative} %" if args.negative else ", even pace"))
    print(f"{'km':>7} {'pace':>7} {'split':>9} {'elapsed':>9}")
    marks, d = [], args.every
    while d < args.distance - 1e-6:
        marks.append(d)
        d += args.every
    marks.append(args.distance)
    elapsed, prev = 0.0, 0.0
    half = args.distance / 2
    for m in marks:
        seg = 0.0
        a = prev
        while a < m - 1e-9:  # integrate pace over the segment, switching at halfway
            b = min(m, half) if a < half else m
            pace = avg + delta if a < half else avg - delta
            seg += (b - a) * pace
            a = b
        elapsed += seg
        print(f"{m:>7.2f} {fmt_pace(seg / (m - prev)):>7} {fmt_time(seg):>9} {fmt_time(elapsed):>9}")
        prev = m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    z = sub.add_parser("zones", help="print pace + HR zones")
    z.add_argument("--threshold-pace")
    z.add_argument("--lthr", type=int)
    z.add_argument("--tp-settings", help="JSON file with tp_get_athlete_settings output")
    z.set_defaults(func=cmd_zones)

    c = sub.add_parser("convert", help="pace <-> %% of threshold speed")
    c.add_argument("--threshold-pace", required=True)
    c.add_argument("values", nargs="+", help="paces like 4:25 or 4:00-4:05, or percents like 95 or 102-104")
    c.set_defaults(func=cmd_convert)

    r = sub.add_parser("race", help="estimate threshold pace from a race result")
    r.add_argument("--distance", type=float, required=True, help="km")
    r.add_argument("--time", required=True, help="h:mm:ss or mm:ss")
    r.set_defaults(func=cmd_race)

    p = sub.add_parser("predict", help="equivalent race times (Riegel)")
    p.add_argument("--distance", type=float, required=True, help="km")
    p.add_argument("--time", required=True, help="h:mm:ss or mm:ss")
    p.add_argument("--weekly-km", type=float, help="typical weekly km in the build (marathon models)")
    p.add_argument("--race2-distance", type=float, help="a second recent race, km (Vickers model 2)")
    p.add_argument("--race2-time")
    p.add_argument("--training-pace", help="mean pace of all runs over weeks -9 to -1, m:ss (Tanda)")
    p.set_defaults(func=cmd_predict)

    w = sub.add_parser("power", help="running power zones and watts <-> %% of rFTP")
    w.add_argument("--rftp", type=float, help="running FTP in watts")
    w.add_argument("--effort-watts", type=float, help="average power of a hard effort (race or test)")
    w.add_argument("--effort-minutes", type=float)
    w.add_argument("values", nargs="*", help="watts (e.g. 300) or percents (e.g. 95-100)")
    w.set_defaults(func=cmd_power)

    s = sub.add_parser("splits", help="race pacing table")
    s.add_argument("--distance", type=float, required=True, help="km")
    s.add_argument("--goal", required=True, help="goal time h:mm:ss")
    s.add_argument("--every", type=float, default=1.0, help="split every N km (default 1)")
    s.add_argument("--negative", type=float, default=0.0, help="negative split in %% of pace (e.g. 1)")
    s.set_defaults(func=cmd_splits)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
