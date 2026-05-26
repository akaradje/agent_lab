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
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("Build a hello-world CLI", llm)

        assert state.status == "complete"
        assert len(state.artifacts) == 4
        assert state.artifacts[0]["stage"] == "orchestrator"
        assert state.artifacts[1]["stage"] == "researcher"
        assert state.artifacts[2]["stage"] == "architect"
        assert state.artifacts[3]["stage"] == "worker"
        assert len(state.transcript) >= 4

    def test_state_passes_brief_through(self) -> None:
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("Custom brief", llm)

        assert state.brief == "Custom brief"

    def test_llm_called_four_times(self) -> None:
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
        ]
        llm = _make_mock_llm(responses)
        run_pipeline("brief", llm)

        assert llm.complete.call_count == 4

    def test_state_writes_valid_json(self) -> None:
        responses = [
            json.dumps([{"id": "1", "goal": "g", "success_criterion": "s"}]),
            json.dumps([{"sub_goal_id": "1", "findings": "f", "sources": "s"}]),
            json.dumps({"overview": "o", "components": [], "build_order": [], "notes": ""}),
            "done",
        ]
        llm = _make_mock_llm(responses)
        state = run_pipeline("brief", llm)

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "output.json"
            state.save(path)
            loaded = RunState.load(path)
            assert loaded.status == "complete"
            assert len(loaded.artifacts) == 4
