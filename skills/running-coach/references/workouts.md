# Workout library

Sessions with their purpose, the TrainingPeaks structure, and a description in the athlete's
style. Percentages are % of threshold speed (`percentOfThresholdPace`). Convert them to paces with
`scripts/paces.py convert` for the description. The example paces below assume a 4:10/km
threshold and LTHR 174.

## Description style

Descriptions are short, concrete, and say *why* and *how it should feel*, plus what to do if
the day goes badly. The runner reads them on the watch or phone right before running. Write
them in the runner's language. Example (Slovak):

> 15 min rozklus (posledné 3 min postupne svižnejšie + 3 rovinky). Potom 5× 1 km @ 4:10–4:15/km,
> medzi nimi 2 min pomalý klus. 10 min výklus.
> Cieľ: kontrolovane, rovnomerne. Posledný úsek má byť rovnako rýchly ako prvý, NIE rýchlejší.
> Tep na konci úsekov ~170–175. Ak ide ľahko, nabudúce pridáme 6. úsek, nie tempo.

Include: paces (min/km) and HR cap/target, recovery type, the goal of the session, and a bail-out
rule for quality sessions ("ak sa cítiš rozbitý…, urob z toho ľahkých 8 km").

## Structure format

Write the session as a spec for `scripts/tp_structure.py`. Every step goes to TP in the unit it
is written in (`km`/`m` as distance, `seconds`/`minutes` as time), so one session can mix them
and the watch counts each step the way it was meant. The spec's `unit` (the runner's unit) only
sets the primary axis in TP. The script also returns the time-based `structure` below for
`tp_validate_structure`. Example spec, a km runner's cruise intervals:

```json
{"threshold_pace": "4:10", "unit": "km", "metric": "pace", "steps": [
  {"name": "Rozklus 12 min", "minutes": 12, "pct": [68, 76], "class": "warmUp", "pace": "6:00"},
  {"repeat": 3, "steps": [
    {"name": "Rovinka 20 s", "seconds": 20, "pct": [115, 125], "class": "warmUp"},
    {"name": "Klus 40 s", "seconds": 40, "pct": [55, 66], "class": "warmUp", "pace": "6:40"}]},
  {"repeat": 6, "steps": [
    {"name": "1 km @ 4:10–4:15", "km": 1, "pct": [98, 100]},
    {"name": "Klus 75 s", "seconds": 75, "pct": [55, 66], "class": "rest", "pace": "6:40"}]},
  {"name": "Výklus 2 km", "km": 2, "pct": [62, 70], "class": "coolDown", "pace": "6:10"}]}
```

**Pick the unit per step, by what the step is for:**
- Reps on flat ground: distance (1 km, 400 m), what the runner can match against a pace.
  Hill reps, trail and fartlek: time, because a kilometre there says little.
- Recoveries: usually time (75 s klus, 2' klus, 30 s stoj); distance where it is natural, like
  200 m or 400 m on a track. Choose whichever fits the session; mixing is fine.
- Warm-up, cool-down, easy and long runs: the runner's unit from the profile.
- Strides go into the structure, not only into the description: e.g. a 15' warm-up is
  12' easy + 3 × (20 s rovinka / 40 s klus). Strides inside a warm-up get class `warmUp`, so the
  session analysis doesn't count them as reps; in an "easy + strides" run they are `active`.

Give easy steps a `pace` from the runner's real easy runs on their terrain, because the % midpoint
is a flat-road estimate. With `"metric": "hr"` (hilly ground, no flat option) the targets are
% of LTHR (easy ≈ 75–83 %, threshold reps ≈ 97–100 %), and every step needs a `pace` estimate
for the conversion.

The time-based `structure` the script produces (and that `tp_validate_structure` reads) looks
like this:

```json
{"primaryIntensityMetric": "percentOfThresholdPace", "steps": [
  {"name": "Rozklus", "duration_seconds": 900, "intensity_min": 65, "intensity_max": 72, "intensityClass": "warmUp"},
  {"type": "repetition", "reps": 5, "steps": [
    {"name": "1 km @ prah", "duration_seconds": 250, "intensity_min": 98, "intensity_max": 100, "intensityClass": "active"},
    {"name": "Klus", "duration_seconds": 120, "intensity_min": 55, "intensity_max": 66, "intensityClass": "rest"}
  ]},
  {"name": "Výklus", "duration_seconds": 600, "intensity_min": 62, "intensity_max": 70, "intensityClass": "coolDown"}
]}
```

In it, distance reps are written as their expected duration at the target pace (1 km at
4:12 ≈ 252 s); that only feeds the TSS estimate, TP gets the native steps. Name every step with
its distance or time and the pace ("1 km @ 4:10–4:15", "Klus 75 s"), so the watch screen says
what to do.

### Prescribing by running power

For runners with power (Stryd, newer Garmin, Coros) who trust it, especially on hills where pace
misleads: `paces.py power --rftp <W>` gives the zones and converts watts ↔ % of rFTP. In the
spec, use `"metric": "power"` (TrainingPeaks `percentOfFtp`), and give each step a `pace` estimate
if the workout is written in km.

| Session | % of rFTP |
|---|---|
| Recovery | 60–70 % |
| Easy / long run | 65–80 % |
| Steady, marathon pace | 80–90 % |
| Threshold / cruise intervals | 95–100 % |
| Sub-threshold | 88–95 % |
| VO2 intervals | 105–115 % |
| Strides, short reps | 115–130 % |

- rFTP: take it from TrainingPeaks (its run power zones are built on it), or estimate it with
  `paces.py power --effort-watts <W> --effort-minutes <min>` from a recent race or hard effort.
  Watts from different devices aren't comparable (wrist power on Garmin reads higher than Stryd).
- Keep HR as the check: power targets with an HR cap on easy runs.
- Power lags reality less than HR and isn't fooled by hills, but wind, treadmill calibration and
  firmware changes shift it. Retest rFTP with the threshold (every 8–12 weeks).

---

## Easy / aerobic

Easy % ranges are a default. When the runner has recent easy runs, use their real easy pace range
(at the HR cap) in the structure and description instead; on hilly or trail routes it's often
slower than 70 %.

| Session | Purpose | Structure | Example |
|---|---|---|---|
| **Regeneračný beh** | recovery the day after a hard session | 1 step, 30–40 min, 65–72 % | 5:50–6:25/km, tep do ~140 |
| **Ľahký beh** | aerobic base | 1 step, 40–60 min, 70–80 % | 5:15–5:55/km, tep do ~145 |
| **Ľahko + rovinky** | base + leg speed | easy 35–45 min, then 4–8 × (20 s @ 110–120 % / 60–70 s @ 55–65 %), 3 min @ 62–70 % | rovinky ~3:30–3:50, svižne, uvoľnene, NIE šprint |
| **Dlhý beh** | endurance | 1 step 70–150 min @ 70–80 % | celé ľahko, do kopca podľa tepu, voda nad 75 min |
| **Dlhý beh s rýchlym záverom** | specific endurance (build/peak) | easy 60–90 min, then 10–20 min @ 87–93 % (X) | posledných 15 min v tempe ~4:35–4:45 |
| **Progresívny beh** | aerobic power | 3 thirds: 70–76 % / 78–84 % / 87–93 % | each third a bit quicker, last at marathon effort |

## Threshold (Z3 / Y)

Threshold work sits at **93–100 %** (Z3) up to ~102 % (Y). Reps above 102 % are Z4, so name
them that way.

| Session | Structure | Example paces | Notes |
|---|---|---|---|
| **Tempo 2× 10–15 min** | WU 15' · 2 × (10–15' @ 90–95 % / 3' klus) · CD 10' | 4:23–4:38 | "príjemne náročné", short sentence possible |
| **Súvislé tempo 20–30 min** | WU 15' · 20–30' @ 92–96 % · CD 10' | 4:20–4:32 | only after 2× 15' is comfortable |
| **Cruise intervaly 5–6× 1 km** | WU 12' + 3 × (20 s rovinka / 40 s klus) · 5–6 × (1 km @ 98–100 % / 60–90 s klus) · CD 10' | 4:10–4:15 | progress: 5 → 6 → 7 reps, then 3 × 2 km |
| **3× 2 km @ prah** | WU 15' · 3 × (2 km @ 97–99 % / 2' klus) · CD 10' | 4:12–4:18 | |
| **Kopce tempo** | 4–6 × 3–4 min uphill by HR 165–174 / jog down | HR, not pace | trail-friendly threshold |

### Option: sub-threshold weeks ("Norwegian singles")

Many short reps just under threshold, with short rests, two or three times a week, everything
else truly easy. Elite runners do a lactate-guided double-threshold version [S28]. The amateur
"singles" version is coaching practice without trials, so offer it as an option, never as the
default, and say so.

- **Who:** 4+ runs a week, injury-free for 8+ weeks, an established base, and a runner who likes
  structure.
- **Dose:** 2 sessions a week (3 only with 6 runs), at least one easy day between them, 15–25 % of
  weekly time at sub-threshold. VO2 work is dropped except strides or short hills, and comes
  back 4–6 weeks before a 5k/10k.
- **Intensity:** ~90–96 % of threshold speed (about half-marathon to 30k pace), HR at least
  ~5 bpm under LTHR, RPE 6–7/10. The rule without a lactate meter: finish feeling 1–2 more reps
  were possible. (The % translation is an estimate, not a measured value.)

| Session | Structure |
|---|---|
| **5–6 × 6 min** | WU 15' · 5–6 × (6' @ 90–94 % / 1' klus) · CD 10' |
| **8–10 × 1 km** | WU 15' · 8–10 × (1 km @ 92–96 % / 1' klus) · CD 10' |
| **3 × 10 min** | WU 15' · 3 × (10' @ 90–93 % / 2' klus) · CD 10' |
| **20 × 400 m** | WU 15' · 20 × (400 m @ 95–98 % / 30 s stoj) · CD 10' |

## VO2max / speed (Z4–Z5)

| Session | Structure | Example paces | Notes |
|---|---|---|---|
| **5× 3 min** | WU 15' + rovinky · 5 × (3' @ 106–110 % / 2–3' klus) · CD 10' | 3:47–3:56 | build phase, max 1×/week |
| **6–8× 800 m** | WU · 6–8 × (800 m @ 108–112 % / 400 m klus) · CD | 3:43–3:51 | 10k/5k focus |
| **Krátke kopce** | after easy 30': 8–10 × (45–60 s hard uphill / walk-jog down) | effort | strength + economy, base phase |
| **Fartlek** | 40–50 min with 8–10 × 1–2 min @ 100–108 % | by feel | good on trails |

## Race-specific

| Goal | Session | Structure |
|---|---|---|
| 10k | 3 × 3 km @ 10k pace (≈ 100–102 %) | 3' jog between |
| Half marathon | 2–3 × 5 km @ HM pace (≈ 95–98 %), or long run with last 5–8 km @ HM pace | 3' jog |
| Marathon | long run 25–32 km with 10–16 km @ M pace (≈ 88–92 %) | inside the long run |

## Progressions

The ladders behind the roadmap's default draft (`season.md` §2b; `scripts/key_sessions.py` has
them in full). They describe a typical runner, not this one: the coach adapts them (injuries,
terrain, what worked, recovery). This is coaching practice, not a tested protocol. The rule
throughout: first more reps, then longer reps, only then a faster pace (`methodology.md` §4). One
step per build week; after a session under target, usually repeat the step.

| Phase | Threshold / tempo | VO2 / speed | Long run | Typical milestones |
|---|---|---|---|---|
| Base | 5–7× 1 km @ 98–100 % → 3–4× 2 km → 3× 3 km → 2× 15–20 min @ 93–96 % → continuous 25–30 min | hills 8–10× 45–60 s, then fartlek 8–10× 1–2 min | easy, +1–2 km a week; at the end of base the last 15 min steady | threshold check (30 min test or a 10k race) at the end of base |
| Build | half-marathon pace 3× 3 km → 2× 5 km → 3× 4 km → 2× 6 km | 5–6× 3 min @ 106–110 %, then 5–7× 1 km @ 104–106 % | marathon: every other long run with the last 8 km or 3× 4 km at marathon pace | longest run (30–32 km for a marathon) |
| Specific, marathon | marathon pace mid-week 2× 5 → 2× 6 → 2× 7 km | none: the long run carries the load | 30–32 km with 14–16 km at marathon pace; continuous 18–23 km at marathon pace 2–4 weeks before | both marathon-pace long runs, the tune-up half |
| Specific, half / 10k | 2× 6 km → 3× 5 km → 10 km continuous @ half-marathon pace; 10k: 3× 2 → 3× 3 → 4× 2.5 km @ 10k pace | 6–8× 800 m @ 108–112 % | half: last 6 km at half-marathon pace | dress rehearsal 2–3 weeks out |
| Specific, 5k | 6× 800 m → 8× 800 m → 6× 1 km @ 5k pace | threshold maintenance 5× 1 km | easy | dress rehearsal 2–3 weeks out |
| Taper | sharpening 3× 1 km at race pace | – | shorter; marathon: 6 km at marathon pace inside it | – |

**The continuous marathon-pace run** (18–23 km, after 3–5 km easy) is the best test of marathon
pace, fuelling and head. Two to four weeks before the race, not in the week after a hard race,
with gels as in the race. Verdict: HR in the second half at most ~92 % of LTHR and no fade →
the goal pace is realistic. HR climbing past that or a fade in the last 5 km → race the first
half slower, and say so in the race plan.

## Fuelling practice (gut training)

The gut adapts to carbohydrate during running like the legs adapt to load: what's tolerated at
race pace goes up with practice [S37]. For a marathon (and halves over ~90 min), practise on the
long runs of the build and specific phases:

1. **Step up**: 30 g/h on the first long runs → 45 → 60 → 75 → 90 g/h, one step only when the
   last one went without stomach trouble (bloating, cramps, nausea, urgency). Glucose:fructose
   products for anything over 60 g/h.
2. **Use the race products** and the race's drink at least on the last 3–4 long runs, and on the
   marathon-pace long runs at race pace.
3. **Record each one**: after the long run ask for grams per hour, products, and GI comfort 0–10
   (0 = no trouble), and add a comment to that workout in TP: `tp_add_workout_comment` with
   "Výživa: 60 g/h (2 gély + iónový nápoj), žalúdok 1/10" (after the runner agreed, like the health
   diary). The highest rate tolerated well goes into the profile (`Gut: 60 g/h, 2027-03-21`) and
   into `race_plan.py` (`gut_trained_gph`).
4. **Key sessions**: the roadmap's marathon-pace long runs are the dress rehearsals for fuelling
   too: say so in their description.

## Race week

| Session | Structure |
|---|---|
| **Ostrenie** (3–4 days out) | WU 15' · 3 × 1 km @ race pace / 2' klus · CD 10' |
| **Predzávodný** (day before) | 20–25 min easy + mobilita + abeceda + 4–6 × 100 m rovinky, 1' pauza |
| **Závod** | create as sport `Run` with the race distance and goal pace in the description; add the event if missing |
