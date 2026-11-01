# Season plan

A season plan is the rough map: one row per week from now to the A race (and its recovery), with
phase, role, target volume, long run and the key session. Detailed sessions are still planned one
or two weeks at a time (Week mode). The map changes when life does, and every change is logged.

## Contents
1. Races and priorities
2. Building the plan
3. TrainingPeaks ATP
4. Where the plan lives
5. Keeping it current: re-planning rules
6. Weekly review, automatically
7. Several seasons in a year

---

## 1. Races and priorities

Ask for every race the runner has in mind for the period: name, date, distance, terrain, and
how much it matters.

| Priority | Meaning | In the plan |
|---|---|---|
| **A** | the goal of the season | phases are planned backwards from it; full taper |
| **B** | important, run hard | a lighter week around it, no full taper; a checkpoint for the A goal |
| **C** | training race | replaces that week's key session; no change to volume |

More than one A race in a season only works with ~8+ weeks between them. Two A races closer than
that: suggest making one a B. Run the reality check (`onboarding.md` §4) for each A race. With TP,
offer to add missing races with `tp_create_event` (with `priority` A, B or C), after a yes.

## 2. Building the plan

Write a spec and run `scripts/season_plan.py generate` (the docstring has the format):

- `start`: Monday of the first week to plan (usually next Monday).
- `current`: the runner's typical recent week (km and longest run), from the history.
- `runs_per_week`, `easy_pace` (their real easy pace on their terrain), `lang`.
- `races`: all races with priority.
- `peak_km`: from the goal table in `onboarding.md` §4 and the runner's history (their best block
  is the best guide). Omit to use the default for the distance.
- `rhythm`: 3 (3:1) by default, 2 (2:1) for older runners or after a hard block.
- `busy`: weeks the runner already knows will be light (travel, holidays, work peaks), with a
  factor (0.5–0.7).

The script plans backwards from each A race: taper (1–3 weeks by distance), specific phase,
build, and base for whatever time is left. Volume grows at most 10 % per build week, every 4th
(or 3rd) week is a deload, B races and busy weeks count as lighter weeks, the long run grows
≤ 2 km a week within its share and cap. Warnings (peak not reachable, too few weeks) go to the
runner as part of the reality check, with numbers.

Present the plan as the block overview table (`methodology.md` §5) or, when the page exists,
link to it. Agree it with the runner before saving.

## 3. TrainingPeaks ATP

`tp_get_atp` reads the runner's Annual Training Plan in TP (weekly TSS targets, periods, races,
max 90 days per call). The MCP cannot write it. If there is one, show what it says and **ask**
whether to respect it:

- **Respect it**: use its periods and weekly TSS as the frame. Our weekly volumes should land near
  its targets (the plan's `tss` column is a rough estimate). Where they disagree a lot, say so.
- **Ignore it**: plan from scratch, and suggest the runner clears or ends it in TP so the two don't
  conflict.

Record the answer in the profile (`ATP: respected` or `ATP: ignored`). Without an ATP, nothing to
ask.

## 4. Where the plan lives

The plan file (`plan.json` from the script) is the source of truth. Store it where the runner's
setup allows, and keep one visible view of it.

**Plan page with a fixed link (preferred when the `Artifact` and `ArtifactData` tools exist).**
1. First time only: publish `assets/season-plan.html` with the `Artifact` tool, `icon`
   `"calendar"`, a description, and
   `capabilities: {"db": {"rules": [{"path": "", "read": "view", "write": "admin"}]}}`.
   Everyone the runner shares it with can read; only the runner (and Claude acting as them)
   writes.
2. Fill it: `season_plan.py export plan.json --format batch --out-dir docs` writes one JSON file
   per document (`plan/meta`, `weeks/<monday>`, `changes/<id>`) and prints the `ArtifactData`
   batch writes (≤ 50 per batch). Send each batch with `action: "batch"`.
3. Later updates: `ArtifactData` `list` of `weeks` (and `get` of `plan/meta`) to read the current
   versions, save them as `{"weeks/2027-01-11": 3, "plan/meta": 2, ...}`, and pass that file as
   `--versions`, so each write is pinned to the version it replaces. For one week's actuals, an
   `update` of that one document is enough. If a replan made the plan shorter, `delete` the weeks
   that fell off.
4. Save the page URL in the profile (`Plan page: https://claude.ai/artifact/...`). Never publish a
   second page for the same runner; update the one in the profile. The page is private until the
   runner shares it from its Share menu.

5. Keep it alive (each of these is optional; the page hides a section without data):
   - **This week**: when a week is planned in detail, `update` its `weeks/<monday>` document with
     `days`: `[{"date", "title", "km" or "minutes", "done": false}, ...]`. Mark `done: true` in
     the review or the morning check-in.
   - **Readiness**: `readiness.py metrics.json --trend 56` → rows for the `trends` collection
     (one per day: HRV 7-day mean, the normal band, verdict, resting HR, sleep).
   - **Aerobic fitness**: `analyze_session.py <data_file> --json --title "..."` for long and
     steady runs → rows for the `sessions` collection (EF, decoupling, km, date).
   - **Predictions**: `forecast.py input.json --json` → rows for the `predictions` collection
     (`--id id`): each race's forecast range over the weeks and the current form table
     (`analysis.md` "Race predictions").
   - `scripts/page_docs.py rows.json --collection trends --id date --out-dir docs` turns any of
     these lists into document files plus the `ArtifactData` batch writes, like the plan export.

The page shows the races, this week's sessions, the next race countdown, race predictions
(each race's forecast and its trend, current form), the volume chart
(planned bars by phase, actual line, today marker), readiness (HRV 7-day mean in the runner's
band, coloured by verdict), aerobic fitness (EF of steady runs, coloured by decoupling), the week
table and the change log. It is in the runner's
language when `lang` is `sk` or `en`; for other languages the labels stay English, while the
week rows (key sessions, notes) are in the runner's language.

**Without those tools** (e.g. claude.ai chat):
- TP: save `season_plan.py export plan.json --format markdown` as a TP note titled
  `Running coach plan` (same rules as the profile note: update its date so it stays in the
  90-day search window). Keep the full `plan.json` as a file in the Claude Project.
- No TP: `season-plan.md` (the markdown export) plus `plan.json` in the Claude Project knowledge.
- Show it as an artifact in the conversation when asked ("ukáž mi plán"): render the same
  information as the page from the stored plan. It's regenerated each time, so say so.

## 5. Keeping it current: re-planning rules

The A race date and its taper are fixed points. Everything before them can move. When something
changes, re-run `season_plan.py replan` from the first affected week with the runner's *current*
level, add a `--note`, then update the stored plan and the page.

| What happened | What changes |
|---|---|
| Training goes better than planned (reps easy, HR low, HRV stable) | keep the plan; discuss a threshold retest; raise the peak only if the history supports it |
| Signs of fatigue (TSB < −25 for 2+ weeks, HRV down, legs dead) | bring the next deload forward: `replan --busy <next monday>:0.7:early deload` |
| Illness ≤ 1 week | return as in `methodology.md` §8; the block continues, no replan needed |
| 1–2 weeks lost | `replan` from the return week with the reduced current volume; the script shortens base, then build. Say what it costs the goal. |
| > 2 weeks lost | `replan`, then redo the reality check: adjust the target time or switch the A race |
| Busy period at work, travel | add it as `--busy` weeks (factor 0.5–0.7): one quality session + the long run, everything else short and easy |
| Race added, moved or dropped | edit `races` in the plan's spec, `replan` from next Monday |
| Planned week missed partly (≥ 85 % done) | nothing; the review notes it |

The runner can report a change at any time ("do štvrtka som chorý", "next two weeks are a work
deadline"). Re-plan straight away, don't wait for the weekly review. Each change goes into the
log (`changes`) and, briefly, into the profile's decision log.

## 6. Weekly review, automatically

Review mode (`SKILL.md`) is the weekly checkpoint. With the plan it also:
1. Fills in the actuals: `season_plan.py actuals plan.json --history <last weeks' tp_get_workouts>`.
   Then update those week documents on the page, mark the week's `days` done, and add the
   long run's `analyze_session.py --json` row to `sessions`.
2. Compares the week with its row: volume ±15 %, the key session done, the long run.
   Re-runs `forecast.py` and adds its rows to `predictions`; a race goal that left the range is
   part of the review's decisions.
3. Applies section 5 if something changed, then plans next week in detail (Week mode) from the
   next row.

**Scheduled review.** If the `create_scheduled_task` tool is available (Claude desktop app), offer
once to schedule the review, e.g. Sunday 19:00 (`cronExpression` `0 19 * * 0`). The prompt must be
self-contained. Use this template, filled in, in the runner's language:

> Use the running-coach skill for the weekly review of <name>. Data: TrainingPeaks
> (trainingpeaks MCP). Profile: TP note "Running coach profile". Season plan: <page URL> (plus
> plan.json in <location>). Review the week that ends today: planned vs. actual, key sessions,
> readiness. Update the plan's actuals and the page. If the re-planning rules apply, propose the
> change; don't apply it without the runner's yes. Draft next week's sessions in detail.
> Do NOT write anything to the TrainingPeaks calendar: end with the draft and ask for confirmation.

Tell the runner that the task only runs while the app is open (otherwise at the next launch), and
that the review session waits for their answer before anything goes to the watch. Without
scheduled tasks, the runner starts the review themselves ("ako išiel týždeň?").

## 7. Several seasons in a year

Plan one season at a time, up to its A race and recovery. When that's done (or a few weeks
before), plan the next one as a new spec that starts after the recovery weeks, with `current` from
the actual recovery level. Append its weeks to the same plan and page, so the year reads as one
timeline. Keep the old weeks; they are the history the next reality check needs.
