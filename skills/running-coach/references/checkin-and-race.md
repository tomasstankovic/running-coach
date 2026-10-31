# Daily check-in and race day

## Daily check-in

Triggered by "should I train today?", "how's my readiness?", "I slept badly, what now?", or the
runner reporting how they feel before a session.

1. **Today's planned session**: `tp_get_workouts` for today (or the plan from the conversation).
2. **Objective signals**: `tp_get_metrics` for the last 28 days. Save the output and run
   ```bash
   python scripts/readiness.py metrics.json
   ```
   It compares today's HRV, resting HR and sleep with the runner's own baseline and prints
   green / amber / red with the reasons. Without metrics, skip this and rely on how they feel.
3. **Subjective**: ask at most three quick things if not already said: sleep, legs (fresh /
   normal / heavy / sore), mood and stress, any pain or illness symptoms.
4. **Decide** (subjective beats objective when they disagree strongly, e.g. green numbers but
   feverish):

| Signal | Easy / recovery day | Quality session | Long run |
|---|---|---|---|
| Green | as planned | as planned | as planned |
| Amber (one flag) | as planned, at the bottom of the range | keep it but trim: one rep fewer, or do it at the lower % | shorten 15–20 % |
| Amber (two flags) or heavy legs | shorter or recovery pace | swap with a later easy day if spacing allows; otherwise make it easy | shorten 25–30 %, all easy |
| Red, or illness below the neck | rest or 20–30 min very easy | move or drop | move or drop |
| Pain that changes the gait | rest; physio if it persists > 2–3 days | – | – |

5. **Answer in 3–5 lines**: the verdict, what to do today exactly (paces/HR), and what happens to
   the rest of the week if something moves. If a change is made and TP is connected, offer to
   update the workout (`tp_update_workout`) after confirmation.

One amber day is noise. Three or more amber or red days in a row, or a downward HRV trend over
1–2 weeks, means the load is too high: say so and suggest making the rest of the week easier
(Adapt mode).

## Race day

Triggered by "race plan", "pacing for Sunday", "what should I eat before the race", or the
race-week part of a block.

Produce one compact race plan (in the runner's language):

1. **Goal & realistic range**: from the current threshold and recent training (`paces.py race` in
   reverse: is the goal pace sustainable? HM ≈ 98–100 % of threshold speed for well-trained, ~95 %
   for less experienced runners; marathon ≈ 88–92 %; 10k ≈ 102–104 %). Give an A goal and a
   safe B goal.
2. **Pacing**: even or slightly negative split. Generate splits with:
   ```bash
   python scripts/paces.py splits --distance 21.0975 --goal 1:35:00 --every 5 --negative 1
   ```
   Course profile: on hills pace by effort/HR and give the HR ceiling for the first half. Don't
   bank time.
3. **Weather**: above ~15 °C, slow the goal pace by ~1–2 % per 5 °C (more if humid). In strong
   wind, tuck in behind runners and run by effort.
4. **Fuelling & drinking**:
   - Days before: normal eating. For HM/marathon, carb-rich meals the last 1–2 days
     (marathon ~7–10 g carbs/kg/day). Nothing new.
   - Race morning: carb breakfast 2–4 h before (≈ 1–2 g/kg), 300–500 ml fluid. Optional caffeine
     ~3 mg/kg about 60 min before, only if it's been tried in training.
   - During: races under ~75 min need water only if hot. HM: 30–60 g carbs/h is optional but
     helps. Marathon: 60–90 g carbs/h from the start (gels every 20–30 min), only at amounts
     practised on long runs. Drink to thirst, roughly 400–800 ml/h, more in heat, with
     electrolytes.
5. **Warm-up**: 5k/10k: 15–20 min easy + drills + 3–4 strides at race pace, finishing ~10 min
   before the start. HM: 10 min easy + 2–3 strides. Marathon: 5–10 min walking/very easy jogging.
6. **Race-week schedule**: from the taper rules in `methodology.md` (sharpening session 3–4 days out,
   shakeout the day before).
7. **After**: easy days ≈ one per 3–5 km raced before the next quality session (5k: ~2 days,
   10k: ~3, HM: ~5–7, marathon: ~2–3 weeks of easy running).

With TP, offer to write the race-week sessions and the race itself (with the pacing table in the
description) after confirmation.
