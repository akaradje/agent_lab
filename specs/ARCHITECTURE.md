# ARCHITECTURE.md

## Purpose

A 6-agent pipeline that takes a research/build brief and produces a reviewed,
tested deliverable. Maps directly to the original blueprint's org chart, but
reframed as software components rather than "staff".

## The pipeline

```
  Human brief
      |
      v
  [1] Orchestrator  -- decomposes brief into sub-goals, plans the run
      |
      v
  [2] Researcher    -- gathers/synthesizes relevant info for each sub-goal
      |
      v
  [3] Architect     -- designs the solution: prompts, workflow, structure
      |
      v
  [4] Worker        -- produces the actual deliverable (code/text/spec)
      |
      v
  [5] Critic (QA)   -- reviews for errors; can send work back to Worker
      |   ^______________|  (bounded loop: MAX_QA_ROUNDS)
      v
  [6] Sandbox       -- runs/validates the deliverable; HUMAN-APPROVED only
      |
      v
  Human final approval
```

## Module breakdown

| File           | Responsibility                                              |
|----------------|-------------------------------------------------------------|
| `config.py`    | Settings: model names, budget ceilings, iteration caps.     |
| `llm_client.py`| Thin wrapper over the DeepSeek API (via the OpenAI SDK). Single place the API is called. |
| `budget.py`    | Token + cost accounting. Raises `BudgetExceeded` at ceiling.|
| `agents.py`    | The 6 agent classes. Each has one `run()` method.           |
| `pipeline.py`  | Wires agents together. Owns the QA loop and approval gates. |
| `sandbox.py`   | Isolated code execution. Approval-gated.                    |
| `state.py`     | Run state: artifacts, transcript, JSON persistence.         |
| `main.py`      | CLI entry point.                                            |

## Key design decisions

**Agents don't call the API directly.** Every agent receives an `LLMClient`
that is already wrapped by the budget tracker. This makes rule 1 unbypassable.

**Mixed-model routing.** The provider is DeepSeek V4, which ships two models
at roughly a 3x price difference. Light agents (Orchestrator, Sandbox
summarizer) run on `deepseek-v4-flash`; reasoning-heavy agents (Architect,
Critic) run on `deepseek-v4-pro`. DeepSeek's own guidance is to default to
Flash and escalate to Pro only where evaluation shows Flash is insufficient.
The per-agent model + reasoning mode is a table in `config.py` — agent code
never names a model itself.

**Reasoning modes.** V4 supports Non-think / Think High / Think Max via the
`reasoning_effort` parameter. `config.py` sets the mode per agent: planning
and summarizing use Non-think; design and review use Think High.

**The QA loop is bounded.** `pipeline.py` runs Worker -> Critic at most
`MAX_QA_ROUNDS` times. If the Critic still rejects after the cap, the run
ends with status `needs_human_review`. This prevents the most common failure
mode of multi-agent systems: two agents disagreeing forever.

**The Critic returns structured verdicts**, not prose. A verdict is
`{approved: bool, issues: [...]}`. Prose reviews are too easy to "mostly
approve"; structure forces a real decision.

**Sandbox is opt-in and gated.** In v1 the Sandbox never runs code without a
human typing `approve`. Generated code is shown first. Execution happens in a
subprocess with no network and a wall-clock timeout. A container is better;
that is a documented Phase 6 upgrade, not v1.

**State is a plain dict persisted to JSON.** Every agent appends its output
to `state["artifacts"]` and a log line to `state["transcript"]`. The run can
be inspected or resumed from the JSON file.

## Honest limitations (read before building)

- A Critic agent built from the same model family tends to be agreeable.
  Mitigation: give it a strict checklist and structured output, and treat
  `needs_human_review` as a normal, frequent outcome — not a failure.
- "Innovation" is not an output this system can guarantee. It produces
  *structured, reviewed work*. Quality depends on the brief and the prompts.
- Cost scales with pipeline depth. A single run is 6+ LLM calls minimum,
  more with QA rounds. The budget ceiling is the safety net.
