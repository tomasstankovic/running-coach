# Working with Strava

The official Strava connector (claude.ai → Settings → Connectors → Strava, URL
`https://mcp.strava.com/mcp`) works on web, desktop and mobile. Each runner connects their own
account. It is **read-only**: it can't create planned workouts, so the plan is delivered as text
plus an `.ics` file (`scripts/export_ics.py`).

Tool names can carry a client prefix. Match on the suffix.

| Tool | Use |
|---|---|
| `get_athlete_profile` | name, units, basic profile |
| `get_athlete_zones` | HR zones the runner set in Strava (often max-HR based; treat LTHR from them as an estimate) |
| `list_activities` | recent activities: date, type, distance, moving time, avg HR, elevation |
| `get_activity_performance` | per-activity detail for key sessions: laps/splits, pace, HR |
| `get_activity_streams` | raw HR/pace streams when you need rep-by-rep analysis |
| `get_gear` | shoe mileage, if relevant |

## What Strava doesn't give you, and how to fill it

- **Threshold pace**: estimate it from a recent race or a hard 20–30 min effort found in the
  activities (`paces.py race`), or ask the runner. Prefer flat road efforts; trail and hilly races
  understate fitness.
- **LTHR**: use the runner's value if they know it. Otherwise take the average HR of the last
  20 min of a hard ~30 min effort, or ~89–90 % of max HR. Say that it's an estimate.
- **CTL/ATL/TSB**: not available. Use the weekly time and distance trend from `list_activities`
  instead (`check_week.py` computes it).
- **Planned workouts and past coaching decisions**: Strava has no plan. Ask the runner what was
  planned last week if a review needs it, or use the plan from earlier in the conversation.

## Units

`list_activities` returns distance in metres and times in seconds. `check_week.py` accepts these
fields directly (`distance`, `moving_time`, `start_date_local`, `sport_type`). Non-running
activities (rides, swims, walks) are excluded from running volume, but mention significant
cross-training when judging fatigue.
