# Planning a week

Week mode, and the detailed weeks of a Block or Season: decide the week's role, draft it from
`workouts.md`, check it with `check_week.py`, present it, and save it after the runner's yes.
Read `SKILL.md` Steps 0–2 first (profile, data, zones); the paces come from there.

## 1. Decide the week's role

Every week has one role: `base`, `build`, `peak`, `deload`, `taper`, `race` or `return`. Decide it
from the block (weeks to race), the last 3–4 weeks' load, the CTL ramp or volume trend, TSB,
readiness, and how the runner feels. State it at the top of the plan with one sentence of why.

## 2. Draft

Build the week from `references/workouts.md`. With a season roadmap, start from the week's key
sessions (`season.md` §2b), and change them when this week's readiness, illness, terrain, weather
or the last session says so; say why. The principles that matter most:

- Mostly easy. One long run, one or two quality sessions, everything else easy (strides are fine).
- Fit the week to the runner's time budget (`methodology.md` §11): its tier sets the runs, the
  long run and the quality; extra time goes to easy running for a half or marathon, to quality
  for 5k/10k; in a busy week keep 2 runs with intensity rather than easy-only.
- Never two hard days in a row. Keep the long run away from hard days when possible.
- Progress one variable at a time: add a rep or some minutes before adding pace.
- Prescribe easy running by HR cap, with the runner's own easy pace range as a guide.
- Write sessions in the runner's unit from the profile (km or time), with the other in brackets:
  "10 km (~60 min)". Fit intensity to their terrain and to where quality can happen: pace on
  the flat, HR or effort on hills (`methodology.md` §9). If the profile has no `Units:` line yet,
  ask once.
- Available days are a maximum, not a target.
- Respect earlier decisions, unless they rested on mislabelled zones. Then re-anchor and say so.
- Add strength sessions only if the runner chose them (the profile says so, or ask once; see
  `strength.md`). Use their setting (gym, home, bodyweight), placement rules and phase dosage.

## 3. Check with the script

Write the plan and history to a JSON file and run:

```bash
python scripts/check_week.py week.json
```

History can be raw `tp_get_workouts` or Strava `list_activities` output. Give every plan item
both `minutes` and `km`, whatever the runner's unit, because the volume check compares time.
Planned-but-skipped TP workouts are ignored automatically. Without per-run data, pass weekly
totals as `history_weeks`; the docstring has the format. Give strength sessions
`"type": "strength"`.

The output starts with the longest allowed run for the week (it can change mid-week as an old long
run leaves the 30-day window); put it in the plan's header. Fix every FAIL. For each WARN, either
fix it or say in the plan why it's intended (e.g. "volume +14 %, but last week was a deload").

## 4. Present

Use this format, in the runner's language:

```
## Week 3–9 Nov: build (week 2 of block)
Status: CTL 28, ATL 34, TSB −6 · last week 52 km / 5 h 10 min · threshold 4:10/km, LTHR 174
Longest allowed run: 15.4 km (30-day longest 14 km + 10 %)
Why: <one or two sentences: what this week is for and what changed vs. last week>

| Day | Session | Volume | Intensity | Purpose |
|---|---|---|---|---|
| Mon | Rest | – | – | recover from the long run |
| Tue | Easy + 6 strides | 7 km · 45 min | 5:15–5:55/km, HR ≤ 145 | aerobic base, leg speed |
| ... |

Total: 54 km · 5 h 25 min · planned TSS ~330 · ~82 % easy
Check: volume +4 %, 2 hard days, long run 31 % of the week: all OK

### Sessions
**Tue: Easy + 6 strides.** <the full description exactly as it will appear on the watch/calendar>
...
```

Omit CTL/TSS when the source doesn't provide them. For a block, put the overview table
(`methodology.md` §5) above the first week. End by offering the next step: with TP, whether to
write the week to the calendar; without it, the calendar file.

## 5. Save the plan (after confirmation)

**TrainingPeaks.** Nothing is written before a clear yes, because the runner's watch syncs from
that calendar.
1. Check the target days with `tp_get_workouts` (and `tp_get_strength_workouts`). If something is
   already planned there, ask whether to replace or keep it. Never touch completed workouts.
2. Runs: write the session as a spec and run `scripts/tp_structure.py` with the runner's unit
   (`km` or `time`) and intensity metric (`pace`, or `hr` for hilly runs without a flat option).
   It returns a native `structured_workout`, a time-equivalent `structure`, `duration_minutes`
   and `distance_km`. Run `tp_validate_structure` on the `structure` to get the TSS, then
   `tp_create_workout` with sport `Run`, title, description, `structured_workout`,
   `duration_minutes`, `distance_km` and `tss_planned`. Kilometre steps need the native payload;
   the simplified `structure` is time-only. Easy and long runs get a one-step structure too, so
   the watch shows a target. See `trainingpeaks.md`.
3. Strength: `tp_create_strength_workout`, as in `strength.md`.
4. Report what was created (date, title, planned TSS) and anything that failed.

**No TrainingPeaks.** Make an `.ics` file for Google, Apple or Outlook calendar. It uses the same
`plan` list, each item with `date`, `title`, `description`, `minutes` and `km`:

```bash
python scripts/export_ics.py week.json --out plan-2026-11-03.ics --time 07:00
```

For a **Block** or **Season**, save only the first 1–2 weeks of sessions. Later weeks are
planned from what actually happens. The rough plan itself is stored and shown as in
`season.md` §4. With TP, offer to add the races with `tp_create_event` (priority A/B/C) if
they're missing.
