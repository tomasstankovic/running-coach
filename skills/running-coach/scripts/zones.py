#!/usr/bin/env python3
"""Training zones (Tréningové zóny): one table of pace, heart rate and power, and proposals to
update them from new evidence (monthly, or after a race, a test or a run of sessions that say
the zones are off).

Usage:
  zones.py show --tp-settings zones.json [--lang sk] [--json] [--date 2026-11-02]
  zones.py show --threshold-pace 4:20 --lthr 168 [--max-hr 186] [--rest-hr 50] [--rftp 300]
                [--source "30 min test"] [--lang sk] [--json]
  zones.py suggest evidence.json [--lang sk] [--json]

show: with TrainingPeaks, save only the `heartRateZones`, `speedZones` and `powerZones` blocks of
tp_get_athlete_settings to zones.json (the rest is personal data). TP's own bands are used (the
run set if there is one, else the general one); without TP the default 7-zone ratios. --json
gives the documents for the plan page's `zones` collection: `current` and one history entry.

suggest: evidence.json
{
  "today": "2026-11-02",
  "current": {"threshold_pace": "4:20", "lthr": 168, "max_hr": 186, "rest_hr": 50, "rftp": 300,
              "set_on": "2026-08-10"},            # when the zones were last set (profile)
  "tests": [{"date": "2026-10-20", "minutes": 30, "km": 7.05, "hr_last20": 171}],
  "races": [{"date": "2026-10-25", "km": 21.0975, "time": "1:31:40", "avg_hr": 171,
             "flat": true}],                      # hilly, trail or hot races don't set the pace
  "sessions": [{"date": "2026-10-28", "kind": "intervals", "rep_pace": 252, "rep_max_hr": 162,
                "target": "threshold"}],          # analyze_session.py --json rows of threshold work
  "max_hr_seen": [{"date": "2026-10-25", "hr": 189}],
  "rest_hr_7d": 48,
  "power_efforts": [{"date": "2026-10-20", "watts": 318, "minutes": 30}]
}
Rules (methodology.md "When the threshold evidence disagrees" and "Keeping the zones current"):
a 30-min test sets both threshold pace and LTHR; a flat 5k-HM race sets the pace (paces.py race
factors) and a half's average HR is a floor for LTHR; threshold sessions only hint ("faster" or
"slower", no number). Evidence older than 120 days is ignored. Sources more than 3 % apart are
reported as a disagreement to discuss (or settle with a test), not averaged. A change under
1.5 % (~4 s/km) is noise and is kept. With no new evidence and zones older than 12 weeks, it
suggests talking about a retest. It never writes anything: the coach proposes, the runner
decides, then TrainingPeaks is updated (trainingpeaks.md "Zones").
"""
import argparse
import json
import sys
from datetime import date

from paces import (DEFAULT_HR_ZONES, DEFAULT_SPEED_ZONES, EFFORT_TO_RFTP, POWER_ZONES, RACE_TO_THRESHOLD,
                   fmt_pace, parse_pace, parse_time)

RUN_TYPE = 3                 # TrainingPeaks workoutTypeId of running (0 = general)
MAX_AGE = 120                # days of evidence that count
NOISE = 1.5                  # % change below which the zones stay
DISAGREE = 3.0               # % between sources that needs a conversation, not an average
RETEST_DAYS = 84             # 12 weeks
EASY_CAP = 0.83              # easy running up to ~83 % of LTHR (methodology.md §1)
NAMES = {"zone 1": "Z1", "zone 2": "Z2", "zone x": "X", "zone 3": "Z3", "zone y": "Y", "zone 4": "Z4", "zone 5": "Z5"}

USE = {
    "en": {"Z1": "recovery, warm-up and cool-down", "Z2": "easy and long runs (upper half: steady)",
           "X": "marathon pace, steady: only on purpose", "Z3": "tempo, cruise intervals",
           "Y": "threshold", "Z4": "VO2 intervals (5k-3k pace)", "Z5": "strides, short fast reps"},
    "sk": {"Z1": "regenerácia, rozklus, výklus", "Z2": "ľahké a dlhé behy (horná polovica: svižnejšie)",
           "X": "maratónske tempo, len zámerne", "Z3": "tempo, cruise intervaly",
           "Y": "prah", "Z4": "VO2 úseky (tempo 5 km až 3 km)", "Z5": "rovinky, krátke rýchle úseky"},
}
POWER_USE_SK = {"Easy": "ľahko, dlhé behy", "Moderate": "svižnejšie, maratónske tempo",
                "Threshold": "tempo, prah", "Interval": "VO2 úseky", "Repetition": "krátke rýchle úseky"}
TX = {
    "en": {"title": "Training zones", "zone": "Zone", "pace": "Pace /km", "pct": "% thr", "hr": "HR",
           "power": "Power", "use": "Use", "thr": "Threshold", "easy": "Easy running: HR up to {cap}",
           "from": "from {src}, {d}", "power_title": "Running power (rFTP {w} W)"},
    "sk": {"title": "Tréningové zóny", "zone": "Zóna", "pace": "Tempo /km", "pct": "% prahu", "hr": "Tep",
           "power": "Výkon", "use": "Na čo", "thr": "Prah", "easy": "Ľahký beh: tep do {cap}",
           "from": "zdroj: {src}, {d}", "power_title": "Bežecký výkon (rFTP {w} W)"},
}
SOURCE = {"en": {"default": "default ratios"}, "sk": {"default": "predvolené pomery"}}


def pick(blocks, key):
    sets = blocks.get(key) or []
    return next((s for s in sets if s.get("workoutTypeId") == RUN_TYPE), None) or next(
        (s for s in sets if s.get("workoutTypeId") in (0, None)), None) or (sets[0] if sets else None)


def from_tp(blocks):
    """Normalize TP's zone blocks (speed in m/s, HR in bpm, power in W)."""
    speed, hr, power = pick(blocks, "speedZones"), pick(blocks, "heartRateZones"), pick(blocks, "powerZones")
    z = {"source": "TrainingPeaks", "rows": [], "power": []}
    if speed:
        z["threshold_s"] = 1000 / speed["threshold"]
        for b in speed["zones"]:
            lo, hi = b["minimum"], b["maximum"]
            z["rows"].append({"name": NAMES.get(b["label"].lower(), b["label"]),
                              "pace_slow": 1000 / lo if lo > 0.5 else None,
                              "pace_fast": 1000 / hi if hi < 50 else None,
                              "pct_lo": round(lo / speed["threshold"] * 100), "pct_hi": round(hi / speed["threshold"] * 100) if hi < 50 else None})
    if hr:
        z.update(lthr=hr.get("threshold"), max_hr=hr.get("maximumHeartRate"), rest_hr=hr.get("restingHeartRate"))
        bands = hr["zones"]
        if len(bands) == len(z["rows"]):
            for row, b in zip(z["rows"], bands):
                row.update(hr_lo=b["minimum"], hr_hi=b["maximum"] if b["maximum"] < 250 else None)
        elif not z["rows"]:
            z["rows"] = [{"name": NAMES.get(b["label"].lower(), b["label"]), "hr_lo": b["minimum"],
                          "hr_hi": b["maximum"] if b["maximum"] < 250 else None} for b in bands]
    if power:
        z["rftp"] = power.get("threshold")
        z["power"] = [{"name": b["label"], "w_lo": b["minimum"], "w_hi": b["maximum"] if b["maximum"] < 1500 else None}
                      for b in power["zones"]]
    return z


def from_thresholds(thr_s, lthr=None, max_hr=None, rest_hr=None, rftp=None, source=None):
    z = {"source": source or "default", "threshold_s": thr_s, "lthr": lthr, "max_hr": max_hr,
         "rest_hr": rest_hr, "rftp": rftp, "rows": [], "power": []}
    for (name, lo, hi), (_, hlo, hhi) in zip(DEFAULT_SPEED_ZONES, DEFAULT_HR_ZONES):
        top = name == "Z5"
        row = {"name": name, "pace_slow": thr_s / lo, "pace_fast": None if top else thr_s / hi,
               "pct_lo": round(lo * 100), "pct_hi": None if top else round(hi * 100)}
        if lthr:
            row.update(hr_lo=round(lthr * hlo), hr_hi=None if top else round(lthr * hhi))
        z["rows"].append(row)
    if rftp:
        z["power"] = [{"name": n, "w_lo": round(lo * rftp), "w_hi": None if n == "Repetition" else round(hi * rftp)}
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


def table(z, lang, day):
    tx, use = TX[lang], USE[lang]
    lines = [f"{tx['title']}"]
    head = [f"{tx['thr']} {fmt_pace(z['threshold_s'])}/km" if z.get("threshold_s") else None,
            f"LTHR {z['lthr']:.0f}" if z.get("lthr") else None, f"max {z['max_hr']:.0f}" if z.get("max_hr") else None,
            f"rFTP {z['rftp']:.0f} W" if z.get("rftp") else None]
    src = SOURCE[lang].get(z["source"], z["source"])
    lines.append(" · ".join(h for h in head if h) + f"  ({tx['from'].format(src=src, d=day)})")
    lines.append("")
    lines.append(f"{tx['zone']:<5} {tx['pace']:<13} {tx['pct']:<10} {tx['hr']:<10} {tx['use']}")
    for r in z["rows"]:
        pace = (f"{fmt_pace(r['pace_fast'])}–{fmt_pace(r['pace_slow'])}" if r.get("pace_fast") and r.get("pace_slow")
                else f"< {fmt_pace(r['pace_fast'])}" if r.get("pace_fast") else f"> {fmt_pace(r['pace_slow'])}" if r.get("pace_slow") else "–")
        if r["name"] == "Z5" and r.get("pace_slow"):
            pace = f"< {fmt_pace(r['pace_slow'])}"
        pct = rng(r.get("pct_lo"), r.get("pct_hi")) + " %" if r.get("pct_lo") is not None else "–"
        lines.append(f"{r['name']:<5} {pace:<13} {pct:<10} {rng(r.get('hr_lo'), r.get('hr_hi')):<10} {use.get(r['name'], '')}")
    if z.get("lthr"):
        lines.append("\n" + tx["easy"].format(cap=round(z["lthr"] * EASY_CAP)))
    if z["power"]:
        lines.append("\n" + tx["power_title"].format(w=round(z["rftp"] or 0)))
        for p in z["power"]:
            u = POWER_USE_SK.get(p["name"], "") if lang == "sk" else next((x[3] for x in POWER_ZONES if x[0] == p["name"]), "")
            lines.append(f"  {p['name']:<11} {rng(p['w_lo'], p['w_hi']):<10} W  {u}")
    return "\n".join(lines)


def page_docs(z, lang, day):
    """Documents for the plan page's `zones` collection: `current`, and a history entry."""
    use = USE[lang]
    cur = {"id": "current", "date": day, "source": SOURCE[lang].get(z["source"], z["source"]),
           "threshold_pace": fmt_pace(z["threshold_s"]) if z.get("threshold_s") else None,
           "lthr": z.get("lthr"), "max_hr": z.get("max_hr"), "rest_hr": z.get("rest_hr"), "rftp": z.get("rftp"),
           "easy_hr_cap": round(z["lthr"] * EASY_CAP) if z.get("lthr") else None,
           "rows": [{"name": r["name"], "pace_fast": fmt_pace(r["pace_fast"]) if r.get("pace_fast") else None,
                     "pace_slow": fmt_pace(r["pace_slow"]) if r.get("pace_slow") else None,
                     "pct_lo": r.get("pct_lo"), "pct_hi": r.get("pct_hi"), "hr_lo": r.get("hr_lo"),
                     "hr_hi": r.get("hr_hi"), "use": use.get(r["name"], "")} for r in z["rows"]],
           "power": [dict(p, use=(POWER_USE_SK.get(p["name"], "") if lang == "sk" else
                                   next((x[3] for x in POWER_ZONES if x[0] == p["name"]), ""))) for p in z["power"]]}
    hist = {"id": day, "date": day, "source": cur["source"], "threshold_pace": cur["threshold_pace"],
            "lthr": z.get("lthr"), "max_hr": z.get("max_hr"), "rftp": z.get("rftp")}
    return [cur, hist]


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
                     "(trainingpeaks.md 'Zones'), then `season_plan.py retarget` and the page.")
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
    s.add_argument("--source")
    s.add_argument("--date")
    s.add_argument("--lang", default="en")
    s.add_argument("--json", action="store_true")
    g = sub.add_parser("suggest")
    g.add_argument("evidence")
    g.add_argument("--lang", default="en")
    g.add_argument("--json", action="store_true")
    args = ap.parse_args()
    lang = args.lang if args.lang in TX else "en"
    if args.cmd == "show":
        day = args.date or date.today().isoformat()
        if args.tp_settings:
            with open(args.tp_settings) as f:
                z = from_tp(json.load(f))
            if args.source:
                z["source"] = args.source
        elif args.threshold_pace:
            z = from_thresholds(parse_pace(args.threshold_pace), args.lthr, args.max_hr, args.rest_hr, args.rftp, args.source)
        else:
            sys.exit("show needs --tp-settings or --threshold-pace")
        print(json.dumps(page_docs(z, lang, day), ensure_ascii=False) if args.json else table(z, lang, day))
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
