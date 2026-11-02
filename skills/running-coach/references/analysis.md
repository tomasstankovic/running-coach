# Reading a completed session

`scripts/analyze_session.py` turns `tp_analyze_workout`'s file into numbers. This is how to read
them. Most thresholds here are practice-based, so the runner's own trend over weeks matters more
than any single cut-off. Bracketed tags point to `sources.md`.

## Steady runs: easy, long, steady

**Aerobic decoupling (Pa:Hr)** compares efficiency (graded speed per heartbeat) in the first and
second half of a steady run [S21]. Positive = heart rate drifted up, or pace drifted down, at the
same effort.

| Decoupling | Reading |
|---|---|
| < 5 % | good aerobic endurance at this intensity and duration |
| 5–10 % | some limitation, or fatigue, heat, dehydration, low fuel |
| > 10 % | probably above the aerobic threshold, or not enough endurance for this duration yet |
| negative | fine; often a warm-up or weather artefact |

- Only meaningful on runs of ~60 min or more, steady and below threshold. Intervals, fartleks
  and races don't count.
- The script's own figure skips the first 10 minutes; TrainingPeaks' Pa:Hr uses the whole run.
  They can differ by a few points (on the same runs: 2.9 vs 2.5, 2.2 vs −1.2, 5.0 vs 5.5); use
  one of them consistently for the trend.
- Hills: the script uses graded pace (NGP), but long descents and heat still distort it. On a
  hilly route compare only with the same route.
- Use it as a **test of the long run**: when a runner's long runs stay under 5 % at their easy
  HR, the aerobic base supports more volume or a longer long run. Over 10 % at an easy HR: more
  easy volume before more intensity.

**Efficiency factor (EF)**, graded speed (m/min) per beat. Higher means more speed for the same
heart rate. Compare only similar runs (same type, route, weather, freshness); a rising EF over
4–8 weeks is the clearest sign aerobic fitness is improving, often before race results show it.
Keep a short EF log in the profile (date, run, EF, decoupling).

**Durability** (how well the runner holds pace at the same HR late in long efforts) predicts
marathon performance: runners whose HR-to-speed ratio drifted least in the marathon finished
faster [S22, S23]. In training, read it from the long run's decoupling and from the last third of
long runs with a fast finish: steady HR and pace there is the goal of the marathon-specific
phase.

**Time above the easy cap**: under ~10 % of the run is fine (hills, a bridge, a stop). More means
the easy run wasn't easy. The fix is slower pace or walking the hills, not a shorter run.

## Interval sessions

**How the script finds the reps.** It reads the laps the watch recorded while running the
structured workout:
- laps inside one workout step are joined, so a 10-min rep that the 1-km auto-lap cut into three
  laps is one rep;
- Active steps run slower than 85 % of threshold speed (or 30 % slower than the hardest step when
  no threshold is given), like a 10-min Z2 build-up, are listed as easy parts, not reps;
- reps are grouped by kind (similar distance or time): in 2 km + 1 km + 2 × 400 m each kind is
  judged on its own, and nested sets like 4 × (4 × 30 s) are one kind;
- a few short accelerations (reps under a minute, 4 min in all at most) are strides: one line, no
  evenness check, and the run is also read as a steady run.

It does not know the planned paces (TrainingPeaks' "Structure" channel follows the planned
timing, not the laps actually run). Compare each kind with the workout description yourself. A
session run without a workout on the watch (manual laps, or none) is read as a steady run: say
so, and judge the reps from the laps by hand if the runner did them.

| Number | Reading |
|---|---|
| pace variation (CV) | < 2 % even, 2–4 % acceptable, > 4 % uneven (practice-based [S24]) |
| first → last rep | > 3 % slower: faded (too fast a start, too short recoveries, or fatigue). > 2 % faster: the runner pushed the end; fine if planned, otherwise the reps were too easy |
| % of threshold speed | is it the zone the session was meant for? Reps at 102–104 % are Z4, not threshold |
| max HR at the end of reps vs LTHR | threshold reps end around LTHR − 3 to LTHR. Well above means the reps were above threshold. Not for reps under a minute: HR lags behind them |
| reps faster than threshold without HR above LTHR | the threshold may be stale: raise a retest (`methodology.md` "Settling the threshold") |
| HR drop in recoveries | compare with the same session type in earlier weeks; a shrinking drop through the session means accumulating fatigue |

Judge against the runner's own previous sessions of the same type, not a fixed number [S24].

## Turning numbers into decisions

End every analysis with what changes next time, in the runner's language:
- even reps, HR at or under LTHR, felt controlled → progress one variable (one more rep)
- faded → same session, slower first rep or longer recoveries
- reps clearly faster than prescribed at low HR → discuss the threshold
- long run decoupling > 10 % → keep the long run, slow it down, check fuel and heat
- EF rising over weeks → say so; it's motivating and it's real progress

## Race predictions

**`scripts/forecast.py`** answers "what could I run now?" over 5 km, 10 km, half and marathon, and
"what can I expect at my race?" for every race in the season. It combines everything below and
prints ranges, not single numbers.

Gather the input (format in the script's docstring):
- **results**: races of the last ~16 weeks (`kind: "race"`), and best efforts inside workouts
  (`kind: "effort"`). With TrainingPeaks, `tp_get_peaks` (sport `Run`, `days` 112) for
  `speed5K`, `speed10K`, `speedHalfMarathon`; `value` is speed in m/s, so time = km × 1000 /
  value (skip entries far slower than easy pace: walks, GPS artefacts). A peak whose workout
  was a race (the title, `tp_get_events`, or the runner says so) is a race; the rest are
  efforts. Efforts only count as "at least this fast".
- **threshold_pace** from the profile; **weekly_km**: mean of the last 8 weeks; **training_pace**:
  total time / total km of all runs in those weeks (Tanda's input).
- **history**: earlier best races with the weekly km of the 8 weeks before them (onboarding's
  history summary), and with TP the CTL on each race day (`ctl`, from the saved `tp_get_fitness`
  file). They set the optimistic end when the plan brings the volume back; with CTL they also
  give the projection below.
- **ctl** (today's CTL) and **weekly_tss** (mean weekly run TSS of the last 8 weeks) with TP.
- **plan**: the season plan file, so races and planned volume come from it; add `goal`,
  `course_pct` (a slow course +1–3 %, a fast one −1 %) and `temp_c` to a race when known.

Read it:
- **Today's level is the slow end of a race forecast.** The fast end comes from the plan's
  volume (marathon models) and the runner's own earlier results at a similar volume. Nothing
  else is assumed: there is no reliable "+x % per block", so the forecast moves only with new
  evidence (a race, a test, key sessions). Re-run it in every weekly review.
- **Present a range and a likely time**, with what it rests on ("from your October half and
  33 km a week"). A goal inside the range is realistic; up to ~3 % faster than the fast end is a
  stretch; more is out of reach on current evidence: say so and offer options (more weeks, more
  volume, a different goal) as in the onboarding reality check.
- **Disagreement is information.** Races and threshold > 3 % apart: the threshold or the races
  are off (hills, heat, a bad day): suggest a test. Marathon models far apart: little
  marathon-specific evidence yet; the tune-up half and long runs with marathon-pace segments
  narrow it.
- **Projection: "if the plan happens".** Runners ask what they will run on race day with the
  training that's planned, not only what they could run today. With `ctl` (today's CTL from
  `tp_get_fitness`), `ctl` on each history result (CTL on that race day) and a plan whose weeks
  carry `tss`, the script adds a projection next to the forecast. Add `weekly_tss` (mean weekly run
  TSS of the last 8 weeks, `tp_get_weekly_summary`): the plan's TSS is a rough per-hour estimate, and
  the script rescales it to the runner's own TSS per km. It runs the planned TSS through
  the CTL formula to the race day and applies the runner's own time-vs-CTL slope (their history
  plus today's level; held between 0.05 and 0.4 % per CTL point, no extrapolation beyond 15 %
  above the highest CTL they have raced at). Fast end: the whole plan; slow end: 80 % of its load.
  The marathon goes through the runner's own marathon/half ratio, moved to the planned volume
  (Vickers model 1). Present both, labelled: "today's form" (evidence) and "if the plan happens"
  (the runner's history applied to the plan). When the projection barely beats an earlier result,
  say what it means: the plan matches the runner's earlier load, so a faster time needs more
  load or better execution (e.g. marathon-specific long runs), not hope. When a week is missed,
  the next run of the script moves the projection; that is the point.
- **Plan page**: `forecast.py input.json --json` gives rows for the `predictions` collection
  (`page_docs.py rows.json --collection predictions --id id`): the page shows each race's latest
  forecast with its trend over the weeks and a current-form table.

The pieces it is built from:

`paces.py predict` gives Riegel equivalents, which fit well up to the half marathon. For the
marathon, Riegel is often 10+ minutes too optimistic for recreational runners [S25]. With
`--weekly-km` it adds the Vickers & Vertosick models (a race plus weekly volume; with two races
the most accurate) and, with `--training-pace`, Tanda's model (weekly km plus mean pace of all
runs in weeks −9 to −1; validated for roughly 2:47–3:36) [S25, S26]. Plan the marathon from the
slowest credible estimate and refine it after the tune-up race.
