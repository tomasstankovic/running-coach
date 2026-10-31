# Daily check-in and race day

## Daily check-in

Triggered by "should I train today?", "how's my readiness?", "I slept badly, what now?", or the
runner reporting how they feel before a session.

1. **Today's planned session**: `tp_get_workouts` for today (or the plan from the conversation).
2. **Objective signals**: `tp_get_metrics` for the last 35–60 days (the HRV rule needs a
   baseline of 3+ weeks before the current week). Save the output and run
   ```bash
   python scripts/readiness.py metrics.json
   ```
   It compares the 7-day HRV trend, resting HR and sleep with the runner's own baseline
   (`methodology.md` §7) and prints green / amber / red with the reasons. Without metrics, skip
   this and rely on how they feel.
3. **Subjective**: ask at most three quick things if not already said: sleep, legs (fresh /
   normal / heavy / sore), mood and stress, any pain or illness symptoms.
4. **Decide** (subjective beats objective when they disagree strongly, e.g. green numbers but
   feverish):

| Signal | Easy / recovery day | Quality session | Long run |
|---|---|---|---|
| Green | as planned | as planned | as planned |
| Amber (one flag) | as planned, at the bottom of the range | keep it but trim: one rep fewer, or do it at the lower % | shorten 15–20 % |
| Amber (two flags) or heavy legs | shorter or recovery pace | swap with a later easy day if spacing allows; otherwise make it easy | shorten 25–30 %, all easy |
| Red, or chest or whole-body symptoms (fever, aches, cough) | rest, or 20–30 min very easy only if red is from the numbers alone | move or drop | move or drop |
| Chest pain, palpitations, fainting | no running; see a doctor | – | – |
| Pain that changes the gait | rest; physio if it persists > 2–3 days | – | – |

5. **Answer in 3–5 lines**: the verdict, what to do today exactly (paces/HR), and what happens to
   the rest of the week if something moves. If a change is made and TP is connected, offer to
   update the workout (`tp_update_workout`) after confirmation.

One amber day is noise. The HRV 7-day mean below the normal band for 4+ days, or three or more
amber or red days in a row, means the load is too high: −25 % volume and no quality for 3–4 days
(Adapt mode), and look at what's behind it (sleep, stress, illness, fuelling).

**Hot weather**: run by HR or RPE, not pace. Recreational runners slow ~3–8 % in real heat (more
than elites, who lose ~1–3 %) [S39]. Above ~28 °C (or WBGT ~25 °C) move key sessions to the
cool of the day or shorten them. Dizziness, nausea, headache, chills or goose bumps in the heat:
stop, cool down, drink. Confusion or collapse: an emergency, cool first and call for help [S40].

## Race day

Triggered by "race plan", "pacing for Sunday", "what should I eat before the race", or the
race-week part of a block.

Produce one compact race plan (in the runner's language):

1. **Goal & realistic range**: from the current threshold and recent training (`paces.py race` in
   reverse: is the goal pace sustainable? HM ≈ 98–100 % of threshold speed for well-trained, ~95 %
   for less experienced runners; marathon ≈ 88–92 %; 10k ≈ 102–104 %). For the marathon also run
   `paces.py predict` with `--weekly-km` (and a second race or `--training-pace`): Riegel alone
   is often 10+ min too fast for recreational runners (`analysis.md`). Give an A goal and a safe
   B goal.
2. **Pacing**: even or slightly negative split. Generate splits with:
   ```bash
   python scripts/paces.py splits --distance 21.0975 --goal 1:35:00 --every 5 --negative 1
   ```
   Course profile: on hills pace by effort/HR and give the HR ceiling for the first half. Don't
   bank time.
3. **Weather**: above ~15 °C, slow the goal pace by ~1–2 % per 5 °C (more if humid, and more for
   slower runners, who are out in it longer) [S39]. In strong wind, tuck in behind runners and
   run by effort.
4. **Fuelling & drinking** (general guidance from the sports-nutrition position stands [S36–S38];
   not a dietitian's plan):
   - **Carb loading**: for a half marathon over ~90 min and every marathon, 10–12 g carbs/kg/day
     for the last 36–48 h, low-fibre foods. Shorter races: normal carb-rich eating. Nothing new.
   - **Race morning**: 1–4 g carbs/kg 1–4 h before, low in fat, fibre and protein; 5–10 ml fluid/kg
     in the 2–4 h before. Optional caffeine ~3 mg/kg about 60 min before, only if tried in
     training.
   - **During**:

     | Race / run | Carbohydrate |
     |---|---|
     | under ~45–60 min (5k, 10k) | none needed |
     | 45–75 min | a few sips of sports drink or a mouth rinse, optional |
     | 1–2.5 h (half marathon, long runs) | 30–60 g/h |
     | over 2.5 h (marathon) | 60–90 g/h of glucose:fructose for a trained gut, otherwise 30–60 g/h; a dose every 15–20 min from ~20 min |

     Practise the race plan on at least 3 long runs. Long runs over 90 min carry 30–60 g/h.
   - **Drinking**: to thirst, typically 0.4–0.8 L/h, more in heat. Never finish heavier than you
     started; overdrinking, not dehydration, causes hyponatremia (slower runners and women are at
     higher risk). Add sodium on runs over 2 h or for heavy, salty sweaters. Headache, nausea,
     bloating or confusion after drinking a lot: urgent medical help.
5. **Warm-up**: 5k/10k: 15–20 min easy + drills + 3–4 strides at race pace, finishing ~10 min
   before the start. HM: 10 min easy + 2–3 strides. Marathon: 5–10 min walking/very easy jogging.
6. **Race-week schedule**: from the taper rules in `methodology.md` (sharpening session 3–4 days out,
   shakeout the day before).
7. **After**: easy days ≈ one per 3–5 km raced before the next quality session (5k: ~2 days,
   10k: ~3, HM: ~5–7, marathon: ~2–3 weeks of easy running).

With TP, offer to write the race-week sessions and the race itself (with the pacing table in the
description) after confirmation.
