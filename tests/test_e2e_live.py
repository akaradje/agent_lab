"""End-to-end test against the live DeepSeek API.

This test costs real money (a few cents per run) and requires a valid
DEEPSEEK_API_KEY. It is skipped by default.

To run::

    AGENT_LAB_LIVE_TEST=1 python -m pytest tests/test_e2e_live.py -v

The opt-in is deliberate — there is no way to accidentally run this test
as part of a normal ``pytest`` invocation.
"""
from __future__ import annotations

import os

import pytest

from agent_lab.budget import BudgetTracker
from agent_lab.config import MAX_TOTAL_TOKENS, MAX_USD
from agent_lab.llm_client import LLMClient
from agent_lab.pipeline import run_pipeline


@pytest.mark.skipif(
    os.environ.get("AGENT_LAB_LIVE_TEST") != "1",
    reason="Set AGENT_LAB_LIVE_TEST=1 to run live API tests (costs real money).",
)
class TestLivePipeline:
    """Full pipeline run against the live DeepSeek API.

    Uses a trivial brief to keep cost minimal (typically < $0.01 per run).
    """

    SIMPLE_BRIEF = (
        "Write a single Python function called `add(a, b)` that returns "
        "the sum of two numbers. Return ONLY the function, no explanation."
    )

    def test_full_pipeline_completes(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        state = run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        assert state.status == "complete", f"Expected complete, got {state.status}"
        assert len(state.artifacts) >= 5, f"Expected >= 5 artifacts, got {len(state.artifacts)}"

    def test_all_stages_present(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        state = run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        stages = {a["stage"] for a in state.artifacts}
        assert stages >= {
            "orchestrator", "researcher", "architect", "worker", "critic", "sandbox"
        }, f"Missing stages: {stages}"

    def test_orchestrator_produces_sub_goals(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        state = run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        orch = _find_artifact(state, "orchestrator")
        sub_goals = orch.get("sub_goals", [])
        assert isinstance(sub_goals, list) and len(sub_goals) >= 1

    def test_worker_produces_deliverable(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        state = run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        worker = _find_artifact(state, "worker")
        assert worker.get("deliverable")

    def test_critic_approves_simple_task(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        state = run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        critic = _find_artifact(state, "critic")
        verdict = critic.get("verdict", {})
        assert verdict.get("approved"), f"Critic did not approve: {verdict}"

    def test_sandbox_executes_deliverable(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        state = run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        sandbox = _find_artifact(state, "sandbox")
        assert sandbox["exit_code"] == 0, f"Sandbox failed: {sandbox}"
        assert not sandbox.get("timed_out")

    def test_cost_report_printed(self) -> None:
        budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
        llm = LLMClient(budget)
        run_pipeline(self.SIMPLE_BRIEF, llm, yes=True)

        report = budget.summary()
        assert "Cost Report" in report
        assert budget.call_count >= 5  # at minimum 5 LLM calls
        assert budget.total_cost > 0
        # Print report so it appears in the test output
        print(report)


def _find_artifact(state, stage: str) -> dict:
    for a in state.artifacts:
        if a.get("stage") == stage:
            return a
    return {}
