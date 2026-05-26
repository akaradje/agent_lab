from __future__ import annotations

from pathlib import Path

from agent_lab.agents import Architect, Orchestrator, Researcher, Worker
from agent_lab.llm_client import LLMClient
from agent_lab.state import RunState

PROMPT_DIR = Path("specs/prompts")


def _load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def run_pipeline(brief: str, llm: LLMClient) -> RunState:
    """Run stages 1-4 (Orchestrator -> Researcher -> Architect -> Worker)
    linearly. Each agent reads previous artifacts from state and appends
    its own output."""
    state = RunState(brief=brief)

    orch = Orchestrator("Orchestrator", _load_prompt("orchestrator"), llm)
    state = orch.run(state)

    researcher = Researcher("Researcher", _load_prompt("researcher"), llm)
    state = researcher.run(state)

    architect = Architect("Architect", _load_prompt("architect"), llm)
    state = architect.run(state)

    worker = Worker("Worker", _load_prompt("worker"), llm)
    state = worker.run(state)

    state.status = "complete"
    return state
