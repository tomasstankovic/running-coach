#!/usr/bin/env python3
"""Race plan: target time from the forecast and the weather, splits by the course profile, and
the fuelling and drinking plan, in one place.

Usage:
  race_plan.py plan.json [--lang sk] [--json] [--no-weather]

plan.json
{
  "race": {"name": "City Half", "date": "2027-04-03", "start": "10:00", "distance_km": 21.0975,
           "lat": 50.08, "lon": 14.42},             # the venue: for the weather only
  "forecast": {"low": 5330, "mid": 5420, "high": 5540},   # forecast.py race-day range (s), before heat
  "goal": "1:29:30",
  "course_gpx": "course.gpx",                        # optional: elevation profile
  "aid_km": [5, 10, 15, 20],                         # optional: aid stations
  "strategy": "even",                                # even | negative
  "weight_kg": 72,                                   # carb loading and breakfast in grams
  "gut_trained_gph": 60,                             # most carbs per hour tolerated in training
  "gel_carbs_g": 25, "caffeine_tested": false,
  "weather": {"temp_c": 12, "dew_c": 5}              # optional: instead of fetching
}

Target: the forecast range moved for the heat (weather.py: above 15 °C, 1-2 % slower per 5 °C,
the upper end when humid [S39]). The plan runs at the goal when it's inside that range, at the
fast end when the goal is beyond it (and says so), and gives a safe B. Splits are even effort:
each kilometre's pace follows its grade (Daniels' rule, ~8 s/km slower per 1 % uphill and ~5 s/km
faster per 1 % downhill [S46], never more than ~12 % faster downhill, Strava's GAP data [S51]) and
the total adds up to the target;
"negative" runs the second half ~2 % faster than the first. Fuelling follows the position
stands [S36-S38] (checkin-and-race.md), capped at what the runner's gut tolerated in training.
"""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from datetime import date

import weather as wx
from paces import fmt_pace, fmt_time, parse_time

STRETCH = 3.0          # % beyond the fast end that's still "a stretch"


# --- course --------------------------------------------------------------------------------------

def gpx_profile(path):
    """[(cumulative km, elevation m)] from a GPX track or route."""
    root = ET.parse(path).getroot()
    pts = [p for p in root.iter() if p.tag.endswith("trkpt") or p.tag.endswith("rtept")]
    out, km, prev = [], 0.0, None
    for p in pts:
        lat, lon = float(p.get("lat")), float(p.get("lon"))
        ele = next((float(c.text) for c in p if c.tag.endswith("ele") and c.text), None)
        if prev:
            km += haversine(prev[0], prev[1], lat, lon)
        out.append((km, ele))
        prev = (lat, lon)
    return out


def haversine(a, b, c, d):
    r = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def km_grades(profile, distance):
    """Average grade (%) of each kilometre, the profile scaled to the race distance."""
    pts = [(k, e) for k, e in profile if e is not None]
    n = math.ceil(distance - 1e-6)
    if len(pts) < 2:
        return [0.0] * n
    scale = distance / pts[-1][0] if pts[-1][0] else 1.0
    pts = [(k * scale, e) for k, e in pts]

    def ele_at(x):
        for (k1, e1), (k2, e2) in zip(pts, pts[1:]):
            if k1 <= x <= k2:
                return e1 + (e2 - e1) * ((x - k1) / (k2 - k1) if k2 > k1 else 0)
        return pts[-1][1]
    grades = []
    for i in range(n):
        a, b = i, min(i + 1, distance)
        grades.append((ele_at(b) - ele_at(a)) / ((b - a) * 1000) * 100 if b > a else 0.0)
    return grades


UP_S, DOWN_S = 8.4, 5.0   # s/km per 1 % grade: Daniels' 12-15 s/mile up, ~8 s/mile down [S46]
DOWN_CAP = 0.88           # downhill is never more than ~12 % faster (Strava's data-fitted GAP) [S51]


def grade_factor(g, pace):
    """Pace multiplier for an average grade in % at a flat pace of `pace` s/km."""
    if g >= 0:
        return 1 + UP_S * g / pace
    return max(DOWN_CAP, 1 - DOWN_S * -g / pace)


def splits(distance, total, grades, strategy):
    n = len(grades)
    lengths = [min(1.0, distance - i) for i in range(n)]
    f = [grade_factor(g, total / distance) for g in grades]
    if strategy == "negative":
        half = distance / 2
        f = [x * (1.01 if i + 0.5 < half else 0.99) for i, x in enumerate(f)]
    base = total / sum(x * l for x, l in zip(f, lengths))
    out, t = [], 0.0
    for i, (x, l, g) in enumerate(zip(f, lengths, grades)):
        secs = base * x * l
        t += secs
        out.append({"km": round(i + l, 4), "grade": round(g, 1), "pace": base * x, "split": secs, "cum": t})
    return out


# --- fuelling -----------------------------------------------------------------------------------

def carbs_per_hour(minutes, gut):
    """(g/h planned, (lo, hi) of the position stands or None) for a race of this many minutes."""
    if minutes < 75:
        return 0, None
    lo, hi = (30, 60) if minutes <= 150 else (60, 90)
    target = hi if minutes > 150 else 45
    if gut:
        target = max(30, min(target, gut))
    return target, (lo, hi)


def gel_times(minutes, gph, gel_g):
    if not gph:
        return []
    every = 60 * gel_g / gph
    first = 20 if minutes > 150 else 30
    out, t = [], first
    while t < minutes - 10:
        out.append(t)
        t += every
    return out


def at_minute(spl, minute):
    sec = minute * 60
    for s in spl:
        if s["cum"] >= sec:
            return s["km"] - (s["cum"] - sec) / s["pace"]
    return spl[-1]["km"]


# --- plan ---------------------------------------------------------------------------------------

def build(cfg, use_weather=True, today=None):
    race = cfg["race"]
    dist = float(race["distance_km"])
    fc = cfg.get("forecast") or {}
    goal = parse_time(cfg["goal"]) if cfg.get("goal") else None
    mid = fc.get("mid") or goal
    if not mid:
        raise ValueError("needs a forecast (forecast.py) or a goal")
    w = cfg.get("weather")
    if w and not w.get("source"):
        w = {**w, "source": "given"}                 # typed in by the runner, e.g. from a weather app
    if not w and use_weather and race.get("lat") is not None:
        w = wx.weather(race["lat"], race["lon"], race["date"], race.get("start", "09:00"), mid / 3600 + 0.25, today)
    heat = wx.heat_pct(w)
    adj = lambda x, p: x * (1 + p / 100) if x else None
    low, high = adj(fc.get("low") or mid, heat[0]), adj(fc.get("high") or mid, heat[1])
    mid_h = adj(mid, (heat[0] + heat[1]) / 2)
    notes = []
    if goal and low <= goal <= high:
        target, verdict = goal, "inside"
    elif goal and goal < low:
        gap = (low - goal) / low * 100
        target, verdict = low, ("stretch" if gap <= STRETCH else "out")
        notes.append(("goal_fast", {"goal": fmt_time(goal), "gap": f"{gap:.1f}", "start": fmt_time(low)}))
    elif goal:
        target, verdict = goal, "safe"
    else:
        target, verdict = mid_h, "forecast"
    b_goal = max(mid_h, target * 1.02)
    grades = km_grades(gpx_profile(cfg["course_gpx"]), dist) if cfg.get("course_gpx") else [0.0] * math.ceil(dist - 1e-6)
    spl = splits(dist, target, grades, cfg.get("strategy", "even"))
    minutes = target / 60
    gph, band = carbs_per_hour(minutes, cfg.get("gut_trained_gph"))
    gel = cfg.get("gel_carbs_g", 25)
    times = gel_times(minutes, gph, gel)
    aid = sorted(cfg.get("aid_km") or [])
    fuel = []
    for t in times:
        k = at_minute(spl, t)
        near = min(aid, key=lambda a: abs(a - k), default=None)   # take it at an aid station within 1 km
        fuel.append({"minute": round(t), "km": round(k, 1), "aid_km": near if near is not None and abs(near - k) <= 1 else None})
    kg = cfg.get("weight_kg")
    temp = (w or {}).get("temp_p75_c") or (w or {}).get("temp_c")
    pre = {"load": [round(10 * kg), round(12 * kg)] if kg and (dist > 40 or minutes > 90) else None,
           "breakfast_g": round(2 * kg) if kg else None,
           "caffeine_mg": round(3 * kg) if kg and cfg.get("caffeine_tested") else None,
           "warm": bool(temp and temp > 18), "long": minutes > 120}
    if minutes > 150 and not cfg.get("gut_trained_gph"):
        notes.append(("no_gut", {}))
    climb = sum(max(0, g) * min(1, dist - i) * 10 for i, g in enumerate(grades))
    # the gels start late and stop before the finish, so the rest of the hourly rate comes from the drink
    need = round(gph * minutes / 60) if gph else 0
    drink_g = need - len(fuel) * gel if need - len(fuel) * gel >= 10 else 0
    return {"race": race, "weather": w, "heat_pct": heat, "range": [low, mid_h, high], "goal": goal, "verdict": verdict,
            "target": target, "b_goal": b_goal, "splits": spl, "climb_m": round(climb), "gph": gph, "gph_band": band,
            "gut": cfg.get("gut_trained_gph"), "fuel": fuel, "gel_g": gel, "carbs_total_g": need,
            "drink_carbs_g": drink_g, "pre": pre, "notes": notes}


TX = {
    "en": {"title": "Race plan", "target": "Plan", "b": "safe B", "range": "forecast with the weather",
           "verdict": {"inside": "goal inside the range", "stretch": "goal a stretch", "out": "goal out of reach today",
                       "safe": "goal slower than the range: safe", "forecast": "no goal: the forecast"},
           "weather": "Weather", "forecast_w": "forecast", "climate_w": "typical for the date", "given_w": "given", "no_w": "no weather data",
           "splits": "Splits", "km": "km", "grade": "grade", "pace": "pace", "time": "time",
           "fuel": "Fuelling", "during": "during", "gel": "gel", "aid": "aid station", "drink": "Drinking",
           "before": "Before", "carb": "carb loading", "breakfast": "breakfast", "caffeine": "caffeine",
           "climb": "climb", "dew": "dew point", "wind": "wind", "up_to": "up to", "heat": "slower for the heat",
           "gph": lambda g, b, gut: (f"{g} g/h" + (f" (position stands {b[0]}-{b[1]} g/h" + (f", capped at your tolerated {gut} g/h" if gut else "") + ")" if b else ""))
                  if g else "none needed; a few sips of sports drink are optional",
           "total": lambda t, n, gels, drink: f"in all ~{t} g: {n} gels ({gels} g)"
                    + (f" + ~{drink} g from sports drink (~{drink / 60:.1f} L at 6 %)" if drink else ""),
           "drink_t": lambda warm, long: "0.4-0.8 L/h to thirst" + ("; more in the heat" if warm else "")
                    + ("; with sodium" if warm or long else "") + ". Never finish heavier than you started.",
           "load": lambda l: f"{l[0]}-{l[1]} g carbs a day for the last 36-48 h, low fibre" if l else "normal carb-rich eating, nothing new",
           "bf": lambda g: (f"~{g} g carbs about 3 h before" if g else "1-4 g carbs per kg 1-4 h before") + ", low fat and fibre",
           "caf": lambda mg: f"~{mg} mg about 60 min before" if mg else "only if tried in training (~3 mg/kg, 60 min before)",
           "notes": {"goal_fast": "goal {goal} is {gap} % faster than the fast end: start at {start} pace and decide after halfway",
                     "no_gut": "no gut-training data: plan 60 g/h and practise it on 3+ long runs before the race"}},
    "sk": {"title": "Plán pretekov", "target": "Plán", "b": "bezpečné B", "range": "predpoveď s počasím",
           "verdict": {"inside": "cieľ v rozpätí", "stretch": "náročný cieľ", "out": "cieľ dnes mimo dosahu",
                       "safe": "cieľ pomalší než rozpätie: bezpečný", "forecast": "bez cieľa: podľa predpovede"},
           "weather": "Počasie", "forecast_w": "predpoveď", "climate_w": "typické pre tento deň", "given_w": "zadané", "no_w": "bez údajov o počasí",
           "splits": "Medzičasy", "km": "km", "grade": "sklon", "pace": "tempo", "time": "čas",
           "fuel": "Výživa", "during": "počas", "gel": "gél", "aid": "občerstvovačka", "drink": "Pitie",
           "before": "Pred pretekmi", "carb": "sacharidové plnenie", "breakfast": "raňajky", "caffeine": "kofeín",
           "climb": "stúpanie", "dew": "rosný bod", "wind": "vietor", "up_to": "do", "heat": "pomalšie kvôli teplu",
           "gph": lambda g, b, gut: (f"{g} g/h" + (f" (odporúčania {b[0]}-{b[1]} g/h" + (f", obmedzené na tvojich vyskúšaných {gut} g/h" if gut else "") + ")" if b else ""))
                  if g else "netreba; pár dúškov iontového nápoja je voliteľných",
           "total": lambda t, n, gels, drink: f"spolu ~{t} g: {n}× gél ({gels} g)"
                    + (f" + ~{drink} g z iónového nápoja (~{drink / 60:.1f} l pri 6 %)".replace(".", ",") if drink else ""),
           "drink_t": lambda warm, long: "0,4-0,8 l/h podľa smädu" + ("; v teple viac" if warm else "")
                    + ("; so sodíkom" if warm or long else "") + ". Nikdy nedobehni ťažší, než si štartoval.",
           "load": lambda l: f"{l[0]}-{l[1]} g sacharidov denne posledných 36-48 h, málo vlákniny" if l else "bežné jedlo bohaté na sacharidy, nič nové",
           "bf": lambda g: (f"~{g} g sacharidov asi 3 h pred štartom" if g else "1-4 g sacharidov na kg 1-4 h pred štartom") + ", málo tuku a vlákniny",
           "caf": lambda mg: f"~{mg} mg asi 60 min pred štartom" if mg else "len ak si ho skúšal v tréningu (~3 mg/kg, 60 min pred)",
           "notes": {"goal_fast": "cieľ {goal} je o {gap} % rýchlejší než rýchly koniec: štartuj na {start} a rozhodni sa po polovici",
                     "no_gut": "chýbajú údaje o tréningu výživy: naplánuj 60 g/h a vyskúšaj to na 3+ dlhých behoch pred pretekmi"}},
}


def render(p, lang):
    tx = TX[lang]
    r = p["race"]
    low, mid, high = p["range"]
    lines = [f"{tx['title']}: {r['name']} {r['date']} {r.get('start', '')} ({r['distance_km']:g} km)", "",
             f"{tx['target']} {fmt_time(p['target'])} ({fmt_pace(p['target'] / float(r['distance_km']))}/km) · "
             f"{tx['b']} {fmt_time(p['b_goal'])} · {tx['range']} {fmt_time(low)}-{fmt_time(high)}"
             + (f" · {tx['verdict'][p['verdict']]}" if p["goal"] else "")]
    w = p["weather"] or {}
    if w.get("source"):
        src = tx.get(w["source"] + "_w", tx["climate_w"])
        lines.append(f"{tx['weather']}: {w['temp_c']} °C" + (f" ({tx['up_to']} {w['temp_p75_c']} °C)" if w.get("temp_p75_c") else "")
                     + (f", {tx['dew']} {w['dew_c']} °C" if w.get("dew_c") is not None else "")
                     + (f", {tx['wind']} {w['wind_kmh']} km/h" if w.get("wind_kmh") is not None else "") + f" ({src})")
        lo_h, hi_h = p["heat_pct"]
        if hi_h:
            lines.append(f"  {tx['heat']}: +{lo_h:g} %" if lo_h == hi_h else f"  {tx['heat']}: +{lo_h:g}-{hi_h:g} %")
    else:
        lines.append(f"{tx['weather']}: {tx['no_w']}")
    lines += ["", f"{tx['splits']} ({tx['climb']} {p['climb_m']} m):",
              f"  {tx['km']:>5}  {tx['grade']:>6}  {tx['pace']:>6}  {tx['time']:>8}"]
    dist = float(r["distance_km"])
    for s in p["splits"]:
        if s["km"] % 5 < 1e-6 or s["km"] >= dist - 1e-6 or abs(s["grade"]) >= 1.5 or s["km"] <= 2:
            lines.append(f"  {s['km']:>5g}  {s['grade']:>+5.1f}%  {fmt_pace(s['pace']):>6}  {fmt_time(s['cum']):>8}")
    lines += ["", f"{tx['fuel']}:", f"  {tx['during']}: " + tx["gph"](p["gph"], p["gph_band"], p["gut"])]
    for f in p["fuel"]:
        where = f" ({tx['aid']} {f['aid_km']:g} km)" if f["aid_km"] is not None else ""
        lines.append(f"  {f['minute']:>3} min · km {f['km']:g}: {tx['gel']} {p['gel_g']} g{where}")
    if p["carbs_total_g"]:
        lines.append("  " + tx["total"](p["carbs_total_g"], len(p["fuel"]), len(p["fuel"]) * p["gel_g"], p["drink_carbs_g"]))
    pre = p["pre"]
    lines += [f"  {tx['drink']}: " + tx["drink_t"](pre["warm"], pre["long"]), "", f"{tx['before']}:",
              f"  {tx['carb']}: " + tx["load"](pre["load"]), f"  {tx['breakfast']}: " + tx["bf"](pre["breakfast_g"]),
              f"  {tx['caffeine']}: " + tx["caf"](pre["caffeine_mg"])]
    lines += ["! " + tx["notes"][code].format(**kw) for code, kw in p["notes"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-weather", action="store_true")
    ap.add_argument("--today", help="for tests")
    a = ap.parse_args()
    with open(a.plan) as f:
        cfg = json.load(f)
    try:
        p = build(cfg, not a.no_weather, date.fromisoformat(a.today) if a.today else None)
    except (ValueError, KeyError) as e:
        sys.exit(f"error: {e}")
    if a.json:
        out = dict(p)
        out["splits"] = [dict(s, pace=fmt_pace(s["pace"]), cum=fmt_time(s["cum"])) for s in p["splits"]]
        out.update(target=fmt_time(p["target"]), b_goal=fmt_time(p["b_goal"]), range=[fmt_time(x) for x in p["range"]])
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(render(p, a.lang if a.lang in TX else "en"))


if __name__ == "__main__":
    main()
