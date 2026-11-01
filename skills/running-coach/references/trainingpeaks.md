# Working with TrainingPeaks

The tools come from the `trainingpeaks-mcp` server (github.com/JamsusMaximus/trainingpeaks-mcp). It
runs **locally over stdio**, so it's available in Claude Desktop, Claude Code and Cowork, not in the
claude.ai web or mobile apps. Tool names can carry a client prefix (e.g. `mcp__trainingpeaks__tp_get_workouts`);
match on the `tp_…` suffix.

If a call fails with an auth error, run `tp_auth_status`, then `tp_refresh_auth`. If that fails too,
tell the athlete to run `tp-mcp auth` again. The session cookie expires every few weeks.

## Reading

| Tool | Use | Notes |
|---|---|---|
| `tp_get_athlete_settings` | threshold pace, LTHR, max HR, zones | `speedZones[0].threshold` is m/s → pace = 1000 / speed |
| `tp_get_fitness` | CTL / ATL / TSB per day | `days: 90` |
| `tp_get_workouts` | list of planned + completed workouts | max 90 days per call; `type: all`; durations are in **hours** |
| `tp_get_workout` | details: structure, avg HR, RPE, feeling, comments; `metrics.elevation_gain`, `metrics.avg_power` | use for key sessions; the only source of elevation (the list has none) |
| `tp_analyze_workout` | laps (Active/Rest from the structure), totals incl. NGP, Pa:Hr decoupling and EF, plus a 1,000-point time series saved to `data_file` | large response: only for 1–2 key sessions; pass `data_file` to `scripts/analyze_session.py`. Contains GPS positions: don't copy it anywhere. |
| `tp_get_weekly_summary` | weekly totals | quick history |
| `tp_get_focus_event`, `tp_get_next_event`, `tp_get_events` | goal race and other races | |
| `tp_get_atp` | the runner's Annual Training Plan: weekly TSS target, period, races | read-only through the MCP, max 90 days per call; ask whether to respect it (`season.md` §3) |
| `tp_get_metrics` | HRV, sleep, resting HR, weight (if logged) | |
| `tp_get_peaks`, `tp_get_workout_prs` | best efforts (`speed5K`, `speed10K`, `speedHalfMarathon`, `speedMarathon`; `value` in m/s) | threshold sanity check; results for `forecast.py` |

Strength workouts don't show up in `tp_get_workouts`. Use `tp_get_strength_workouts` if strength
training matters for the plan.

## Writing (only after the athlete confirms)

| Tool | Use |
|---|---|
| `tp_validate_structure` | validate a structure, get duration + estimated IF/TSS. Always run before creating. |
| `tp_create_workout` | create a planned workout |
| `tp_update_workout` | change a planned workout (moving a day, editing the description) |
| `tp_delete_workout` | remove a *planned* workout. Ask first; never delete completed ones. |
| `tp_create_event` | add a race, with `priority` A, B or C (defaults to C) |
| `tp_update_speed_zones`, `tp_update_hr_zones` | update threshold. Ask first. Test-based zone methods return `TEST_BASED_METHOD` and must be changed in the TP web UI. |

### tp_create_workout for a run

`tp_create_workout` takes either a simplified `structure` (time steps only) or TP's native
`structured_workout` (time *or* distance steps: `"unit": "meter"` with
`"primaryLengthMetric": "distance"`). `scripts/tp_structure.py` builds the native one from a spec,
in km or time, plus a time-equivalent `structure` for validation:

```bash
python scripts/tp_structure.py spec.json --out workout.json
```

```json
{
  "date": "2026-11-04",
  "sport": "Run",
  "title": "Cruise intervaly 6× 1 km @ prah",
  "description": "…",
  "structured_workout": { …from workout.json… },
  "duration_minutes": 55,
  "distance_km": 11,
  "tss_planned": 70
}
```

- `tp_validate_structure` reads only the simplified format, so validate `workout.json`'s
  `structure` and take `tss_planned` from it.
- With `structured_workout`, TP doesn't compute the duration, so always pass `duration_minutes`
  and `distance_km` from the script.
- Intensity metric: `percentOfThresholdPace` (% of threshold **speed**: faster = higher; use
  `scripts/paces.py convert`), `percentOfThresholdHr` (% LTHR, for hilly ground) or
  `percentOfFtp` (running power vs. running FTP). All three validate.
- A time-based runner can still pass the simplified `structure` directly, as before.
- Take `tss_planned` from `tp_validate_structure`. Its estimate for long easy runs may be higher than
  the athlete's real rTSS. That's fine; mention it if it's far off from similar past runs.
- One workout per call. Create the week's workouts in parallel calls only after checking the
  target days are free.

## Duplicates and existing plans

Before writing, list `tp_get_workouts` for the target range with `type: planned`. If something is
already planned there, show it and ask: replace (delete + create), keep, or merge. Never modify a
workout that already has actual data (`duration_actual` set).

## Profile, metrics and strength

| Tool | Use |
|---|---|
| `tp_list_notes` / `tp_get_note` | find the `Running coach profile` note (max 90-day range per call) |
| `tp_create_note` / `tp_update_note` | save or update the profile. On update also set `date` to today, so the note stays in the 90-day window. Ask before the first save. |
| `tp_get_metrics` | HRV, resting HR ("Pulse"), sleep, Body Battery, stress (often synced from Garmin). The response is large, so request 21–28 days and pass the saved JSON to `scripts/readiness.py` rather than reading it day by day. |
| `tp_get_strength_workouts` / `tp_get_strength_workout` | existing strength sessions (separate from `tp_get_workouts`) |
| `tp_search_exercises` | exercise library IDs and each exercise's native parameters |
| `tp_create_strength_workout` | create a strength session (see `strength.md`) |

`tp_get_athlete_settings` also returns personal data (email, phone, calendar keys). Save only the
`heartRateZones` and `speedZones` blocks when writing zones to a file.
