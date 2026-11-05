---
tags: [running-coach, en, readme]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Use the running-coach skill for Mark's morning brief. Today is 2026-11-02. In this run the data are in files instead of TrainingPeaks: metrics.json (the last 56 days of tp_get_metrics: HRV, resting HR, sleep), today.json (today's planned workout from tp_get_workouts), notes.json (tp_list_notes for the last 30 days) and profile.md. Run scripts/readiness.py --brief on the metrics and scripts/health_log.py read on the notes. Weather in Bristol at 07:00: 6 °C, dry, light wind. Write the check-in in 3-5 lines: the verdict, what to do today exactly (keep, trim or swap the session, with paces and HR cap; heat adjustment if any), active pain or illness, and what moves if something changes. Then the ONE line for the phone (under 180 characters); PushNotification is not available in this run, so print it on its own line starting with "Notification:". Never change the TrainingPeaks calendar. Write in English.

Input files: metrics.json, today.json, notes.json, profile.md
