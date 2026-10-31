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
4. **Terrain & tools**: road, trail, track or treadmill; hills nearby; watch brand; whether they
   train by pace, HR or feel.
5. **Health**: current pains or niggles, injury history (what, when, recurring?), anything a doctor
   said to watch.
6. **Strength & extras**: do they want strength training (where: gym or home, what equipment),
   mobility, and how much time for it.
7. **Preferences**: what kind of sessions they like or hate, how much structure they want, and
   language.

## 3. Load and assess history

Pull 8–12 weeks (TP: `tp_get_workouts` in ≤ 90-day windows, `tp_get_fitness`, `tp_get_peaks` for
best efforts, and `tp_get_metrics` for baselines. Strava: `list_activities`, then
`get_activity_performance` for races and key sessions).

Summarize as a short assessment the runner can read:

- **Load**: average and range of weekly time/km, runs per week, longest run, and the trend (building,
  stable, coming back from a break). CTL now and 6 weeks ago if available.
- **Intensity**: roughly how much is easy vs. hard. Flag "everything at the same moderate pace",
  a very common pattern.
- **Thresholds**: threshold pace and LTHR. Their source (TP setting, race-derived, estimated) and
  whether recent efforts agree (`scripts/paces.py race`).
- **Consistency**: missed weeks, gaps, how often long runs happen.
- **Readiness to train**: from HRV, resting HR and sleep baselines if available.
- **Gap to goal**: what the goal requires (volume, threshold, long run) vs. where they are. Say
  honestly if the target time or date looks unrealistic, and offer an alternative ("1:45 is
  realistic, 1:39 would need ~6 more months").

## 4. Propose the plan shape

Recommend the block structure (phases and their lengths, from `methodology.md`), weekly volume to
start at and to peak at, runs per week, where strength fits, and the next 1–2 weeks in detail
(then continue as in Week mode).

## 5. Save the profile

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
- Season goal: sub-1:38 HM, stay injury-free

## Current state (2026-11-02)
- Threshold pace 4:20/km (race-derived 2026-10-11), LTHR 170, max HR 189
- Typical week: 5 runs, 42–48 km, 4.5 h; longest run 15 km / 90 min
- CTL 31 (6 weeks ago 33); HRV baseline ~58, resting HR ~52
- Assessment: solid base, little threshold work so far, easy runs on hilly trails

## Availability
- Mon rest; Tue–Thu ≤ 60 min, morning; Sat/Sun up to 2 h; long run Sunday
- Strength: 2× per week at home, kettlebell 16 kg, 30 min

## Health
- Left Achilles tightness 2025 (resolved); watch calf load

## Preferences
- Likes intervals on flat road, dislikes treadmill; descriptions in Slovak; trains by HR on trails

## Plan shape
- Base to 2026-12-06 → Build to 2027-02-14 → Specific to 2027-03-14 → Taper
- Peak volume ~60 km / 6 h

## Decision log (latest first)
- 2026-11-02: start 5× 1 km @ 98–100 %; add a rep before pace
```
