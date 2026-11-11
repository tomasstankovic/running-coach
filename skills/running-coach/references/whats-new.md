# What's new, and what to check after an update

Read at Step 0 when the profile's `Coach version` is older than the installed version (the
`running-coach-version` meta in `assets/season-plan.html`) or missing. A profile without the
line is from 0.15 or earlier: apply every section below.

For each version newer than the profile's, oldest first:
1. Tell the runner, once and in their language, what you learned that touches them: 2–4 lines
   in the coach's voice, with what it means for them, not a changelog ("Since last time I've
   learned to read a marathon that faded after km 30 from its steady pace: your range moved
   from 3:20 to 3:16").
2. Run the checks listed for that version on their files. Results that need no change go in
   one line ("your plan already keeps the new rules"). Anything that would change the plan, the
   goals or the predictions is a proposal with numbers; apply it only after their yes
   (`season.md` §5 for a replan).
3. Then refresh the plan page (`season.md` §4 step 6) and set `Coach version` in the profile.

In a scheduled run with nobody to answer, do 1–3, put the proposals into the report as
questions, and change nothing in the plan.

## 0.16.0

What changed for the runner:
- Plans are built from the hours a week the runner can really give, with what an extra hour
  would buy (`methodology.md` §11).
- Faster runners (half ≤ ~1:25, marathon ≤ ~3:00): volume from their best block, easy doubles,
  double threshold only as labelled practice, the limiter from two results (`methodology.md` §5).
- Predictions: the planned weekly TSS sets the plan's effect, a runner faster than the pooled
  slope is credited, a marathon that faded after km 30 is read from its steady pace, and the
  key sessions on each race's road move the middle of the range (`analysis.md`).
- Each A/B race has its road of 4–6 key sessions; the marathon's longest easy long run practises
  race fuelling (`season.md` §2b).
- Plan page: a Today card, the current phase explained, the races with their roads, key
  sessions split into next and done.
- Trail and mountain races (`methodology.md` §9).

Checks:
- `forecast.json`: `weekly_tss` is set (the planned weekly TSS); a marathon in the history that
  faded after km 30 has `steady_pace` (`analyze_session.py` prints it). Re-run `forecast.py` and
  say how the ranges moved.
- `season_plan.py roads plan.json` (keeps results) and `check-roadmap`; report roads outside 4–6.
- Hours: the plan's peak week (`minutes`) against the availability in the profile; with no
  weekly hours there, ask once.
- Volume against the goal: the peak km against the goal table (`onboarding.md` §4). When the
  runner wants more than the forecast gives, show what a higher peak would buy (`forecast.py`
  with the higher `weekly_km`) as an option, with the extra time it costs.

## 0.16.1

What changed for the runner:
- At the end of a block ("how did the base block go?"), the review is built on `block_report.py`
  and names the key sessions as counts: on target, missed, under target, with the reason for
  the misses (`SKILL.md` "End of a block").

Checks: none; nothing in the plan, goals or predictions changes.

## 0.16.2

What changed for the runner:
- The morning check-in counts several short nights in a row (3 of the last 4 under 6 h) even
  when HRV is back to normal, and takes their own 1–5 rating of load outside running (travel,
  work, heat, family). A normal HRV after a hard trip no longer clears a quality session.

Checks: none; nothing in the plan, goals or predictions changes.

## 0.16.3

What changed for the runner:
- Before planning a week the coach checks the training days: what they said in the
  conversation first, then their weekly template, and it asks whether the usual days hold this
  week. It no longer copies the days from last week's calendar, which may have been an
  exception (family, travel).

Checks: the profile's `## Availability` has a `Weekly template` line (which day is what). If it
doesn't, ask for it once and save it.

## 0.17.0

What changed for the runner:
- Sessions in TrainingPeaks can mix kilometres and time, step by step: 1 km reps with a 75 s
  jog between them stay "1.00 km" and "1:15" on the watch, instead of the jog turning into
  "300 m". Strides are steps of the structure too (12' easy + 3 × 20 s / 40 s jog), not only
  a line in the description.

Checks: none; nothing in the plan, goals or predictions changes. Sessions already in the
calendar stay as they are; new ones are written the new way.
