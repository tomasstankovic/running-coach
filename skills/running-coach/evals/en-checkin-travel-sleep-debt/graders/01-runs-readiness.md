---
type: llm
focus: trace
weight: 1
arm: with-only
---

The coach runs `scripts/readiness.py` on metrics.json and its output shows the sleep debt (several of the last nights under 6 h). Passing the travel as `--stress 4` or `--stress 5` is the expected way to count it; running without `--stress` still passes if the answer counts the travel as a separate sign on top of the script's result.
