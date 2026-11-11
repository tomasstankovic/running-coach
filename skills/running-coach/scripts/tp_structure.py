#!/usr/bin/env python3
"""Build a TrainingPeaks run structure from one compact spec, each step in its own unit.

trainingpeaks-mcp's simplified `structure` only knows time steps. Distance steps (what the
watch shows as "1.00 km") need TP's native `structured_workout`. This script writes both:

  structured_workout  native payload for tp_create_workout: every step keeps the unit it was
                      given (km/m as distance, seconds/minutes as time), so one session can mix
                      them: 15 min warm-up, 6 x (1 km / 75 s jog), 2 km cool-down
  structure           time-equivalent simplified structure, for tp_validate_structure (TSS)
  duration_minutes, distance_km   the planned totals to pass along

Usage:
  tp_structure.py spec.json [--out workout.json]

Spec:
{
  "threshold_pace": "4:10",        # needed to estimate km <-> time for pace targets
  "unit": "km",                    # km | time: the workout's primary axis in TP (chart, totals)
  "metric": "pace",                # pace (% threshold speed) | hr (% LTHR) | power (% rFTP)
  "steps": [
    {"name": "Rozklus 12 min", "minutes": 12, "pct": [68, 76], "class": "warmUp", "pace": "6:00"},
    {"repeat": 3, "steps": [
      {"name": "Rovinka 20 s", "seconds": 20, "pct": [115, 125], "class": "warmUp"},
      {"name": "Klus 40 s", "seconds": 40, "pct": [55, 66], "class": "warmUp", "pace": "6:40"}
    ]},
    {"repeat": 6, "steps": [
      {"name": "1 km @ 4:10-4:15", "km": 1, "pct": [98, 100]},
      {"name": "Klus 75 s", "seconds": 75, "pct": [55, 66], "class": "rest", "pace": "6:40"}
    ]},
    {"name": "Vyklus 2 km", "km": 2, "pct": [62, 70], "class": "coolDown", "pace": "6:10"}
  ]
}

A step's length is one of km, m, seconds or minutes, and it goes to TP in that unit. The other
measure is estimated for the totals and the chart: from the "pace" field ("5:40") if given,
otherwise from the pace implied by "pct" with metric pace. A distance step always needs a time
estimate; with unit km a timed step also needs a distance estimate. With metric hr or power,
give "pace" on those steps (the runner's usual pace for that effort on their terrain).
"""
import argparse
import json
import re
import sys

CLASSES = {"warmUp", "active", "rest", "coolDown", "other"}
METRICS = {"pace": "percentOfThresholdPace", "hr": "percentOfThresholdHr", "power": "percentOfFtp"}


def parse_pace(text):
    m = re.fullmatch(r"\s*(\d+):(\d{1,2})\s*", str(text))
    if not m:
        raise ValueError(f"not a pace: {text!r} (expected m:ss)")
    return int(m.group(1)) * 60 + int(m.group(2))


def step_pace(step, spec):
    """Expected seconds per km for a step, or None if it can't be known."""
    if step.get("pace"):
        return parse_pace(step["pace"])
    if spec["metric"] == "pace" and spec.get("threshold_pace"):
        lo, hi = step["pct"]
        return parse_pace(spec["threshold_pace"]) / ((lo + hi) / 200.0)
    return None


def lengths(step, spec):
    """(metres or None, seconds or None) for a step, converting where a pace is known."""
    metres = seconds = None
    if step.get("km") is not None:
        metres = float(step["km"]) * 1000
    elif step.get("m") is not None:
        metres = float(step["m"])
    if step.get("seconds") is not None:
        seconds = float(step["seconds"])
    elif step.get("minutes") is not None:
        seconds = float(step["minutes"]) * 60
    if metres is None and seconds is None:
        raise ValueError(f"step {step.get('name')!r} needs km, m, seconds or minutes")
    pace = step_pace(step, spec)
    if metres is None and pace:
        metres = seconds / pace * 1000
    if seconds is None and pace:
        seconds = metres / 1000 * pace
    return metres, seconds


def check_step(step):
    name = step.get("name", "")
    if not 1 <= len(name) <= 100:
        raise ValueError(f"step name must be 1-100 characters: {name!r}")
    lo, hi = step.get("pct", [None, None])
    if lo is None or hi is None or lo > hi:
        raise ValueError(f"step {name!r} needs pct [min, max] with min <= max")
    cls = step.get("class", "active")
    if cls not in CLASSES:
        raise ValueError(f"step {name!r}: class must be one of {sorted(CLASSES)}")
    return cls


def build(spec):
    spec.setdefault("metric", "pace")
    spec.setdefault("unit", "km")
    if spec["metric"] not in METRICS:
        raise ValueError(f"metric must be one of {sorted(METRICS)}")
    if spec["unit"] not in ("km", "time"):
        raise ValueError("unit must be km or time")
    by_km = spec["unit"] == "km"

    wire, simple, bars = [], [], []
    pos, total_s, total_m = 0, 0.0, 0.0
    missing_distance = False

    def one(step):
        cls = check_step(step)
        metres, seconds = lengths(step, spec)
        if by_km and metres is None:
            raise ValueError(f"step {step['name']!r} is timed; add \"pace\" to estimate its distance")
        if seconds is None:
            raise ValueError(f"step {step['name']!r} is in km; add \"pace\" to estimate its time")
        given_m = step.get("km") is not None or step.get("m") is not None
        length = ({"value": round(metres), "unit": "meter"} if given_m
                  else {"value": round(seconds), "unit": "second"})
        lo, hi = step["pct"]
        native = {"type": "step", "name": step["name"], "length": length,
                  "targets": [{"minValue": lo, "maxValue": hi}],
                  "intensityClass": cls, "openDuration": False}
        if step.get("notes"):
            native["notes"] = step["notes"]
        plain = {"name": step["name"], "duration_seconds": int(round(seconds)),
                 "intensity_min": lo, "intensity_max": hi, "intensityClass": cls}
        axis = round(metres) if by_km else round(seconds)
        return {"native": native, "plain": plain, "axis": axis, "hi": hi,
                "metres": metres, "seconds": seconds}

    for block in spec["steps"]:
        begin = pos
        if "repeat" in block:
            reps = int(block["repeat"])
            if reps < 1:
                raise ValueError("repeat must be >= 1")
            built = [one(s) for s in block["steps"]]
            wire.append({"type": "repetition", "length": {"value": reps, "unit": "repetition"},
                         "steps": [b["native"] for b in built]})
            simple.append({"type": "repetition", "reps": reps, "steps": [b["plain"] for b in built]})
        else:
            reps, built = 1, [one(block)]
            wire.append({"type": "step", "length": {"value": 1, "unit": "repetition"},
                         "steps": [built[0]["native"]]})
            simple.append(built[0]["plain"])
        for _ in range(reps):
            for b in built:
                bars.append((pos, pos + b["axis"], b["hi"]))
                pos += b["axis"]
                total_s += b["seconds"]
                if b["metres"] is None:
                    missing_distance = True
                else:
                    total_m += b["metres"]
        wire[-1]["begin"], wire[-1]["end"] = begin, pos

    polyline = []
    for start, end, hi in bars:
        x0, x1, y = round(start / pos, 4), round(end / pos, 4), round(hi / 100, 3)
        polyline += [[x0, 0], [x0, y], [x1, y], [x1, 0]]

    structured = {"structure": wire, "polyline": polyline,
                  "primaryLengthMetric": "distance" if by_km else "duration",
                  "primaryIntensityMetric": METRICS[spec["metric"]],
                  "primaryIntensityTargetOrRange": "range"}
    if by_km:
        structured["visualizationDistanceUnit"] = "kilometer"
    return {"structured_workout": structured,
            "structure": {"primaryIntensityMetric": METRICS[spec["metric"]], "steps": simple},
            "duration_minutes": round(total_s / 60),
            "distance_km": None if missing_distance else round(total_m / 1000, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", help="write the result here instead of stdout")
    args = ap.parse_args()
    with open(args.spec) as f:
        spec = json.load(f)
    try:
        result = build(spec)
    except ValueError as e:
        sys.exit(f"error: {e}")
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"wrote {args.out}: {result['duration_minutes']} min, "
              f"{result['distance_km'] if result['distance_km'] is not None else '?'} km")
    else:
        print(text)


if __name__ == "__main__":
    main()
