from __future__ import annotations

from pathlib import Path

from agent_lab.agents import Architect, Critic, Orchestrator, Researcher, Worker
from agent_lab.config import MAX_QA_ROUNDS
from agent_lab.llm_client import LLMClient
from agent_lab.sandbox import Sandbox, extract_code_from_deliverable
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

    1. Before Sandbox execution.
    2. Before final output.

    If *yes* is True, both gates auto-approve (for tests only). If the
    Critic rejects after MAX_QA_ROUNDS rounds, status is set to
    needs_human_review and gates are skipped.
    """
    state = RunState(brief=brief)
    gate = HumanGate(yes=yes)

    orch = Orchestrator("Orchestrator", _load_prompt("orchestrator"), llm)
    state = orch.run(state)

    clarifications = _clarification_sub_goals(state)
    if clarifications:
        state.status = "needs_human_review"
        state.transcript.append(
            f"[pipeline] halted at orchestrator: "
            f"{len(clarifications)} clarification request(s) need human input"
        )
        for sg in clarifications:
            state.transcript.append(f"[clarification] {sg.get('goal', '')}")
        return state

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

    # Extract code from the final Worker deliverable and run in sandbox.
    worker_deliverable = _find_last_worker_deliverable(state)
    if not worker_deliverable:
        state.status = "needs_human_review"
        return state

    code = extract_code_from_deliverable(worker_deliverable)
    sandbox = Sandbox()
    try:
        result = sandbox.run(code, pre_approved=True)
    except Exception as exc:
        state.artifacts.append({
            "stage": "sandbox",
            "agent": "Sandbox",
            "error": str(exc),
        })
        state.transcript.append(f"[sandbox] execution raised: {exc}")
        state.status = "needs_human_review"
        return state

    state.artifacts.append({
        "stage": "sandbox",
        "agent": "Sandbox",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
    })
    state.transcript.append(
        f"[sandbox] exit_code={result.exit_code}, timed_out={result.timed_out}"
    )

    # Gate 2 — before final output
    decision = gate.ask("Sandbox completed. Review the deliverable and approve final output?")
    state.transcript.append(f"[gate] final gate decision: {decision}")
    if decision != "approve":
        state.status = "rejected_at_gate_final"
        return state

    state.status = "complete"
    return state


def resume_pipeline(state: RunState, llm: LLMClient, yes: bool = False) -> RunState:
    """Continue a saved pipeline run from its current status.

    Handles four cases:
    - ``complete`` — nothing to do, return as-is.
    - ``rejected_at_gate_final`` — re-present the final approval gate.
    - ``rejected_at_gate_sandbox`` — re-present the sandbox gate, run sandbox
      if approved, then re-present the final gate.
    - ``needs_human_review`` — show the last Critic issues, then proceed
      through sandbox + final gates (the human is making the call the
      automated QA loop could not).
    - ``running`` — should not appear in a saved state; treat as no-op.
    """
    gate = HumanGate(yes=yes)

    if state.status == "complete":
        return state

    if state.status == "running":
        return state

    if state.status == "rejected_at_gate_final":
        decision = gate.ask(
            "Sandbox completed. Review the deliverable and approve final output?"
        )
        state.transcript.append(f"[gate] final gate decision (resume): {decision}")
        state.status = "complete" if decision == "approve" else "rejected_at_gate_final"
        return state

    # rejected_at_gate_sandbox or needs_human_review — (re)present sandbox gate
    if state.status == "needs_human_review":
        _print_critic_issues(state)

    decision = gate.ask("About to execute the deliverable in a sandbox. Approve?")
    state.transcript.append(f"[gate] sandbox gate decision (resume): {decision}")
    if decision != "approve":
        state.status = "rejected_at_gate_sandbox"
        return state

    worker_deliverable = _find_last_worker_deliverable(state)
    if not worker_deliverable:
        state.status = "needs_human_review"
        return state

    code = extract_code_from_deliverable(worker_deliverable)
    sandbox = Sandbox()
    try:
        result = sandbox.run(code, pre_approved=True)
    except Exception as exc:
        state.artifacts.append({
            "stage": "sandbox",
            "agent": "Sandbox",
            "error": str(exc),
        })
        state.transcript.append(f"[sandbox] execution raised: {exc}")
        state.status = "needs_human_review"
        return state

    state.artifacts.append({
        "stage": "sandbox",
        "agent": "Sandbox",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
    })
    state.transcript.append(
        f"[sandbox] exit_code={result.exit_code}, timed_out={result.timed_out}"
    )

    decision = gate.ask(
        "Sandbox completed. Review the deliverable and approve final output?"
    )
    state.transcript.append(f"[gate] final gate decision (resume): {decision}")
    state.status = "complete" if decision == "approve" else "rejected_at_gate_final"
    return state


def _print_critic_issues(state: RunState) -> None:
    """Print the last Critic's issues to stdout so the human can review them."""
    for a in reversed(state.artifacts):
        if a.get("stage") == "critic":
            verdict = a.get("verdict", {})
            issues = verdict.get("issues", [])
            if issues:
                print(f"\nCritic flagged {len(issues)} issue(s):")
                for i, issue in enumerate(issues, 1):
                    print(f"  {i}. {issue}")
            break


def _clarification_sub_goals(state: RunState) -> list[dict]:
    """Return Orchestrator sub-goals carrying `needs_clarification: true`.
    Used as the structural halt signal — no string matching on goal text.
    """
    for a in state.artifacts:
        if a.get("stage") == "orchestrator":
            sub_goals = a.get("sub_goals", [])
            return [sg for sg in sub_goals if sg.get("needs_clarification")]
    return []


def _find_last_worker_deliverable(state: RunState) -> str | None:
    """Return the deliverable text from the last Worker artifact, or None."""
    for a in reversed(state.artifacts):
        if a.get("stage") == "worker":
            return a.get("deliverable")  # type: ignore[no-any-return]
    return None
