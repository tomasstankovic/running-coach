# Strength training for runners

Add strength only when the runner asks for it or agreed to it during onboarding. Its purposes:
injury resilience (calves, Achilles, hips), running economy, and keeping power with age. It
supports the running and never competes with it.

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
