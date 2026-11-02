# Changelog

All notable changes. Versions follow semver; installed copies update when the version in
`.claude-plugin/plugin.json` changes.

## 0.15.0

- **Race plan** (`race_plan.py`, `weather.py`): the forecast range moved for the weather (Open-Meteo:
  the real forecast up to 16 days out, the typical weather of that date in the last 10 years
  before), the goal checked against it with a safe B, splits by the course's GPX profile (Daniels'
  hill rule, downhill capped at ~12 % faster from Strava's GAP data), even or negative, and the
  fuelling plan: carbs per hour by duration capped at what the gut tolerated in training, gel times
  matched to aid stations, drinking, carb loading, breakfast and caffeine in grams for the runner.
- **Durability**: `analyze_session.py` reports, for runs of 90+ min, the efficiency lost in the last
  quarter vs. early (`durability` in the page rows, charted under aerobic fitness).
- **Pain and illness diary in TrainingPeaks** (`health_log.py`): each report a calendar note with a
  machine-readable line; read back into check-ins, reviews and the page with the rules (pain
  monitoring up to 3/10, reduce at 4-5, stop at 6+ or a changed stride; illness by the IOC triage).
- **Morning brief to the phone**: the scheduled check-in adds the diary and the weather and sends
  one line with PushNotification.
- **Fuelling practice**: a gut-training ladder (30 -> 90 g/h) on long runs, recorded as TP workout
  comments, feeding the race plan.
- **Block reports** (`block_report.py`): volume, key-session verdicts, milestones, efficiency and
  durability, threshold, forecast, readiness, health and takeaways; a blocks section on the page.
- Sources S51 (Strava GAP), S53 (pain-monitoring model).

## 0.14.0

- **The runner's own zones are the default**, whatever the method (TrainingPeaks and the watch:
  80/20, Friel, 5-zone, ...). `zones.py show` reads any TP method and gives each band its use
  from where it sits relative to the threshold; a heart-rate set with another method than the
  pace set gets its own table. The profile records it (`Zones: own set (TP = Garmin) ...`).
- **Other methods to compare** (`--method`): 80/20 from thresholds, % max HR, heart-rate reserve
  (Karvonen), Daniels VDOT paces (E/M/T/I/R from a race, Daniels-Gilbert equations). Friel is read
  from TP or the watch rather than computed (his published percentages differ between versions).
- **Personal aerobic threshold** (`zones.py lt1`): flat steady runs of 45+ min under 5 % decoupling
  were at or below it; the highest proven HR becomes the easy cap instead of the population 83 % of
  LTHR (with a drift test to confirm big changes).
- **The watch**: its own threshold detection counts as evidence in `zones.py suggest`; after a
  change the runner is told which values to set on the watch (this skill can't write to Garmin).
- `methodology.md` "Zone methods"; sources S46–S50 (Daniels, Karvonen, 80/20, Friel, drift test).
- Fix: the 7-zone X/Y model is 80/20 Endurance (Fitzgerald), not Friel's.

## 0.13.0

- **Training zones** ("Tréningové zóny"): `zones.py show` puts pace, % of threshold, heart rate,
  power and what each zone is for in one table, from TrainingPeaks' own bands (the run set when
  there is one) or from thresholds. The plan page has a training zones panel with the current
  table, power, the easy-run HR cap and how the threshold moved over the season (`zones`
  collection).
- **Keeping them current**: checked in the first review of every month and after new evidence (a
  flat race, a 30-min test, threshold sessions clearly faster or slower than the zones, a new max
  HR, resting HR, power efforts). `zones.py suggest` proposes old -> new with what it means for
  the paces; it never averages sources more than 3 % apart, ignores changes under 1.5 % and hilly
  or hot races, and asks for a retest after 12 weeks without evidence.
- **Writing to TrainingPeaks** after the runner's yes: threshold pace, LTHR / max / resting HR,
  rFTP (`tp_update_speed_zones`, `tp_update_hr_zones`, `tp_update_ftp`), re-read to confirm, then
  the key sessions re-target and the page updates. Creating a missing run power set is offered,
  never done unasked. The scheduled weekly review includes the monthly check.
- Eval `zones-after-race`.

## 0.12.0

- **The coach designs the key sessions; the script computes and checks.** Tested blind on three
  fictional runners who needed adapting (Achilles history before a marathon, no flat ground for a
  half, a 57-year-old 10k runner with a treadmill winter): the roadmap the coach adapted from the
  script's draft beat the script-led one on all three (68 : 54 points), and the losers' misses all
  traced back to the draft's defaults. Paces were right in both (0 errors in 344 sessions).
- `season_plan.py roadmap` now writes a *default draft*; `season.md` §2b has the coach adapt it
  (injuries, terrain, what worked, recovery, weather, order of sessions) with a reason per change.
- `season_plan.py check-roadmap`: pace vs. its %, two hard days in a row, quality 1–2 days after a
  race or test (3 after a half or longer), long run longer than the week's, big marathon-pace runs
  in consecutive weeks or the week before a B race, the continuous marathon-pace run 2–4 weeks out
  and never the week after a race, milestone count.
- `retarget` without a new threshold just fills the targets of the coach's new or edited sessions.
- Reviews: after a session under target or missed, `actuals` only proposes holding back
  (`PROPOSE`); the coach decides with the context, `--hold-back` applies it.
- Draft fixes: no quality 2–3 days after races and tests, big marathon-pace long runs never in
  consecutive weeks or before a B race, half-marathon pace never drops from build to specific
  (3× 3 → 2× 5 → 3× 4 → 2× 6 km, then 2× 6 → 3× 5 → 10 km continuous), dress rehearsal a real
  race-pace session in a full week 2–3 weeks out.
- Evals: `roadmap-achilles-marathon`, `roadmap-hilly-half`, `roadmap-masters-10k`.

## 0.11.0

- **Key-session roadmap** (`season_plan.py roadmap`, `key_sessions.py`): every week of the season
  gets its key sessions from progression ladders by phase and goal distance (more reps, then
  longer reps, then faster), placed on the runner's quality and long-run days, with targets as
  % of threshold speed and paces from `paces.py`. Race-pace targets use the goal pace, at most
  3 % faster than the threshold supports. 6–10 milestones: threshold check, longest run, B races,
  marathon-pace long runs and a continuous 18–23 km at marathon pace 2–4 weeks before a
  marathon, a dress rehearsal for shorter goals, the A race.
- **Results against the map**: `actuals --sessions` matches `analyze_session.py --json` rows to the
  key sessions and judges them (on target, better, under, missed). After under or missed, the
  rest of that ladder moves back a step, logged. `retarget` recomputes future paces after a new
  threshold or goal and logs what moved. `replan` keeps the roadmap.
- **Plan page**: a key sessions section (next + milestones, milestones only, all), by phase, with
  target pace, HR cap, result and verdict, and an "adjusted" mark that leads to the change log.
- `workouts.md` "Progressions", `season.md` §2b, Week mode starts from the week's key sessions.
  Proposed in a coaching session on real data.

## 0.10.0

- **"If the plan happens"**: `forecast.py` adds a race-day projection next to the forecast from
  today's form. The plan's weekly TSS is run through the CTL formula to race day and the
  runner's own results against their CTL give how much faster they get per CTL point (held to
  0.05–0.4 %, no extrapolation beyond 15 % above the highest CTL they raced at). The marathon
  goes through their own marathon/half ratio. The plan's TSS estimate is rescaled to the
  runner's own TSS per km (`weekly_tss`, or today's CTL). Needs `ctl` and `history[].ctl`;
  without them nothing changes. Proposed and first built in a coaching session on real data.
- **Plan page, this week**: always Monday to Sunday, rest days shown as rest, strength
  sessions tagged, the week's total and how many sessions are done.
- **Plan page, readiness**: today's verdict with what to do and why (HRV, resting HR, sleep),
  where the 7-day HRV sits in the runner's band, last night's HRV, and the trend only from
  5 days on. `readiness.py --trend` rows carry `reasons` codes and `hrv_state`.
- Fix: the page used the UTC date for "today", so after midnight in Europe it marked the wrong
  day.

## 0.9.1

- **Choose your setup.** The first conversation explains where the coach keeps things in the
  runner's setup (TrainingPeaks notes, a working folder, or files in a Claude Project), what that
  setup gives and misses, and the better option; the choice goes into the profile's `Setup:`
  line.
- **Folder sessions save files themselves.** In Claude Code or Cowork the profile (without TP),
  `plan.json` and `season-plan.md` go into `running-coach/` in the folder and are read at the
  start of every chat, instead of being handed over for download.
- README: a "Choose your setup" comparison with what each setup gives and misses.

## 0.9.0

- **Race predictions** (`forecast.py`): current form over 5 km, 10 km, half and marathon, and a
  race-day forecast for every race in the season. Recent races count most (by age and distance),
  workout best efforts only as "at least this fast", threshold as a second view (a > 3 % gap is
  flagged as a stale threshold or misleading races), and the marathon comes from the volume
  models instead of Riegel. Race day: today's level is the slow end; the plan's volume and the
  runner's own earlier results at similar volume set the fast end; course and heat adjust it. The
  goal is judged as realistic, a stretch or out of reach. No generic "+x % per block".
- **Plan page**: a predictions section with each race's forecast, its trend over the weeks against
  the goal, and a current-form table (`predictions` collection).
- Weekly review re-runs the forecast; onboarding and race plans start from it. A Predict mode in
  the skill.
- README: the Slovak section is gone.

## 0.8.1

- **Fix: session analysis on real watch files.** Checked against nine real TrainingPeaks sessions:
  `analyze_session.py` counted every lap as a rep. A 2 × 10 min tempo came out as 6 reps (the 1-km
  auto-lap split each rep), 6 × 2 km as 12, a 10-min Z2 build-up counted as a rep, and mixed sessions
  (2 km + 1 km + 2 × 400 m) got a "pushed the end" verdict across different kinds of rep. Now laps
  inside one workout step are joined, easy Active steps are listed as easy parts, reps are judged per
  kind, strides get one line, short reps skip HR checks, and short-rep pace comes from the lap's
  average pace instead of the rounded distance. Seven new tests cover these cases.

## 0.8.0

- **Morning brief**: `readiness.py --brief` (one line), `--json` and `--trend DAYS`; a
  scheduled daily check-in template in `checkin-and-race.md` that never changes the calendar
  without a yes.
- **Plan page 2.0**: this week's sessions (with done marks), readiness (HRV 7-day mean in the
  runner's band, coloured by verdict) and aerobic fitness (EF of steady runs, coloured by
  decoupling). Fed by `readiness.py --trend`, `analyze_session.py --json` and the new
  `page_docs.py`, which turns any row list into plan-page database writes.
- **Evals**: 8 test cases for `claude plugin eval` (unrealistic goal, 30-day rule, red
  check-in, fever, beginner, interval analysis, marathon prediction, no write without a yes).
  First run, 4 cases with the skill on Sonnet: 15 of 15 checks passed (long run capped at
  16.4 km instead of the requested 18 km; red check-in with no intervals; 1:30 goal pushed back
  with numbers and options; reps read as even with a stale threshold flagged).
- **Fix**: `paces.py --help` crashed on a bare `%` in the help text; `check_week.py` and
  `terrain.py` now answer `--help`. A test runs `--help` on every script.

## 0.7.0

- **Running power**: `paces.py power` gives zones from running FTP (or estimates rFTP from a race
  or hard effort) and converts watts ↔ % of rFTP; workouts can be prescribed by power;
  `analyze_session.py --rftp` adds watts per rep, Pw:Hr and normalized power.
- **Tests**: `tests/test_scripts.py` (27 behaviour tests on fictional data) and
  `tests/check_skill.py` run in CI on every push.
- **Fix**: the "+30 min is fine" exemption in the weekly volume check now applies only below
  4 h a week, as the methodology says.
- Repository: changelog, issue templates, example outputs, social preview image, screenshot of
  the plan page.

## 0.6.1

- The skill description was 1,235 characters, over the 1,024-character limit, so claude.ai cut
  it off and the skill didn't trigger in chat. Rewritten to 817 characters with English and
  Slovak triggers. Description checks in CI.

## 0.6.0

- Research-backed rules with `references/sources.md` (45 sources, evidence strength).
- No run more than 10 % longer than the longest of the last 30 days; weekly +10–15 %, error
  above +20 % or +30 % over two weeks; cautious mode.
- HRV readiness by 7-day trend vs personal band; IOC illness triage; evidence-based taper.
- `analyze_session.py` (reps, decoupling, EF), volume-aware marathon predictions, strength,
  fuelling, heat, masters and REDs guidance. Longest allowed run per week, unplanned spikes in
  reviews, pre-race long-run targets.

## 0.5.0

- Season plan (`season_plan.py`), A/B/C races, busy weeks, re-planning rules, plan page with a
  fixed link (`assets/season-plan.html`), TrainingPeaks ATP question, scheduled weekly review.

## 0.4.0

- Units (km or time) and terrain (`terrain.py`); TrainingPeaks workouts in kilometres
  (`tp_structure.py`); HR and power targets for hilly ground.

## 0.3.0

- Logo, README, goal reality check (goal × time × current level), preferred days.

## 0.2.0

- 12–24 months of history in onboarding (`history_summary.py`); strength and threshold tests as
  discussions.

## 0.1.0

- First version: onboarding and profile, weekly plans, blocks, reviews, check-ins, strength,
  race day; TrainingPeaks, Strava or manual input.
