#!/usr/bin/env python3
"""Pain and illness diary, kept as TrainingPeaks calendar notes (one source of truth): writes the
note text in a fixed format, reads the notes back, and says what they mean for training.

Usage:
  health_log.py note --type pain --part "lýtko vľavo" --score 3 [--status new|same|better|worse|resolved]
                [--gait normal|changed] [--when during|after|morning|rest] [--text "..."] [--lang sk]
  health_log.py note --type illness --symptoms "nádcha, škrabanie v krku" [--fever] [--chest]
                [--status new|same|better|resolved] [--text "..."] [--lang sk]
  health_log.py read notes.json [--today 2026-11-02] [--lang sk] [--json]

note: prints {"title": ..., "description": ...} for tp_create_note on the day it happened (after
the runner agreed that reports go to TP). The last line of the description is machine-readable:
  rc: type=pain; part=lýtko vľavo; score=3; status=new; gait=normal; when=during
read: notes.json is tp_list_notes output (or a list of {date, title, description}); only notes
with an `rc:` line count. It groups pain by body part and illness by episode, and flags:
  pain (adapted from the pain-monitoring model [S53]): up to 3/10 that settles by the next
    morning: easy running, watch it; 4-5/10: no quality, shorter, watch it; 6+/10, a changed gait,
    pain at rest or at night, or worse in 3 reports in a row: stop and get it checked; the same
    place for more than 14 days: get it checked;
  illness (IOC consensus [S8], methodology.md §8): nose and throat only: easy running if OK;
    fever, chest symptoms or whole-body symptoms: no running until gone; then a 10-20 min test
    run and as many easy days as days missed.
--json gives the active issues and rows for the plan page's `health` collection.
"""
import argparse
import json
import re
import sys
from datetime import date

PAIN_EASY, PAIN_STOP = 3, 6        # /10: easy running allowed up to 3, 4-5 reduce, 6+ stop
LONG_DAYS = 14
TX = {
    "en": {"pain": "Pain", "illness": "Illness", "status": {"new": "new", "same": "same", "better": "better",
                                                           "worse": "worse", "resolved": "resolved"},
           "gait": "gait changed", "fever": "fever", "chest": "chest symptoms",
           "when": {"during": "during running", "after": "after running", "morning": "in the morning", "rest": "at rest"}},
    "sk": {"pain": "Bolesť", "illness": "Choroba", "status": {"new": "nové", "same": "rovnaké", "better": "lepšie",
                                                             "worse": "horšie", "resolved": "preč"},
           "gait": "zmenený krok", "fever": "horúčka", "chest": "príznaky na hrudníku",
           "when": {"during": "počas behu", "after": "po behu", "morning": "ráno", "rest": "v pokoji"}},
}
ADVICE = {
    "en": {"stop": "stop running and get it checked", "reduce": "no quality, shorter runs, watch it",
           "easy": "easy running is fine if it settles by the next morning", "check": "same place for {d} days: get it checked",
           "no_run": "no running until the fever / chest / whole-body symptoms are gone",
           "easy_ill": "easy running allowed if you feel OK", "return": "then a 10-20 min test run, and {d} easy days before quality",
           "doctor": "chest pain, palpitations or fainting: see a doctor first"},
    "sk": {"stop": "prestaň behať a daj si to skontrolovať", "reduce": "bez kvality, kratšie behy, sleduj to",
           "easy": "ľahký beh je OK, ak to do rána prejde", "check": "rovnaké miesto už {d} dní: daj si to skontrolovať",
           "no_run": "nebehaj, kým neprejde horúčka / hrudník / celkové príznaky",
           "easy_ill": "ľahký beh môžeš, ak sa cítiš OK", "return": "potom 10-20 min skúšobný beh a {d} ľahkých dní pred kvalitou",
           "doctor": "bolesť na hrudníku, búšenie srdca alebo mdloba: najprv k lekárovi"},
}


def note(a):
    tx = TX[a.lang]
    if a.type == "pain":
        title = f"{tx['pain']}: {a.part} {a.score}/10" + (f" ({tx['status'][a.status]})" if a.status != "new" else "")
        parts = [tx["when"][a.when] if a.when else None, tx["gait"] if a.gait == "changed" else None, a.text]
        rc = f"rc: type=pain; part={a.part}; score={a.score}; status={a.status}; gait={a.gait}" + (f"; when={a.when}" if a.when else "")
    else:
        title = f"{tx['illness']}: {a.symptoms}" + (f" ({tx['status'][a.status]})" if a.status != "new" else "")
        parts = [tx["fever"] if a.fever else None, tx["chest"] if a.chest else None, a.text]
        rc = (f"rc: type=illness; symptoms={a.symptoms}; fever={'yes' if a.fever else 'no'}; "
              f"chest={'yes' if a.chest else 'no'}; status={a.status}")
    desc = "\n".join([p for p in parts if p] + [rc])
    return {"title": title, "description": desc}


def parse(notes):
    out = []
    for n in notes:
        text = (n.get("description") or n.get("note") or "")
        m = re.search(r"^rc:\s*(.+)$", text, re.M)
        if not m:
            continue
        kv = dict(x.strip().split("=", 1) for x in m.group(1).split(";") if "=" in x)
        d = (n.get("date") or n.get("noteDate") or "")[:10]
        if not d:
            continue
        kv["date"] = d
        if "score" in kv:
            kv["score"] = int(float(kv["score"]))
        out.append(kv)
    return sorted(out, key=lambda e: e["date"])


def assess(entries, today, lang):
    adv = ADVICE[lang]
    issues, rows = [], []
    pains = {}
    for e in entries:
        if e.get("type") == "pain":
            pains.setdefault(e["part"].lower(), []).append(e)
    for part, es in pains.items():
        last = es[-1]
        first = next((x for x in reversed(es) if x.get("status") == "new"), es[0])
        days = (today - date.fromisoformat(first["date"])).days
        active = last.get("status") != "resolved"
        worse3 = len(es) >= 3 and all(x.get("status") == "worse" for x in es[-3:])
        rising = len(es) >= 3 and es[-1]["score"] > es[-2]["score"] > es[-3]["score"]
        if not active:
            level, advice = "resolved", ""
        elif last["score"] >= PAIN_STOP or last.get("gait") == "changed" or last.get("when") == "rest" or worse3 or rising:
            level, advice = "stop", adv["stop"]
        elif last["score"] > PAIN_EASY:
            level, advice = "reduce", adv["reduce"]
        else:
            level, advice = "easy", adv["easy"]
        if active and days > LONG_DAYS and level != "stop":
            advice += "; " + adv["check"].format(d=days)
        issues.append({"type": "pain", "part": es[-1]["part"], "since": first["date"], "days": days, "score": last["score"],
                       "trend": [x["score"] for x in es[-6:]], "level": level, "advice": advice, "active": active})
        rows += [{"id": f"{x['date']}-pain-{part}", "date": x["date"], "type": "pain", "part": x["part"], "score": x["score"],
                  "status": x.get("status")} for x in es]
    ill = [e for e in entries if e.get("type") == "illness"]
    episodes, cur = [], []
    for e in ill:
        if cur and (date.fromisoformat(e["date"]) - date.fromisoformat(cur[-1]["date"])).days > 7:
            episodes.append(cur)
            cur = []
        cur.append(e)
    if cur:
        episodes.append(cur)
    for ep in episodes:
        last = ep[-1]
        start, end = ep[0]["date"], last["date"]
        serious = any(x.get("fever") == "yes" or x.get("chest") == "yes" for x in ep)
        active = last.get("status") != "resolved"
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        if active:
            advice = adv["no_run"] if (last.get("fever") == "yes" or last.get("chest") == "yes") else adv["easy_ill"]
            level = "stop" if advice == adv["no_run"] else "easy"
        else:
            advice, level = (adv["return"].format(d=min(days, 7)) if serious else ""), "resolved"
        issues.append({"type": "illness", "symptoms": last.get("symptoms"), "since": start, "days": days, "serious": serious,
                       "level": level, "advice": advice, "active": active})
        rows += [{"id": f"{x['date']}-illness", "date": x["date"], "type": "illness", "symptoms": x.get("symptoms"),
                  "fever": x.get("fever") == "yes", "status": x.get("status")} for x in ep]
    if any(i["type"] == "illness" and i["active"] and i["serious"] for i in issues):
        issues.append({"type": "note", "advice": adv["doctor"], "level": "info", "active": True})
    return issues, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("note")
    n.add_argument("--type", choices=["pain", "illness"], required=True)
    n.add_argument("--part")
    n.add_argument("--score", type=int)
    n.add_argument("--gait", choices=["normal", "changed"], default="normal")
    n.add_argument("--when", choices=["during", "after", "morning", "rest"])
    n.add_argument("--symptoms")
    n.add_argument("--fever", action="store_true")
    n.add_argument("--chest", action="store_true")
    n.add_argument("--status", choices=["new", "same", "better", "worse", "resolved"], default="new")
    n.add_argument("--text")
    n.add_argument("--lang", default="en")
    r = sub.add_parser("read")
    r.add_argument("notes")
    r.add_argument("--today")
    r.add_argument("--lang", default="en")
    r.add_argument("--json", action="store_true")
    a = ap.parse_args()
    a.lang = a.lang if a.lang in TX else "en"
    if a.cmd == "note":
        if a.type == "pain" and (not a.part or a.score is None):
            sys.exit("pain needs --part and --score (0-10)")
        if a.type == "illness" and not a.symptoms:
            sys.exit("illness needs --symptoms")
        print(json.dumps(note(a), ensure_ascii=False))
        return
    with open(a.notes) as f:
        data = json.load(f)
    notes = data.get("notes", data) if isinstance(data, dict) else data
    today = date.fromisoformat(a.today) if a.today else date.today()
    issues, rows = assess(parse(notes), today, a.lang)
    if a.json:
        print(json.dumps({"issues": issues, "rows": rows}, ensure_ascii=False))
        return
    act = [i for i in issues if i["active"] and i["type"] != "note"]
    if not act:
        print("no active pain or illness" if a.lang == "en" else "žiadna aktívna bolesť ani choroba")
    for i in issues:
        if not i["active"] and i["type"] != "note":
            continue
        if i["type"] == "pain":
            print(f"{i['level'].upper():<7} {i['part']}: {i['score']}/10 (od {i['since']}, {i['days']} d, trend "
                  f"{'-'.join(map(str, i['trend']))}): {i['advice']}" if a.lang == "sk" else
                  f"{i['level'].upper():<7} {i['part']}: {i['score']}/10 (since {i['since']}, {i['days']} d, trend "
                  f"{'-'.join(map(str, i['trend']))}): {i['advice']}")
        elif i["type"] == "illness":
            print(f"{i['level'].upper():<7} {i['symptoms']} ({i['since']}, {i['days']} d): {i['advice']}")
        elif act:
            print(f"        {i['advice']}")


if __name__ == "__main__":
    main()
