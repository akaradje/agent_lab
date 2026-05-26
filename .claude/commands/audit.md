---
description: Audit recent changes for scope drift and hard-rule violations
---

Review the current state of the repository against `specs/BUILD_PLAN.md`
and `CLAUDE.md`. Check specifically:

1. **Scope**: does anything implemented go beyond the current phase, or
   appear in the "Out of scope for v1" list? Flag it.
2. **Hard rule 1 (budget)**: does any agent code call the OpenAI/DeepSeek SDK
   directly instead of going through the budgeted `LLMClient`?
3. **Hard rule 2 (iteration cap)**: is there any `while` loop around an LLM
   call without a bounded counter?
4. **Hard rule 3 (approval)**: can any code path execute generated code
   without a human approval step?
5. **Hard rule 4 (secrets)**: any hardcoded keys, or `.env` not gitignored?
6. **Tests**: does every module under `agent_lab/` have a corresponding test?

Report findings as a list. For each problem, give the file, the line, and
the minimal fix. Do not fix anything yet — just report.

$ARGUMENTS
