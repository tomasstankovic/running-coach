#!/usr/bin/env python3
"""Block report: what a training block (a phase of the season plan, or any date range) brought,
in one page: volume, key sessions, durability and efficiency, threshold, race forecast, readiness,
pain and illness, and the takeaways for the next block.

Usage:
  block_report.py plan.json [--phase base] [--from 2026-11-09 --to 2027-01-31]
                  [--sessions rows.json] [--predictions rows.json] [--zones rows.json]
                  [--trends rows.json] [--health health.json] [--lang sk] [--json]

Inputs are the plan file and the rows already kept for the plan page: `analyze_session.py --json`
rows (sessions), `forecast.py --json` (predictions), `zones.py show --json` history (zones),
`readiness.py --trend` (trends) and `health_log.py read --json` (health). Each is optional. With
--phase the block is the last run of weeks in that phase; with --from/--to any range. --json gives
one document for the plan page's `blocks` collection (id = the block's first Monday).
"""
import argparse
import json
from datetime import date, timedelta

TX = {
    "en": {"title": "Block report", "weeks": "weeks", "volume": "Volume", "of_plan": "of the plan", "longest": "longest run",
           "key": "Key sessions", "verdicts": {"on": "on target", "over": "better", "under": "under target", "missed": "missed"},
           "ms": "Milestones", "aerobic": "Aerobic fitness", "ef": "efficiency", "dur": "durability (late fade)",
           "thr": "Threshold", "fc": "Race forecast", "ready": "Readiness", "amber": "amber days", "red": "red days",
           "health": "Pain and illness", "none": "none", "take": "Takeaways", "planned": "planned",
           "t_volume_low": "volume reached only {p} % of the plan: plan the next block from what was actually run",
           "t_volume_ok": "volume as planned ({p} %)", "t_missed": "{lad}: {n} key sessions missed or under target: repeat that step before moving on",
           "ladders": {"threshold": "threshold", "hills": "hills / fartlek", "vo2": "VO2", "hm": "half-marathon pace",
                       "mp_mid": "marathon pace", "hm_spec": "half-marathon pace", "10k_spec": "10k pace", "5k_spec": "5k pace",
                       "800s": "800 m reps"},
           "phases": {},
           "t_over": "{n} sessions faster than target: check the threshold (race or test)",
           "t_fc_better": "the forecast for {race} improved by {d}", "t_fc_worse": "the forecast for {race} got slower by {d}",
           "t_dur": "durability improved from {a} % to {b} %", "t_dur_bad": "durability got worse ({a} % -> {b} %): long runs, fuelling, or fatigue?",
           "t_ready": "{n} amber/red days: look at sleep, stress and load", "t_health": "{n} days with pain or illness"},
    "sk": {"title": "Prehľad bloku", "weeks": "týž.", "volume": "Objem", "of_plan": "z plánu", "longest": "najdlhší beh",
           "key": "Kľúčové tréningy", "verdicts": {"on": "v cieli", "over": "lepšie", "under": "pod cieľom", "missed": "vynechané"},
           "ms": "Míľniky", "aerobic": "Aeróbna forma", "ef": "efektivita", "dur": "výdrž (pokles na konci)",
           "thr": "Prah", "fc": "Predpoveď pretekov", "ready": "Pripravenosť", "amber": "oranžových dní", "red": "červených dní",
           "health": "Bolesti a choroby", "none": "žiadne", "take": "Zhrnutie", "planned": "plán",
           "t_volume_low": "objem len {p} % plánu: ďalší blok plánuj od toho, čo sa naozaj odbehlo",
           "t_volume_ok": "objem podľa plánu ({p} %)", "t_missed": "{lad}: vynechané alebo pod cieľom {n}×: pred posunom zopakovať krok",
           "ladders": {"threshold": "prah", "hills": "kopce / fartlek", "vo2": "VO2", "hm": "polmaratónske tempo",
                       "mp_mid": "maratónske tempo", "hm_spec": "polmaratónske tempo", "10k_spec": "tempo na 10 km",
                       "5k_spec": "tempo na 5 km", "800s": "úseky 800 m"},
           "phases": {"base": "základ", "build": "budovanie", "specific": "špecifická", "taper": "ladenie", "race": "závod",
                      "recovery": "regenerácia"},
           "t_over": "{n} tréningov rýchlejších než cieľ: skontrolovať prah (pretek alebo test)",
           "t_fc_better": "predpoveď pre {race} sa zlepšila o {d}", "t_fc_worse": "predpoveď pre {race} sa zhoršila o {d}",
           "t_dur": "výdrž sa zlepšila z {a} % na {b} %", "t_dur_bad": "výdrž sa zhoršila ({a} % -> {b} %): dlhé behy, výživa alebo únava?",
           "t_ready": "{n} oranžových/červených dní: pozri spánok, stres a záťaž", "t_health": "{n} dní s bolesťou alebo chorobou"},
}


def fmt_secs(s):
    s = round(s)
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def load(path):
    if not path:
        return []
    with open(path) as f:
        d = json.load(f)
    return d.get("rows", d) if isinstance(d, dict) else d


def block_weeks(plan, phase=None, frm=None, to=None):
    weeks = plan["weeks"]
    if frm or to:
        return [w for w in weeks if (not frm or w["week_start"] >= frm) and (not to or w["week_start"] <= to)]
    if phase:
        idx = [i for i, w in enumerate(weeks) if w["phase"] == phase]
        if not idx:
            return []
        end = idx[-1]
        start = end
        while start > 0 and weeks[start - 1]["phase"] == phase:
            start -= 1
        return weeks[start:end + 1]
    return weeks


def report(plan, weeks, sessions, preds, zones, trends, health, lang):
    tx = TX[lang]
    first, last = weeks[0]["week_start"], weeks[-1]["week_start"]
    end = (date.fromisoformat(last) + timedelta(days=6)).isoformat()
    inside = lambda d: first <= (d or "")[:10] <= end
    planned = sum(w.get("km") or 0 for w in weeks)
    done = [w for w in weeks if w.get("actual_km") is not None]
    actual = sum(w["actual_km"] for w in done)
    planned_done = sum(w.get("km") or 0 for w in done)
    pct = round(actual / planned_done * 100) if planned_done else None
    ks = [s for w in weeks for s in w.get("key_sessions") or []]
    verdicts = {}
    for s in ks:
        v = (s.get("actual") or {}).get("verdict")
        if v:
            verdicts[v] = verdicts.get(v, 0) + 1
    ms = [{"date": s["date"], "title": s["title"], "verdict": (s.get("actual") or {}).get("verdict"),
           "summary": (s.get("actual") or {}).get("summary")} for s in ks if s.get("milestone")]
    steady = sorted((r for r in sessions if r.get("kind") == "steady" and inside(r.get("date"))), key=lambda r: r["date"])
    ef = [r["ef"] for r in steady if r.get("ef")]
    dur = [r["durability"] for r in steady if r.get("durability") is not None]
    zs = sorted((z for z in zones if z.get("id") != "current" and z.get("threshold_pace")), key=lambda z: z["date"])
    thr_start = next((z["threshold_pace"] for z in reversed(zs) if z["date"] <= first), zs[0]["threshold_pace"] if zs else None)
    thr_end = next((z["threshold_pace"] for z in reversed(zs) if z["date"] <= end), thr_start)
    races = {}
    for p in preds:
        if p.get("kind") == "race" and inside(p.get("date")):
            races.setdefault((p["name"], p["race_date"]), []).append(p)
    fc = []
    for (name, rd), rows in races.items():
        rows.sort(key=lambda r: r["date"])
        a, b = rows[0], rows[-1]
        key = "proj_mid" if b.get("proj_mid") is not None and a.get("proj_mid") is not None else "mid"
        fc.append({"race": name, "race_date": rd, "start": a[key], "end": b[key], "goal": b.get("goal")})
    tr = [t for t in trends if inside(t.get("date"))]
    amber = sum(1 for t in tr if t.get("verdict") == "AMBER")
    red = sum(1 for t in tr if t.get("verdict") == "RED")
    hrows = [h for h in (health.get("rows", []) if isinstance(health, dict) else health) if inside(h.get("date"))]
    hdays = len({h["date"] for h in hrows})
    longest = max((w.get("long_km") or 0 for w in weeks), default=0)
    take = []
    if pct is not None:
        take.append(tx["t_volume_low"].format(p=pct) if pct < 85 else tx["t_volume_ok"].format(p=pct))
    bad = {}
    for s in ks:
        if (s.get("actual") or {}).get("verdict") in ("under", "missed") and s.get("ladder"):
            bad[s["ladder"]] = bad.get(s["ladder"], 0) + 1
    for lad, n in bad.items():
        if n >= 2:
            take.append(tx["t_missed"].format(n=n, lad=tx["ladders"].get(lad, lad)))
    if verdicts.get("over", 0) >= 2:
        take.append(tx["t_over"].format(n=verdicts["over"]))
    for f in fc:
        if abs(f["end"] - f["start"]) >= 30:
            k = "t_fc_better" if f["end"] < f["start"] else "t_fc_worse"
            take.append(tx[k].format(race=f["race"], d=fmt_secs(abs(f["end"] - f["start"]))))
    if len(dur) >= 2 and abs(dur[-1] - dur[0]) >= 1:
        take.append((tx["t_dur"] if dur[-1] < dur[0] else tx["t_dur_bad"]).format(a=dur[0], b=dur[-1]))
    if amber + red >= 4:
        take.append(tx["t_ready"].format(n=amber + red))
    if hdays:
        take.append(tx["t_health"].format(n=hdays))
    phases = sorted({w["phase"] for w in weeks}, key=lambda p: [w["phase"] for w in weeks].index(p))
    return {"id": first, "from": first, "to": end, "phase": "+".join(phases), "weeks": len(weeks),
            "planned_km": round(planned), "actual_km": round(actual), "pct": pct, "weeks_with_data": len(done),
            "longest_km": longest, "verdicts": verdicts, "milestones": ms,
            "ef": [ef[0], ef[-1]] if ef else None, "durability": [dur[0], dur[-1]] if dur else None,
            "threshold": [thr_start, thr_end] if thr_start else None,
            "forecast": [dict(f, start=fmt_secs(f["start"]), end=fmt_secs(f["end"]),
                              goal=fmt_secs(f["goal"]) if f.get("goal") else None) for f in fc],
            "amber": amber, "red": red, "health_days": hdays, "takeaways": take}


def render(r, lang):
    tx = TX[lang]
    v = tx["verdicts"]
    phase = "+".join(tx["phases"].get(p, p) for p in r["phase"].split("+"))
    lines = [f"{tx['title']}: {phase} {r['from']} – {r['to']} ({r['weeks']} {tx['weeks']})", "",
             f"{tx['volume']}: {r['actual_km']} km" + (f" ({r['pct']} % {tx['of_plan']}; {tx['planned']} {r['planned_km']} km)"
                                                        if r["pct"] is not None else f" ({tx['planned']} {r['planned_km']} km)")
             + f" · {tx['longest']} {r['longest_km']} km"]
    if r["verdicts"]:
        lines.append(f"{tx['key']}: " + ", ".join(f"{n} {v.get(k, k)}" for k, n in r["verdicts"].items()))
    for m in r["milestones"]:
        lines.append(f"  ★ {m['date']} {m['title']}" + (f": {v.get(m['verdict'], m['verdict'])}, {m['summary']}" if m["verdict"] else ""))
    if r["ef"] or r["durability"]:
        bits = []
        if r["ef"]:
            bits.append(f"{tx['ef']} {r['ef'][0]:.2f} -> {r['ef'][1]:.2f}")
        if r["durability"]:
            bits.append(f"{tx['dur']} {r['durability'][0]:g} % -> {r['durability'][1]:g} %")
        lines.append(f"{tx['aerobic']}: " + " · ".join(bits))
    if r["threshold"]:
        lines.append(f"{tx['thr']}: {r['threshold'][0]} -> {r['threshold'][1]} /km")
    for f in r["forecast"]:
        lines.append(f"{tx['fc']} {f['race']}: {f['start']} -> {f['end']}" + (f" (cieľ {f['goal']})" if f["goal"] and lang == "sk"
                                                                            else f" (goal {f['goal']})" if f["goal"] else ""))
    lines.append(f"{tx['ready']}: {r['amber']} {tx['amber']}, {r['red']} {tx['red']}")
    lines.append(f"{tx['health']}: {r['health_days'] or tx['none']}")
    if r["takeaways"]:
        lines += ["", f"{tx['take']}:"] + [f"- {t}" for t in r["takeaways"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--phase")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    for k in ("sessions", "predictions", "zones", "trends", "health"):
        ap.add_argument(f"--{k}")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    lang = a.lang if a.lang in TX else "en"
    with open(a.plan) as f:
        plan = json.load(f)
    weeks = block_weeks(plan, a.phase, a.frm, a.to)
    if not weeks:
        raise SystemExit("no weeks in that block")
    health = {}
    if a.health:
        with open(a.health) as f:
            health = json.load(f)
    r = report(plan, weeks, load(a.sessions), load(a.predictions), load(a.zones), load(a.trends), health, lang)
    print(json.dumps(r, ensure_ascii=False) if a.json else render(r, lang))


if __name__ == "__main__":
    main()
