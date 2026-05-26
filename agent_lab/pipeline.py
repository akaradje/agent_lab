from __future__ import annotations

from pathlib import Path

from agent_lab.agents import Architect, Critic, Orchestrator, Researcher, Worker
from agent_lab.config import MAX_QA_ROUNDS
from agent_lab.llm_client import LLMClient
from agent_lab.state import RunState

PROMPT_DIR = Path("specs/prompts")


def _load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def run_pipeline(brief: str, llm: LLMClient) -> RunState:
    """Run stages 1-4 linearly, then a bounded Worker <-> Critic QA loop.
    If the Critic rejects after MAX_QA_ROUNDS rounds, status is set to
    needs_human_review."""
    state = RunState(brief=brief)

    orch = Orchestrator("Orchestrator", _load_prompt("orchestrator"), llm)
    state = orch.run(state)

    researcher = Researcher("Researcher", _load_prompt("researcher"), llm)
    state = researcher.run(state)

    architect = Architect("Architect", _load_prompt("architect"), llm)
    state = architect.run(state)

    worker = Worker("Worker", _load_prompt("worker"), llm)
    state = worker.run(state)

    for _round in range(1, MAX_QA_ROUNDS + 1):
        critic = Critic("Critic", _load_prompt("critic"), llm)
        state = critic.run(state)
        verdict = state.artifacts[-1].get("verdict", {})
        if verdict.get("approved"):
            state.status = "complete"
            return state
        if _round < MAX_QA_ROUNDS:
            state = worker.run(state, feedback=verdict.get("issues", []))

    state.status = "needs_human_review"
    return state
