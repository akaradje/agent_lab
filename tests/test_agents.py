import json
from pathlib import Path
from unittest.mock import MagicMock

from agent_lab.agents import Architect, Orchestrator, Researcher, Worker
from agent_lab.state import RunState


def _make_mock_llm(response_text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response_text
    return llm


def _load_prompt(name: str) -> str:
    prompt_path = Path(f"specs/prompts/{name}.md")
    return prompt_path.read_text(encoding="utf-8")


class TestOrchestrator:
    def test_run_produces_sub_goals(self) -> None:
        sub_goals_json = json.dumps([
            {"id": "1", "goal": "Set up project", "success_criterion": "Folder exists"},
            {"id": "2", "goal": "Write main module", "success_criterion": "main.py runs"},
            {"id": "3", "goal": "Add tests", "success_criterion": "pytest passes"},
        ])
        llm = _make_mock_llm(sub_goals_json)
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
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
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.transcript) == 1
        assert "[orchestrator]" in result.transcript[0]
        assert "1 sub-goals" in result.transcript[0]

    def test_run_passes_brief_to_llm(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "ok", "success_criterion": "ok"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
        state = RunState(brief="Design a REST API")

        agent.run(state)
        call_args = llm.complete.call_args
        assert call_args[1]["messages"][0]["content"] == "Design a REST API"

    def test_run_passes_system_prompt_and_model(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "ok", "success_criterion": "ok"}
        ]))
        prompt = _load_prompt("orchestrator")
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
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
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
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.artifacts[0]["sub_goals"]) == 1
        assert result.artifacts[0]["sub_goals"][0]["goal"] == "Use ``` fences"

    def test_run_returns_state_with_unchanged_brief(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "g", "success_criterion": "s"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
        state = RunState(brief="unchanged")

        result = agent.run(state)
        assert result.brief == "unchanged"
        assert result is state  # mutates in place

    def test_parse_invalid_json_falls_back_to_raw_text(self) -> None:
        llm = _make_mock_llm("not valid json at all")
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
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
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
        state = RunState(brief="test")

        result = agent.run(state)
        assert len(result.artifacts[0]["sub_goals"]) == 1

    def test_run_uses_model_from_config_not_hardcoded(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"id": "1", "goal": "g", "success_criterion": "s"}
        ]))
        agent = Orchestrator(name="orch", system_prompt=_load_prompt("orchestrator"), llm=llm)
        state = RunState(brief="test")

        agent.run(state)
        kwargs = llm.complete.call_args[1]
        # Model is read from AGENT_MODELS config, not hardcoded in agent code
        from agent_lab.config import AGENT_MODELS
        expected_model, expected_reasoning = AGENT_MODELS["orchestrator"]
        assert kwargs["model"] == expected_model
        assert kwargs["reasoning_effort"] == expected_reasoning


def _state_with_orchestrator_artifact(brief: str = "test") -> RunState:
    """Helper: returns a RunState that already has an orchestrator artifact."""
    state = RunState(brief=brief)
    state.artifacts.append({
        "stage": "orchestrator",
        "agent": "Orchestrator",
        "sub_goals": [
            {"id": "1", "goal": "Research topic", "success_criterion": "Notes exist"},
            {"id": "2", "goal": "Write code", "success_criterion": "Code runs"},
        ],
    })
    return state


class TestResearcher:
    def test_run_produces_findings_artifact(self) -> None:
        findings_json = json.dumps([
            {"sub_goal_id": "1", "findings": "Use X library", "sources": "docs.x.com"},
            {"sub_goal_id": "2", "findings": "Pattern Y works", "sources": "ref.y.com"},
        ])
        llm = _make_mock_llm(findings_json)
        agent = Researcher(name="res", system_prompt=_load_prompt("researcher"), llm=llm)
        state = _state_with_orchestrator_artifact()

        result = agent.run(state)
        assert len(result.artifacts) == 2  # orch + researcher
        researcher_artifact = result.artifacts[1]
        assert researcher_artifact["stage"] == "researcher"
        assert len(researcher_artifact["findings"]) == 2

    def test_run_passes_context_to_llm(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"sub_goal_id": "1", "findings": "ok", "sources": "ok"}
        ]))
        agent = Researcher(name="res", system_prompt=_load_prompt("researcher"), llm=llm)
        state = _state_with_orchestrator_artifact("Design a REST API")

        agent.run(state)
        call_args = llm.complete.call_args
        user_content = call_args[1]["messages"][0]["content"]
        assert "Design a REST API" in user_content
        assert "Research topic" in user_content

    def test_run_uses_model_from_config(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"sub_goal_id": "1", "findings": "ok", "sources": "ok"}
        ]))
        agent = Researcher(name="res", system_prompt=_load_prompt("researcher"), llm=llm)
        state = _state_with_orchestrator_artifact()

        agent.run(state)
        kwargs = llm.complete.call_args[1]
        from agent_lab.config import AGENT_MODELS
        expected_model, expected_reasoning = AGENT_MODELS["researcher"]
        assert kwargs["model"] == expected_model
        assert kwargs["reasoning_effort"] == expected_reasoning

    def test_run_appends_transcript(self) -> None:
        llm = _make_mock_llm(json.dumps([
            {"sub_goal_id": "1", "findings": "ok", "sources": "ok"}
        ]))
        agent = Researcher(name="res", system_prompt=_load_prompt("researcher"), llm=llm)
        state = _state_with_orchestrator_artifact()

        result = agent.run(state)
        assert any("[researcher]" in entry for entry in result.transcript)

    def test_parse_fallback_on_invalid_json(self) -> None:
        llm = _make_mock_llm("plain text findings")
        agent = Researcher(name="res", system_prompt=_load_prompt("researcher"), llm=llm)
        state = _state_with_orchestrator_artifact()

        result = agent.run(state)
        findings = result.artifacts[1]["findings"]
        assert findings == {"raw": "plain text findings"}


class TestArchitect:
    def test_run_produces_design_artifact(self) -> None:
        design_json = json.dumps({
            "overview": "Build a CLI tool",
            "components": [_make_component()],
            "build_order": ["Set up project", "Implement parser"],
            "notes": "Keep it simple",
        })
        llm = _make_mock_llm(design_json)
        agent = Architect(name="arch", system_prompt=_load_prompt("architect"), llm=llm)
        state = _state_with_orchestrator_and_researcher()

        result = agent.run(state)
        assert len(result.artifacts) == 3  # orch + researcher + architect
        arch_artifact = result.artifacts[2]
        assert arch_artifact["stage"] == "architect"
        assert arch_artifact["design"]["overview"] == "Build a CLI tool"

    def test_run_passes_full_context_to_llm(self) -> None:
        design_json = json.dumps(_minimal_design())
        llm = _make_mock_llm(design_json)
        agent = Architect(name="arch", system_prompt=_load_prompt("architect"), llm=llm)
        state = _state_with_orchestrator_and_researcher()

        agent.run(state)
        call_args = llm.complete.call_args
        user_content = call_args[1]["messages"][0]["content"]
        assert "test brief" in user_content
        assert "Research topic" in user_content  # sub_goals present
        assert "Use X library" in user_content  # research present

    def test_run_uses_pro_model_from_config(self) -> None:
        design_json = json.dumps(_minimal_design())
        llm = _make_mock_llm(design_json)
        agent = Architect(name="arch", system_prompt=_load_prompt("architect"), llm=llm)
        state = _state_with_orchestrator_and_researcher()

        agent.run(state)
        kwargs = llm.complete.call_args[1]
        from agent_lab.config import AGENT_MODELS
        expected_model, expected_reasoning = AGENT_MODELS["architect"]
        assert kwargs["model"] == expected_model
        assert kwargs["reasoning_effort"] == expected_reasoning

    def test_run_appends_transcript(self) -> None:
        design_json = json.dumps(_minimal_design())
        llm = _make_mock_llm(design_json)
        agent = Architect(name="arch", system_prompt=_load_prompt("architect"), llm=llm)
        state = _state_with_orchestrator_and_researcher()

        result = agent.run(state)
        assert any("[architect]" in entry for entry in result.transcript)

    def test_parse_wraps_list_in_dict(self) -> None:
        """If the LLM returns a list, it gets wrapped in {"raw": [...]}."""
        list_json = json.dumps([{"name": "comp1"}, {"name": "comp2"}])
        llm = _make_mock_llm(list_json)
        agent = Architect(name="arch", system_prompt=_load_prompt("architect"), llm=llm)
        state = _state_with_orchestrator_and_researcher()

        result = agent.run(state)
        design = result.artifacts[2]["design"]
        assert isinstance(design, dict)
        assert "raw" in design


class TestWorker:
    def test_run_produces_deliverable_artifact(self) -> None:
        deliverable = "```python\nprint('hello')\n```"
        llm = _make_mock_llm(deliverable)
        agent = Worker(name="wrk", system_prompt=_load_prompt("worker"), llm=llm)
        state = _state_with_full_context()

        result = agent.run(state)
        assert len(result.artifacts) == 4  # orch + researcher + architect + worker
        worker_artifact = result.artifacts[3]
        assert worker_artifact["stage"] == "worker"
        assert "print('hello')" in worker_artifact["deliverable"]

    def test_run_passes_full_context_to_llm(self) -> None:
        deliverable = "code here"
        llm = _make_mock_llm(deliverable)
        agent = Worker(name="wrk", system_prompt=_load_prompt("worker"), llm=llm)
        state = _state_with_full_context()

        agent.run(state)
        call_args = llm.complete.call_args
        user_content = call_args[1]["messages"][0]["content"]
        assert "test brief" in user_content
        assert "Research topic" in user_content  # sub_goals
        assert "Use X library" in user_content  # research
        assert "Build a CLI tool" in user_content  # design

    def test_run_uses_model_from_config(self) -> None:
        llm = _make_mock_llm("deliverable")
        agent = Worker(name="wrk", system_prompt=_load_prompt("worker"), llm=llm)
        state = _state_with_full_context()

        agent.run(state)
        kwargs = llm.complete.call_args[1]
        from agent_lab.config import AGENT_MODELS
        expected_model, expected_reasoning = AGENT_MODELS["worker"]
        assert kwargs["model"] == expected_model
        assert kwargs["reasoning_effort"] == expected_reasoning

    def test_run_appends_transcript_with_character_count(self) -> None:
        llm = _make_mock_llm("a" * 100)
        agent = Worker(name="wrk", system_prompt=_load_prompt("worker"), llm=llm)
        state = _state_with_full_context()

        result = agent.run(state)
        assert any("100 character" in entry for entry in result.transcript)


def _make_component() -> dict:
    return {"name": "parser", "purpose": "Parse args", "interface": "argparse", "depends_on": []}


def _minimal_design() -> dict:
    return {"overview": "test", "components": [], "build_order": [], "notes": ""}


# ── helpers for building state with prior artifacts ──────────────────


def _state_with_orchestrator_and_researcher() -> RunState:
    state = _state_with_orchestrator_artifact("test brief")
    state.artifacts.append({
        "stage": "researcher",
        "agent": "Researcher",
        "findings": [
            {"sub_goal_id": "1", "findings": "Use X library", "sources": "docs.x.com"},
            {"sub_goal_id": "2", "findings": "Pattern Y works", "sources": "ref.y.com"},
        ],
    })
    return state


def _state_with_full_context() -> RunState:
    state = _state_with_orchestrator_and_researcher()
    state.artifacts.append({
        "stage": "architect",
        "agent": "Architect",
        "design": {
            "overview": "Build a CLI tool",
            "components": [_make_component()],
            "build_order": ["Set up project", "Implement parser"],
            "notes": "Keep it simple",
        },
    })
    return state
