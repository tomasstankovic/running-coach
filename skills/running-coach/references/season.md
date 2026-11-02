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

### 2b. Key-session roadmap

Volume alone doesn't show where the preparation is going. Right after `generate`, design the key
sessions of every week **for this runner**. You are the coach; the script is the calculator, the
rule check and the memory. (Tested blind on three runners who needed adapting: the coach-designed
roadmap beat the script's own on all three. The script's draft can't see injuries, terrain, what
worked before or the winter.)

1. **Draft**: `season_plan.py roadmap plan.json --threshold-pace 4:12 --lthr 172 --days
   q1=tue,q2=fri,long=sun --out plan.json` writes a default for a typical runner (ladders in
   `workouts.md` "Progressions"; goals from the races' `goal`, or `--goals
   "21.1=1:29:30,42.2=3:15:00"`). Race-pace targets are at most 3 % faster than the threshold
   supports; the script warns when a goal is beyond that, and the runner hears it with numbers.
2. **Make it theirs.** Go through the profile and history and change what doesn't fit, including
   the *order* of sessions, not just single sessions:
   - injuries: drop or replace what aggravates them (hill sprints, fast reps, spikes);
   - terrain: no flat ground means effort/HR sessions; put pace sessions on the days flat ground
     is available; use the hills they have (hill reps, hill tempo by HR);
   - what worked before: reuse those formats as checkpoints; what broke them: leave it out, and
     check that nothing similar is left (e.g. 8× 2 min near 5k pace for someone wrecked by
     3–5 min VO2);
   - age and recovery, weather and season (ice, treadmill limits), holidays, the race course;
   - recovery around races and tests: 2 easy days after a short race or test, 3 after a half or
     longer; big marathon-pace long runs not in consecutive weeks or the week before a B race.
   Replace, move, drop or add sessions. Keep the principles: mostly easy, never two hard days in
   a row, one variable at a time (more reps, then longer reps, then faster), deloads lighter.
   Write the reason for each change in the session's `note` ("bez kopcových šprintov:
   Achillovka"). Keep the session format (`id`, `date`, `slot`, `type`, `title`, `target`,
   `milestone`, `status`, `actual`, `note`) and give every paced session a `basis`: `[lo, hi]` %
   of threshold speed, or `"race:<km>"` for race pace.
3. **Fill the targets**: `season_plan.py retarget plan.json --out plan.json` computes every
   future pace (and HR cap with LTHR) from `basis`. Never write a pace by hand.
4. **Check**: `season_plan.py check-roadmap plan.json`. Fix every FAIL (pace not matching its %,
   two hard days in a row, quality 1–2 days after a race or test, a long run longer than the
   week's, a continuous marathon-pace run in the week after a race). For each WARN, fix it or
   know why it's right for this runner.
- **Milestones** (★, 6–10 a season): the threshold check at the end of base (a short B race can
  be it), the longest run, the B races, the A race; for a marathon the long runs with 14–16 km
  at marathon pace and a continuous 18–23 km at marathon pace 2–4 weeks before the race (never
  in the week after a race; the long run a week before it stays easy); for shorter goals a dress
  rehearsal 2–3 weeks out.
- It's an estimate. Say so when you show it: the milestones, the next 4–6 sessions, and what you
  adapted for them and why, rather than the whole list.

**Week mode** starts from the week's key sessions: they set the quality days and their targets.
Deviate when readiness, illness, terrain or the last session says so, and say why.

**Weekly review**: run `analyze_session.py --json` for the week's key sessions and pass the rows to
`season_plan.py actuals ... --sessions rows.json`. Each past key session gets `actual` (what was
run, the pace, the HR) and a verdict: `on`, `over` (faster than target with HR under the cap),
`under` (> 1 % slower, HR over the cap, or a long run > 10 % short) or `missed`. A session not
uploaded yet (less than 2 days old) is left open. After `under` or `missed` the script only
*proposes* repeating that step next time (`PROPOSE` lines). Decide with the context: heat, wind,
hills, a bad night or illness explain a slow session without lost fitness, and a session missed
for travel isn't a reason to step back. When it is right, edit the next sessions (or run
`actuals ... --hold-back`), log it, and re-check. `over` changes nothing by itself: if the
threshold looks stale, retest it.

**New threshold or goal**: `season_plan.py retarget plan.json --threshold-pace 4:05` recomputes
every future target and logs which paces moved (e.g. "threshold 4:12–4:17 -> 4:08–4:13"). Tell
the runner how much the paces moved. Without `--threshold-pace` it only fills the targets of new
or edited sessions. `replan` keeps the roadmap: new weeks get the default draft
again (adapt them as in step 2 and re-check), past weeks keep theirs and their results.

Nothing from the roadmap goes to TrainingPeaks on its own: only the current week, planned in
detail and confirmed, goes to the calendar (`SKILL.md` Step 7).

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
setup allows (`onboarding.md` "Where things are kept"): in a working folder as
`running-coach/plan.json`, written directly; in chat as a file the runner adds to the Project.
Keep one visible view of it.

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
     `days`: `[{"date", "title", "km" or "minutes", "done": false}, ...]`. Strength sessions get
     `"kind": "strength"`; a day with no entry shows as a rest day (or add `"rest": true` with a
     title such as "Voľno, prechádzka"). The page always shows Monday to Sunday with the week's
     total. Mark `done: true` in the review or the morning check-in.
   - **Readiness**: `readiness.py metrics.json --trend 56` → rows for the `trends` collection
     (one per day: HRV 7-day mean, the normal band, verdict with its reason codes, resting HR,
     sleep). The page shows today's verdict, what to do and why, where the HRV sits in the band,
     and the trend from 5 days on.
   - **Aerobic fitness**: `analyze_session.py <data_file> --json --title "..."` for long and
     steady runs → rows for the `sessions` collection (EF, decoupling, km, date).
   - **Key sessions**: the week documents carry `key_sessions` from the roadmap, so the batch
     export puts them on the page. The page shows the next sessions with the milestones by
     default (also "milestones" and "all"), grouped by phase, with target pace, HR cap, the
     result and its verdict, and an "adjusted" mark that leads to the change log.
   - **Training zones**: `zones.py show ... --lang sk --json` → the `current` document and a history
     entry for the `zones` collection (`page_docs.py ... --collection zones --id id`). The page
     shows the table (pace, % of threshold, HR, use), power if set, and how the threshold moved.
     Write it after every zone change, and once at the start.
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

**Without those tools** (e.g. claude.ai chat; in a working folder also save
`running-coach/season-plan.md` next to `plan.json`):
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
2. Compares the week with its row: volume ±15 %, the key sessions (`actuals --sessions`, §2b), the
   long run. Milestone results are also results for `forecast.py` (`kind: "effort"`).
   Re-runs `forecast.py` and adds its rows to `predictions`; a race goal that left the range is
   part of the review's decisions.
   Training zones: in the first review of each month, and whenever the week brought a race, a
   test or sessions that say the zones are off, run `zones.py suggest` (`methodology.md`
   "Keeping the zones current"); a proposed change waits for the runner's yes.
3. Applies section 5 if something changed, then plans next week in detail (Week mode) from the
   next row.

**Scheduled review.** If the `create_scheduled_task` tool is available (Claude desktop app), offer
once to schedule the review, e.g. Sunday 19:00 (`cronExpression` `0 19 * * 0`). The prompt must be
self-contained. Use this template, filled in, in the runner's language:

> Use the running-coach skill for the weekly review of <name>. Data: TrainingPeaks
> (trainingpeaks MCP). Profile: TP note "Running coach profile". Season plan: <page URL> (plus
> plan.json in <location>). Review the week that ends today: planned vs. actual, key sessions,
> readiness. Update the plan's actuals and the page. If the re-planning rules apply, propose the
> change; don't apply it without the runner's yes. In the first review of the month (or after a
> race or test) check the training zones with zones.py suggest and propose any change; don't
> change zones in TrainingPeaks without the runner's yes. Draft next week's sessions in detail.
> Do NOT write anything to the TrainingPeaks calendar: end with the draft and ask for confirmation.

Tell the runner that the task only runs while the app is open (otherwise at the next launch), and
that the review session waits for their answer before anything goes to the watch. Without
scheduled tasks, the runner starts the review themselves ("ako išiel týždeň?").

## 7. Several seasons in a year

Plan one season at a time, up to its A race and recovery. When that's done (or a few weeks
before), plan the next one as a new spec that starts after the recovery weeks, with `current` from
the actual recovery level. Append its weeks to the same plan and page, so the year reads as one
timeline. Keep the old weeks; they are the history the next reality check needs.
