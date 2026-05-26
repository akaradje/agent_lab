# BUILD_PLAN.md

Build in order. Do ONE phase per Claude Code session (or per `/clear`).
After each phase: run lint + tests, summarize, then STOP.

Each phase below has an **acceptance check**. The phase is not done until
that check passes.

---

## Phase 0 — Scaffold

Create the package skeleton and tooling.

- `agent_lab/__init__.py`, empty module files for each component.
- `requirements.txt`: `openai`, `pytest`, `ruff`.
- `pyproject.toml` with ruff config.
- `.env.example` (key name only, no value). `.gitignore` includes `.env`.
- `tests/` with one trivial passing test to prove pytest runs.

**Acceptance:** `pip install -r requirements.txt`, `ruff check .`, and
`pytest` all succeed on a fresh clone.

---

## Phase 1 — Budget + LLM client

The safety core. Build this before any agent.

- `config.py`:
  - `MAX_TOTAL_TOKENS`, `MAX_USD`, `MAX_QA_ROUNDS`.
  - `PRICING`: per-model input/output USD-per-million-token constants.
    NOTE: DeepSeek V4 Pro is under a promo discount until 2026-05-31; its
    price changes after that. Keep these as plain editable constants with a
    comment, so the user updates one place when pricing moves.
  - `AGENT_MODELS`: a table mapping each agent name to `(model,
    reasoning_effort)`. Defaults: Orchestrator + Sandbox -> `deepseek-v4-flash`,
    Non-think; Researcher + Worker -> `deepseek-v4-flash`, Think High;
    Architect + Critic -> `deepseek-v4-pro`, Think High.
- `budget.py`: `BudgetTracker` records tokens/cost per call, looks up price
  by model name in `PRICING`, exposes `remaining()`, raises `BudgetExceeded`
  when a ceiling is crossed.
- `llm_client.py`: uses the `openai` SDK with
  `base_url="https://api.deepseek.com"` and the key from `DEEPSEEK_API_KEY`.
  `LLMClient.complete(messages, system, model, reasoning_effort)` makes the
  call, reads `usage` from the response, reports it to the `BudgetTracker`,
  returns text. Model + reasoning mode are passed in by the caller (from the
  `AGENT_MODELS` table) — never defaulted inside this file.

**Acceptance:** a test simulates calls until the ceiling trips and asserts
`BudgetExceeded` is raised, and asserts cost is computed correctly for both
`deepseek-v4-flash` and `deepseek-v4-pro` prices. No agent code yet.

---

## Phase 2 — State + one agent (Orchestrator)

- `state.py`: `RunState` dataclass — brief, artifacts list, transcript list,
  status; `save()`/`load()` to JSON.
- `agents.py`: base `Agent` class (holds name, system prompt, llm client);
  implement `Orchestrator` only. It turns a brief into a list of sub-goals.
- Prompt lives in `specs/prompts/orchestrator.md`.

**Acceptance:** running the Orchestrator on a sample brief produces a
structured sub-goal list and appends to state. Test with a mocked client.

---

## Phase 3 — Researcher, Architect, Worker

Three more agents, same `Agent` base. No QA loop yet — linear pass.

- Each gets a prompt file in `specs/prompts/`.
- `pipeline.py`: first version runs 1->2->3->4 linearly.

**Acceptance:** `python -m agent_lab.main --brief "..."` runs four stages
end to end on a mock client and writes a complete state JSON.

---

## Phase 4 — Critic + bounded QA loop

- `Critic` agent returns structured `{approved, issues}` — not prose.
- `pipeline.py`: insert Worker <-> Critic loop, capped at `MAX_QA_ROUNDS`.
  On cap-without-approval, set status `needs_human_review`.

**Acceptance:** a test forces the Critic to always reject and asserts the
loop stops at exactly `MAX_QA_ROUNDS` and status is `needs_human_review`.

---

## Phase 5 — Human approval gates

- `pipeline.py`: before the Sandbox stage, and before final output, pause
  for human input (`approve` / `reject` / `edit`).
- A `--yes` flag may auto-approve ONLY for tests, never by default.

**Acceptance:** a normal run blocks for input before the Sandbox stage.

---

## Phase 6 — Sandbox

- `sandbox.py`: run code in a subprocess, no network, wall-clock timeout,
  captured output. Approval-gated (rule 3).
- Document (do not silently skip) that container isolation is the
  recommended hardening and how to add it.

**Acceptance:** a benign script runs and returns output; a script that
exceeds the timeout is killed; nothing runs without approval.

---

## Phase 7 — Polish

Real-run cost report, `README.md`, resume-from-JSON, end-to-end test
against the live API behind an explicit opt-in flag.

**Acceptance:** README lets a new user run the pipeline from scratch.

---

## Out of scope for v1 (do not build unless asked)

Web UI, database, parallel agent execution, self-modifying agents,
auto-spawning sub-agents, unattended scheduled runs.
