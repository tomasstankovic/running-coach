#!/usr/bin/env python3
"""Classify where a runner trains from elevation gain per kilometre.

Usage:
  terrain.py runs.json [more.json ...]

Each file holds one run or a list of runs, in any of these shapes:
  TrainingPeaks:  tp_get_workout output (metrics.elevation_gain, metrics.distance_actual_km)
  Strava:         list_activities items (total_elevation_gain in m, distance in m, name)
  simple:         {"date": "2026-10-25", "km": 11.6, "elev_m": 244, "title": "easy", "kind": "easy"}

"kind" (easy | long | quality | race) is optional. When given, the summary splits by it, which
answers the question that matters: are the easy runs hilly while quality happens on the flat?

Classes by gain per km: flat < 10, rolling 10-25, hilly 25-50, mountain > 50 m/km.
"""
import json
import sys
from statistics import median

CLASSES = [(10, "flat"), (25, "rolling"), (50, "hilly"), (float("inf"), "mountain")]


def classify(m_per_km):
    for limit, name in CLASSES:
        if m_per_km < limit:
            return name
    return "mountain"


def normalize(r):
    """(date, km, elevation m, title, kind) or None if the run lacks the data."""
    m = r.get("metrics") or {}
    if m:
        km, elev = m.get("distance_actual_km"), m.get("elevation_gain")
    elif "total_elevation_gain" in r:
        km, elev = (r.get("distance") or 0) / 1000, r.get("total_elevation_gain")
    else:
        km, elev = r.get("km"), r.get("elev_m")
    if not km or elev is None or km < 1:
        return None
    sport = (r.get("sport") or r.get("sport_type") or r.get("type") or "Run").lower()
    if "run" not in sport and sport not in ("completed", "planned"):
        return None
    date = str(r.get("date") or r.get("start_date_local") or "")[:10]
    title = r.get("title") or r.get("name") or ""
    return date, float(km), float(elev), title, r.get("kind")


def load(paths):
    runs = []
    for p in paths:
        with open(p) as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("workouts") or data.get("activities") or [data]
        runs += [n for n in (normalize(r) for r in data) if n]
    return sorted(runs)


def summary(label, runs):
    rates = [e / k for _, k, e, _, _ in runs]
    mid = median(rates)
    flat = sum(1 for r in rates if r < 10)
    n = len(runs)
    print(f"{label}: {n} run{'s' if n != 1 else ''}, median {mid:.0f} m/km ({classify(mid)}), "
          f"{flat} of {n} flat (< 10 m/km)")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    runs = load(sys.argv[1:])
    if not runs:
        sys.exit("no runs with distance and elevation gain found")

    print(f"{'date':<11}{'km':>6}{'gain m':>8}{'m/km':>6}  class     title")
    for date, km, elev, title, kind in runs:
        rate = elev / km
        tag = f" [{kind}]" if kind else ""
        print(f"{date:<11}{km:>6.1f}{elev:>8.0f}{rate:>6.0f}  {classify(rate):<9} {title[:40]}{tag}")
    print()
    summary("All runs", runs)
    kinds = sorted({r[4] for r in runs if r[4]})
    for kind in kinds:
        summary(f"  {kind}", [r for r in runs if r[4] == kind])


if __name__ == "__main__":
    main()
