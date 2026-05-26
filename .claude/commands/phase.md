---
description: Start the next build phase from BUILD_PLAN.md, staying strictly in scope
---

Read `specs/BUILD_PLAN.md` and identify the next unfinished phase.

Before writing any code:
1. State which phase you are starting and its acceptance check.
2. List the files you will create or change — nothing outside that list.
3. Confirm the change does not weaken any hard rule in CLAUDE.md.

Then implement ONLY that phase. Write a test for every new module.

When done:
- Run `ruff check .` and `pytest`.
- Report the acceptance check result explicitly (pass/fail).
- STOP. Do not begin the next phase.

If the phase is ambiguous or you are tempted to add something not listed
in the plan, stop and ask instead of guessing.

$ARGUMENTS
