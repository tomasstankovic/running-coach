#!/usr/bin/env python3
"""Key-session roadmap for a season plan: the calculator, the rule check and the memory behind
the key sessions the coach designs. Used by `season_plan.py roadmap`, `retarget`,
`check-roadmap` and `actuals --sessions`; not run on its own.

The coach (Claude) designs the key sessions for the runner. `roadmap` writes a default draft for
a typical runner from progression ladders per phase (workouts.md "Progressions"): threshold
5x1 km -> 3x2 km -> 3x3 km -> 2x15 min -> 30 min continuous, hills/fartlek in base, VO2 and
half-marathon pace in build, race pace in the specific phase, sharpening in the taper; quality
waits 2-3 days after a race or test; marathon-pace long runs alternate with easy ones. The draft
knows nothing about injuries, terrain, what worked before or the weather: the coach edits it.

Targets are % of threshold speed (`basis`: [lo, hi] or "race:<km>"). Race-pace sessions use the
goal pace of the matching race, but never more than 3 % faster than the threshold supports; the
gap is reported. `retarget` fills or recomputes every future target from `basis` (after the
coach's edits, or after a new threshold or goal). `check-roadmap` checks the rules the coach's
version must keep: paces, hard days, recovery after races, marathon-pace long runs, milestones.

Milestones (6-10 a season): threshold check at the end of base, the longest run, the B races,
for a marathon the long runs with 14-16 km at marathon pace and a continuous 18-23 km at
marathon pace 2-4 weeks before (never in the week after a race), a dress rehearsal for shorter
goals, and the A race.

After the review, `actuals --sessions` judges each session (on / over / under / missed) and
proposes holding back the next step after under or missed; the coach decides with the context
(heat, hills, illness, a missed day for travel isn't lost fitness).
"""
from datetime import date, timedelta

from paces import RACE_TO_THRESHOLD, fmt_pace, pace_from_pct

DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
DEFAULT_DAYS = {"q1": "tue", "q2": "fri", "long": "sun"}
GOAL_CAP = 1.03          # race-pace targets at most 3 % faster than the threshold supports
MAX_MILESTONES = 10
TOLERANCE = (0.01, 0.02)  # rep pace: > 1 % slower than the target = under, > 2 % faster = over
HR_SLACK = 3             # bpm over the cap before a session counts as under target
HARD = {"threshold", "tempo", "vo2", "hm_pace", "mp", "mp_long", "race_pace", "test", "race", "hills", "speed", "fartlek"}
BIG_MP_KM = 14           # a long run with this much at marathon pace is a big session

# Ladders: (en, sk, % of threshold speed or None). "{km}" is filled with the week's long run.
LADDERS = {
    "threshold": ("threshold", [
        ("5x 1 km at threshold", "5× 1 km na prahu", (98, 100)),
        ("6x 1 km at threshold", "6× 1 km na prahu", (98, 100)),
        ("7x 1 km at threshold", "7× 1 km na prahu", (98, 100)),
        ("3x 2 km at threshold", "3× 2 km na prahu", (97, 99)),
        ("4x 2 km at threshold", "4× 2 km na prahu", (97, 99)),
        ("3x 3 km at threshold", "3× 3 km na prahu", (96, 98)),
        ("2x 15 min tempo", "2× 15 min v tempe", (93, 96)),
        ("2x 20 min tempo", "2× 20 min v tempe", (93, 96)),
        ("25 min continuous tempo", "25 min súvislé tempo", (92, 96)),
        ("30 min continuous tempo", "30 min súvislé tempo", (92, 96))]),
    "hills": ("hills", [
        ("8x 45 s uphill", "8× 45 s do kopca", None),
        ("10x 45 s uphill", "10× 45 s do kopca", None),
        ("10x 60 s uphill", "10× 60 s do kopca", None),
        ("fartlek 8x 1 min", "fartlek 8× 1 min", (100, 108)),
        ("fartlek 10x 1 min", "fartlek 10× 1 min", (100, 108)),
        ("fartlek 8x 2 min", "fartlek 8× 2 min", (100, 106))]),
    "vo2": ("vo2", [
        ("5x 3 min VO2", "5× 3 min (VO2)", (106, 110)),
        ("6x 3 min VO2", "6× 3 min (VO2)", (106, 110)),
        ("5x 1 km fast", "5× 1 km rýchlo", (104, 106)),
        ("6x 1 km fast", "6× 1 km rýchlo", (104, 106)),
        ("7x 1 km fast", "7× 1 km rýchlo", (104, 106))]),
    "hm": ("hm_pace", [
        ("3x 3 km at half-marathon pace", "3× 3 km v polmaratónskom tempe", "race:21.0975"),
        ("2x 5 km at half-marathon pace", "2× 5 km v polmaratónskom tempe", "race:21.0975"),
        ("3x 4 km at half-marathon pace", "3× 4 km v polmaratónskom tempe", "race:21.0975"),
        ("2x 6 km at half-marathon pace", "2× 6 km v polmaratónskom tempe", "race:21.0975")]),
    "mp_mid": ("mp", [
        ("2x 5 km at marathon pace", "2× 5 km v maratónskom tempe", "race:42.195"),
        ("2x 6 km at marathon pace", "2× 6 km v maratónskom tempe", "race:42.195"),
        ("2x 7 km at marathon pace", "2× 7 km v maratónskom tempe", "race:42.195")]),
    "hm_spec": ("hm_pace", [   # picks up where the build's 2x 6 km left off
        ("2x 6 km at half-marathon pace", "2× 6 km v polmaratónskom tempe", "race:21.0975"),
        ("3x 5 km at half-marathon pace", "3× 5 km v polmaratónskom tempe", "race:21.0975"),
        ("10 km continuous at half-marathon pace", "10 km súvisle v polmaratónskom tempe", "race:21.0975")]),
    "10k_spec": ("tempo", [
        ("3x 2 km at 10k pace", "3× 2 km v tempe na 10 km", "race:10"),
        ("3x 3 km at 10k pace", "3× 3 km v tempe na 10 km", "race:10"),
        ("4x 2.5 km at 10k pace", "4× 2,5 km v tempe na 10 km", "race:10")]),
    "5k_spec": ("vo2", [
        ("6x 800 m at 5k pace", "6× 800 m v tempe na 5 km", "race:5"),
        ("8x 800 m at 5k pace", "8× 800 m v tempe na 5 km", "race:5"),
        ("6x 1 km at 5k pace", "6× 1 km v tempe na 5 km", "race:5")]),
    "800s": ("vo2", [
        ("6x 800 m", "6× 800 m", (108, 112)),
        ("7x 800 m", "7× 800 m", (108, 112)),
        ("8x 800 m", "8× 800 m", (108, 112))]),
}

REHEARSAL = {
    "hm": ("2x 5 km at half-marathon pace", "2× 5 km v polmaratónskom tempe", "race:21.0975"),
    "10k": ("3x 3 km at 10k pace", "3× 3 km v tempe na 10 km", "race:10"),
    "5k": ("5x 1 km at 5k pace", "5× 1 km v tempe na 5 km", "race:5"),
}

TEXT = {
    "en": {"long": "Long run {km} km", "long_steady": "Long run {km} km, last 15 min steady",
           "long_mp_blocks": "Long run {km} km with 3x 4 km at marathon pace",
           "long_mp_end": "Long run {km} km, last 8 km at marathon pace",
           "long_hm_end": "Long run {km} km, last 6 km at half-marathon pace",
           "mp_long": "{km} km with {mp} km at marathon pace",
           "mp_cont": "{wu} km easy + {mp} km continuous at marathon pace",
           "taper_long_m": "{km} km with 6 km at marathon pace",
           "deload": "short threshold 4x 1 km", "maintain": "threshold maintenance 5x 1 km",
           "sharpen": "sharpening 3x 1 km at race pace",
           "test": "threshold check: 30 min time trial", "race": "{prio} race: {name}",
           "rehearsal": "dress rehearsal: {title}", "longest": "longest run: {title}",
           "hr": "HR", "hr_max": "HR max", "over_cap": "above the {cap} cap",
           "held": "held back a step after {date} ({verdict})",
           "held_log": "{title} {date}: {verdict}; the next sessions of this kind are held back a step (next: {next})",
           "propose": "{title} {date}: {verdict}. Proposal: repeat that step next time ({next}) instead of moving on",
           "verdict": {"under": "under target", "missed": "missed"}},
    "sk": {"long": "Dlhý beh {km} km", "long_steady": "Dlhý beh {km} km, posledných 15 min svižnejšie",
           "long_mp_blocks": "Dlhý beh {km} km s 3× 4 km v maratónskom tempe",
           "long_mp_end": "Dlhý beh {km} km, posledných 8 km v maratónskom tempe",
           "long_hm_end": "Dlhý beh {km} km, posledných 6 km v polmaratónskom tempe",
           "mp_long": "{km} km, z toho {mp} km v maratónskom tempe",
           "mp_cont": "{wu} km rozklus + {mp} km súvisle v maratónskom tempe",
           "taper_long_m": "{km} km so 6 km v maratónskom tempe",
           "deload": "krátky prah 4× 1 km", "maintain": "udržiavací prah 5× 1 km",
           "sharpen": "ostrenie 3× 1 km v tempe pretekov",
           "test": "kontrola prahu: 30 min test", "race": "{prio} závod: {name}",
           "rehearsal": "generálka: {title}", "longest": "najdlhší beh: {title}",
           "hr": "tep", "hr_max": "tep max", "over_cap": "nad limitom {cap}",
           "held": "o krok späť po {date} ({verdict})",
           "held_log": "{title} {date}: {verdict}; ďalšie tréningy tohto typu idú o krok späť (najbližší: {next})",
           "propose": "{title} {date}: {verdict}. Návrh: nabudúce zopakovať tento krok ({next}) namiesto posunu",
           "verdict": {"under": "pod cieľom", "missed": "vynechané"}},
}

# HR cap as a share of LTHR, by session type (methodology.md zones); None = no cap
HR_CAP = {"threshold": 1.0, "tempo": 0.97, "hm_pace": 0.96, "mp": 0.92, "mp_long": 0.92, "long": 0.83}


def distance_class(km):
    return "5k" if km <= 6 else "10k" if km <= 12 else "hm" if km <= 25 else "m"


class Targets:
    """Turns % of threshold speed into paces, and race-pace bases into % (goal-capped)."""

    def __init__(self, threshold_s, goals, lthr=None):
        self.thr, self.goals, self.lthr, self.notes = threshold_s, goals, lthr, []

    def race_pct(self, km):
        km = min(RACE_TO_THRESHOLD, key=lambda d: abs(d - km))   # 42.2 and 42.195 are the same race
        support = 100 / RACE_TO_THRESHOLD[km]
        goal = next((t for d, t in self.goals.items() if abs(d - km) < 0.5), None)
        if not goal:
            return support
        pct = self.thr / (goal / km) * 100
        if pct > support * GOAL_CAP:
            note = (f"goal pace for {km:g} km is {pct / support * 100 - 100:.1f} % faster than the threshold "
                    f"supports: targets use {fmt_pace(self.thr / (support * GOAL_CAP / 100))}/km until it improves")
            if note not in self.notes:
                self.notes.append(note)
            return support * GOAL_CAP
        return pct

    def pct(self, basis):
        if basis is None or isinstance(basis, tuple):
            return basis
        mid = self.race_pct(float(basis.split(":")[1]))
        return (round(mid - 0.5, 1), round(mid + 0.5, 1))

    def target(self, basis, kind, km=None, mp_km=None):
        t = {}
        pct = self.pct(basis)
        if pct:
            t["pct"] = list(pct)
            t["pace"] = f"{fmt_pace(pace_from_pct(self.thr, pct[1]))}–{fmt_pace(pace_from_pct(self.thr, pct[0]))}"
        if km:
            t["km"] = km
        if mp_km:
            t["mp_km"] = mp_km
        if self.lthr and HR_CAP.get(kind):
            t["hr_max"] = round(self.lthr * HR_CAP[kind])
        return t


def week_slots(week, days):
    start = date.fromisoformat(week["week_start"])
    return {slot: (start + timedelta(days=DAYS[d])).isoformat() for slot, d in days.items()}


def session(day, slot, kind, title, target, basis=None, ladder=None, step=None, milestone=False):
    s = {"id": f"{day}-{slot}", "date": day, "slot": slot, "type": kind, "title": title, "target": target,
         "milestone": milestone, "status": "planned", "actual": None, "note": ""}
    if basis is not None:
        s["basis"] = basis if isinstance(basis, str) else list(basis)
    if ladder:
        s["ladder"], s["step"] = ladder, step
    return s


def from_ladder(name, step, day, slot, lang, tg):
    kind, steps = LADDERS[name]
    step = min(step, len(steps) - 1)
    en, sk, basis = steps[step]
    kind = "tempo" if kind == "threshold" and isinstance(basis, tuple) and basis[1] < 97 else kind
    return session(day, slot, kind, sk if lang == "sk" else en, tg.target(basis, kind), basis, name, step)


def build_roadmap(plan, threshold_s, goals, days=None, lthr=None, runs=None):
    """Fill `key_sessions` on every week; returns notes (goal gaps etc.)."""
    spec = plan["spec"]
    lang = "sk" if spec.get("lang") == "sk" else "en"
    tx = TEXT[lang]
    days = {**DEFAULT_DAYS, **(days or {})}
    runs = runs or int(spec.get("runs_per_week", 5))
    tg = Targets(threshold_s, goals, lthr)
    races = {r["date"]: r for r in spec.get("races", [])}
    race_weeks = {(date.fromisoformat(d) - timedelta(days=date.fromisoformat(d).weekday())).isoformat(): r
                  for d, r in races.items()}
    weeks = plan["weeks"]
    a_races = sorted((r for r in spec["races"] if r.get("priority") == "A"), key=lambda r: r["date"])
    steps = {}
    b_race_weeks = {(date.fromisoformat(r["date"]) - timedelta(days=date.fromisoformat(r["date"]).weekday())).isoformat()
                    for r in spec.get("races", []) if r.get("priority") == "B"}
    last_long_mp = False

    def a_race_for(week):
        return next((r for r in a_races if r["date"] >= week["week_start"]), a_races[-1])

    def advance(name, move):
        s = steps.get(name, 0)
        if move:
            steps[name] = s + 1
        return s

    for i, w in enumerate(weeks):
        slot_day = week_slots(w, days)
        a = a_race_for(w)
        cls = distance_class(float(a["distance_km"]))
        phase, role, long_km = w["phase"], w["role"], w["long_km"]
        build = role == "build"
        ks = []
        race = race_weeks.get(w["week_start"])
        if role == "recovery":
            w["key_sessions"] = []
            continue
        if role in ("race", "race-B"):
            r = race
            if role == "race":
                sharpen = (date.fromisoformat(r["date"]) - timedelta(days=4)).isoformat()
                ks.append(session(sharpen, "q1", "race_pace", tx["sharpen"],
                                  tg.target(f"race:{r['distance_km']}", "race_pace"), f"race:{r['distance_km']}"))
            ks.append(session(r["date"], "race", "race", tx["race"].format(prio=r.get("priority", "C"), name=r["name"]),
                              {"km": r["distance_km"]}, milestone=True))
            w["key_sessions"] = ks
            continue
        if phase == "taper":
            ks.append(session(slot_day["q1"], "q1", "race_pace", tx["sharpen"],
                              tg.target(f"race:{a['distance_km']}", "race_pace"), f"race:{a['distance_km']}"))
            if cls == "m":
                ks.append(session(slot_day["long"], "long", "mp_long", tx["taper_long_m"].format(km=long_km),
                                  tg.target("race:42.195", "mp_long", long_km, 6), "race:42.195"))
            else:
                ks.append(session(slot_day["long"], "long", "long", tx["long"].format(km=long_km),
                                  tg.target(None, "long", long_km)))
            w["key_sessions"] = ks
            continue
        if role == "deload":
            ks.append(session(slot_day["q1"], "q1", "threshold", tx["deload"], tg.target((97, 99), "threshold"), (97, 99)))
        else:
            q1 = {"base": "threshold", "build": "hm" if cls in ("m", "hm") else "threshold",
                  "specific": {"m": "mp_mid", "hm": "hm_spec", "10k": "10k_spec", "5k": "5k_spec"}[cls]}[phase]
            ks.append(from_ladder(q1, advance(q1, build), slot_day["q1"], "q1", lang, tg))
            # second quality session with 5+ runs; a marathon's specific phase has enough with the
            # mid-week marathon pace and the long run, a 5k keeps threshold as maintenance
            q2 = {"base": "hills", "build": "vo2",
                  "specific": {"m": None, "hm": "800s", "10k": "800s", "5k": "maintain"}[cls]}[phase]
            if runs >= 5 and role == "build" and q2 == "maintain":
                ks.append(session(slot_day["q2"], "q2", "threshold", tx["maintain"],
                                  tg.target((98, 100), "threshold"), (98, 100)))
            elif runs >= 5 and role == "build" and q2:
                ks.append(from_ladder(q2, advance(q2, True), slot_day["q2"], "q2", lang, tg))
        if race and race.get("priority") == "C":
            ks[0] = session(race["date"], "race", "race", tx["race"].format(prio="C", name=race["name"]),
                            {"km": race["distance_km"]})
        # long run; big marathon-pace long runs never two weeks in a row or the week before a B race
        before_b = (date.fromisoformat(w["week_start"]) + timedelta(weeks=1)).isoformat() in b_race_weeks
        if cls == "m" and phase == "specific" and role == "build" and not last_long_mp and not before_b:
            mp = max(10, min(16, round(long_km * 0.45)))
            ks.append(session(slot_day["long"], "long", "mp_long", tx["mp_long"].format(km=long_km, mp=mp),
                              tg.target("race:42.195", "mp_long", long_km, mp), "race:42.195"))
        elif cls == "m" and phase == "build" and role == "build":
            n = advance("long_m", True)   # easy, last 8 km at M, easy, 3x 4 km at M, ...
            if n % 2 == 0 or before_b:
                ks.append(session(slot_day["long"], "long", "long", tx["long"].format(km=long_km), tg.target(None, "long", long_km)))
            else:
                key = "long_mp_end" if n // 2 % 2 == 0 else "long_mp_blocks"
                ks.append(session(slot_day["long"], "long", "mp_long", tx[key].format(km=long_km),
                                  tg.target("race:42.195", "mp_long", long_km, 8 if key == "long_mp_end" else 12), "race:42.195"))
        elif cls == "hm" and phase == "specific" and role == "build":
            ks.append(session(slot_day["long"], "long", "long", tx["long_hm_end"].format(km=long_km),
                              tg.target("race:21.0975", "hm_pace", long_km), "race:21.0975"))
        else:
            late_base = phase == "base" and i + 1 < len(weeks) and weeks[i + 1]["phase"] != "base"
            ks.append(session(slot_day["long"], "long", "long", tx["long_steady" if late_base else "long"].format(km=long_km),
                              tg.target(None, "long", long_km)))
        w["key_sessions"] = ks
        last_long_mp = any(x["slot"] == "long" and x["type"] == "mp_long" and x["target"].get("mp_km", 0) >= BIG_MP_KM
                           for x in ks)

    _milestones(plan, tg, tx, cls_of=lambda w: distance_class(float(a_race_for(w)["distance_km"])), a_races=a_races)
    _space_after_races(plan)
    plan["roadmap"] = {"threshold_pace": fmt_pace(threshold_s), "goals": {f"{k:g}": v for k, v in goals.items()},
                       "days": days, "lthr": lthr, "runs_per_week": runs}
    return tg.notes


def _milestones(plan, tg, tx, cls_of, a_races):
    weeks = plan["weeks"]
    # threshold check: the last full base week before build (or the race of <= 12 km in those weeks)
    for i, w in enumerate(weeks):
        if w["phase"] == "base" and i + 1 < len(weeks) and weeks[i + 1]["phase"] == "build":
            cand = [x for x in weeks[max(0, i - 3): i + 1] if x["role"] == "build"]
            if cand:
                q = next(s for s in cand[-1]["key_sessions"] if s["slot"] in ("q1", "race"))
                if q["type"] == "race":
                    q["milestone"] = True
                else:
                    q.update(type="test", title=tx["test"], target=tg.target((96, 100), "threshold"),
                             basis=[96, 100], milestone=True)
                    q.pop("ladder", None), q.pop("step", None)
    for a in a_races:
        seg = [w for w in weeks if w["week_start"] <= a["date"] and w["phase"] in ("build", "specific")
               and cls_of(w) == distance_class(float(a["distance_km"]))]
        prev_end = max((x["date"] for x in a_races if x["date"] < a["date"]), default="")
        seg = [w for w in seg if w["week_start"] > prev_end]
        if not seg:
            continue
        cls = distance_class(float(a["distance_km"]))
        race_day = date.fromisoformat(a["date"])
        longs = [s for w in seg for s in w["key_sessions"] if s["slot"] == "long"]
        if cls == "m":
            mp_longs = [s for s in longs if s["type"] == "mp_long" and (race_day - date.fromisoformat(s["date"])).days > 28]
            # continuous marathon-pace run 2-4 weeks out, not in the week after a race
            raced = {w["week_start"] for w in weeks if w["role"] in ("race", "race-B")}
            for back in (3, 2, 4):
                wk = (race_day - timedelta(days=race_day.weekday()) - timedelta(weeks=back))
                prev = (wk - timedelta(weeks=1)).isoformat()
                w = next((x for x in weeks if x["week_start"] == wk.isoformat()), None)
                if w and w["role"] not in ("race", "race-B") and prev not in raced and w["phase"] != "recovery":
                    s = next((s for s in w["key_sessions"] if s["slot"] == "long"), None)
                    if s:
                        mp = max(16, min(23, round(w["long_km"] - 5)))
                        wu = max(3, min(5, round(w["long_km"]) - mp))   # 3-5 km easy, then marathon pace
                        s.update(type="mp", title=tx["mp_cont"].format(wu=wu, mp=mp), milestone=True,
                                 target=tg.target("race:42.195", "mp", wu + mp, mp), basis="race:42.195")
                        # the long run a week before stays easy: two big marathon-pace runs 7 days apart is too much
                        pw = next((x for x in weeks if x["week_start"] == prev), None)
                        pl = pw and next((x for x in pw["key_sessions"] if x["slot"] == "long" and x["type"] == "mp_long"), None)
                        if pl:
                            pl.update(type="long", title=tx["long"].format(km=pw["long_km"]), milestone=False,
                                      target=tg.target(None, "long", pw["long_km"]))
                            pl.pop("basis", None)
                        break
            for s in sorted(mp_longs, key=lambda s: -s["target"].get("km", 0))[:2]:
                s["milestone"] = True
        else:
            if longs:
                top = max(longs, key=lambda s: s["target"].get("km", 0))
                top["milestone"] = True
                top["title"] = tx["longest"].format(title=top["title"][0].lower() + top["title"][1:])
            for back in (2, 3):
                wk = (race_day - timedelta(days=race_day.weekday()) - timedelta(weeks=back)).isoformat()
                w = next((x for x in weeks if x["week_start"] == wk and x["role"] == "build"), None)
                q = w and next((s for s in w["key_sessions"] if s["slot"] == "q1" and s["type"] != "race"), None)
                if q:
                    en, sk, basis = REHEARSAL[cls]
                    q.update(type="race_pace", title=tx["rehearsal"].format(title=sk if tx is TEXT["sk"] else en),
                             target=tg.target(basis, "race_pace"), basis=basis, milestone=True)
                    q.pop("ladder", None), q.pop("step", None)
                    break
        if cls == "m":
            top = max(longs, key=lambda s: s["target"].get("km", 0), default=None)
            if top and not top["milestone"]:
                top["milestone"] = True
    # keep at most MAX_MILESTONES: races and checks first, then the later long runs
    ms = [s for w in weeks for s in w["key_sessions"] if s["milestone"]]
    if len(ms) > MAX_MILESTONES:
        rank = {"race": 0, "test": 1, "mp": 2, "mp_long": 3}
        keep = sorted(ms, key=lambda s: (rank.get(s["type"], 4), s["date"]))[:MAX_MILESTONES]
        for s in ms:
            if s not in keep:
                s["milestone"] = False


def recovery_days(s):
    """Easy days needed after a race or test before the next hard session."""
    km = (s.get("target") or {}).get("km") or 0
    return 3 if s["type"] == "race" and float(km) >= 20 else 2


def _space_after_races(plan):
    """Move a hard session that follows a race or test too soon to the first allowed day of the
    same week, or drop it when that day is taken (the draft's rule; the coach may decide otherwise)."""
    weeks = plan["weeks"]
    hard = lambda x: x["type"] in HARD
    for w in weeks:
        for s in w["key_sessions"]:
            if s["type"] not in ("race", "test"):
                continue
            d0 = date.fromisoformat(s["date"])
            gap = recovery_days(s)
            for w2 in weeks:
                for x in list(w2["key_sessions"]):
                    dx = date.fromisoformat(x["date"])
                    if x is s or not hard(x) or not 0 < (dx - d0).days <= gap:
                        continue
                    new = d0 + timedelta(days=gap + 1)
                    end = date.fromisoformat(w2["week_start"]) + timedelta(days=6)
                    taken = any(y is not x and hard(y) and abs((date.fromisoformat(y["date"]) - new).days) <= 1
                                for wk in weeks for y in wk["key_sessions"])
                    if new <= end and not taken:
                        x["date"], x["id"] = new.isoformat(), f"{new.isoformat()}-{x['slot']}"
                    else:
                        w2["key_sessions"].remove(x)


def check_roadmap(plan):
    """The rules a roadmap must keep, whoever wrote it. Returns [(level, message)], level FAIL/WARN."""
    out = []
    rm = plan.get("roadmap") or {}
    thr = None
    if rm.get("threshold_pace"):
        m, sec = rm["threshold_pace"].split(":")
        thr = int(m) * 60 + int(sec)
    weeks = plan["weeks"]
    ks = sorted((dict(s, _week=w) for w in weeks for s in w.get("key_sessions") or []), key=lambda s: s["date"])
    need = ("id", "date", "slot", "type", "title", "target", "milestone", "status")
    for s in ks:
        miss = [k for k in need if k not in s]
        if miss:
            out.append(("FAIL", f"{s.get('date')} {s.get('title')}: missing {', '.join(miss)}"))
        t = s.get("target") or {}
        if thr and t.get("pct") and t.get("pace"):
            fast, slow = (int(x.split(":")[0]) * 60 + int(x.split(":")[1]) for x in t["pace"].split("–"))
            if abs(fast - pace_from_pct(thr, max(t["pct"]))) > 2.5 or abs(slow - pace_from_pct(thr, min(t["pct"]))) > 2.5:
                out.append(("FAIL", f"{s['date']} {s['title']}: pace {t['pace']} doesn't match {t['pct']} % of "
                                    f"{rm['threshold_pace']} (run `retarget` to fill paces)"))
        if s.get("basis") is not None and t.get("pct") is None and s["type"] != "race":
            out.append(("FAIL", f"{s['date']} {s['title']}: has a basis but no target pace (run `retarget`)"))
        if s["slot"] == "long" and t.get("km") and float(t["km"]) > s["_week"]["long_km"] + 1 and s["type"] != "race":
            out.append(("FAIL", f"{s['date']} {s['title']}: {t['km']} km is longer than the week's long run "
                                f"({s['_week']['long_km']} km, the plan's load rules)"))
    hard = [s for s in ks if s["type"] in HARD]
    for a, b in zip(hard, hard[1:]):
        if (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days == 1:
            out.append(("FAIL", f"two hard days in a row: {a['date']} {a['title']} and {b['date']} {b['title']}"))
    for r in (s for s in ks if s["type"] in ("race", "test")):
        d0, gap = date.fromisoformat(r["date"]), recovery_days(r)
        for x in hard:
            days = (date.fromisoformat(x["date"]) - d0).days
            if x is not r and 0 < days <= 2:
                out.append(("FAIL", f"{x['date']} {x['title']}: {days} day(s) after {r['title']}"))
            elif x is not r and 2 < days <= gap:
                out.append(("WARN", f"{x['date']} {x['title']}: {days} days after {r['title']} (3 easy days after a long race)"))
    big = [s for s in ks if s["type"] in ("mp", "mp_long") and (s["target"].get("mp_km") or 0) >= BIG_MP_KM]
    for a, b in zip(big, big[1:]):
        if (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days <= 8:
            out.append(("WARN", f"big marathon-pace runs a week apart: {a['date']} and {b['date']}"))
    races = [s for s in ks if s["type"] == "race"]
    for x in big:
        nxt = next((r for r in races if 0 < (date.fromisoformat(r["date"]) - date.fromisoformat(x["date"])).days <= 7
                    and float(r["target"].get("km") or 0) < 40), None)
        if nxt:
            out.append(("WARN", f"{x['date']} {x['title']}: big marathon-pace run in the week before {nxt['title']}"))
    a_marathons = {r["date"] for r in plan["spec"].get("races", [])
                   if r.get("priority") == "A" and float(r.get("distance_km", 0)) >= 40}
    for r in races:
        if r["date"] in a_marathons:
            d0 = date.fromisoformat(r["date"])
            cont = [x for x in ks if x["type"] == "mp" and x["slot"] == "long" and 14 <= (d0 - date.fromisoformat(x["date"])).days <= 28]
            if not cont:
                out.append(("WARN", f"{r['title']}: no continuous marathon-pace run 2-4 weeks before it"))
            for x in cont:
                after = [p for p in races if 0 < (date.fromisoformat(x["date"]) - date.fromisoformat(p["date"])).days <= 7]
                if after:
                    out.append(("FAIL", f"{x['date']} {x['title']}: in the week after {after[0]['title']}"))
    n_ms = sum(1 for s in ks if s.get("milestone"))
    if not 4 <= n_ms <= 10:
        out.append(("WARN", f"{n_ms} milestones (aim for 6-10)"))
    empty = [w["week_start"] for w in weeks if w["role"] != "recovery" and not w.get("key_sessions")]
    if empty:
        out.append(("WARN", f"weeks without key sessions: {', '.join(empty[:4])}" + (" ..." if len(empty) > 4 else "")))
    return out


def retarget(plan, threshold_s, goals, today):
    """Recompute targets of future sessions; returns {label: (old, new)} for the paces that moved."""
    rm = plan.get("roadmap") or {}
    lthr = rm.get("lthr")
    tg = Targets(threshold_s, goals, lthr)
    moved = {}
    for w in plan["weeks"]:
        for s in w.get("key_sessions", []):
            if s["date"] < today or s["status"] in ("done", "missed") or "basis" not in s:
                continue
            basis = s["basis"] if s["basis"] is None or isinstance(s["basis"], str) else tuple(s["basis"])
            old = s["target"].get("pace")
            new = tg.target(basis, s["type"], s["target"].get("km"), s["target"].get("mp_km"))
            s["target"] = new
            if old and new.get("pace") != old:
                moved.setdefault(s["type"], (old, new["pace"]))
    rm.update(threshold_pace=fmt_pace(threshold_s), goals={f"{k:g}": v for k, v in goals.items()})
    plan["roadmap"] = rm
    return moved, tg.notes


def judge(s, row, threshold_s, lang="en"):
    """Verdict of one key session against an analyze_session.py --json row."""
    t, tx = s["target"], TEXT[lang]
    num = (lambda v: f"{v:g}".replace(".", ",")) if lang == "sk" else (lambda v: f"{v:g}")
    if row is None:
        return "missed", ""
    km = row.get("km") or 0
    pace = row.get("rep_pace") if row.get("kind") == "intervals" else (row["minutes"] * 60 / km if km else None)
    parts = []
    if row.get("kind") == "intervals":
        parts.append(f"{row.get('reps')}× {num(row.get('rep_km'))} km @ {fmt_pace(row['rep_pace'])}")
    else:
        parts.append(f"{num(km)} km @ {fmt_pace(pace) if pace else '--'}/km")
    hr = row.get("rep_max_hr") or row.get("avg_hr")
    if hr:
        parts.append(f"{tx['hr_max'] if row.get('rep_max_hr') else tx['hr']} {hr:.0f}")
    verdict = "on"
    if t.get("pct") and pace and s["type"] not in ("mp_long", "mp"):
        slow, fast = pace_from_pct(threshold_s, t["pct"][0]), pace_from_pct(threshold_s, t["pct"][1])
        if pace > slow * (1 + TOLERANCE[0]):
            verdict = "under"
        elif pace < fast * (1 - TOLERANCE[1]):
            verdict = "over"
    if t.get("km") and km < t["km"] * 0.9:
        verdict = "under"
    if t.get("hr_max") and hr and hr > t["hr_max"] + HR_SLACK:
        verdict = "under"
        parts.append(tx["over_cap"].format(cap=t["hr_max"]))
    return verdict, ", ".join(parts)


def fill_actuals(plan, rows, today, hold_back=False):
    """Match analyze_session rows to past key sessions and judge them. After a session under target
    or missed, propose holding the rest of that ladder back a step (apply it with hold_back=True,
    once the coach has decided). Returns (change-log entries, proposals)."""
    rm = plan.get("roadmap") or {}
    if not rm.get("threshold_pace"):
        return [], []
    m, sec = rm["threshold_pace"].split(":")
    thr = int(m) * 60 + int(sec)
    by_date = {}
    for r in rows:
        by_date.setdefault(r.get("date", ""), []).append(r)
    changes, proposals, used = [], [], set()
    lang = "sk" if plan["spec"].get("lang") == "sk" else "en"
    tx = TEXT[lang]
    sessions = sorted((s for w in plan["weeks"] for s in w.get("key_sessions", [])), key=lambda s: s["date"])
    for s in sessions:
        if s["date"] >= today or s["status"] in ("done", "missed") or s["type"] == "race":
            continue
        d = date.fromisoformat(s["date"])
        cands = []
        for off in (0, -1, 1):
            day = (d + timedelta(days=off)).isoformat()
            cands += [(off, i, r) for i, r in enumerate(by_date.get(day, [])) if (day, i) not in used]
        any_run = s["slot"] == "long" or s["type"] in ("mp", "mp_long", "test")
        cands = [c for c in cands if any_run or c[2].get("kind") == "intervals"]
        pick = max(cands, key=lambda c: (c[0] == 0, c[2].get("km", 0) if any_run else 0), default=None)
        if pick is None and (date.fromisoformat(today) - d).days < 2:
            continue   # maybe not uploaded yet
        row = pick[2] if pick else None
        if pick:
            used.add(((d + timedelta(days=pick[0])).isoformat(), pick[1]))
        verdict, summary = judge(s, row, thr, lang)
        s["status"] = "missed" if verdict == "missed" else "done"
        s["actual"] = {"date": row.get("date") if row else None, "summary": summary, "verdict": verdict}
        if verdict in ("under", "missed") and s.get("ladder"):
            later = [x for x in sessions if x.get("ladder") == s["ladder"] and x["date"] > s["date"]
                     and x["status"] in ("planned", "adjusted") and x.get("step", 0) > s["step"]]
            if later and not hold_back:
                proposals.append(tx["propose"].format(title=s["title"], date=s["date"], verdict=tx["verdict"][verdict],
                                                      next=from_ladder(later[0]["ladder"], later[0]["step"] - 1, later[0]["date"],
                                                                       later[0]["slot"], lang, Targets(thr, {}, None))["title"]))
            elif later:
                tg = Targets(thr, {float(k): v for k, v in rm.get("goals", {}).items()}, rm.get("lthr"))
                for x in later:
                    new = from_ladder(x["ladder"], x["step"] - 1, x["date"], x["slot"], lang, tg)
                    x.update(title=new["title"], target=new["target"], step=new["step"], type=new["type"],
                             basis=new.get("basis"), status="adjusted",
                             note=tx["held"].format(date=s["date"], verdict=tx["verdict"][verdict]))
                changes.append({"date": today, "session": later[0]["id"],
                                "text": tx["held_log"].format(title=s["title"], date=s["date"], verdict=tx["verdict"][verdict],
                                                             next=later[0]["title"])})
    return changes, proposals


def upcoming(plan, today, n=6):
    sessions = [s for w in plan["weeks"] for s in w.get("key_sessions", [])]
    nxt = [s for s in sessions if s["date"] >= today][:n]
    return nxt, [s for s in sessions if s["milestone"]]


if __name__ == "__main__":
    print(__doc__)
