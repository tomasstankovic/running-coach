#!/usr/bin/env python3
"""Makes the English copies (en-*, tag `readme`) of the Slovak eval cases behind the README tables.

Run from the repository root after changing one of those Slovak cases:  python3 tests/make_en_evals.py
The Slovak case stays the source: its graders and data are copied, and the prompt, profile and
data text are replaced with the English versions below. Each en-* folder is rewritten from scratch.
"""
import json
import re
import shutil
from pathlib import Path

EV = Path(__file__).resolve().parent.parent / "skills" / "running-coach" / "evals"
SK = re.compile(r"[áäčďéíĺľňóôŕšťúýžÁČĎÉÍĽŇÓŠŤÚÝŽ]")

CASES = {
    "race-plan-hilly-half": "en-race-plan-hilly-half",
    "block-overview": "en-block-overview",
    "morning-brief-amber": "en-morning-brief-amber",
    "pain-diary-rising": "en-pain-diary-rising",
    "fuelling-practice": "en-fuelling-practice",
    "durability-long-run": "en-durability-long-run",
    "marathon-sub3-from-3-08": "en-marathon-sub3-from-3-08",
    "halfmarathon-sub90-from-1-33": "en-half-sub90-from-1-33",
}

FRONT = """---
tags: [running-coach, en, readme]
max_turns: {turns}
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

"""

PROMPTS = {
    "en-race-plan-hilly-half": """Today is 2 November 2026. On Sunday 15 November I'm running the Hilly Half Marathon, start at 10:00. The course is in course.gpx, and the aid stations are at km 5, 10, 15 and 20. I want to run 1:35. The forecast for the start: 21 °C, dew point 16 °C. My profile is in profile.md. Can you make me a race plan (pace, splits, fuelling)?

Input files: course.gpx, profile.md
""",
    "en-block-overview": """Today is 26 January 2027. My base block has just finished. How did it go, and what does it mean for the next block? The season plan is in plan.json, the long-run analyses in sessions.json, my illness records in health.json, my profile in profile.md.

Input files: plan.json, sessions.json, health.json, profile.md
""",
    "en-morning-brief-amber": """Use the running-coach skill for Mark's morning brief. Today is 2026-11-02. In this run the data are in files instead of TrainingPeaks: metrics.json (the last 56 days of tp_get_metrics: HRV, resting HR, sleep), today.json (today's planned workout from tp_get_workouts), notes.json (tp_list_notes for the last 30 days) and profile.md. Run scripts/readiness.py --brief on the metrics and scripts/health_log.py read on the notes. Weather in Bristol at 07:00: 6 °C, dry, light wind. Write the check-in in 3-5 lines: the verdict, what to do today exactly (keep, trim or swap the session, with paces and HR cap; heat adjustment if any), active pain or illness, and what moves if something changes. Then the ONE line for the phone (under 180 characters); PushNotification is not available in this run, so print it on its own line starting with "Notification:". Never change the TrainingPeaks calendar. Write in English.

Input files: metrics.json, today.json, notes.json, profile.md
""",
    "en-pain-diary-rising": """Today is 2 November 2026. My left calf hurt again on today's easy run, about 5/10, worse than last time. It also aches in the morning when I get up, even without running. I have intervals tomorrow. Can I go? My TrainingPeaks notes from the last few weeks are in notes.json, my profile in profile.md.

Input files: notes.json, profile.md
""",
    "en-fuelling-practice": """I'm training for a marathon in April 2027 (goal 3:20). On long runs I don't eat anything yet, one gel at most. In races my stomach always turns when I take more gels. How should I train my fuelling on the run?
""",
    "en-durability-long-run": """Yesterday I did a 26 km long run. The TrainingPeaks analysis is in analysis.json, my profile in profile.md. How does it look? It got pretty hard towards the end, and in my last marathon I hit the wall from km 32.

Input files: analysis.json, profile.md
""",
    "en-marathon-sub3-from-3-08": """Hi, I'm 38. I ran a 3:08 marathon this April and a 1:25:10 half in September. I run 5 times a week now, about 60 km, and I can give it 6-7 hours a week. I want to go under 3 hours at the Vienna City Marathon on 18 April 2027. Is that possible? How would you build my training for it?
""",
    "en-half-sub90-from-1-33": """I'm 29. I ran a 1:33:40 half in October and a 43:10 10k in September. I run 4 times a week, about 40 km, and I don't have more than 5 hours a week. I want to go under 1:30 this spring, at a half marathon on 11 April 2027. Is it realistic, and what should I change?
""",
}

PROFILES = {
    "en-race-plan-hilly-half": """# Running coach profile: Peter (fictional runner)
- 41, weight 68 kg. Goal: Hilly Half Marathon 15 Nov 2026 (B race), spring marathon 2027.
- Setup: TP + folder (no TP connection in this test).
- Threshold pace 4:22/km, LTHR 170, max HR 188. Easy runs up to HR 142.
- Forecast (forecast.py, 1 Nov 2026) for the half marathon: 1:34:30–1:37:30, middle 1:36:00 (before the heat adjustment, flat course).
- Gut: 45 g/h, 2026-10-18 (25 g gels, sports drink). Has not tried caffeine in training.
""",
    "en-block-overview": """# Running coach profile: Lucy (fictional runner)
- 39. Goals: half marathon 21 Mar 2027 in 1:38 (B), marathon 25 Apr 2027 in 3:25 (A).
- Setup: TP + folder (no TP connection in this test). Season plan: plan.json.
- Threshold pace 4:25/km, LTHR 168. Easy runs up to HR 140.
""",
    "en-morning-brief-amber": """# Running coach profile: Mark (fictional runner)
- 33. Goal: marathon 25 Apr 2027 in 3:05. Setup: TP + folder (no TP connection in this test).
- Threshold pace 4:12/km, LTHR 174, max HR 192, resting HR 47. Easy runs up to HR 145.
- Town: Bristol. Runs in the morning around 7:00.
""",
    "en-pain-diary-rising": """# Running coach profile: Kate (fictional runner)
- 35. Goal: half marathon 21 Mar 2027 under 1:45. Setup: TP + folder (no TP connection in this test).
- Threshold pace 4:48/km, LTHR 172, max HR 191. Easy runs up to HR 150.
- Health log: TP notes, ask each time.
- Tomorrow (3 Nov) planned: 6× 1 km @ 4:48–4:53, 2' jog.
""",
    "en-durability-long-run": """# Running coach profile: Tom (fictional runner)
- 44. Goal: marathon 25 Apr 2027 in 3:15. Last marathon 3:31, hit the wall from km 32.
- Setup: TP + folder (no TP connection in this test).
- Threshold pace 4:15/km, LTHR 172, max HR 189. Easy runs up to HR 145.
""",
}

# season_plan.py's own English labels, plus the session titles and summaries in the fixture
EXACT = {
    "A: Maratón": "A: Marathon", "B: Polmaratón": "B: Half marathon",
    "Maratón": "Marathon", "Polmaratón": "Half marathon",
    "A závod: Maratón": "A race: Marathon", "B závod: Polmaratón": "B race: Half marathon",
    "dlhý beh s úsekmi v maratónskom tempe": "long run with marathon-pace segments",
    "krátky prah, rovinky": "short threshold, strides",
    "len ľahké behy": "easy running only",
    "ostrenie v závodnom tempe": "race-pace sharpening",
    "prah (cruise intervaly)": "threshold (cruise intervals)",
    "regenerácia po závode": "recovery after the race",
    "rovinky + krátke kopce": "strides + short hills",
    "základ": "base", "budovanie": "build", "špecifická": "specific", "ladenie": "taper",
    "závod": "race", "regenerácia": "recovery",
    "nebežané (choroba / sviatky)": "not run (illness / holidays)",
    "podľa plánu": "as planned",
    "skrátené, ťažké nohy": "cut short, heavy legs",
    "5 km rozklus + 23 km súvisle v maratónskom tempe": "5 km warm-up + 23 km continuous at marathon pace",
    "Dlhý beh 20 km, posledných 15 min svižnejšie": "Long run 20 km, last 15 min brisker",
    "Dlhý beh 24 km, posledných 8 km v maratónskom tempe": "Long run 24 km, last 8 km at marathon pace",
    "Dlhý beh 29 km s 3× 4 km v maratónskom tempe": "Long run 29 km with 3× 4 km at marathon pace",
    "Jar 2027": "Spring 2027",
    "kontrola prahu: 30 min test": "threshold check: 30 min test",
    "ostrenie 3× 1 km v tempe pretekov": "sharpening 3× 1 km at race pace",
    "Choroba: nádcha, horúčka": "Illness: cold, fever",
}
PATTERNS = [
    (r"^Dlhý beh (\d+) km$", r"Long run \1 km"),
    (r"^(.+) do kopca$", r"\1 uphill"),
    (r"^(\d+) km so (\d+) km v maratónskom tempe$", r"\1 km with \2 km at marathon pace"),
    (r"^(.+) v polmaratónskom tempe$", r"\1 at half-marathon pace"),
    (r"^(.+) v maratónskom tempe$", r"\1 at marathon pace"),
    (r"^(.+) v tempe$", r"\1 tempo"),
    (r"^(.+) na prahu$", r"\1 at threshold"),
    (r"^(.+) rýchlo$", r"\1 fast"),
    (r"^krátky prah (.+)$", r"short threshold \1"),
]
TEXT_KEYS = {"title", "name", "key", "phase_label", "summary", "note"}


def tr(s):
    if s in EXACT:
        return EXACT[s]
    for pat, rep in PATTERNS:
        if re.match(pat, s):
            return re.sub(pat, rep, s)
    return s


def walk(x, key=None):
    if isinstance(x, dict):
        return {k: walk(v, k) for k, v in x.items()}
    if isinstance(x, list):
        return [walk(v, key) for v in x]
    if isinstance(x, str):
        if key == "lang":
            return "en"
        if key in TEXT_KEYS:
            return tr(x)
    return x


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def notes(rows):
    return {"notes": rows}


for sk, en in CASES.items():
    src, dst = EV / sk, EV / en
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    old_prompt = (src / "prompt.md").read_text()
    turns = re.search(r"max_turns: (\d+)", old_prompt).group(1)
    (dst / "prompt.md").write_text(FRONT.format(turns=turns) + PROMPTS[en])

    case = (dst / "case.yaml").read_text().replace(f"name: {sk}", f"name: {en}")
    case = case.replace(" Slovak.", " English.").replace("in Slovak", "in English")
    case = case.replace("9. 11. 2026 - 24. 1. 2027", "9 Nov 2026 - 24 Jan 2027").replace("on 19. 1.", "on 19 Jan")
    (dst / "case.yaml").write_text(case)

    if en in PROFILES:
        (dst / "files" / "profile.md").write_text(PROFILES[en])

    for g in (dst / "graders").glob("*.md"):
        t = g.read_text()
        t = t.replace("The response is in Slovak.", "The response is in English.")
        t = t.replace("amber (oranžová) verdict", "amber verdict").replace('"Notifikácia:"', '"Notification:"')
        g.write_text(t)

files = EV / "en-block-overview" / "files"
for name in ("plan.json", "sessions.json", "health.json"):
    write_json(files / name, walk(json.loads((files / name).read_text())))

files = EV / "en-morning-brief-amber" / "files"
write_json(files / "notes.json", notes([{
    "id": 1810111, "date": "2026-10-31T00:00:00", "title": "Pain: right Achilles 2/10",
    "description": "after running\nrc: type=pain; part=right Achilles; score=2; status=new; gait=normal; when=after"}]))
today = json.loads((files / "today.json").read_text())
today["description"] = today["description"].replace("klus", "jog")
write_json(files / "today.json", today)

files = EV / "en-pain-diary-rising" / "files"
write_json(files / "notes.json", notes([
    {"id": 6433012, "date": "2026-10-24T00:00:00", "title": "Pain: left calf 2/10",
     "description": "after running\nrc: type=pain; part=left calf; score=2; status=new; gait=normal; when=after"},
    {"id": 3530829, "date": "2026-10-28T00:00:00", "title": "Pain: left calf 3/10 (worse)",
     "description": "during running\nrc: type=pain; part=left calf; score=3; status=worse; gait=normal; when=during"},
    {"id": 7624039, "date": "2026-10-31T00:00:00", "title": "Pain: left calf 4/10 (worse)",
     "description": "during running\nrc: type=pain; part=left calf; score=4; status=worse; gait=normal; when=during"},
    {"id": 5550001, "date": "2026-10-20T00:00:00", "title": "Massage", "description": "Sports massage, thighs."},
]))

left = [str(p) for en in CASES.values() for p in (EV / en).rglob("*") if p.is_file() and SK.search(p.read_text(errors="ignore"))]
print("files with Slovak left:", left or "none")
