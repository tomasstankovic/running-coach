# Running Coach for Claude

A Claude skill that coaches your running week to week. It gets to know you first (goals,
availability, history, an honest assessment of where you are), then plans the next week, builds
a block toward a race, reviews how last week went, tells you each morning whether to train as
planned, adds strength sessions for runners, and prepares race-day pacing and fuelling.

What makes it different from asking Claude for "a training plan":

- **Your data first.** On onboarding it studies 12–24 months of history (seasons, peaks, breaks,
  races, what worked), not just the last few weeks. Then it reads your recent training, fitness
  trend and zones before every plan, and honours decisions from earlier weeks.
- **Asks, doesn't impose.** Strength training (gym, home or bodyweight) and threshold tests are
  discussed with you: why, what the options are, and what you prefer.
- **Computed, not guessed.** Paces, heart-rate zones and % of threshold come from a script, so
  they're the same every week.
- **Checked before you see it.** A load checker flags volume jumps above ~10 %, back-to-back hard
  days, an oversized long run, too much intensity and missing deload weeks.
- **Lands where you train.** With TrainingPeaks it writes structured workouts to your calendar
  (after you confirm), so they sync to your watch. Without it, you get an `.ics` file for
  Google/Apple/Outlook calendar.

- **Remembers you.** Your profile (goals, availability, injuries, decisions from past reviews)
  is saved as a TrainingPeaks note or a file in your Claude Project, and read at the start of
  every conversation.
- **Daily check-in.** Compares today's HRV, resting HR and sleep with your own baseline (green,
  amber or red) and adjusts today's session.

It replies in your language (tested in English and Slovak).

## Install

**claude.ai (web, desktop, mobile):** download `running-coach.zip` from the
[latest release](https://github.com/tomasstankovic/running-coach/releases/latest), then go to *Settings → Capabilities*, enable *Code
execution*, and upload the zip under *Skills*.

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

## What's inside

```
skills/running-coach/
├── SKILL.md                    modes and the core workflow
├── references/
│   ├── onboarding.md           questionnaire, history assessment, athlete profile
│   ├── methodology.md          intensity, progression, periodization, thresholds, illness
│   ├── workouts.md             session library with TrainingPeaks structures
│   ├── strength.md             strength for runners: placement, phases, TP strength workouts
│   ├── checkin-and-race.md     daily readiness check-in, race pacing and fuelling
│   ├── trainingpeaks.md        TP tools, structure format, pitfalls
│   └── strava.md               Strava tools and how to fill what Strava lacks
└── scripts/
    ├── paces.py                zones, pace ↔ % threshold, threshold from a race, predictions, splits
    ├── check_week.py           load-progression checks (TP, Strava, or weekly totals)
    ├── readiness.py            HRV / resting HR / sleep vs. personal baseline
    ├── history_summary.py      1–2 years → seasons, peaks, breaks, likely races, best efforts
    └── export_ics.py           plan → calendar file
```

## Releasing a new version

Bump `version` in `.claude-plugin/plugin.json` (semver) with every change you want users to
receive. Installed copies update only when the version changes. Then push to `main`.

## Disclaimer

This is a coaching aid for healthy recreational runners, not medical advice. Pain that changes
your stride, chest pain, dizziness or unusual heart-rate responses: stop and see a professional.

---

## Po slovensky

Skill pre Claude, ktorý ti plánuje beh týždeň po týždni. Naplánuje týždeň, pripraví blok k
závodu, vyhodnotí uplynulý týždeň a upraví plán, keď ochorieš alebo vynecháš tréning. Na
začiatku si ťa „vyspovedá“ (ciele, čas, história, posúdenie stavu) a uloží si tvoj profil.
Vie ranný check-in podľa HRV a spánku, silové tréningy pre bežcov aj plán na závod. Tempá a
zóny počíta skriptom a každý týždeň pred zobrazením skontroluje (nárast objemu, tvrdé dni po
sebe, dlhý beh, odľahčovací týždeň). S TrainingPeaks zapíše štruktúrované tréningy do kalendára
(až po tvojom súhlase). So Stravou alebo bez dát dostaneš plán ako text a `.ics` súbor do
kalendára.

**Inštalácia v claude.ai:** stiahni `running-coach.zip` z releases, zapni *Code execution* v
*Settings → Capabilities* a zip nahraj v sekcii *Skills*.

## License

MIT
