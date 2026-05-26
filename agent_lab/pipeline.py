from __future__ import annotations

from pathlib import Path

from agent_lab.agents import Architect, Critic, Orchestrator, Researcher, Worker
from agent_lab.config import MAX_QA_ROUNDS
from agent_lab.llm_client import LLMClient
from agent_lab.state import RunState

PROMPT_DIR = Path("specs/prompts")


def _load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


class HumanGate:
    """Prompts a human for approval at pipeline checkpoints.

    In normal mode reads from stdin. The *yes* flag auto-approves for tests
    without requiring human input — it must never be the default in production.
    """

    def __init__(self, yes: bool = False) -> None:
        self._yes = yes

    def ask(self, summary: str) -> str:
        """Return 'approve', 'reject', or 'edit'."""
        if self._yes:
            return "approve"

        print(f"\n{'=' * 60}")
        print(f"APPROVAL REQUIRED: {summary}")
        print(f"{'=' * 60}")
        response = input("Choose [approve / reject / edit]: ").strip().lower()
        while response not in ("approve", "reject", "edit"):
            print("Invalid choice. Type: approve, reject, or edit")
            response = input("Choose [approve / reject / edit]: ").strip().lower()
        return response


def run_pipeline(brief: str, llm: LLMClient, yes: bool = False) -> RunState:
    """Run the full pipeline with human-approval gates.

    Stages 1-4 linear, then a bounded Worker <-> Critic QA loop. If the
    Critic approves, the pipeline proceeds through two human gates:

    1. Before Sandbox execution (Phase 6 will insert the Sandbox call here).
    2. Before final output.

    If *yes* is True, both gates auto-approve (for tests only). If the
    Critic rejects after MAX_QA_ROUNDS rounds, status is set to
    needs_human_review and gates are skipped.
    """
    state = RunState(brief=brief)
    gate = HumanGate(yes=yes)

    orch = Orchestrator("Orchestrator", _load_prompt("orchestrator"), llm)
    state = orch.run(state)

    researcher = Researcher("Researcher", _load_prompt("researcher"), llm)
    state = researcher.run(state)

    architect = Architect("Architect", _load_prompt("architect"), llm)
    state = architect.run(state)

    worker = Worker("Worker", _load_prompt("worker"), llm)
    state = worker.run(state)

    approved = False
    for _round in range(1, MAX_QA_ROUNDS + 1):
        critic = Critic("Critic", _load_prompt("critic"), llm)
        state = critic.run(state)
        verdict = state.artifacts[-1].get("verdict", {})
        if verdict.get("approved"):
            approved = True
            break
        if _round < MAX_QA_ROUNDS:
            state = worker.run(state, feedback=verdict.get("issues", []))

    if not approved:
        state.status = "needs_human_review"
        return state

    # Gate 1 — before Sandbox execution
    decision = gate.ask("About to execute the deliverable in a sandbox. Approve?")
    state.transcript.append(f"[gate] sandbox gate decision: {decision}")
    if decision != "approve":
        state.status = "rejected_at_gate_sandbox"
        return state

    # Phase 6 will insert the Sandbox call here.

    # Gate 2 — before final output
    decision = gate.ask("Sandbox completed. Review the deliverable and approve final output?")
    state.transcript.append(f"[gate] final gate decision: {decision}")
    if decision != "approve":
        state.status = "rejected_at_gate_final"
        return state

    state.status = "complete"
    return state
