---
type: llm
focus: trace
weight: 1
---

After the runner's correction, the coach runs `scripts/check_week.py` on the new week, and the week it passes in is the corrected one: runs only on Monday, Tuesday, Thursday, Saturday or Sunday, with the same distances as the table in the final answer (not the earlier 3-run week, not 6 runs or 65 km). The totals and warnings in the final answer agree with what the script printed.
