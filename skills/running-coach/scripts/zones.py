#!/usr/bin/env python3
"""Training zones (Tréningové zóny): one table of pace, heart rate and power, other zone methods
for comparison, a personal aerobic-threshold estimate, and proposals to update the zones from new
evidence (monthly, or after a race, a test or a run of sessions that say the zones are off).

Usage:
  zones.py show --tp-settings zones.json [--lang sk] [--json] [--date 2026-11-02]
  zones.py show --threshold-pace 4:20 --lthr 168 [--max-hr 186] [--rest-hr 50] [--rftp 300]
                [--method 8020|hrmax|hrr|daniels] [--race 10=43:05] [--easy-cap 142 --easy-source ...]
                [--source "30 min test"] [--lang sk] [--json]
  zones.py suggest evidence.json [--lang sk] [--json]
  zones.py lt1 runs.json --lthr 168 [--lang sk] [--json]

The runner's own zones are the default: the set in TrainingPeaks (and on their watch: Garmin,
Coros, Polar) whatever its method. `show --tp-settings` reads TP's bands as they are (the run
set if there is one, else the general one): 80/20 (Z1/Z2/X/Z3/Y/Z4/Z5), Friel (Z1-Z5c), 5-zone
or any other. Each band gets its use from where it sits relative to the threshold, so any
method reads the same way. Save only the `heartRateZones`, `speedZones` and `powerZones` blocks of
tp_get_athlete_settings (the rest is personal data).

Other methods, for a runner without zones or to compare (`--method`):
  8020     7 zones from threshold pace and LTHR (80/20 Endurance ratios, as TP computes them)
  hrmax    5 zones at 50/60/70/80/90-100 % of max HR (needs --max-hr; no threshold involved)
  hrr      the same % of heart-rate reserve, Karvonen (needs --max-hr and --rest-hr)
  daniels  E/M/T/I/R paces from a race (--race km=time), Daniels-Gilbert VDOT equations
Friel's zones aren't computed here (his published percentages differ between versions): read
them from TP or the watch, which calculate them.

lt1: steady runs (`analyze_session.py --json` rows, flat, 45+ min) where pace:HR decoupling stays
under 5 % were at or below the aerobic threshold; runs over 5 % were above it. The HR between
the two is a personal estimate of the aerobic threshold, the real top of easy running, instead
of the population ~83 % of LTHR. Heat, hills and dehydration raise drift, so it's an estimate to
confirm with a drift test (60 min flat at a steady HR, < 5 % drift).

suggest: evidence.json
{
  "today": "2026-11-02",
  "current": {"threshold_pace": "4:20", "lthr": 168, "max_hr": 186, "rest_hr": 50, "rftp": 300,
              "set_on": "2026-08-10"},            # when the zones were last set (profile)
  "tests": [{"date": "2026-10-20", "minutes": 30, "km": 7.05, "hr_last20": 171}],
  "races": [{"date": "2026-10-25", "km": 21.0975, "time": "1:31:40", "avg_hr": 171,
             "flat": true}],                      # hilly, trail or hot races don't set the pace
  "device": [{"date": "2026-10-30", "source": "Garmin", "threshold_pace": "4:18", "lthr": 170}],
                                                  # the watch's own threshold detection
  "sessions": [{"date": "2026-10-28", "kind": "intervals", "rep_pace": 252, "rep_max_hr": 162,
                "target": "threshold"}],          # analyze_session.py --json rows of threshold work
  "max_hr_seen": [{"date": "2026-10-25", "hr": 189}],
  "rest_hr_7d": 48,
  "power_efforts": [{"date": "2026-10-20", "watts": 318, "minutes": 30}]
}
Rules (methodology.md "When the threshold evidence disagrees" and "Keeping the zones current"):
a 30-min test sets both threshold pace and LTHR; a flat 5k-HM race sets the pace (paces.py race
factors) and a half's average HR is a floor for LTHR; the watch's detection counts, a bit less
than a race or test; threshold sessions only hint ("faster" or "slower", no number). Evidence
older than 120 days is ignored. Sources more than 3 % apart are reported as a disagreement to
discuss (or settle with a test), not averaged. A change under 1.5 % (~4 s/km) is noise and is
kept. With no new evidence and zones older than 12 weeks, it suggests talking about a retest. It
never writes anything: the coach proposes, the runner decides, then TrainingPeaks is updated
(trainingpeaks.md "Zones") and the runner sets the same values on the watch.
"""
import argparse
import json
import math
import sys
from datetime import date

from paces import (DEFAULT_HR_ZONES, DEFAULT_SPEED_ZONES, EFFORT_TO_RFTP, POWER_ZONES, RACE_TO_THRESHOLD,
                   fmt_pace, parse_pace, parse_time)

RUN_TYPE = 3                 # TrainingPeaks workoutTypeId of running (0 = general)
MAX_AGE = 120                # days of evidence that count
NOISE = 1.5                  # % change below which the zones stay
DISAGREE = 3.0               # % between sources that needs a conversation, not an average
RETEST_DAYS = 84             # 12 weeks
EASY_CAP = 0.83              # easy running up to ~83 % of LTHR (methodology.md §1), population default
DEVICE_WEIGHT = 0.7          # the watch's threshold detection, a bit less than a race or test
DRIFT_OK = 5.0               # % decoupling at or below the aerobic threshold
LT1_MIN_MIN, LT1_MAX_GAIN = 45, 15   # steady runs that count: 45+ min, < 15 m climb per km
NAMES = {"zone 1": "Z1", "zone 2": "Z2", "zone x": "X", "zone 3": "Z3", "zone y": "Y", "zone 4": "Z4", "zone 5": "Z5"}

# What a band is for, by where its middle sits: % of threshold speed, % of LTHR, % of rFTP,
# % of max HR (or of HR reserve). Upper edges of each use.
EDGES = {"pace": [76, 87, 93, 100, 102, 115], "hr": [81, 90, 95, 100, 102, 105],
         "power": [80, 90, 100, 115], "hrmax": [60, 70, 80, 90]}
USES = {
    "en": {"pace": ["recovery, warm-up and cool-down", "easy and long runs (upper half: steady)",
                    "marathon pace, steady: only on purpose", "tempo, cruise intervals", "threshold",
                    "VO2 intervals (5k-3k pace)", "strides, short fast reps"],
           "power": ["easy and long runs", "steady, marathon pace", "tempo, threshold", "VO2 intervals",
                     "short fast reps"],
           "hrmax": ["recovery", "easy and long runs", "steady aerobic", "tempo, threshold", "VO2, races"]},
    "sk": {"pace": ["regenerácia, rozklus, výklus", "ľahké a dlhé behy (horná polovica: svižnejšie)",
                    "maratónske tempo, len zámerne", "tempo, cruise intervaly", "prah",
                    "VO2 úseky (tempo 5 km až 3 km)", "rovinky, krátke rýchle úseky"],
           "power": ["ľahké a dlhé behy", "svižnejšie, maratónske tempo", "tempo, prah", "VO2 úseky",
                     "krátke rýchle úseky"],
           "hrmax": ["regenerácia", "ľahké a dlhé behy", "svižnejší aeróbny beh", "tempo, prah", "VO2, preteky"]},
}
USES["en"]["hr"], USES["sk"]["hr"] = USES["en"]["pace"], USES["sk"]["pace"]
DANIELS = {  # % of VO2max (VDOT); M is the marathon race pace itself
    "en": [("E", (59, 74), "easy and long runs"), ("M", None, "marathon pace"), ("T", (86, 88), "threshold, tempo"),
           ("I", (95, 100), "intervals 3-5 min"), ("R", (105, 105), "repetitions 200-400 m")],
    "sk": [("E", (59, 74), "ľahké a dlhé behy"), ("M", None, "maratónske tempo"), ("T", (86, 88), "prah, tempo"),
           ("I", (95, 100), "úseky 3-5 min"), ("R", (105, 105), "krátke úseky 200-400 m")],
}
TX = {
    "en": {"title": "Training zones", "zone": "Zone", "pace": "Pace /km", "pct": "% thr", "hr": "HR",
           "power": "Power", "use": "Use", "thr": "Threshold", "easy": "Easy running: HR up to {cap} ({src})",
           "from": "from {src}, {d}", "power_title": "Running power (rFTP {w} W)", "method": "method",
           "hr_title": "Heart rate", "pct_lthr": "83 % of LTHR", "pct_hrmax": "% max", "pct_hrr": "% reserve"},
    "sk": {"title": "Tréningové zóny", "zone": "Zóna", "pace": "Tempo /km", "pct": "% prahu", "hr": "Tep",
           "power": "Výkon", "use": "Na čo", "thr": "Prah", "easy": "Ľahký beh: tep do {cap} ({src})",
           "from": "zdroj: {src}, {d}", "power_title": "Bežecký výkon (rFTP {w} W)", "method": "metodika",
           "hr_title": "Tep", "pct_lthr": "83 % LTHR", "pct_hrmax": "% max", "pct_hrr": "% rezervy"},
}
SOURCE = {"en": {"default": "default ratios", "computed": "computed"}, "sk": {"default": "predvolené pomery", "computed": "vypočítané"}}
METHOD = {"8020": "80/20", "friel": "Friel", "hrmax": "% max HR", "hrr": "HRR (Karvonen)", "daniels": "Daniels (VDOT)"}


def use_for(kind, lo, hi, lang):
    """Use of a band from where its middle sits (lo/hi in % of the anchor; None = open)."""
    mid = lo * 1.03 if hi is None else (hi * 0.9 if not lo else (lo + hi) / 2)
    edges = EDGES[kind]
    return USES[lang][kind][next((i for i, e in enumerate(edges) if mid <= e), len(edges))]


def method_of(labels):
    low = " ".join(labels).lower()
    if "zone x" in low or "zone y" in low:
        return "80/20"
    if "5a" in low or "5b" in low:
        return "Friel"
    return f"{len(labels)} zones"


def pick(blocks, key):
    sets = blocks.get(key) or []
    return next((s for s in sets if s.get("workoutTypeId") == RUN_TYPE), None) or next(
        (s for s in sets if s.get("workoutTypeId") in (0, None)), None) or (sets[0] if sets else None)


def from_tp(blocks, lang="en"):
    """Normalize TP's zone blocks (speed in m/s, HR in bpm, power in W), whatever the method."""
    speed, hr, power = pick(blocks, "speedZones"), pick(blocks, "heartRateZones"), pick(blocks, "powerZones")
    z = {"source": "TrainingPeaks", "rows": [], "hr_rows": [], "power": [], "method": None}
    if speed and speed.get("zones"):
        t = speed["threshold"]
        z["threshold_s"] = 1000 / t
        z["method"] = method_of([b["label"] for b in speed["zones"]])
        for b in speed["zones"]:
            lo, hi = b["minimum"], b["maximum"]
            plo, phi = round(lo / t * 100), (round(hi / t * 100) if hi < 50 else None)
            z["rows"].append({"name": NAMES.get(b["label"].lower(), b["label"]),
                              "pace_slow": 1000 / lo if lo > 0.5 else None, "pace_fast": 1000 / hi if hi < 50 else None,
                              "pct_lo": plo, "pct_hi": phi, "use": use_for("pace", plo, phi, lang)})
    if hr and hr.get("zones"):
        z.update(lthr=hr.get("threshold"), max_hr=hr.get("maximumHeartRate"), rest_hr=hr.get("restingHeartRate"))
        bands = hr["zones"]
        z["method"] = z["method"] or method_of([b["label"] for b in bands])
        lthr = hr.get("threshold") or 0
        rows = [{"name": NAMES.get(b["label"].lower(), b["label"]), "hr_lo": b["minimum"] or None,
                 "hr_hi": b["maximum"] if b["maximum"] < 250 else None} for b in bands]
        for r in rows:
            if lthr:
                r["use"] = use_for("hr", (r["hr_lo"] or 0) / lthr * 100, r["hr_hi"] and r["hr_hi"] / lthr * 100, lang)
        if len(rows) == len(z["rows"]):
            for row, r in zip(z["rows"], rows):
                row.update(hr_lo=r["hr_lo"], hr_hi=r["hr_hi"])
        elif not z["rows"]:
            z["rows"] = rows
        else:
            z["hr_rows"] = rows      # a different method for HR than for pace: its own table
    if power and power.get("zones"):
        z["rftp"] = power.get("threshold")
        z["power"] = [{"name": b["label"], "w_lo": b["minimum"], "w_hi": b["maximum"] if b["maximum"] < 1500 else None,
                       "use": use_for("power", b["minimum"] / z["rftp"] * 100,
                                      b["maximum"] / z["rftp"] * 100 if b["maximum"] < 1500 else None, lang)}
                      for b in power["zones"]] if z["rftp"] else []
    return z


# --- Daniels-Gilbert VDOT equations (Daniels' Running Formula) ---------------------------------

def vo2_at(v):            # ml/kg/min at v metres per minute
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def share_of_max(t):      # share of VO2max sustainable for t minutes
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t) + 0.2989558 * math.exp(-0.1932605 * t)


def vdot(km, secs):
    t = secs / 60
    return vo2_at(km * 1000 / t) / share_of_max(t)


def speed_at(vo2):        # m/min for a given VO2
    a, b, c = 0.000104, 0.182258, -4.60 - vo2
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def race_secs(v_dot, km):
    lo, hi = 60.0, 600.0     # minutes
    for _ in range(60):
        mid = (lo + hi) / 2
        if vdot(km, mid * 60) > v_dot:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 60


def daniels(km, secs, lang):
    vd = vdot(km, secs)
    rows = []
    for name, pct, use in DANIELS[lang]:
        if pct is None:
            p = race_secs(vd, 42.195) / 42.195
            rows.append({"name": name, "pace_fast": p, "pace_slow": p, "use": use})
        else:
            fast, slow = (1000 / speed_at(vd * x / 100) * 60 for x in (pct[1], pct[0]))
            rows.append({"name": name, "pace_fast": fast, "pace_slow": slow, "use": use})
    return vd, rows


def from_thresholds(thr_s, lthr=None, max_hr=None, rest_hr=None, rftp=None, source=None, method="8020",
                    race=None, lang="en"):
    z = {"source": source or ("default" if method == "8020" else "computed"), "threshold_s": thr_s, "lthr": lthr, "max_hr": max_hr, "rest_hr": rest_hr,
         "rftp": rftp, "rows": [], "hr_rows": [], "power": [], "method": METHOD.get(method, method)}
    if method == "8020":
        for (name, lo, hi), (_, hlo, hhi) in zip(DEFAULT_SPEED_ZONES, DEFAULT_HR_ZONES):
            top = name == "Z5"
            row = {"name": name, "pace_slow": thr_s / lo, "pace_fast": None if top else thr_s / hi,
                   "pct_lo": round(lo * 100), "pct_hi": None if top else round(hi * 100),
                   "use": use_for("pace", lo * 100, None if top else hi * 100, lang)}
            if lthr:
                row.update(hr_lo=round(lthr * hlo), hr_hi=None if top else round(lthr * hhi))
            z["rows"].append(row)
    elif method in ("hrmax", "hrr"):
        if not max_hr or (method == "hrr" and not rest_hr):
            sys.exit(f"--method {method} needs --max-hr" + (" and --rest-hr" if method == "hrr" else ""))
        base = rest_hr if method == "hrr" else 0
        span = max_hr - base
        for i, (lo, hi) in enumerate(((50, 60), (60, 70), (70, 80), (80, 90), (90, 100)), 1):
            z["hr_rows"].append({"name": f"Z{i}", "hr_lo": round(base + span * lo / 100), "hr_hi": round(base + span * hi / 100),
                                 "pct_lo": lo, "pct_hi": hi, "use": USES[lang]["hrmax"][i - 1]})
    elif method == "daniels":
        if not race:
            sys.exit("--method daniels needs --race km=time, e.g. 10=43:05")
        km, t = race.split("=")
        z["vdot"], z["rows"] = daniels(float(km), parse_time(t), lang)
        z["threshold_s"] = next(r for r in z["rows"] if r["name"] == "T")["pace_fast"]
        z["method"] = f"Daniels (VDOT {z['vdot']:.1f})"
    if rftp:
        z["power"] = [{"name": n, "w_lo": round(lo * rftp), "w_hi": None if n == "Repetition" else round(hi * rftp),
                       "use": use_for("power", lo * 100, None if n == "Repetition" else hi * 100, lang)}
                      for n, lo, hi, _ in POWER_ZONES]
    return z


def rng(lo, hi, fmt=lambda v: f"{v:.0f}"):
    if lo is None and hi is None:
        return "–"
    if hi is None:
        return f"> {fmt(lo)}"
    if lo is None:
        return f"< {fmt(hi)}"
    return f"{fmt(lo)}–{fmt(hi)}"


def pace_cell(r):
    if r.get("pace_fast") and r.get("pace_slow"):
        a, b = fmt_pace(r["pace_fast"]), fmt_pace(r["pace_slow"])
        return a if a == b else f"{a}–{b}"
    if r.get("pace_slow"):
        return f"< {fmt_pace(r['pace_slow'])}"
    if r.get("pace_fast"):
        return f"> {fmt_pace(r['pace_fast'])}"
    return "–"


def easy_cap(z, args_cap=None, args_src=None, lang="en"):
    if args_cap:
        return args_cap, args_src or "lt1"
    if z.get("lthr"):
        return round(z["lthr"] * EASY_CAP), TX[lang]["pct_lthr"]
    return None, None


def table(z, lang, day, cap=None, cap_src=None):
    tx = TX[lang]
    lines = [tx["title"]]
    head = [f"{tx['thr']} {fmt_pace(z['threshold_s'])}/km" if z.get("threshold_s") else None,
            f"LTHR {z['lthr']:.0f}" if z.get("lthr") else None, f"max {z['max_hr']:.0f}" if z.get("max_hr") else None,
            f"rFTP {z['rftp']:.0f} W" if z.get("rftp") else None,
            f"{tx['method']} {z['method']}" if z.get("method") else None]
    src = SOURCE[lang].get(z["source"], z["source"])
    lines.append(" · ".join(h for h in head if h) + f"  ({tx['from'].format(src=src, d=day)})")
    if z["rows"]:
        has_hr = any(r.get("hr_lo") or r.get("hr_hi") for r in z["rows"])
        has_pct = any(r.get("pct_lo") is not None for r in z["rows"])
        lines += ["", f"{tx['zone']:<6} {tx['pace']:<13} " + (f"{tx['pct']:<10} " if has_pct else "")
                  + (f"{tx['hr']:<10} " if has_hr else "") + tx["use"]]
        for r in z["rows"]:
            pct = (rng(r.get("pct_lo"), r.get("pct_hi")) + " %") if r.get("pct_lo") is not None else "–"
            pace = pace_cell(r) if r.get("pace_fast") or r.get("pace_slow") else "–"
            lines.append(f"{r['name']:<6} {pace:<13} " + (f"{pct:<10} " if has_pct else "")
                         + (f"{rng(r.get('hr_lo'), r.get('hr_hi')):<10} " if has_hr else "") + r.get("use", ""))
    if z["hr_rows"]:
        lines += ["", tx["hr_title"]]
        for r in z["hr_rows"]:
            pct = f"{r['pct_lo']}–{r['pct_hi']} %" if r.get("pct_lo") is not None else ""
            lines.append(f"  {r['name']:<10} {rng(r.get('hr_lo'), r.get('hr_hi')):<10} {pct:<10} {r.get('use', '')}")
    if cap:
        lines.append("\n" + tx["easy"].format(cap=cap, src=cap_src))
    if z["power"]:
        lines.append("\n" + tx["power_title"].format(w=round(z["rftp"] or 0)))
        for p in z["power"]:
            lines.append(f"  {p['name']:<11} {rng(p['w_lo'], p['w_hi']):<10} W  {p.get('use', '')}")
    return "\n".join(lines)


def page_docs(z, lang, day, cap=None, cap_src=None):
    """Documents for the plan page's `zones` collection: `current`, and a history entry."""
    keep = lambda r: {k: (fmt_pace(v) if k in ("pace_fast", "pace_slow") and v else v) for k, v in r.items()}
    cur = {"id": "current", "date": day, "source": SOURCE[lang].get(z["source"], z["source"]), "method": z.get("method"),
           "threshold_pace": fmt_pace(z["threshold_s"]) if z.get("threshold_s") else None,
           "lthr": z.get("lthr"), "max_hr": z.get("max_hr"), "rest_hr": z.get("rest_hr"), "rftp": z.get("rftp"),
           "easy_hr_cap": cap, "easy_source": cap_src,
           "rows": [keep(r) for r in z["rows"]], "hr_rows": [keep(r) for r in z["hr_rows"]], "power": z["power"]}
    hist = {"id": day, "date": day, "source": cur["source"], "threshold_pace": cur["threshold_pace"],
            "lthr": z.get("lthr"), "max_hr": z.get("max_hr"), "rftp": z.get("rftp")}
    return [cur, hist]


# --- aerobic threshold from decoupling ---------------------------------------------------------

def lt1(rows, lthr=None):
    """Personal aerobic-threshold HR from steady runs: under 5 % decoupling = at or below it."""
    runs = [r for r in rows if r.get("kind", "steady") == "steady" and r.get("avg_hr") and r.get("decoupling") is not None
            and (r.get("minutes") or 0) >= LT1_MIN_MIN and (r.get("gain_per_km") or 0) < LT1_MAX_GAIN
            and (r.get("temp_c") or 0) <= 22]
    below = [r["avg_hr"] for r in runs if r["decoupling"] <= DRIFT_OK]
    above = [r["avg_hr"] for r in runs if r["decoupling"] > DRIFT_OK]
    out = {"runs": len(runs), "below": sorted(below), "above": sorted(above), "estimate": None, "note": ""}
    if len(runs) < 3:
        out["note"] = "fewer than 3 flat steady runs of 45+ min: not enough to estimate"
    elif below and above and max(below) < min(above):
        out["estimate"] = round((max(below) + min(above)) / 2)
        out["note"] = f"between {max(below):.0f} (still under 5 % drift) and {min(above):.0f} (over)"
    elif below and above:
        out["estimate"] = round(min(above))
        out["note"] = (f"runs overlap ({max(below):.0f} under 5 % vs {min(above):.0f} over: heat, hills or fatigue): "
                       "the lower value, confirm with a drift test")
    elif below:
        out["estimate"] = round(max(below))
        out["note"] = f"at least {max(below):.0f}: no run over 5 % drift yet, the real value may be higher"
    else:
        out["note"] = f"every run drifted over 5 % (lowest at {min(above):.0f}): easy runs are probably above it"
        out["estimate"] = None
    # the easy-run cap: the highest HR proven to stay under 5 % drift, never the guess above it
    out["suggested_cap"] = round(max(below)) if below and out["estimate"] else None
    if out["estimate"] and lthr:
        out["pct_lthr"] = round(out["estimate"] / lthr * 100)
        out["default_cap"] = round(lthr * EASY_CAP)
    return out


# --- suggest -----------------------------------------------------------------------------------

def age(today, d):
    return (today - date.fromisoformat(d)).days


def suggest(ev):
    today = date.fromisoformat(ev.get("today") or date.today().isoformat())
    cur = ev["current"]
    thr = parse_pace(cur["threshold_pace"])
    out = {"pace": None, "lthr": None, "max_hr": None, "rest_hr": None, "rftp": None, "notes": [], "sources": []}
    cands = []   # (threshold seconds, weight, label)
    for t in ev.get("tests", []):
        if age(today, t["date"]) > MAX_AGE:
            continue
        pace = t["minutes"] * 60 / t["km"] if t.get("km") else parse_pace(t["pace"])
        cands.append((pace, 1.0, f"{t['minutes']} min test {t['date']}"))
        if t.get("hr_last20"):
            out["lthr"] = (t["hr_last20"], f"{t['minutes']} min test {t['date']} (avg HR, last 20 min)")
    for r in ev.get("races", []):
        if age(today, r["date"]) > MAX_AGE or not 4.5 <= r["km"] <= 22:
            continue
        if r.get("flat") is False or (r.get("temp_c") or 0) > 22:
            out["notes"].append(f"race {r['date']} ({r['km']:g} km) was hilly or hot: it doesn't set the pace")
            continue
        pace = parse_time(r["time"]) / r["km"]
        factor = RACE_TO_THRESHOLD[min(RACE_TO_THRESHOLD, key=lambda d: abs(d - r["km"]))]
        w = (1.0 if r["km"] >= 9 else 0.8) * (1.0 if age(today, r["date"]) <= 60 else 0.6)
        cands.append((pace / factor, w, f"{r['km']:g} km race {r['date']}"))
        if r.get("avg_hr") and r["km"] >= 15 and r["avg_hr"] > (cur.get("lthr") or 0) + 2:
            if not out["lthr"] or r["avg_hr"] > out["lthr"][0]:
                out["lthr"] = (r["avg_hr"], f"{r['km']:g} km race {r['date']}: a half is run just under LTHR, so "
                                            f"its average HR ({r['avg_hr']}) is a floor")
    for d in ev.get("device", []):
        if age(today, d["date"]) > MAX_AGE:
            continue
        src = f"{d.get('source', 'watch')} detection {d['date']}"
        if d.get("threshold_pace"):
            cands.append((parse_pace(d["threshold_pace"]), DEVICE_WEIGHT, src))
        if d.get("lthr") and not out["lthr"] and abs(d["lthr"] - (cur.get("lthr") or d["lthr"])) >= 2:
            out["lthr"] = (d["lthr"], src)
    if cands:
        vals = [c[0] for c in cands]
        spread = (max(vals) - min(vals)) / min(vals) * 100
        if spread > DISAGREE:
            out["notes"].append("the sources disagree by {:.1f} %: {} -> talk it through or settle it with a test; "
                                "meanwhile threshold work by HR with the slower pace".format(
                                    spread, "; ".join(f"{c[2]} says {fmt_pace(c[0])}" for c in cands)))
        else:
            new = sum(c[0] * c[1] for c in cands) / sum(c[1] for c in cands)
            change = (thr - new) / thr * 100            # + = faster
            out["sources"] = [c[2] for c in cands]
            if abs(change) >= NOISE:
                out["pace"] = (new, ", ".join(c[2] for c in cands))
            else:
                out["notes"].append(f"threshold pace confirmed ({fmt_pace(new)}/km, {change:+.1f} %): keep {cur['threshold_pace']}")
    # sessions only hint
    ses = [s for s in ev.get("sessions", []) if age(today, s["date"]) <= 42 and s.get("rep_pace")]
    fast = [s for s in ses if s["rep_pace"] < thr * 0.98 and s.get("rep_max_hr") and cur.get("lthr") and s["rep_max_hr"] <= cur["lthr"]]
    slow = [s for s in ses if s["rep_pace"] > thr * 1.02 and s.get("rep_max_hr") and cur.get("lthr") and s["rep_max_hr"] >= cur["lthr"] + 2]
    if len(fast) >= 2 and not out["pace"]:
        out["notes"].append(f"{len(fast)} threshold sessions in 6 weeks were > 2 % faster than {cur['threshold_pace']} "
                            "with HR under LTHR: the threshold is probably faster; a race or a 30 min test would put a number on it")
    if len(slow) >= 2 and not out["pace"]:
        out["notes"].append(f"{len(slow)} threshold sessions were slower than {cur['threshold_pace']} with HR above LTHR: "
                            "the zones may be too fast (or fatigue, heat, hills); check before changing")
    seen = [m for m in ev.get("max_hr_seen", []) if age(today, m["date"]) <= 365]
    if seen and cur.get("max_hr"):
        top = max(seen, key=lambda m: m["hr"])
        if cur["max_hr"] < top["hr"] <= cur["max_hr"] + 12:
            out["max_hr"] = (top["hr"], f"seen {top['date']}")
        elif top["hr"] > cur["max_hr"] + 12:
            out["notes"].append(f"max HR {top['hr']} on {top['date']} is far above {cur['max_hr']}: likely a sensor spike, ignored")
    if ev.get("rest_hr_7d") and cur.get("rest_hr") and abs(ev["rest_hr_7d"] - cur["rest_hr"]) >= 3:
        out["rest_hr"] = (ev["rest_hr_7d"], "7-day mean")
    eff = [e for e in ev.get("power_efforts", []) if age(today, e["date"]) <= MAX_AGE]
    if eff and cur.get("rftp"):
        est = max(e["watts"] * next((f for lim, f in EFFORT_TO_RFTP if e["minutes"] <= lim), 1.12) for e in eff)
        if abs(est - cur["rftp"]) / cur["rftp"] * 100 >= NOISE * 2:
            out["rftp"] = (round(est), "best effort in 120 days (same device only)")
    if not any(out[k] for k in ("pace", "lthr", "max_hr", "rftp")) and not cands and cur.get("set_on") \
            and age(today, cur["set_on"]) > RETEST_DAYS:
        out["notes"].append(f"zones set {cur['set_on']} ({age(today, cur['set_on']) // 7} weeks ago) and nothing new since: "
                            "worth talking about a retest (methodology.md 'Settling the threshold')")
    return out


def describe(out, ev, lang):
    cur = ev["current"]
    lines = ["Training zones: monthly check" if lang == "en" else "Tréningové zóny: kontrola"]
    changes = []
    if out["pace"]:
        new, src = out["pace"]
        old = parse_pace(cur["threshold_pace"])
        changes.append(f"threshold pace {cur['threshold_pace']} -> {fmt_pace(new)}/km ({(old - new) / old * 100:+.1f} %, "
                       f"{old - new:+.0f} s/km) from {src}")
        a, b = from_thresholds(old, cur.get("lthr")), from_thresholds(new, cur.get("lthr"))
        for name in ("Z2", "Z3"):
            ra, rb = next(r for r in a["rows"] if r["name"] == name), next(r for r in b["rows"] if r["name"] == name)
            changes.append(f"  {name}: {fmt_pace(ra['pace_fast'])}–{fmt_pace(ra['pace_slow'])} -> "
                           f"{fmt_pace(rb['pace_fast'])}–{fmt_pace(rb['pace_slow'])}")
    for key, label in (("lthr", "LTHR"), ("max_hr", "max HR"), ("rest_hr", "resting HR"), ("rftp", "rFTP")):
        if out[key]:
            changes.append(f"{label} {cur.get(key)} -> {out[key][0]} ({out[key][1]})")
    lines += ["PROPOSE " + c if not c.startswith("  ") else c for c in changes] or ["no change proposed"]
    lines += [f"note: {n}" for n in out["notes"]]
    if changes:
        lines.append("Nothing is written: show the runner, and update TrainingPeaks only after a yes "
                     "(trainingpeaks.md 'Zones'), then the same values on the watch, `season_plan.py retarget` "
                     "and the page.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("--tp-settings")
    s.add_argument("--threshold-pace")
    s.add_argument("--lthr", type=int)
    s.add_argument("--max-hr", type=int)
    s.add_argument("--rest-hr", type=int)
    s.add_argument("--rftp", type=int)
    s.add_argument("--method", choices=["8020", "hrmax", "hrr", "daniels"], default="8020")
    s.add_argument("--race", help="daniels: km=time, e.g. 10=43:05")
    s.add_argument("--easy-cap", type=int, help="easy-run HR cap from `lt1` (default 83 %% of LTHR)")
    s.add_argument("--easy-source", help="where the easy cap comes from, e.g. 'odhad z decouplingu'")
    s.add_argument("--source")
    s.add_argument("--date")
    s.add_argument("--lang", default="en")
    s.add_argument("--json", action="store_true")
    g = sub.add_parser("suggest")
    g.add_argument("evidence")
    g.add_argument("--lang", default="en")
    g.add_argument("--json", action="store_true")
    l1 = sub.add_parser("lt1")
    l1.add_argument("runs", help="analyze_session.py --json rows of steady runs (a JSON list)")
    l1.add_argument("--lthr", type=int)
    l1.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.cmd == "lt1":
        with open(args.runs) as f:
            out = lt1(json.load(f), args.lthr)
        if args.json:
            print(json.dumps(out, ensure_ascii=False))
        else:
            est = f"~{out['estimate']} bpm" + (f" ({out['pct_lthr']} % of LTHR)" if out.get("pct_lthr") else "") \
                if out["estimate"] else "no estimate"
            print(f"Aerobic threshold from {out['runs']} steady runs: {est}\n{out['note']}")
            if out.get("suggested_cap"):
                print(f"Easy-run cap: {out['suggested_cap']} (proven under 5 % drift)"
                      + (f"; the default 83 % of LTHR would be {out['default_cap']}" if out.get("default_cap") else ""))
        return
    lang = args.lang if args.lang in TX else "en"
    if args.cmd == "show":
        day = args.date or date.today().isoformat()
        if args.tp_settings:
            with open(args.tp_settings) as f:
                z = from_tp(json.load(f), lang)
            if args.source:
                z["source"] = args.source
        elif args.threshold_pace or args.method != "8020":
            z = from_thresholds(parse_pace(args.threshold_pace) if args.threshold_pace else None, args.lthr, args.max_hr,
                                args.rest_hr, args.rftp, args.source, args.method, args.race, lang)
        else:
            sys.exit("show needs --tp-settings, --threshold-pace or a --method")
        cap, cap_src = easy_cap(z, args.easy_cap, args.easy_source, lang)
        print(json.dumps(page_docs(z, lang, day, cap, cap_src), ensure_ascii=False) if args.json else table(z, lang, day, cap, cap_src))
        return
    with open(args.evidence) as f:
        ev = json.load(f)
    out = suggest(ev)
    if args.json:
        print(json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in out.items()}, ensure_ascii=False))
    else:
        print(describe(out, ev, lang))


if __name__ == "__main__":
    main()
