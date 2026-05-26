# Claude Code Setup Guide — Agent Lab

How to use this package to build the project in Claude Code without drift.

## What's in this package

```
agent_lab/
├── CLAUDE.md                  # Loaded every session. Conventions + hard rules.
├── specs/
│   ├── ARCHITECTURE.md        # Module breakdown + design decisions
│   ├── BUILD_PLAN.md          # Phased build order with acceptance checks
│   ├── AGENT_ROLES.md         # The 6 agents' roles + output formats
│   ├── DEEPSEEK_REFERENCE.md  # Provider, models, pricing, routing table
│   └── prompts/               # (you create these during the build)
├── .claude/
│   ├── commands/
│   │   ├── phase.md           # /phase  — start next build phase in scope
│   │   └── audit.md           # /audit  — scan for drift + rule violations
│   └── skills/
│       └── add-agent/SKILL.md # Skill: correct way to add a pipeline agent
└── docs/SETUP.md              # This file
```

## First-time setup

1. Put this folder in a fresh git repo: `git init && git add . && git commit -m "spec"`.
2. Install Claude Code and open it in the project root.
3. Confirm Claude Code picks up `CLAUDE.md` — it loads files from the working
   directory upward at session start.
4. Set your key in the environment, never in a file:
   `export DEEPSEEK_API_KEY=...` (the build will read it from env).

## The build loop — repeat per phase

1. Start a session. Run `/phase` — it reads BUILD_PLAN.md and starts the next
   unfinished phase, in scope.
2. Let it implement, lint, and test that one phase.
3. Run `/audit` to catch any scope drift or hard-rule violation.
4. Review the diff yourself. Commit.
5. Run `/clear` to reset context before the next phase. Phases are designed
   to be independent so a cleared context is fine — and keeps cost down.

Do not try to build multiple phases in one session. A long session
accumulates context, drifts, and costs more.

## Staying on-track — why each piece exists

- **CLAUDE.md** carries the *conventions* and a short statement of scope.
  It is guidance, not enforcement — so the things that truly must not break
  (budget, loop caps, approval) are also written as enforced Python, per the
  hard-rules section.
- **BUILD_PLAN.md** is the anti-drift backbone: one phase at a time, each
  with a concrete acceptance check, plus an explicit out-of-scope list.
- **/phase** forces Claude Code to declare scope before coding and stop after.
- **/audit** is your periodic check that nothing crept in.
- **The add-agent skill** keeps future agent work consistent with the rules.

## Keeping cost under control

- `/clear` between phases — the single biggest token saver.
- The pipeline's own `budget.py` caps runtime API spend; that is separate
  from what you spend *building* the project in Claude Code.
- If you have `ccusage` or similar, watch per-session cost; long sessions
  are where it grows.

## Honest expectations

This package builds a solid, controlled multi-agent pipeline. It will not,
on its own, become an autonomous research lab — that part of the original
blueprint is a direction to steer in, not a feature to mark complete. The
value here is reliability: bounded cost, human checkpoints, reviewable
output. Build that well first; ambitious autonomy can come later, carefully.

## If Claude Code drifts anyway

- It invents scope -> point it back to BUILD_PLAN.md's out-of-scope list.
- It writes an unbounded loop -> rule 2; the loop must be capped.
- An agent calls the SDK directly -> rule 1; route through `LLMClient`.
- It bundles multiple phases -> `/clear` and restart with `/phase`.
