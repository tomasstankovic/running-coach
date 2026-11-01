# Changelog

All notable changes. Versions follow semver; installed copies update when the version in
`.claude-plugin/plugin.json` changes.

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
