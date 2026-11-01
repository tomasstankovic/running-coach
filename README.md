<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-wordmark-dark.svg">
    <img src="assets/logo-wordmark-light.svg" width="330" alt="Running Coach">
  </picture>
</p>

<p align="center">
  <b>Running Coach for Claude</b>: a running coach that knows your history, tells you the truth, and puts the plan on your watch.<br>
  Season plans · weekly plans · HRV check-ins · session analysis · strength · race day<br>
  TrainingPeaks · Strava · or just a conversation
</p>

<p align="center">
  <a href="https://github.com/tomasstankovic/running-coach/actions/workflows/check.yml"><img src="https://github.com/tomasstankovic/running-coach/actions/workflows/check.yml/badge.svg" alt="checks"></a>
  <a href="https://github.com/tomasstankovic/running-coach/releases/latest"><img src="https://img.shields.io/github/v/release/tomasstankovic/running-coach" alt="latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
</p>

---

> **You:** I want a half marathon under 1:30 in April. I can run once a week.
>
> **Coach:** 1:30 means 4:16/km. Your recent 10k (48:30) points to about 1:47, so that's a 16 %
> jump, and one run a week won't get you there; 1:30 usually takes 5–6 runs and 55–75 km a week.
> Three honest options: aim for **1:42–1:45** this spring on 4 runs a week, keep 1:30 as a
> **next-season** goal, or tell me what time you could add. What sounds right?

Most "AI training plans" are a fresh guess every time. This one works like a coach:

- **Gets to know you first.** Goals, the time you really have, which days suit you, injuries,
  and 12–24 months of your history: seasons, peaks, breaks, races, what worked.
- **Honest, not agreeable.** If the goal doesn't match your time or current level, it says so
  with numbers and offers real alternatives. Then you decide together.
- **Asks, doesn't impose.** Strength training (gym, home or bodyweight) and threshold tests are
  discussed with you: why, what the options are, and what you prefer.
- **The whole season on one page.** A rough week-by-week plan to your A race (phases, volume,
  long run, key session), with B and C races built in. It lives on a page with a fixed link that
  shows plan vs. actual and every change. Illness, a work deadline or a missed week re-plans the
  rest by clear rules, and the weekly review can run by itself every Sunday.
- **Your units, your ground.** Kilometres or minutes, as you prefer. It reads how hilly your runs
  are, asks where you can run fast, and steers by pace on the flat and by heart rate on hills.
  "This week I'm in the mountains" reshapes the rest of the week.
- **Grounded in research.** Load limits from a 5,200-runner injury study (no single run more
  than 10 % longer than your longest in the last month), HRV-guided readiness, evidence-based
  tapers, strength, fuelling and heat guidance, each rule tagged with its source and how strong
  the evidence is.
- **Reads your sessions like a coach.** Rep-by-rep evenness and fade, heart rate vs. threshold,
  aerobic decoupling and efficiency on long runs, and marathon predictions that account for your
  weekly volume.
- **Knows what you could run.** Current form over 5 km, 10 km, half and marathon, and a forecast
  for each of your races, from your recent races, threshold, weekly volume, your plan and your own
  past results, adjusted for course and heat. Ranges, not wishful single numbers; the plan page
  shows how each forecast moves week by week, and it tells you when a goal drifts out of reach.
- **Computed, not guessed.** Paces, heart-rate zones, race predictions and splits come from
  scripts, so they're the same every week.
- **Checked before you see it.** A load checker flags volume jumps above ~10 %, back-to-back hard
  days, an oversized long run, too much intensity and missing deload weeks.
- **Remembers you.** Your profile (goals, weekly template, injuries, decisions from past reviews)
  is saved as a TrainingPeaks note or a file in your Claude Project.
- **Morning check-in.** Compares today's HRV, resting HR and sleep with your own baseline (green,
  amber or red) and adjusts today's session.
- **Lands where you train.** With TrainingPeaks it writes structured workouts and strength sessions
  to your calendar (after you confirm), so they sync to your watch. Without it, you get an `.ics`
  file for Google/Apple/Outlook calendar.

It replies in your language (tested in English and Slovak).

<p align="center"><img src="docs/img/plan-page.jpg" width="720" alt="Season plan page: phases, planned and actual weekly volume, races"></p>

More in **[examples](docs/examples.md)**: a week stopped by the load check, an interval session
read rep by rep, a morning check-in, a marathon prediction. What changed when:
**[changelog](CHANGELOG.md)**.

## Install

**Claude chat and Cowork (web, desktop):** open *Customize → Plugins*, click *Add → Add
marketplace → Add from a repository*, enter `tomasstankovic/running-coach`, then add the
*Running Coach* plugin. New versions come from this repository; if one doesn't show up, use
*Update* on the marketplace.

**claude.ai without plugins:** download `running-coach.zip` from the
[latest release](https://github.com/tomasstankovic/running-coach/releases/latest), enable *Code
execution* in *Settings → Capabilities*, and upload the zip under *Skills*. Upload the new zip
again for each new version.

**Claude Code:** at the prompt of a terminal session:

```
/plugin install running-coach --marketplace tomasstankovic/running-coach
```

From a shell:

```bash
claude plugin install running-coach --marketplace tomasstankovic/running-coach
```

In the Claude desktop app (Code tab): click **+** next to the prompt box, then *Plugins → Add
marketplace* with `tomasstankovic/running-coach`, then *Add plugin*.

## Connect your data (optional, but recommended)

| Source | Where it works | What you get |
|---|---|---|
| [trainingpeaks-mcp](https://github.com/JamsusMaximus/trainingpeaks-mcp) | Claude Desktop, Claude Code (runs locally) | full mode: reads zones, CTL/ATL/TSB, planned + completed workouts; writes structured workouts to your calendar |
| Strava connector (*Settings → Connectors → Strava*) | web, desktop, mobile | reads completed activities and HR zones; plan delivered as text + `.ics` |
| nothing | everywhere | asks a few questions (recent race, weekly volume, goal), plan as text + `.ics` |

A note on trainingpeaks-mcp: it's a community project that uses your TrainingPeaks session cookie,
which gives full access to your account. Pin a version you've looked at, and keep it local. The
skill never writes, changes or deletes anything in TrainingPeaks without your explicit yes.

**Privacy.** The skill itself collects nothing and sends nothing anywhere. Its scripts run
locally (Python standard library only), make no network calls, and work only on the data
Claude passes them. Your training data reaches Claude only through the connectors you choose to
connect.

## Try it

- "Plan my next week. I can run Tue, Wed, Fri, Sat and Sun."
- "Build me a half marathon block for 12 April, goal 1:35."
- "How did last week go?"
- "I've had a cold since Tuesday. Adjust the rest of the week."
- "Slept 5 hours, intervals are planned today. Should I go?"
- "Add two strength sessions a week, I have a kettlebell at home."
- "Race plan for Sunday's half: pacing and what to eat."
- "I'm in the mountains until Sunday. Adjust the rest of the week."
- "Plan my season up to the marathon in April; there's a half in March."
- "Work is crazy for the next two weeks."

## What's inside

```
skills/running-coach/
├── SKILL.md                    modes and the core workflow
├── assets/
│   └── season-plan.html        the season plan page (published once, then updated in place)
├── evals/                      8 test cases (claude plugin eval): load rules, check-ins, pushback
├── references/
│   ├── onboarding.md           questionnaire, history assessment, athlete profile
│   ├── season.md               season plan, races A/B/C, re-planning rules, plan page, weekly review
│   ├── methodology.md          intensity, progression, periodization, thresholds, illness, age, health
│   ├── analysis.md             reading a session: reps, decoupling, efficiency, race predictions
│   ├── sources.md              the research behind each rule, with evidence strength
│   ├── workouts.md             session library with TrainingPeaks structures
│   ├── strength.md             strength for runners: placement, phases, TP strength workouts
│   ├── checkin-and-race.md     daily readiness check-in, race pacing and fuelling
│   ├── trainingpeaks.md        TP tools, structure format, pitfalls
│   └── strava.md               Strava tools and how to fill what Strava lacks
└── scripts/
    ├── paces.py                zones, pace ↔ % threshold, threshold from a race, predictions
    │                           (incl. volume-aware marathon models), splits
    ├── check_week.py           load-progression checks (TP, Strava, or weekly totals)
    ├── readiness.py            HRV 7-day trend / resting HR / sleep vs. personal baseline
    ├── analyze_session.py      one session from TrainingPeaks → reps, drift, efficiency
    ├── forecast.py             current form over 5k–marathon + race-day forecast per race
    ├── history_summary.py      1–2 years → seasons, peaks, breaks, likely races, best efforts
    ├── season_plan.py          rough season plan, re-planning, actuals, export to the plan page
    ├── page_docs.py            any list of rows → plan page database writes
    ├── terrain.py              elevation gain per km → flat / rolling / hilly / mountain
    ├── tp_structure.py         session → TrainingPeaks structure in km or time
    └── export_ics.py           plan → calendar file
```

## Releasing a new version

Run `python3 tests/check_skill.py` and `python3 -m unittest discover -s tests` (CI runs both on
every push: description length and YAML, referenced files, source tags, version, and behaviour
tests of every script on fictional data). For coaching behaviour, run the eval cases from
`skills/running-coach` (real, billed model runs):

```bash
claude plugin eval . --scaffold --allow-tools Bash Write Edit --runs 1
```

Add an entry to `CHANGELOG.md`. The release ZIP leaves `evals/` out. Bump `version` in `.claude-plugin/plugin.json` (semver)
with every change you want users to receive; installed copies update only when the version
changes. Then push to `main`.

## Disclaimer

This is a coaching aid for healthy recreational runners, not medical advice. Pain that changes
your stride, chest pain, dizziness or unusual heart-rate responses: stop and see a professional.

## License

MIT
