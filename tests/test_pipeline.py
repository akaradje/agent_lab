import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from agent_lab.pipeline import run_pipeline
from agent_lab.state import RunState


def _make_mock_llm(responses: list[str]) -> MagicMock:
    """Returns a mock LLMClient that returns each response in sequence."""
    llm = MagicMock()
    llm.complete.side_effect = responses
    return llm


class TestLinearPipeline:
    def test_runs_four_stages_and_returns_complete_state(self) -> None:
        responses = [
            # Orchestrator
            json.dumps([
                {"id": "1", "goal": "Research", "success_criterion": "Notes"},
                {"id": "2", "goal": "Build", "success_criterion": "Works"},
            ]),
            # Researcher
            json.dumps([
                {"sub_goal_id": "1", "findings": "Use library X", "sources": "docs"},
                {"sub_goal_id": "2", "findings": "Pattern Y", "sources": "ref"},
            ]),
            # Architect
            json.dumps({
                "overview": "A CLI tool",
                "components": [
                    {"name": "main", "purpose": "Entry", "interface": "main()", "depends_on": []},
                ],
                "build_order": ["Create main.py"],
                "notes": "",
            }),
            # Worker
            "```python\nprint('hello world')\n```",
            # Critic — approves on first round
            json.dumps({"approved": True, "issues": []}),
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("Build a hello-world CLI", llm, yes=True)

        assert state.status == "complete"
        assert len(state.artifacts) == 5
        assert state.artifacts[0]["stage"] == "orchestrator"
        assert state.artifacts[1]["stage"] == "researcher"
        assert state.artifacts[2]["stage"] == "architect"
        assert state.artifacts[3]["stage"] == "worker"
        assert state.artifacts[4]["stage"] == "critic"
        assert len(state.transcript) >= 7  # 5 agents + 2 gate entries

    def test_state_passes_brief_through(self) -> None:
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
            json.dumps({"approved": True, "issues": []}),
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("Custom brief", llm, yes=True)

        assert state.brief == "Custom brief"

    def test_llm_called_five_times_with_immediate_approval(self) -> None:
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
            json.dumps({"approved": True, "issues": []}),
        ]
        llm = _make_mock_llm(responses)
        run_pipeline("brief", llm, yes=True)

        assert llm.complete.call_count == 5

    def test_state_writes_valid_json(self) -> None:
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
            json.dumps({"approved": True, "issues": []}),
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("brief", llm, yes=True)

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "output.json"
            state.save(path)
            loaded = RunState.load(path)
            assert loaded.status == "complete"
            assert len(loaded.artifacts) == 5


class TestQALoop:
    def test_critic_always_rejects_stops_at_max_rounds(self) -> None:
        """Critic rejects every round; loop stops at MAX_QA_ROUNDS (3)
        and status is needs_human_review."""
        from agent_lab.config import MAX_QA_ROUNDS

        reject_verdict = json.dumps({
            "approved": False,
            "issues": ["Missing error handling", "No tests"],
        })
        # Orchestrator, Researcher, Architect, Worker (initial) = 4
        # Round 1: Critic reject + Worker revise = 2
        # Round 2: Critic reject + Worker revise = 2
        # Round 3: Critic reject, no Worker = 1
        # Total = 4 + 2 + 2 + 1 = 9 for MAX_QA_ROUNDS=3
        responses = [
            # Orchestrator
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            # Researcher
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            # Architect
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            # Worker initial
            "v1",
            # Round 1: Critic rejects
            reject_verdict,
            # Worker revise
            "v2",
            # Round 2: Critic rejects
            reject_verdict,
            # Worker revise
            "v3",
            # Round 3: Critic rejects (last round, no Worker after)
            reject_verdict,
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("brief", llm, yes=True)

        assert state.status == "needs_human_review"
        # 4 initial + 3 critic + 2 worker revisions = 9
        assert len(state.artifacts) == 4 + MAX_QA_ROUNDS + (MAX_QA_ROUNDS - 1)
        critic_artifacts = [a for a in state.artifacts if a["stage"] == "critic"]
        assert len(critic_artifacts) == MAX_QA_ROUNDS
        for ca in critic_artifacts:
            assert ca["verdict"]["approved"] is False

    def test_critic_approves_on_second_round(self) -> None:
        """Critic rejects once, Worker revises, Critic approves on round 2."""
        reject_verdict = json.dumps({
            "approved": False,
            "issues": ["Bug in line 3"],
        })
        approve_verdict = json.dumps({"approved": True, "issues": []})
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "v1",
            # Round 1: Critic rejects
            reject_verdict,
            # Worker revise
            "v2",
            # Round 2: Critic approves
            approve_verdict,
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("brief", llm, yes=True)

        assert state.status == "complete"
        assert llm.complete.call_count == 7  # 4 init + 3 QA (2 critic + 1 revise)
        # Final critic artifact should approve
        last_critic = [a for a in state.artifacts if a["stage"] == "critic"][-1]
        assert last_critic["verdict"]["approved"] is True

    def test_critic_approves_immediately(self) -> None:
        """Critic approves on first round; no Worker revision needed."""
        approve_verdict = json.dumps({"approved": True, "issues": []})
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
            approve_verdict,
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("brief", llm, yes=True)

        assert state.status == "complete"
        assert llm.complete.call_count == 5
        worker_artifacts = [a for a in state.artifacts if a["stage"] == "worker"]
        assert len(worker_artifacts) == 1  # no revision

    def test_worker_revision_includes_feedback(self) -> None:
        """When Critic rejects, the Worker revision call receives the issues."""
        reject_verdict = json.dumps({
            "approved": False,
            "issues": ["Missing docstrings"],
        })
        approve_verdict = json.dumps({"approved": True, "issues": []})
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "v1",
            reject_verdict,
            "v2 revised",
            approve_verdict,
        ]
        llm = _make_mock_llm(responses)
        run_pipeline("brief", llm, yes=True)

        # Call order: Orch, Researcher, Architect, Worker, Critic, Worker-revise, Critic
        # The revision Worker call is index 5 (6th call, 0-indexed)
        revision_call_args = llm.complete.call_args_list[5]
        user_content = revision_call_args[1]["messages"][0]["content"]
        assert "Missing docstrings" in user_content
        assert "issues_to_address" in user_content
        assert "previous_deliverable" in user_content


class TestHumanGates:
    """Tests for Phase 5 human approval gates."""

    @staticmethod
    def _basic_responses() -> list[str]:
        """Return responses that pass QA on the first round."""
        return [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "deliverable",
            json.dumps({"approved": True, "issues": []}),
        ]

    def test_yes_flag_auto_approves_and_completes(self) -> None:
        """With yes=True, gates auto-approve and status is complete."""
        llm = _make_mock_llm(self._basic_responses())
        state = run_pipeline("brief", llm, yes=True)

        assert state.status == "complete"
        # Transcript includes gate entries
        gate_entries = [t for t in state.transcript if t.startswith("[gate]")]
        assert len(gate_entries) == 2
        assert "approve" in gate_entries[0]
        assert "approve" in gate_entries[1]

    def test_no_yes_flag_blocks_for_input(self) -> None:
        """With yes=False (default), the gate calls input() on stdin."""
        llm = _make_mock_llm(self._basic_responses())

        with __import__("unittest").mock.patch("builtins.input") as mock_input:
            mock_input.side_effect = ["approve", "approve"]
            state = run_pipeline("brief", llm, yes=False)

        assert state.status == "complete"
        assert mock_input.call_count == 2

    def test_reject_at_sandbox_gate_stops_pipeline(self) -> None:
        """When user rejects at the sandbox gate, pipeline stops there."""
        llm = _make_mock_llm(self._basic_responses())

        with __import__("unittest").mock.patch("builtins.input") as mock_input:
            mock_input.return_value = "reject"
            state = run_pipeline("brief", llm, yes=False)

        assert state.status == "rejected_at_gate_sandbox"
        assert mock_input.call_count == 1  # only first gate reached

    def test_reject_at_final_gate_stops_pipeline(self) -> None:
        """When user approves sandbox but rejects final, status reflects that."""
        llm = _make_mock_llm(self._basic_responses())

        with __import__("unittest").mock.patch("builtins.input") as mock_input:
            mock_input.side_effect = ["approve", "reject"]
            state = run_pipeline("brief", llm, yes=False)

        assert state.status == "rejected_at_gate_final"
        assert mock_input.call_count == 2

    def test_edit_at_sandbox_gate_stops_pipeline(self) -> None:
        """edit is treated as not-approve and stops the pipeline."""
        llm = _make_mock_llm(self._basic_responses())

        with __import__("unittest").mock.patch("builtins.input") as mock_input:
            mock_input.return_value = "edit"
            state = run_pipeline("brief", llm, yes=False)

        assert state.status == "rejected_at_gate_sandbox"

    def test_gates_skipped_when_qa_never_approves(self) -> None:
        """When QA loop exhausts without approval, gates are never reached."""
        reject = json.dumps({"approved": False, "issues": ["bad"]})
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "v1",
            reject, "v2",
            reject, "v3",
            reject,
        ]
        llm = _make_mock_llm(responses)

        with __import__("unittest").mock.patch("builtins.input") as mock_input:
            state = run_pipeline("brief", llm, yes=False)

        assert state.status == "needs_human_review"
        assert mock_input.call_count == 0  # gates never called

    def test_human_gate_ask_returns_approve_for_yes(self) -> None:
        """HumanGate.ask always returns 'approve' when yes=True."""
        from agent_lab.pipeline import HumanGate

        gate = HumanGate(yes=True)
        assert gate.ask("any summary") == "approve"

    def test_human_gate_validates_input(self) -> None:
        """HumanGate.ask re-prompts on invalid input, then accepts valid."""
        from agent_lab.pipeline import HumanGate

        gate = HumanGate(yes=False)
        with __import__("unittest").mock.patch("builtins.input") as mock_input:
            mock_input.side_effect = ["maybe", "  APPROVE  "]
            result = gate.ask("Test gate")
            assert result == "approve"
            assert mock_input.call_count == 2
