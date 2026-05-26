import json
from pathlib import Path
from unittest.mock import MagicMock

from agent_lab.agents import Orchestrator
from agent_lab.state import RunState


def _make_mock_llm(response_text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response_text
    return llm


def _load_prompt() -> str:
    prompt_path = Path("specs/prompts/orchestrator.md")
    return prompt_path.read_text(encoding="utf-8")


class TestOrchestrator:
    def test_run_produces_sub_goals(self) -> None:
        sub_goals_json = json.dumps([
            {"id": "1", "goal": "Set up project", "success_criterion": "Folder exists"},
            {"id": "2", "goal": "Write main module", "success_criterion": "main.py runs"},
            {"id": "3", "goal": "Add tests", "success_criterion": "pytest passes"},
        ])
        llm = _make_mock_llm(sub_goals_json)
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="Build a calculator CLI")

        result = agent.run(state)
        assert len(result.artifacts) == 1
        assert result.artifacts[0]["stage"] == "orchestrator"
        assert len(result.artifacts[0]["sub_goals"]) == 3
        assert result.artifacts[0]["sub_goals"][0]["id"] == "1"

    def test_run_appends_transcript_entry(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "Do it", "success_criterion": "Done"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.transcript) == 1
        assert "[orchestrator]" in result.transcript[0]
        assert "1 sub-goals" in result.transcript[0]

    def test_run_passes_brief_to_llm(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "ok", "success_criterion": "ok"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="Design a REST API")

        agent.run(state)
        call_args = llm.complete.call_args
        assert call_args[1]["messages"][0]["content"] == "Design a REST API"

    def test_run_passes_system_prompt_and_model(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "ok", "success_criterion": "ok"}
        ]))
        prompt = _load_prompt()
        agent = Orchestrator(name="orch", system_prompt=prompt, llm=llm)
        state = RunState(brief="test")

        agent.run(state)
        kwargs = llm.complete.call_args[1]
        assert kwargs["system"] == prompt
        assert kwargs["model"] == "deepseek-v4-flash"
        assert kwargs["reasoning_effort"] == "non-think"

    def test_parse_strips_markdown_fences(self) -> None:
        fenced = '```json\n[{"id": "1", "goal": "g", "success_criterion": "s"}]\n```'
        llm = _make_mock_llm(fenced)
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.artifacts[0]["sub_goals"]) == 1
        assert result.artifacts[0]["sub_goals"][0]["id"] == "1"

    def test_parse_fences_with_internal_backticks(self) -> None:
        """Internal triple backticks in JSON content should not break parsing."""
        fenced = (
            '```json\n'
            '[{"id": "1", "goal": "Use ``` fences", "success_criterion": "works"}]\n'
            '```'
        )
        llm = _make_mock_llm(fenced)
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.artifacts[0]["sub_goals"]) == 1
        assert result.artifacts[0]["sub_goals"][0]["goal"] == "Use ``` fences"

    def test_run_returns_state_with_unchanged_brief(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "g", "success_criterion": "s"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="unchanged")

        result = agent.run(state)
        assert result.brief == "unchanged"
        assert result is state  # mutates in place

    def test_parse_invalid_json_falls_back_to_raw_text(self) -> None:
        llm = _make_mock_llm("not valid json at all")
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        goals = result.artifacts[0]["sub_goals"]
        assert len(goals) == 1
        assert goals[0]["goal"] == "not valid json at all"

    def test_parse_dict_with_sub_goals_key(self) -> None:
        wrapped = json.dumps({"sub_goals": [
            {"id": "1", "goal": "g", "success_criterion": "s"}
        ]})
        llm = _make_mock_llm(wrapped)
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.artifacts[0]["sub_goals"]) == 1

    def test_run_uses_model_from_config_not_hardcoded(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "g", "success_criterion": "s"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt(), llm=llm)
        state = RunState(brief="test")

        agent.run(state)
        kwargs = llm.complete.call_args[1]
        # Model is read from AGENT_MODELS config, not hardcoded in agent code
        from agent_lab.config import AGENT_MODELS
        expected_model, expected_reasoning = AGENT_MODELS["orchestrator"]
        assert kwargs["model"] == expected_model
        assert kwargs["reasoning_effort"] == expected_reasoning
