<div align="center">

# 🧪 Agent Lab

**A controlled multi-agent pipeline that turns research briefs into reviewed, tested deliverables.**

Six specialized agents. Bounded QA loop. Human-approved code execution. No runaway costs.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![DeepSeek V4](https://img.shields.io/badge/LLM-DeepSeek%20V4-purple?logo=deepseek&logoColor=white)](https://platform.deepseek.com)
[![Tests](https://img.shields.io/badge/tests-pytest-yellow?logo=pytest&logoColor=white)](#running-tests)
[![Lint](https://img.shields.io/badge/lint-ruff-orange?logo=ruff&logoColor=white)](#running-tests)

</div>

---

## How it works

```
  📝 Brief
      │
      ▼
  ┌──────────────┐
  │ Orchestrator │  decomposes into sub-goals
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  Researcher  │  gathers & synthesizes info
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  Architect   │  designs the solution
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │   Worker     │  produces the deliverable
  └──────┬───────┘
         ▼
  ┌──────────────┐       ┌──────────┐
  │   Critic     │──────▶│  Worker  │  (up to 3 rounds)
  └──────┬───────┘       └──────────┘
         ▼
  ┌──────────────┐
  │   Sandbox    │  isolated execution · human-gated
  └──────┬───────┘
         ▼
  ✅ Final output
```

Each stage produces structured artifacts. The QA loop is **bounded** — if the Critic never approves after 3 rounds, the run ends with `needs_human_review`. No infinite loops.

---

## Quick start

### Prerequisites

- Python **3.12+**
- A [DeepSeek API key](https://platform.deepseek.com/api_keys)

### Setup

```bash
git clone https://github.com/akaradje/agent_lab.git
cd agent_lab

python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

Set your API key:

```bash
# macOS / Linux
export DEEPSEEK_API_KEY=sk-...

# Windows
set DEEPSEEK_API_KEY=sk-...
```

### Run it

```bash
python -m agent_lab.main --brief "Write a Python function that checks if a string is a palindrome. Include tests."
```

The pipeline will decompose, research, design, build, review (up to 3 QA rounds), then pause for your approval before executing in a sandbox.

**Output:** `run_output.json` — all artifacts + full transcript.

### Options

| Flag | Description |
|------|-------------|
| `--yes` | Auto-approve all human gates (for testing / automation) |
| `--resume <file>` | Resume a saved run from its state file |

```bash
# Auto-approve (testing only)
python -m agent_lab.main --brief "..." --yes

# Resume a stopped run
python -m agent_lab.main --resume run_output.json
```

---

## Safety features

These are **enforced in code**, not conventions:

| # | Feature | Enforced by |
|---|---------|-------------|
| 🔒 | **Budget ceiling** — run stops at token or cost limit | `budget.py` |
| 🔁 | **Bounded QA loop** — Worker↔Critic capped at 3 rounds | `pipeline.py` |
| 🛡️ | **Human approval gates** — code never auto-executes | `sandbox.py` |
| 🔑 | **No secrets in code** — API key from env var only | `config.py` |

Changes that weaken any of these are blocked by design.

---

## Configuration

Edit `agent_lab/config.py`:

| Setting | Default | What it does |
|---------|---------|-------------|
| `MAX_TOTAL_TOKENS` | 250,000 | Token ceiling per run (soft warning at 80%) |
| `MAX_USD` | 1.00 | Cost ceiling per run (USD) |
| `MAX_QA_ROUNDS` | 3 | Max Worker↔Critic revision rounds |
| `PRICING` | per-model | USD per million tokens (input, output) |
| `AGENT_MODELS` | per-agent | Model + reasoning effort per stage |

### Model routing

| Agent | Model | Reasoning | Why |
|-------|-------|-----------|-----|
| Orchestrator | `deepseek-v4-flash` | low | Light planning |
| Researcher | `deepseek-v4-flash` | high | Info synthesis |
| Architect | `deepseek-v4-pro` | high | Hard reasoning — design |
| Worker | `deepseek-v4-flash` | high | Production |
| Critic | `deepseek-v4-pro` | high | Hard reasoning — adversarial review |
| Sandbox | `deepseek-v4-flash` | low | Summarization |

DeepSeek recommends defaulting to Flash and escalating to Pro only where it measurably helps. See [`specs/DEEPSEEK_REFERENCE.md`](specs/DEEPSEEK_REFERENCE.md) for pricing details.

---

## Project structure

```
agent_lab/                  # Source
├── main.py                 #   CLI entry point
├── config.py               #   Settings, pricing, model routing
├── budget.py               #   Token/cost tracking + ceiling enforcement
├── llm_client.py           #   DeepSeek API wrapper (OpenAI SDK)
├── agents.py               #   6 agent classes
├── pipeline.py             #   Orchestration, QA loop, gates, resume
├── sandbox.py              #   Approval-gated subprocess execution
└── state.py                #   Run state persistence (JSON)

specs/                      # Design docs
├── ARCHITECTURE.md         #   Module breakdown + design decisions
├── BUILD_PLAN.md           #   Phased build order with acceptance checks
├── DEEPSEEK_REFERENCE.md   #   Provider, models, pricing
└── prompts/                #   Agent system prompts (versioned)

tests/                      # pytest suite
```

---

## Running tests

```bash
# Unit tests (no API calls — fast, free)
pytest

# End-to-end tests (calls DeepSeek API — costs money)
AGENT_LAB_LIVE_TEST=1 pytest

# Lint
ruff check .
```

---

## Honest scope

Agent Lab is a **pipeline orchestration tool**, not an autonomous research lab. It runs LLM calls in a controlled sequence with human oversight. It does not train models, self-modify, or operate unattended.

The value is in **reliability**: bounded cost, reviewable output, and explicit checkpoints.

---

## License

[MIT](LICENSE) — use it however you want.

---

<div align="center">

**[Architecture](specs/ARCHITECTURE.md)** · **[Build Plan](specs/BUILD_PLAN.md)** · **[DeepSeek Reference](specs/DEEPSEEK_REFERENCE.md)** · **[Agent Prompts](specs/prompts/)**

</div>
