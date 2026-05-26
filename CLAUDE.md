# CLAUDE.md — Agent Lab

> This file is loaded into context at the start of every Claude Code session.
> Keep it short and skimmable. Detailed specs live in `specs/` and are referenced
> on demand — do not paste their contents here.

## What this project is

A **multi-agent pipeline** that runs a 6-stage research/build workflow.
Each stage is one agent with a narrow role. Agents pass structured artifacts
down a pipeline. Cost controls and human checkpoints are enforced in code.

This is a **pipeline orchestration tool**, not an autonomous research lab.
It does not train models. It runs LLM API calls in a controlled sequence.
If a request implies open-ended autonomy ("let it research on its own"),
stop and ask — that is out of scope.

## Tech stack

- Python 3.12, standard library first. Add dependencies only when justified.
- LLM provider is **DeepSeek V4**. Call it via the `openai` SDK pointed at
  `https://api.deepseek.com` (DeepSeek supports the OpenAI ChatCompletions
  API — only `base_url` and `model` change). No other LLM client unless asked.
- Two models in use: `deepseek-v4-flash` (cheap, fast) for light agents and
  `deepseek-v4-pro` (stronger reasoning) for the agents that need it. Which
  agent uses which is set in `config.py`, never hardcoded in agent code.
- `pytest` for tests. `ruff` for lint/format.
- No web framework, no database in v1. State is JSON files on disk.

## Repository layout

@specs/ARCHITECTURE.md describes the full module breakdown.
@specs/DEEPSEEK_REFERENCE.md has provider/model/pricing facts.
Source lives in `agent_lab/`. Specs live in `specs/`. Tests in `tests/`.

## Hard rules — these are enforced in code, not optional

1. **Budget**: every LLM call goes through `budget.py`. No direct SDK calls
   from agent code. When the token/cost ceiling is hit, the run STOPS.
2. **Iteration cap**: the QA <-> worker correction loop has a max-rounds limit.
   Never write an unbounded `while` loop around an LLM call.
3. **Human approval**: any code execution goes through `sandbox.py`, which
   requires explicit approval before running. Never auto-run generated code.
4. **No secrets in code**: the API key comes from the `DEEPSEEK_API_KEY`
   environment variable only. Never hardcode a key, never commit `.env`.

If a change would weaken rules 1-4, do not make it. Flag it and ask first.

## Workflow for this project

- Work one phase at a time. Phases are defined in @specs/BUILD_PLAN.md.
- After finishing a phase: run `ruff check .` and `pytest`, then stop and
  summarize what changed. Do not start the next phase without being asked.
- Write a test alongside every new module. A module with no test is unfinished.
- Keep agent prompts in `specs/prompts/`, not inline in Python, so they can
  be reviewed and versioned separately.

## Code style

- Type hints on all function signatures.
- Docstrings explain *why*, not *what*.
- Small functions. If a function exceeds ~40 lines, consider splitting.
- Errors are explicit: raise typed exceptions, never silently swallow.

## What "done" means for a phase

- Code runs, lint passes, tests pass.
- The phase's acceptance check in BUILD_PLAN.md is met.
- No hard rule above was weakened.
