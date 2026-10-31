# Training methodology

The rules the plans follow. They are defaults for a healthy recreational runner training
3–6 days a week. When the athlete's own history says otherwise (they recover fast, a rule keeps
leaving them flat), adapt and say why.

## Contents
1. Zones and what each is for
2. Intensity distribution
3. Week structure
4. Load progression
5. Periodization: blocks toward a race
6. Taper and race week
7. Reading fitness data (CTL / ATL / TSB, HR, HRV)
8. Missed sessions, illness, return after a break

---

## 1. Zones and what each is for

Zones come from TrainingPeaks (7-zone set: Z1, Z2, X, Z3, Y, Z4, Z5). Percentages are of
threshold *speed*. Approximate values for the default set:

| Zone | % thr. speed | HR % LTHR | Use |
|---|---|---|---|
| Z1 | 60–76 % | 72–81 % | recovery; easy running sits at its top |
| Z2 | 76–87 % | 81–90 % | aerobic endurance: easy/long running in its lower half, "steady" in its upper half |
| X | 87–93 % | 90–95 % | marathon-ish / "steady"; use on purpose, don't drift into it |
| Z3 | 93–100 % | 95–100 % | tempo up to threshold: tempo runs, cruise intervals |
| Y | 100–102 % | 100–102 % | right at/just above threshold |
| Z4 | 102–115 % | 102–105 % | VO2max-type intervals (≈ 5k–3k pace) |
| Z5 | > 115 % | > 105 % | strides, short reps, speed |

**Easy running** (easy runs, long runs, warm-ups) sits at the **Z1/Z2 boundary: ~70–80 % of
threshold speed, HR up to ~82–85 % of LTHR** (e.g. HR ≤ 145 for LTHR 174). Recovery runs are lower:
65–72 %, HR ≤ ~80 % LTHR. Prescribe easy running by the HR cap, with a pace range as a guide.
Take that range from the runner's own recent easy runs when they exist, because hills, trails and
heat make pace-only targets misleading. Upper Z2 (80–87 %) is "steady", not easy; use it on
purpose (progression runs, long-run finishes).

## 2. Intensity distribution

- ~80 % of running time in Z1–Z2, ~20 % in X and above (count only the work, not warm-ups).
- The X zone ("grey zone") is where easy runs drift when the athlete pushes. Easy days stay easy
  so quality days can be quality.
- Strides (4–8 × 15–20 s fast but relaxed, full recovery) don't count as a hard day. Use them 1–2×
  a week to keep the legs quick.

## 3. Week structure

Typical 5-run week: long run + 1–2 quality sessions + 2–3 easy runs + 1–2 rest days.

- Hard sessions at least 48 h apart. Classic pattern: Tue/Wed quality, Thu/Fri quality or easy,
  Sun long run, Mon rest.
- The day after the long run is rest or very easy.
- With 3–4 runs a week: one quality session, one long run, the rest easy.
- Base phase: quality = strides, hills, short tempo. A runner with an established base (≥ 8 weeks
  of consistent running) can do one controlled threshold session a week in base (cruise
  intervals at 95–100 %). VO2 work waits for build. Build: threshold + one VO2 or race-pace
  session. Peak: race-specific.
- Available days are a maximum, not a target. Use the number of runs the load calls for, and
  leave a day free rather than adding junk miles.

## 4. Load progression

- Weekly volume (time is better than km on trails) rises at most ~10 % week to week. At low volume
  (< 4 h) +30 min is fine even if it's more than 10 %.
- 3:1 rhythm: three build weeks, then a deload at −25 to −35 % volume with one short quality
  session kept. Older athletes or after a hard block use 2:1.
- Long run grows by 10–15 min per build week. It stays ≤ ~35 % of weekly time with 5+ runs
  (up to ~45 % with 3–4 runs a week). Cap ~2 h for 10k/HM, ~3 h for marathon. When the cap
  and the share clash, keep the long run and accept the share, since the long run matters more
  for HM/M.
- Quality progresses one variable at a time: reps → rep length → pace. Pace progresses only when
  the threshold itself moves.
- CTL ramp: for CTL < 40, +2 to +4 per week is sustainable. Above +5 per week for more than two weeks is a red
  flag.

## 5. Periodization: blocks toward a race

| Goal | Block length | Base | Build | Peak/specific | Taper |
|---|---|---|---|---|---|
| 5k / 10k | 8–12 wk | 2–4 | 3–4 | 2–3 | 7–10 days |
| Half marathon | 10–14 wk | 3–4 | 4–5 | 2–3 | 10–14 days |
| Marathon | 14–18 wk | 4–6 | 5–6 | 3–4 | 2–3 wk |
| Trail / ultra | 12–20 wk | like marathon, plus vertical: hills, downhill running, back-to-back long runs |

Base: volume, easy running, strides, hills. Build: threshold work (cruise intervals, tempo) and
gradually longer long runs. Specific: race-pace in the long run and in intervals. B/C races fit
into build weeks as a hard session, with 2–3 easy days around them.

**More weeks than the table needs** (e.g. 24 weeks to a half marathon): lengthen base first, and
consider two cycles (base → build → a tune-up race such as a 10k ~8 weeks before the A race →
short recovery → build/specific → taper). Never lengthen the taper. **Fewer weeks than needed**:
shorten base (if the runner already has one) and say plainly what the goal can and cannot be.

**Is the goal realistic?** `paces.py predict` gives equivalent times from a recent race (Riegel).
The goal is realistic when it's within ~2–3 % of the prediction for a block of this length and
the runner can build the needed volume. 5–8 % needs a long block and things going right. More
than that needs an intermediate goal. A checkpoint race or test halfway through the block
re-anchors the target.

**Block overview format** (one row per week):

| Week | Dates | Phase / role | Volume | Long run | Key sessions |
|---|---|---|---|---|---|
| 1 | 2.–8. 11. | base, build | 4 h 10 · 40 km | 80 min | strides; 6 × 1 min hills |
| 4 | 23.–29. 11. | base, deload | 3 h 15 | 65 min | strides only |

## 6. Taper and race week

- Volume drops 30–50 % (more for the marathon), intensity stays: short sharp sessions at race pace.
- Race week: one short session 3–4 days before (e.g. 3 × 1 km at race pace), a shakeout the day
  before (20–30 min easy + 4–6 strides), nothing new.
- Target TSB on race day +5 to +15 (A race), around 0 for B races.

## 7. Reading fitness data

- **CTL** (fitness, 42-day load): the trend matters more than the number.
- **ATL** (fatigue, 7-day load) and **TSB** = CTL − ATL. TSB −10 to −25 is normal in build weeks.
  Below −30, or a long run of very negative TSB, means back off.
- **HR on easy runs** creeping up at the same pace, or failing to rise in intervals: fatigue.
- **HRV** clearly below the athlete's baseline for 2+ days, poor sleep, heavy legs: swap that day's
  quality for easy or rest. Move the session; don't stack it.
- **Rep pacing**: reps getting faster than prescribed means the zones may be stale (check the
  threshold). Fading reps or HR running away means too hard, or a fatigued athlete.

### When the threshold evidence disagrees

Sources, from most to least reliable:
1. A recent **30-min solo time trial** on flat ground (or a flat 10k–HM race run all-out): average
   pace of the whole effort ≈ threshold pace; average HR of the last 20 min ≈ LTHR.
2. **Interval sessions read through HR**: reps where HR at the end is above LTHR were above
   threshold, whatever the label. Reps holding steady just below LTHR with even pacing were at
   or a bit under threshold.
3. A race on hills, trails or in heat: understates fitness. Use HR and effort, not pace.
4. The value in TrainingPeaks or Strava: only as fresh as when it was last set.

When sources disagree by more than ~3 %, don't silently pick one. Say what each suggests. Until
it's resolved, prescribe threshold work by HR (finish reps at ~LTHR − 3 to LTHR) with the
conservative pace. Schedule a 30-min test in the next lighter week. Update the zones after the
test, with the runner's agreement.

If an earlier coaching decision was based on mislabelled zones (e.g. "threshold" reps that were
really Z4), say so, re-anchor to the true zone, and then progress from there. "Add a rep" still
holds, but at the corrected intensity.

## 8. Missed sessions, illness, return after a break

- Missed easy run: forget it. Missed quality: move it only if 48 h spacing stays intact, otherwise
  drop it. Never make up a missed long run by lengthening the next one.
- Illness, "neck check": symptoms only above the neck (runny nose) → easy running OK if feeling OK.
  Below the neck (fever, chest, aches) → no running until 24–48 h symptom-free.
- Return after illness: as many days easy as days missed (max ~7), then one short quality session.
  First week back ≈ 60–70 % of previous volume.
- Return after a break > 2 weeks: start at ~50–60 % of previous volume, easy only for week 1, add
  strides in week 2, quality in week 3.
- Pain that changes the gait, sharp or worsening pain: rest and get it checked. Don't plan
  around it.
