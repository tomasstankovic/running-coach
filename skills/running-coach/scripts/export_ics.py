#!/usr/bin/env python3
"""Export a planned week as an .ics calendar file (Google / Apple / Outlook).

For runners without TrainingPeaks: each workout becomes a calendar event with the
full description, so the plan is on the phone next to everything else.

Usage:
  export_ics.py week.json --out plan.ics [--time 07:00]

Times are "floating" local times (no time zone), so 07:00 shows as 07:00 wherever the
runner's calendar is set.

week.json is the same file check_week.py reads; only its "plan" list is used
(or the file may be just that list). Each item: date, title, and optionally
description, minutes, km, type. Rest days (type "rest") are skipped.
"""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone


def escape(text):
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n"))


def fold(line):
    """RFC 5545: lines longer than 75 octets are folded with CRLF + space."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > 74:
            out.append(cur.decode("utf-8"))
            cur = b" " + b
        else:
            cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--time", default="07:00", help="start time for every workout, HH:MM")
    args = ap.parse_args()

    with open(args.plan_json) as f:
        data = json.load(f)
    plan = data["plan"] if isinstance(data, dict) else data
    hh, mm = (int(x) for x in args.time.split(":"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//running-coach//plan//EN", "CALSCALE:GREGORIAN"]
    count = 0
    for w in plan:
        if w.get("type") == "rest" or not w.get("title"):
            continue
        start = datetime.fromisoformat(w["date"][:10]).replace(hour=hh, minute=mm)
        minutes = float(w.get("minutes") or 60)
        end = start + timedelta(minutes=minutes)
        title = w["title"]
        summary = title + (f" · {w['km']:g} km" if w.get("km") and "km" not in title else "")
        uid = hashlib.sha1(f"{w['date']}|{title}".encode()).hexdigest()[:16] + "@running-coach"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{escape(summary)}",
            f"DESCRIPTION:{escape(w.get('description', ''))}",
            "CATEGORIES:Running",
            "END:VEVENT",
        ]
        count += 1
    lines.append("END:VCALENDAR")

    with open(args.out, "w", newline="") as f:
        f.write("\r\n".join(fold(l) for l in lines) + "\r\n")
    print(f"wrote {count} workouts to {args.out}")


if __name__ == "__main__":
    main()
