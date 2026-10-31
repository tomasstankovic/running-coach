#!/usr/bin/env python3
"""Build a TrainingPeaks run structure in kilometres or in time, from one compact spec.

trainingpeaks-mcp's simplified `structure` only knows time steps. Distance steps (what the
watch shows as "1.00 km") need TP's native `structured_workout`. This script writes both:

  structured_workout  native payload for tp_create_workout (km or time, as the runner prefers)
  structure           time-equivalent simplified structure, for tp_validate_structure (TSS)
  duration_minutes, distance_km   the planned totals to pass along

Usage:
  tp_structure.py spec.json [--out workout.json]

Spec:
{
  "threshold_pace": "4:10",        # needed to convert km <-> time for pace targets
  "unit": "km",                    # km | time: how steps are measured on the watch
  "metric": "pace",                # pace (% threshold speed) | hr (% LTHR) | power (% rFTP)
  "steps": [
    {"name": "Rozklus 2 km", "km": 2, "pct": [70, 78], "class": "warmUp"},
    {"repeat": 5, "steps": [
      {"name": "1 km @ 4:00-4:05", "km": 1, "pct": [102, 104]},
      {"name": "Klus 2 min", "seconds": 120, "pct": [55, 66], "class": "rest"}
    ]},
    {"name": "Vyklus 2 km", "km": 2, "pct": [62, 70], "class": "coolDown"}
  ]
}

A step's length is one of km, m, seconds or minutes. A step measured the other way is converted
to the workout's unit at its expected pace: the "pace" field ("5:40") if given, otherwise the
pace implied by "pct" with metric pace. With metric hr or power, give "pace" on every step that
needs converting (use the runner's usual pace for that effort on their terrain).
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

    notes, wire, simple, bars = [], [], [], []
    pos, total_s, total_m = 0, 0.0, 0.0
    missing_distance = False

    def one(step):
        cls = check_step(step)
        metres, seconds = lengths(step, spec)
        if by_km and metres is None:
            raise ValueError(f"step {step['name']!r} is timed; add \"pace\" so it can be written in km")
        if seconds is None:
            raise ValueError(f"step {step['name']!r} is in km; add \"pace\" to estimate its time")
        given_m = step.get("km") is not None or step.get("m") is not None
        if by_km and not given_m:
            metres = max(50, round(metres / 50) * 50)
            notes.append(f"{step['name']}: {seconds:.0f} s written as {metres:.0f} m")
        if not by_km and given_m:
            seconds = max(5, round(seconds / 5) * 5)
            notes.append(f"{step['name']}: {metres:.0f} m written as {seconds:.0f} s")
        lo, hi = step["pct"]
        value = round(metres) if by_km else round(seconds)
        native = {"type": "step", "name": step["name"],
                  "length": {"value": value, "unit": "meter" if by_km else "second"},
                  "targets": [{"minValue": lo, "maxValue": hi}],
                  "intensityClass": cls, "openDuration": False}
        if step.get("notes"):
            native["notes"] = step["notes"]
        plain = {"name": step["name"], "duration_seconds": int(round(seconds)),
                 "intensity_min": lo, "intensity_max": hi, "intensityClass": cls}
        return {"native": native, "plain": plain, "value": value, "hi": hi,
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
                bars.append((pos, pos + b["value"], b["hi"]))
                pos += b["value"]
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
            "distance_km": None if missing_distance else round(total_m / 1000, 1),
            "notes": notes}


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
        for n in result["notes"]:
            print(f"note: {n}")
    else:
        print(text)


if __name__ == "__main__":
    main()
