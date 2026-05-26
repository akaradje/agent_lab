# Agent Lab

A controlled multi-agent research/build pipeline with enforced cost limits and
human checkpoints. Six specialized agents pass structured artifacts through a
linear pipeline with a bounded QA loop and approval-gated code execution.

**Provider:** DeepSeek V4 (`deepseek-v4-pro` + `deepseek-v4-flash`) via the
OpenAI SDK. See `specs/DEEPSEEK_REFERENCE.md` for model details and pricing.

## Quick start

### Prerequisites

- Python 3.12+
- A [DeepSeek API key](https://platform.deepseek.com/api_keys)

### Setup

```
git clone <this-repo>
cd agent_lab

python -m venv .venv
.venv\Scripts\activate         # Windows
source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt

set DEEPSEEK_API_KEY=sk-...    # Windows
export DEEPSEEK_API_KEY=sk-... # macOS / Linux
```

### Your first run

```
python -m agent_lab.main --brief "Write a Python function that checks if a string is a palindrome. Include tests."
```

The pipeline will:
1. Decompose the brief into sub-goals
2. Research each sub-goal
3. Design a solution
4. Build the deliverable
5. Run QA review (up to 3 revision rounds)
6. Pause for your approval, then execute in a sandbox
7. Pause for final approval

Output is written to `run_output.json` with all artifacts and a transcript.

### Auto-approve (for automation)

```
python -m agent_lab.main --brief "..." --yes
```

The `--yes` flag auto-approves all human gates. Use only for testing or
automated runs — it skips the safety checks.

### Resume a saved run

If a run stops at a gate or after QA exhaustion, resume it from the saved
state file:

```
python -m agent_lab.main --resume run_output.json
```

This loads the previous state, shows a summary, and re-presents the
appropriate gate. Works for runs that stopped at the sandbox gate, final
gate, or `needs_human_review`.

## Pipeline stages

```
  Brief
    -> Orchestrator  (decomposes into sub-goals)
    -> Researcher     (gathers info per sub-goal)
    -> Architect      (designs the solution)
    -> Worker         (produces the deliverable)
    -> Critic         (QA review; up to 3 rounds back to Worker)
    -> Sandbox        (isolated execution; human-gated)
    -> Final output
```

Each stage appends structured output to the run state. The QA loop is
bounded at `MAX_QA_ROUNDS` (default 3) — if the Critic never approves,
the run ends with status `needs_human_review`.

## Configuration

Edit `agent_lab/config.py` to adjust:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_TOTAL_TOKENS` | 100,000 | Token ceiling per run |
| `MAX_USD` | 1.00 | Cost ceiling per run |
| `MAX_QA_ROUNDS` | 3 | Max Worker-Critic revision rounds |
| `PRICING` | per-model | USD per million tokens (input, output) |
| `AGENT_MODELS` | per-agent | Model + reasoning effort per stage |

Model routing defaults follow DeepSeek's recommendation: Flash for
lighter agents, Pro for reasoning-heavy agents (Architect, Critic).
See `specs/DEEPSEEK_REFERENCE.md` for the full routing table.

## Safety features (enforced in code)

1. **Budget ceiling** — every API call is tracked; run stops hard at the
   token or cost limit.
2. **Bounded QA loop** — Worker-Critic rounds are capped. No infinite loops.
3. **Human approval gates** — code never executes without explicit approval.
   The `--yes` flag exists only for tests.
4. **No secrets in code** — API key comes from the environment only.

These are not conventions. They are enforced by `budget.py`, `pipeline.py`,
and `sandbox.py`. Changes that weaken them are blocked by design.

## Project structure

```
agent_lab/           # Source
├── main.py          # CLI entry point
├── config.py        # Settings, pricing, model routing
├── budget.py        # Token/cost tracking + ceiling enforcement
├── llm_client.py    # DeepSeek API wrapper
├── agents.py        # 6 agent classes
├── pipeline.py      # Orchestration, QA loop, gates, resume
├── sandbox.py       # Approval-gated subprocess execution
└── state.py         # Run state persistence (JSON)
specs/
├── BUILD_PLAN.md    # Phased build order with acceptance checks
├── ARCHITECTURE.md  # Module breakdown + design decisions
├── DEEPSEEK_REFERENCE.md  # Provider, models, pricing
└── prompts/         # Agent system prompts (reviewable, versioned)
tests/               # pytest suite
```

## Running tests

```
pytest                          # All unit tests (no API calls)
AGENT_LAB_LIVE_TEST=1 pytest    # Include live API e2e tests (costs money)
ruff check .                    # Lint
```

## Honest scope

Agent Lab is a **pipeline orchestration tool**, not an autonomous research
lab. It runs LLM calls in a controlled sequence with human oversight. It
does not train models, self-modify, or operate unattended. The value is
in reliability: bounded cost, reviewable output, and explicit checkpoints.
