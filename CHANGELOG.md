# Changelog

All notable changes. Versions follow semver; installed copies update when the version in
`.claude-plugin/plugin.json` changes.

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
