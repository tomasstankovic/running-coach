# Strength training for runners

Strength supports the running and never competes with it. Its purposes: running economy,
injury resilience (calves, Achilles, hips), and keeping power with age.

What the evidence says (tags in `sources.md`):
- **Economy and performance**: heavy strength work improves running economy (~2–8 %) and
  time-trial performance; heavy plus plyometric combined works best, heavy alone next, plyometrics
  alone less. Light circuits and isometrics don't improve economy (still fine for general
  robustness). Expect it after ~6+ weeks of consistent work [S29–S31].
- **Injury**: strength training cuts sports injuries a lot in mixed sports [S32], but the one large
  runner trial (a self-directed home programme) found no effect [S33]. Say "likely helps", and
  remember that avoiding load spikes matters more.
- **Maintenance**: one session a week keeps the gains for months; stopping for ~8 weeks loses
  them [S34]. So in peak go down to 1, not to 0, until the last 7–10 days before an A race.
- **Interference**: a heavy session leaves fatigue that blunts the next quality run for hours to
  days [S35]. Lift after the hard run on the same day (3–6 h later if possible), never the day
  before a key session.

## Discuss it first

Strength is the runner's choice, not a default. Don't add it to a plan unless they asked for it
or agreed in onboarding. The profile records the answer, so don't ask again every week. Revisit
it at the start of a new block, or when an injury pattern suggests it would help.

The conversation, kept short:
1. **Do they do any now?** If they already lift, or do yoga, a gym class or CrossFit, plan around
   it rather than adding more.
2. **Do they want it?** If unsure: the benefit (fewer overuse injuries, better economy, most
   noticeable for calves/Achilles and hips) and the cost (2 × 25–40 min a week, mild soreness the
   first 2–3 weeks). "Not now" is a fine answer.
3. **Setting**, which decides the templates:

| Setting | Typical equipment | Template |
|---|---|---|
| Gym | barbell, dumbbells, machines, box | A (base) → B (build) → C (maintenance) |
| Home with equipment | kettlebell or dumbbells, band, step or chair | A with weights, B-home (below) |
| Bodyweight only | floor, step, wall | BW (below) |
| Mix | gym once, home once | one gym session (A/B) + one short home session (BW) |

4. **Experience and time**: never lifted means 3–4 weeks of technique with light loads first.
   Fit the session to the time they really have; 20 minutes done beats 40 skipped.
5. **Preferences**: sessions they'd enjoy, the time of day, and whether they want it on run days
   (recommended) or separate.

Write the answers into the profile (`Strength:` line), then plan.

## Placement in the week

- **Same day as a hard run** (run first; strength after, or later the same day). That keeps easy
  days easy. Second choice: after an easy run.
- **Not the day before** a key session or the long run, and not right before a race.
- Heavy lower-body work at least ~48 h before the next quality session.
- Frequency by phase:

| Phase | Sessions/week | Emphasis |
|---|---|---|
| Base | 2 | learn movements, moderate loads, 3 × 8–12; calves/soleus volume |
| Build | 2 → 1–2 | heavier, 3–4 × 4–6 at RPE 7–8 + plyometrics |
| Specific/peak | 1 | maintenance, 2 × 4–6 heavy, few plyos |
| Taper | 0–1 | one short session early in the taper; none in the last 7–10 days before an A race |
| Deload week | 1 | half the sets |
| Return after injury/illness | bodyweight only | whatever the physio allows |

Beginners or runners new to lifting: bodyweight and light loads for 3–4 weeks before going heavy.
Count strength in the week's fatigue: after a big strength session, don't add volume.

## Session templates (30–40 min)

**A: Base strength (home or gym)**
| Block | Exercise | Sets × reps |
|---|---|---|
| WarmUp | leg swings, glute bridge, ankle hops | 5 min |
| SingleExercise | Split squat / Bulgarian split squat | 3 × 8–10 per side |
| SingleExercise | Single-leg Romanian deadlift | 3 × 8 per side |
| Superset | Single-leg calf raise (straight knee) + Seated/bent-knee calf raise (soleus) | 3 × 12–15 per side |
| Superset | Side plank + Dead bug | 3 × 30 s per side / 3 × 8 per side |

**B: Build strength + power (gym)**
| Block | Exercise | Sets × reps |
|---|---|---|
| WarmUp | skips, pogo hops, bodyweight squats | 5–8 min |
| SingleExercise | Back squat or trap-bar deadlift | 4 × 4–6, RPE 7–8 |
| SingleExercise | Hip thrust | 3 × 6–8 |
| SingleExercise | Box jump or bounding (plyo) | 3 × 5 |
| Superset | Weighted calf raise + Copenhagen plank | 3 × 8–10 / 3 × 20 s per side |

**C: Maintenance (peak)**: 1 heavy lift 2 × 5, calf raises 2 × 12, 1 plyo 2 × 5, core 2 rounds.
Done in 20 min.

**B-home: Build with a kettlebell or dumbbells**
| Block | Exercise | Sets × reps |
|---|---|---|
| WarmUp | skips, pogo hops, goblet squat with a light weight | 5 min |
| SingleExercise | Rear-foot-elevated split squat holding the weight | 3 × 6–8 per side, slow lowering |
| SingleExercise | Single-leg RDL with the weight | 3 × 6–8 per side |
| SingleExercise | Step-ups onto a chair/step with the weight | 3 × 8 per side |
| Superset | Single-leg calf raise holding the weight + Side plank | 3 × 10–12 / 3 × 30 s |
| SingleExercise | Box or squat jumps (plyo) | 3 × 5 |

**BW: Bodyweight only (20–30 min)**
| Block | Exercise | Sets × reps |
|---|---|---|
| Circuit | Bulgarian split squat (3 s down), Single-leg glute bridge, Single-leg calf raise off a step, Side plank | 3 rounds; 10–12 per side / 30–40 s |
| Circuit | Step-downs (slow), Dead bug, Pogo hops | 2 rounds; 8 per side / 8 per side / 20 s |

Bodyweight progresses through tempo (slower lowering), range (deficit, elevated foot), single-leg
versions and pauses, not load.

Trail runners: add step-downs or eccentric (slow-lowering) work for downhill running, and step-ups
with weight.

## Writing to TrainingPeaks

Strength workouts live in a separate API: `tp_get_strength_workouts` lists them (they do not
appear in `tp_get_workouts`), and `tp_create_strength_workout` creates them.

1. Find exercise IDs: `tp_search_exercises` by name (e.g. "split squat", "calf raise",
   "romanian deadlift", "side plank", "hip thrust"). Each result lists its **native parameters**:
   use exactly those. Many weighted exercises take `WeightLb`. If the runner thinks in kg, convert
   (kg × 2.2046), and put the kg value in the exercise `notes`.
2. Build `blocks`: `{type: WarmUp|SingleExercise|Superset|Circuit|CoolDown, title, notes,
   exercises: [{id, notes, sets: [{RepsPerSide: 10, WeightLb: 35}, ...]}]}`. In a Superset or
   Circuit, every exercise needs the same number of sets.
3. `tp_create_strength_workout` with `date`, `title` and `instructions` (purpose, RPE, how to pick
   the weight: "last 2 reps hard but clean"). Only after the runner confirms, as with runs.

Without TP, put strength sessions in the plan table and the `.ics` file like any other workout,
with exercises listed in the description.

In `check_week.py` give strength sessions `"type": "strength"`. The script then warns when one
lands the day before a hard session or the long run.
