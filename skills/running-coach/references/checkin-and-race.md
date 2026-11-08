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
   (`methodology.md` §7) and prints green / amber / red with the reasons. Several short nights
   count even when last night was fine (`sleep_debt`). Without metrics, skip this and rely on
   how they feel.
3. **Subjective**: ask at most three quick things if not already said: sleep, legs (fresh /
   normal / heavy / sore), mood and stress, any pain or illness symptoms. Load outside running
   goes into the script as `--stress 1-5` (the runner's word, or your reading of what they
   said): long travel or a time-zone change in the last 2 days, a heavy work week, a heat wave,
   a sick child at night count as 4–5. Re-run `readiness.py` with it; a normal HRV this morning
   does not cancel it. With TP, also read the
   diary: `tp_list_notes` for the last 30 days → `scripts/health_log.py read` (active pain or
   illness and what it means, "Pain and illness diary" below).
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

### Morning brief (scheduled, to the phone)

The check-in can run by itself every morning, so the runner wakes up to one line on the phone and
the full answer in the app. If the `create_scheduled_task` tool is available (Claude desktop app),
offer it once after the first check-in, e.g. daily at 06:30 (`cronExpression` `30 6 * * *`); set
it up only after a yes. Self-contained prompt, filled in, in the runner's language:

> Use the running-coach skill for <name>'s morning brief. Data: TrainingPeaks (trainingpeaks
> MCP). Load `tp_get_metrics` for the last 56 days, today's planned workout (`tp_get_workouts`
> for today) and the notes of the last 30 days (`tp_list_notes`). Run `scripts/readiness.py
> --brief` on the metrics and `scripts/health_log.py read` on the notes. Weather for <town>
> (lat <lat>, lon <lon>) at <usual run time>: `scripts/weather.py`. Write the check-in in 3–5
> lines: the verdict, what to do today exactly (keep, trim or swap the session, with paces and
> HR cap; heat adjustment if any), active pain or illness, and what moves if something changes.
> Then send ONE line with PushNotification (under 180 characters), e.g. "Zelená · 6× 1 km
> 4:10–4:15, tep do 174 · 8 °C" or "Oranžová · intervaly presuň, dnes 40 min ľahko do 145". If a
> plan page URL is in the profile, add today's readiness row to its `trends` collection, with
> `advice`: one sentence on today's session in the runner's language (the page's "Today" card shows
> it, e.g. "Daj o 1 úsek menej, na spodku tempa (4:15), alebo vymeň so sobotou."). Never
> change the TrainingPeaks calendar: if the session should change, say so and wait for the
> runner's yes.

The brief is read on waking, often on the phone: one short line each for the verdict (with the
numbers that decided it), today's session, pain or illness, and what moves; no reasoning
paragraphs. Example:

> **Oranžová**: HRV 7 dní 59 pod pásmom 60–63, tep a spánok v norme.
> **Dnes**: namiesto 3× 2 km 40–45 min ľahko 5:35–6:00, tep do 145.
> **Achilovka** 2/10 po behu: ľahký beh OK, pri 3/10 skonči.
> **Tempo** presuň na najbližší deň, keď bude HRV späť v pásme.

The runner asks for more if they want it. Tell the runner: it runs only while the app is open (otherwise at the next launch), and the line
reaches the phone when Remote Control is connected (otherwise it's a desktop notification). Use
the coordinates of their town, never a home address. Without scheduled tasks, the runner just
asks "mám dnes behať?".

### Pain and illness diary (TrainingPeaks notes)

TrainingPeaks is the one place for pain and illness: a calendar note per report, on the day it
happened, so the runner, a physio or a coach sees it next to the training, and every chat and
review reads the same history. (TP's own "Injury" metric has no documented scale, so the notes
carry the score.)

- **Ask once** whether reports may go to TP straight away; record the answer in the profile
  (`Health log: TP notes, write on report` or `ask each time`). Without that agreement, ask
  before each note.
- **Writing**: `scripts/health_log.py note --type pain --part "lýtko vľavo" --score 3 --when
  during --lang sk` (or `--type illness --symptoms "..." [--fever] [--chest]`) prints the title
  and description; pass them to `tp_create_note` with the date it happened. Follow-ups use
  `--status same|better|worse|resolved`. Ask for the score 0–10, where it is, when it hurts
  (during, after, the next morning, at rest), and whether it changes the stride.
- **Reading**: `tp_list_notes` (last 30–60 days) → `health_log.py read --lang sk`: active issues,
  trends per body part and the rule for each [S8, S53]:

| | Training |
|---|---|
| pain up to 3/10 that settles by the next morning | easy running is fine, watch it |
| pain 4–5/10 | no quality, shorter runs, watch it |
| 6+/10, a changed stride, pain at rest or at night, or worse three reports in a row | stop, get it checked |
| same place for more than 14 days | get it checked |
| illness: nose and throat only | easy running if they feel OK |
| fever, chest or whole-body symptoms | no running until gone, then a 10–20 min test run and as many easy days as days missed |

  Check-ins, reviews and the block report read it; the page shows active issues (`health`
  collection from `--json`).

## Race day

Triggered by "race plan", "pacing for Sunday", "what should I eat before the race", or the
race-week part of a block.

Produce one compact race plan (in the runner's language). `scripts/race_plan.py` puts it
together: the forecast range moved for the weather (the real forecast up to 16 days out, the
typical weather of that date before that, `weather.py`), the goal checked against it, splits by
the course profile (a GPX of the course: from the race website, or a route the runner exported),
and the fuelling plan, capped at what the runner's gut tolerated in training ("Fuelling practice"
in `workouts.md`):

```bash
python scripts/race_plan.py race.json --lang sk      # format in the script's docstring
```

Re-run it in race week with the real forecast and the latest `forecast.py` range. The steps below
are what it does and what to add by hand:

1. **Goal & realistic range**: start from `forecast.py` (`analysis.md` "Race predictions"): its
   race-day range already holds recent results, threshold, volume, course and heat. Then check it
   against the current threshold and recent training (`paces.py race` in reverse: is the goal pace sustainable? HM ≈ 98–100 % of threshold speed for well-trained, ~95 %
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
