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
9. Units and terrain
10. Age, energy and health flags

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

### Zone methods: the runner's own set is the default

There are many ways to cut zones; only two points in them are physiology: the aerobic threshold
(LT1/VT1, the real top of easy running) and the lactate threshold (LT2, "threshold"). Every method
estimates those two and splits the rest by convention [S46–S49]:

| Method | Anchor | Zones | Note |
|---|---|---|---|
| 80/20 (Fitzgerald) | threshold pace, LTHR | 1, 2, X, 3, Y, 4, 5 | the table above; X and Y are the in-between zones 80/20 mostly avoids |
| Friel | LTHR, threshold pace (30-min test) | 1–4, 5a, 5b, 5c | his published percentages differ slightly between versions |
| % max HR / HR reserve (Karvonen) | max HR (and resting HR) | 5 | no threshold in it; a max HR from "220 − age" can be off by 10+ bpm |
| Daniels (VDOT) | a race result | paces E, M, T, I, R | paces only, flat-road |
| Seiler 3-zone | LT1 / LT2 | 3 | the research model behind "polarized" |
| Power (Coggan, Stryd) | rFTP | 5–7 | watts differ between devices |

- **Default: the runner's own zones**, the set in TrainingPeaks and on their watch (Garmin,
  Coros, Polar), whatever its method. Don't switch methods on them: their watch alerts, TP's
  time-in-zone and this plan should speak the same language. `zones.py show --tp-settings` reads
  any TP method and gives every band its use from where it sits relative to the threshold.
  Record it in the profile (`Zones: own set (TP = Garmin), 80/20, default`).
- **Other methods** only to compare when the runner asks, or for a runner with no zones at all:
  `zones.py show --method 8020 | hrmax | hrr | daniels`. For someone without a threshold, % max
  HR or HR reserve is a start, replaced by threshold-based zones after a race or test.
- **Workouts don't depend on the method**: targets are % of threshold speed and % of LTHR, so
  the names change between methods, the paces don't. Name sessions with the runner's zone
  names.
- **The anchor matters more than the method.** A stale threshold spoils every method; keeping it
  current ("Keeping the zones current") is worth more than choosing between methods.
- **Personal aerobic threshold.** "Up to ~83 % of LTHR" for easy running is a population
  figure. `zones.py lt1` reads the runner's flat steady runs of 45+ min: pace:HR decoupling under
  5 % means the run was at or below the aerobic threshold, over 5 % above it [S21, S50]. The
  highest HR proven under 5 % becomes their easy cap (`zones.py show --easy-cap ... --easy-source
  ...`), with their agreement. Heat, hills and dehydration raise drift, so confirm a big change with
  a drift test: 60 min on flat ground at a steady HR near the estimate, first vs. second half; under
  5 % drift = at or below the threshold, 0–3 % = repeat ~5 bpm higher [S50].

## 2. Intensity distribution

Bracketed tags like [S1] point to `sources.md`, with the strength of the evidence behind each rule.

- **Default: pyramidal, counted by time.** ~75–85 % of running time easy (Z1–Z2), 10–20 % at
  steady-to-threshold (X–Y), 0–10 % at VO2 and faster (Z4–Z5). Warm-ups count as easy. No
  distribution is clearly better for recreational runners; pyramidal is what most marathoners at
  every level do, and suits them at least as well as polarized [S10–S13].
- **Polarized near a short race:** for the last 4–6 weeks before a 5k/10k, or for well-trained
  runners, shift threshold time to VO2 work (less X–Y, more Z4) [S10, S11].
- **Volume and consistency first.** Add easy volume before adding intensity; faster marathoners
  mostly run more, and more of it easy [S12].
- The X zone ("grey zone") is where easy runs drift when the athlete pushes. Easy days stay easy
  so quality days can be quality.
- Strides (4–8 × 15–20 s fast but relaxed, full recovery) don't count as a hard day. Use them 1–2×
  a week to keep the legs quick.

## 3. Week structure

Typical 5-run week: long run + 1–2 quality sessions + 2–3 easy runs + 1–2 rest days.

- Hard sessions at least 48 h apart. Classic pattern: Tue/Wed quality, Thu/Fri quality or easy,
  Sun long run, Mon rest.
- The day after the long run is rest or very easy.
- With 3 runs a week: one quality session, one long run, one easy run. With 4–6: two quality
  sessions (one can be inside the long run in the specific phase), the rest easy.
- An option for experienced runners: sub-threshold ("Norwegian singles") weeks, see
  `workouts.md`. Offer it, never default to it.
- Base phase: quality = strides, hills, short tempo. A runner with an established base (≥ 8 weeks
  of consistent running) can do one controlled threshold session a week in base (cruise
  intervals at 95–100 %). VO2 work waits for build. Build: threshold + one VO2 or race-pace
  session. Peak: race-specific.
- Available days are a maximum, not a target. Use the number of runs the load calls for, and
  leave a day free rather than adding junk miles.

## 4. Load progression

- **No single run more than 10 % longer than the longest run of the previous 30 days.** This
  applies to every run, not just the long run (a midweek run can become the longest). Spikes of
  10–30 % raised injury risk by ~60 % in a cohort of 5,200 runners; the week-to-week ratio did
  not predict injury [S1]. After a break the reference is what was actually run since returning.
  `check_week.py` enforces it.
- **Weekly volume** (time is better than km on hilly ground): default +10–15 % per build week,
  never more than +20 % in a week or +30 % over two weeks. Use +10 % for novices and anyone
  injured in the last 12 months (`"cautious": true` in `check_week.py`). At low volume (< 4 h)
  +30 min is fine. The famous 10 % rule itself is not supported as a limit; big jumps (> 20–30 %)
  are the risk [S2–S5].
- **Deloads every 3–4 weeks** at −25 to −35 % volume, one short quality session kept, and
  earlier when fatigue, poor sleep, low HRV or niggles appear. 2:1 for older runners or after a
  hard block. The rhythm is coaching practice, not evidence [S6].
- Long run grows within the 10 % single-run rule. It stays ≤ ~35 % of weekly time with 5+ runs
  (up to ~45 % with 3–4 runs a week). Cap ~2 h for 10k/HM, ~3 h for marathon. When the cap
  and the share clash, keep the long run and accept the share, since the long run matters more
  for HM/M. Share and caps are practice-based; the 10 % rule wins when they disagree [S1, S6].
- Quality progresses one variable at a time: reps → rep length → pace. Pace progresses only when
  the threshold itself moves.
- **CTL ramp** is a soft fatigue signal only: more than +5 per week for 2+ weeks means look
  closer. Don't use the acute:chronic workload ratio for injury decisions; it doesn't predict
  injury better than load alone [S1, S7].

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

**Longest run before the race.** A race is a single run too, so plan the long runs so the race
isn't a big spike over the longest run of the previous weeks [S1]. Races are exempt from the
+10 % rule (they're the goal), but:
- 5k / 10k: long runs are longer than the race anyway; nothing to do.
- Half marathon: reach ~18–20 km in the last 4–5 weeks, so the race is ≤ ~+15–20 %.
- Marathon: 30–32 km in the specific phase. The race stays a ~30–40 % spike; that's accepted,
  and it's why marathon recovery takes 2–3 weeks.
`season_plan.py` warns when a plan falls short. With a low-volume runner, say so and choose
together: more volume, a later race, or accepting the spike.

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

Cut volume progressively, keep intensity and keep frequency. A 41–60 % volume reduction over
about two weeks with intensity maintained is the best-supported taper [S14, S15]; for the
marathon, a strict three-week taper (consecutive lighter weeks right before the race) was worth
~2–3 % in 158,000 recreational marathoners [S16].

| Race | Taper | Volume vs. peak |
|---|---|---|
| 5k / 10k | 7–10 days | −30 to −50 % |
| Half marathon | 10–14 days | −40 to −50 % |
| Marathon | 14–21 days | week −3: −20 to −25 %, week −2: −35 to −45 %, race week: −50 to −60 % |

- Keep 1–2 short sessions at race pace or faster per week, and at least ~80 % of the usual
  number of runs. No catch-up long runs in the taper. Runners on 3–4 h a week cut toward the
  lower end.
- Race week: one short session 3–4 days before (e.g. 3 × 1 km at race pace), a shakeout the day
  before (20–30 min easy + 4–6 strides), nothing new.
- Target TSB on race day +5 to +15 (A race), around 0 for B races. A practical heuristic, not
  research.

## 7. Reading fitness data

- **CTL** (fitness, 42-day load): the trend matters more than the number.
- **ATL** (fatigue, 7-day load) and **TSB** = CTL − ATL. TSB −10 to −25 is normal in build weeks.
  Below −30, or a long run of very negative TSB, means back off.
- **HR on easy runs** creeping up at the same pace, or failing to rise in intervals: fatigue.
- **HRV** (Garmin's overnight value): judge the 7-day mean of ln(HRV) against the runner's normal
  band (baseline mean ± 0.5 SD over 4–8 weeks), not single nights. Below the band: no quality,
  move the session, don't stack it. Still below 3 days later: −25 % volume for 3–4 days. A single
  low night matters only together with another sign (resting HR up, poor sleep, illness,
  soreness). Needs 3+ weeks of data. HRV-guided training gives a small benefit, mainly fewer
  runners who don't respond, often with fewer hard sessions [S17–S20]. `readiness.py` applies it.
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
conservative pace.

### Settling the threshold: discuss, don't impose

A test costs a hard day and some motivation, so it's a conversation, not an automatic entry in
the plan.

1. **Explain why** in two or three sentences: what the sources say, how far apart they are, and
   what it changes. "Your 10k effort in September says 4:10, the October half says 4:20. That's
   ~10 s/km on every threshold rep and every easy-run range."
2. **Lay out the options**, recommending one for this runner:

| Option | How | Good for | Cost |
|---|---|---|---|
| **30-min solo time trial** | 15 min warm-up, 30 min all-out but even on flat ground, cool-down. Average pace ≈ threshold pace; average HR of the last 20 min ≈ LTHR. | most runners; the clearest number | one hard day; needs a flat route and motivation |
| **Race as the test** | a 10k or half already on the calendar, run all-out | runners who race anyway; no extra hard day | depends on course and weather; only when a race fits |
| **Read it from training** | over 2–4 weeks, watch HR at the end of threshold reps and the pace at LTHR in steady efforts. Also TP's own threshold-change notifications, if the runner gets them. | runners who dislike tests; coming back from a break | slower, less precise; needs HR data |
| **Lab or field lactate test** | a step test with blood lactate | data lovers, or a big goal | money and travel; still needs translating to the road |
| **Do nothing for now** | keep the conservative value and prescribe by HR | early base, or a busy life | the zones may stay slightly off |

3. **Let the runner choose**, then fit the choice into the plan. A test goes at the end of a
   lighter week or after 2 easy days, never the day after a long run. It replaces that week's
   quality session; it isn't added on top.
4. **Afterwards**: update the zones (with agreement), note the result and its source in the
   profile, and recompute paces for the coming weeks.

Retest every 8–12 weeks of consistent training, or when sessions keep coming out clearly faster
or slower than prescribed. Raise that in a review; don't schedule it unannounced.

If an earlier coaching decision was based on mislabelled zones (e.g. "threshold" reps that were
really Z4), say so, re-anchor to the true zone, and then progress from there. "Add a rep" still
holds, but at the corrected intensity.

### Keeping the zones current

Zones drift as fitness changes: stale zones make easy runs too fast and threshold reps too easy
(or the other way after a break). Check them:
- **every month**, in the first weekly review of the month, even when nothing seems to have
  changed;
- **on new evidence**, in the review that follows it: a flat 5k–half race run all-out, a 30-min
  test, the watch's own threshold detection (Garmin and others detect LTHR and threshold pace),
  two or more threshold sessions in 6 weeks clearly faster than the zones with HR under LTHR (or
  slower with HR above it), a new maximum HR, a resting HR that has moved, a hard power effort;
- after a break of 2+ weeks or an illness (zones are probably too fast for a while: prescribe by
  HR first).

Gather the evidence of the last ~4 months into `evidence.json` (format in `scripts/zones.py`)
and run `zones.py suggest`. In the monthly check also run `zones.py lt1` on the last weeks' long
and easy runs to see whether the easy cap still fits. It proposes; it never changes anything. A 30-min test sets threshold
pace and LTHR; a flat race sets the pace, and a half's average HR is a floor for LTHR; sessions
only hint ("probably faster": put a number on it with a race or a test). Changes under ~1.5 %
are noise and are kept. Sources more than 3 % apart go to "When the threshold evidence disagrees"
above, not into an average.

Show the proposal as old → new with what it means in practice ("Z2 5:04–5:49 → 4:53–5:36, threshold
reps 4:25 → 4:16"), and why. On the runner's yes: write it to TrainingPeaks (`trainingpeaks.md`
"Zones"), re-read the settings to confirm, ask the runner to set the same values on the watch
(this skill can't write to Garmin), run `season_plan.py retarget --threshold-pace ...`
so the key sessions follow, update the page's `zones` (current + a history entry), the
profile's `Zones:` line (values, source, date) and the decision log. On a no, keep the zones and
note why. With no new evidence and zones older than 12 weeks, raise a retest ("Settling the
threshold"); don't schedule it unannounced.

## 8. Missed sessions, illness, return after a break

- Missed easy run: forget it. Missed quality: move it only if 48 h spacing stays intact, otherwise
  drop it. Never make up a missed long run by lengthening the next one.
- **Illness: triage by symptoms** (IOC consensus 2022 [S8]; the old "neck check" has no data
  behind it):
  - Mild, nose and throat only: easy running allowed if the runner feels OK.
  - Chest symptoms (cough, breathlessness) or headache, or whole-body symptoms (fever, chills,
    aches, unusual fatigue): no running until they're gone.
  - Chest pain, palpitations, fainting or unusual breathlessness: see a doctor before running
    again.
- **First run back:** a 10–20 min test at 60–70 % of normal effort. Progress only if nothing
  abnormal appears during it or in the next 24 h. Then as many easy days as days missed (max ~7)
  before one short quality session, first week ≈ 60–70 % of previous volume (practice-based; most
  illnesses cost a week or less [S9]).
- Return after a break > 2 weeks: start at ~50–60 % of previous volume, easy only for week 1, add
  strides in week 2, quality in week 3 (practice-based). The 30-day longest-run rule applies to
  what was run since returning.
- Pain that changes the gait, sharp or worsening pain: rest and get it checked. Don't plan
  around it.

## 9. Units and terrain

**Units are the runner's choice.** Some think in kilometres ("10 km easy"), some in time ("60 min
easy"). Ask in onboarding and keep it in the profile (`Units:`). Write every session in that unit,
with the other one in brackets as a guide: "10 km (~60 min)" or "60 min (~10 km)". The watch
shows the primary one (`scripts/tp_structure.py` builds both kinds for TP).

Time is the more honest measure on hills and trails, because the effort of a kilometre depends on
the ground. So suggest it there, but don't impose it. A runner who prefers km on a hilly easy run
just gets the note that the km will be slower and the HR cap rules. `check_week.py` compares
weekly *time*, so give plan items both `minutes` and `km` whatever the unit: estimate the other one
from the runner's real pace on that terrain.

**Terrain** is measured, not guessed. Gain per km (`scripts/terrain.py`) from 8–15 recent runs:

| Class | Gain | What it changes |
|---|---|---|
| flat | < 10 m/km | nothing; pace targets work |
| rolling | 10–25 m/km | easy and long runs by HR cap, pace as a loose guide; quality on a flat stretch |
| hilly | 25–50 m/km | easy/long by HR (or time); quality on a flat stretch, track or treadmill, or as uphill reps by HR/effort |
| mountain | > 50 m/km | everything by time and HR/effort; volume in hours and vertical metres |

What matters most is **where quality happens**. Ask: "Do you have a flat stretch, a track or a
treadmill for faster sessions?" With one, quality stays pace-based there even if every easy run is
hilly. Without one, prescribe threshold work by HR (finish reps at ~LTHR − 3 to LTHR, structure in
`percentOfThresholdHr`) and VO2 work as uphill reps by effort. Running power (Stryd, newer Garmin
watches) doesn't depend on the gradient; if the runner has it and trusts it, it's the best target
on hills (`percentOfFtp` against their running FTP).

**Terrain vs. the goal race.** Hilly home, flat race: keep at least one flat pace session a week
in build and peak, and put race-pace segments on flat ground. Flat home, hilly or trail race: add
hills (uphill reps, hilly long runs), downhill running and step-downs in strength, and grow weekly
vertical gradually (+10 % like volume). For trail goals, plan volume in hours plus vertical metres.

**Temporary change** ("this week I'm in the mountains", "running on the beach on holiday"):
re-plan the rest of the week in time and HR, swap pace intervals for uphill reps or fartlek by
effort, and say in the review that slow paces were the terrain, not fitness. Note it in the
decision log; the profile's terrain doesn't change.

**Reviewing hilly runs:** judge easy runs by HR (was it under the cap?), not pace. TP's rTSS
already accounts for gradient (it uses normalized graded pace), so load numbers stay comparable.
If a "slow" week was hilly, say so before concluding anything about fitness.

## 10. Age, energy and health flags

**Masters runners (40+, 50+).** Performance declines mainly through VO2max, and much of that
comes from training less hard and less often; running economy doesn't decline with age [S41].
- Keep intensity: 1–2 quality sessions a week. Reduce density, not intensity.
- 50+: 48–72 h between hard, downhill or eccentric-heavy sessions; consider 9–10-day cycles and
  2:1 build:deload; progress volume a little slower (practice-based; recovery data are thin
  [S42]).
- Strength twice a week all year, including heavy work and progressive plyometrics; in peak
  keep one session.
- Protein after hard sessions (~0.3–0.4 g/kg), and a reminder to drink, as thirst fades with age
  [S36, S42].

**Low energy availability (REDs).** Under-fuelling for the training load harms bone, hormones,
immunity and performance, in men and in women [S43]. The coach doesn't diagnose; it screens and
refers. Ask during onboarding, and again when performance stalls or fatigue persists:
1. (Women not on hormonal contraception) Are periods regular? Three or more months missed? First
   period after 15? (Hormonal contraception hides this signal.)
2. (Men) Noticeably lower libido or fewer morning erections?
3. Any bone stress injury? Two or more ever, or one in the pelvis, hip or femoral neck?
4. Unintended weight loss, or trying to lose weight while training hard?
5. Worry about food or weight, skipping meals around training, exercising to "make up" for food?
6. Persistent fatigue, frequent illness, dizziness, gut trouble, low mood, or stalling despite
   training?

Refer to a sports-medicine doctor and a registered sports dietitian with any of: periods missed
3+ months, any bone stress injury, signs of disordered eating, or two or more of the other
flags [S43, S44]. Don't raise the load while waiting. Never set weight or body-composition targets.
Losing periods is never a normal effect of training.

**Menstrual cycle.** Evidence doesn't support planning training by cycle phase: effects on
performance are trivial and inconsistent [S45]. Logging the cycle is optional; adjust only for the
runner's own symptoms.
