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

## Structure format (tp_create_workout `structure`)

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

Distance reps are written as their expected duration at the target pace (1 km at 4:12 ≈ 252 s).
Name the step with the distance ("1 km @ 4:10–4:15") so it's clear on the watch.

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
| **Cruise intervaly 5–6× 1 km** | WU 15' + 3 rovinky · 5–6 × (1 km @ 98–100 % / 60–90 s klus) · CD 10' | 4:10–4:15 | progress: 5 → 6 → 7 reps, then 3 × 2 km |
| **3× 2 km @ prah** | WU 15' · 3 × (2 km @ 97–99 % / 2' klus) · CD 10' | 4:12–4:18 | |
| **Kopce tempo** | 4–6 × 3–4 min uphill by HR 165–174 / jog down | HR, not pace | trail-friendly threshold |

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

## Race week

| Session | Structure |
|---|---|
| **Ostrenie** (3–4 days out) | WU 15' · 3 × 1 km @ race pace / 2' klus · CD 10' |
| **Predzávodný** (day before) | 20–25 min easy + mobilita + abeceda + 4–6 × 100 m rovinky, 1' pauza |
| **Závod** | create as sport `Run` with the race distance and goal pace in the description; add the event if missing |
