# Onboarding and the athlete profile

Run onboarding the first time you coach someone (no profile found), or when they ask to start
over or set a new goal. Its purpose is that every later conversation starts from the same,
written-down picture of the runner instead of re-asking or guessing.

## 1. Look for an existing profile first

- **TrainingPeaks**: `tp_list_notes` for the last 90 days (90 is the tool's maximum range). The
  profile is the note titled `Running coach profile` (keep that exact title in every language, so
  it can be found). Open it with `tp_get_note`.
- **No TP**: the profile is a file `athlete-profile.md`, usually in the claude.ai Project knowledge,
  so it's already in the conversation's context. Otherwise ask the runner to paste it.

If a profile exists, don't onboard again. Read it, check it's still current (goal date passed?
"updated" older than ~8 weeks?), and only ask about what changed.

## 2. Questionnaire

Ask in one message, grouped and short, in the runner's language. Pre-fill whatever the data
already answers, and ask the runner to confirm or correct it rather than asking again.

1. **Goal**: race (name, date, distance, terrain, target time), or a non-race goal (consistency,
   fitness, first 10k, get faster at 5k, trail season…). Also: what would make this season a
   success?
2. **Background**: how long they've been running, best recent results (distance + time + date),
   biggest weekly volume they've handled, and other sports.
3. **Availability**: runs per week, which days, the longest time available on weekdays and on
   weekends, preferred long-run day, and morning or evening.
4. **Units, terrain & tools** (`methodology.md` §9):
   - Kilometres or time: how they want sessions written ("10 km easy" vs. "60 min easy").
   - Where they usually run (road, gravel, forest, trail; flat or hilly). Pre-fill from the
     terrain read in §3 and ask them to confirm.
   - Where they can do faster sessions: a flat stretch, a track or a treadmill? This decides
     whether quality is prescribed by pace or by HR/effort.
   - What they steer by (pace, HR, feel, power) and their watch (does it show running power?).
5. **Health**: current pains or niggles, injury history (what, when, recurring?), anything a doctor
   said to watch.
6. **Strength**: whether they already do any strength work and whether they'd like it in the
   plan. Don't decide for them. If they're unsure, give the short why (fewer injuries, better
   economy, especially for calves, Achilles and hips) and the realistic cost (2 × 30 min a week).
   If yes, discuss the setting: gym, home with some equipment (which: kettlebell, dumbbells,
   bands, a step), bodyweight only, or a mix. Also their lifting experience and the time
   available. `strength.md` has templates for each setting.
7. **Preferences**: what kind of sessions they like or hate, how much structure they want, and
   language.

## 3. Load and assess history: the long view first, then the recent detail

The last few weeks don't tell you who this runner is. A runner at CTL 28 who was at 48 last
spring and has run a marathon is a very different case from a runner who has never been above 28.
So study **12–24 months** before judging the present.

**Long view (TrainingPeaks):**
1. `tp_get_fitness` with `start_date`/`end_date` covering the last 12–24 months (one call per
   year). Each response holds one row per day, so it's large. Save it to a file instead of
   reading it.
2. `tp_get_peaks` (sport `Run`, `days` 730) for `speed5K`, `speed10K`, `speedHalfMarathon` and
   `speedMarathon`: best efforts with dates and workout titles (race names often show up there).
3. Run the summary:
   ```bash
   python scripts/history_summary.py --fitness year1.json --fitness year2.json \
       --peaks p10k.json --peaks phm.json
   ```
   It prints a monthly table (load, CTL, days off), peak fitness and where the runner is now
   relative to it, build blocks with their ramp rate, breaks of 7+ days, likely races (big
   efforts after a taper) and best efforts.
4. Drill into what matters, without reading everything: for the best race and the peak block
   before it, `tp_get_weekly_summary` for 3–4 representative weeks (peak week, a typical build
   week, race week). That shows what training produced their best result: volume, long runs,
   key sessions.

**Long view (Strava):** `list_activities` page by page for the period (use the date filters if
available). Aggregate into weekly totals and run `history_summary.py --weeks weeks.json`. Find
races by name and pace.

**Long view (no data):** ask instead: "How did last year go? Your biggest weeks, best races and
how you prepared for them, longer breaks or injuries, and what worked and what didn't."

**Recent detail:** the last 8–12 weeks as in Week mode (`tp_get_workouts` in ≤ 90-day windows,
`tp_get_metrics` for HRV/RHR baselines).

**Terrain:** `tp_get_workouts` has no elevation, so open 8–12 recent runs with `tp_get_workout`
(a mix: easy, long, quality, a race) and take `metrics.elevation_gain` and
`metrics.distance_actual_km`. With Strava, `list_activities` already has `total_elevation_gain`.
Tag each run with a `kind` and run:
```bash
python scripts/terrain.py runs.json
```
It prints gain per km per run and the median by kind. The typical finding is "easy runs rolling
(~15–20 m/km), quality and races flat". That's what the questionnaire's terrain answers get
pre-filled with. Also note whether the runs carry `avg_power` (running power is available).

**Discuss the history with the runner** before concluding. The data shows *what* happened, and
only they know *why*: "In May your load dropped to almost zero for four weeks. Injury, illness, or
a planned break?" "Your best 10k effort was on 5 September. Was that a race?" "The spring block
took you from CTL 20 to 48 in 10 weeks. How did your body handle that?" Two or three such
questions are enough. Write their answers into the profile.

Summarize as a short assessment the runner can read:

- **Seasons**: when they peaked, how high, what that block looked like, and what followed (rest,
  injury, drop-off). Recurring patterns ("you usually build January–April and drop off in
  summer").
- **What worked**: the block or volume that produced their best results. That's the first
  candidate template for the next block.

- **Load now**: average and range of weekly time/km, runs per week, longest run, and the trend
  (building, stable, coming back from a break). CTL now vs. 6 weeks ago and vs. their peak
  ("you're at 58 % of last spring's fitness").
- **Intensity**: roughly how much is easy vs. hard. Flag "everything at the same moderate pace",
  a very common pattern.
- **Thresholds**: threshold pace and LTHR. Their source (TP setting, race-derived, estimated) and
  whether recent efforts agree (`scripts/paces.py race`).
- **Consistency**: missed weeks, gaps, how often long runs happen.
- **Readiness to train**: from HRV, resting HR and sleep baselines if available.
- **Gap to goal**: what the goal requires (volume, threshold, long run) vs. where they are. Say
  honestly if the target time or date looks unrealistic, and offer an alternative ("1:45 is
  realistic, 1:39 would need ~6 more months").

## 4. Reality check: goal × time × current level

This is where a good coach earns trust: by being honest before the plan, not after the race.
Put three things side by side: **the goal** (target time, date), **the time the runner will
really give** (runs/week, hours, which days) and **where they are now** (recent results,
`paces.py predict`, current vs. peak fitness from the history).

Typical requirements for recreational runners (a guide, not a law; talent, age and history move
these up or down):

| Goal | Runs / week | Peak week | Peak long run | Usually needs now (equivalent) |
|---|---|---|---|---|
| 5k finish / first 10k | 3 | 15–25 km | 6–10 km | running 30 min continuously |
| 10k sub-50 | 3–4 | 30–40 km | 12–14 km | 5k ≈ 23:30 |
| 10k sub-40 | 5–6 | 50–70 km | 16–20 km | 5k ≈ 19:00 |
| HM finish | 3–4 | 25–35 km | 16–18 km | 10k comfortably |
| HM sub-1:45 | 4–5 | 40–50 km | 18–21 km | 10k ≈ 47:30 |
| HM sub-1:30 | 5–6 | 55–75 km | 20–24 km | 10k ≈ 41:00 |
| Marathon finish | 4 | 40–55 km | 30–32 km | HM comfortably |
| Marathon sub-3:30 | 5–6 | 60–80 km | 32–35 km | HM ≈ 1:39 |
| Marathon sub-3:00 | 6–7 | 80–110 km | 32–36 km | HM ≈ 1:25 |

Gains that are realistic within one block (12–16 weeks) for someone already training
consistently: ~2–4 % on race time. For someone returning from a break, or who has never trained
in a structured way, more. Beyond ~5–8 %, it usually takes two blocks or a season.

**When they don't fit, say so: kindly, specifically, with numbers.** Don't build a plan you
don't believe in.

> "Polmaratón za 1:30 je tempo 4:16/km. Tvoj aktuálny 10k (48:30) zodpovedá ~1:47. Rozdiel je
> 16 %, a s jedným behom týždenne sa takýto skok spraviť nedá. Bežne to chce 5–6 behov a
> 55–75 km týždenne."

Then offer real options and let the runner choose:
1. **Adjust the target**: a realistic goal for this block ("1:42–1:45 is realistic, 1:39 if
   everything goes right").
2. **Adjust the time**: what would need to change (e.g. +2 runs/week, a longer weekend run).
   Check that it's actually possible for them, not wishful.
3. **Adjust the date**: a later race, or this race as a stepping stone ("this spring 1:42,
   next autumn sub-1:35 is a realistic path").
4. **A two-step plan**: a process goal now (consistency, a 10k PB), the big goal next season.

If they insist on an unrealistic goal, respect it, but say what you'll do: plan for the
realistic version, set a pacing strategy for race day that doesn't blow up at km 12, and revisit
at the mid-block checkpoint. Write the agreed goal *and* the reasoning into the profile. Never
increase load beyond safe progression to chase a number.

**Availability and preferred days.** Ask which days and how much time per day, and which day
suits the long run. Then check the pattern, not just the count:
- Days that force hard sessions back to back (e.g. only Sat + Sun free for quality): propose
  one hard day plus the long run, or a midweek early-morning slot.
- Too little time for the goal: say so (see above).
- More days than needed: available is a maximum. Suggest the right number and keep the spare
  day as a buffer for life.
- Long run on a day with limited time: move it, or accept a shorter long run and adjust the
  goal.
Agree the weekly template (which day is what) and save it in the profile, so weekly planning
starts from it.

## 5. Propose the plan shape

Recommend the block structure (phases and their lengths, from `methodology.md`), weekly volume to
start at and to peak at, runs per week, where strength fits, and the next 1–2 weeks in detail
(then continue as in Week mode).

## 6. Save the profile

After the runner agrees, save it. **TP**: `tp_create_note` with title `Running coach profile`
and today's date. **No TP**: produce `athlete-profile.md` for download and tell them to add it to
their Claude Project's knowledge (or keep it and paste it in later).

Update the profile at the end of every review, after threshold changes, and when goals change:
TP `tp_update_note` (also set `date` to today, so the note stays inside the 90-day search window).
Without TP, give the updated file. Keep it under ~60 lines; the decision log keeps only the last
~8 entries.

## Profile template

```markdown
# Running coach profile
updated: 2026-11-02 · source: TrainingPeaks

## Goal
- A race: City half marathon, 2027-03-28, road, target 1:38 (≈ 4:39/km)
- Agreed after reality check: runner wanted 1:35; current level predicts ~1:43, so 1:38 = stretch-but-realistic with 5 runs/week; revisit at the Feb 10k
- Season goal: sub-1:38 HM, stay injury-free

## History (last 24 months)
- Spring 2026: Jan–Mar build CTL 22 → 45 (+2.5/wk), marathon 2026-04-19; best 10k effort 4:18/km (2026-09-12)
- May 2026: 3-week break after the marathon (planned rest)
- Pattern: builds well over 10–12 weeks; summer drop-off

## Current state (2026-11-02)
- Threshold pace 4:20/km (race-derived 2026-10-11), LTHR 170, max HR 189
- Typical week: 5 runs, 42–48 km, 4.5 h; longest run 15 km / 90 min
- CTL 31 (6 weeks ago 33); HRV baseline ~58, resting HR ~52
- Assessment: solid base, little threshold work so far

## Availability
- Mon rest; Tue–Thu ≤ 60 min, morning; Sat/Sun up to 2 h; long run Sunday
- Weekly template: Mon rest · Tue quality · Wed easy · Thu easy+strides · Fri rest/strength · Sat easy · Sun long
- Strength: 2× per week at home, kettlebell 16 kg, 30 min

## Units and terrain
- Units: km for everything (time in brackets); hilly runs: km stays, HR cap rules
- Terrain: easy/long runs rolling, gravel + forest (median 16 m/km); quality on a flat road loop (3 m/km)
- Quality: by pace on the flat loop; on hills by HR
- Intensity guide: easy by HR cap ≤ 145; quality by pace, HR as a check; running power available (Garmin), not used yet
- Goal race: flat road

## Health
- Left Achilles tightness 2025 (resolved); watch calf load

## Preferences
- Likes intervals on flat road, dislikes treadmill; descriptions in Slovak

## Plan shape
- Base to 2026-12-06 → Build to 2027-02-14 → Specific to 2027-03-14 → Taper
- Peak volume ~60 km / 6 h

## Decision log (latest first)
- 2026-11-02: start 5× 1 km @ 98–100 %; add a rep before pace
```
