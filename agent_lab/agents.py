from __future__ import annotations

import json
import re

from agent_lab.config import AGENT_MODELS
from agent_lab.llm_client import LLMClient
from agent_lab.state import RunState


class Agent:
    """Base class for pipeline agents. Holds a name, a system prompt, and a
    reference to the budget-tracked LLM client. Subclasses implement run()."""

    def __init__(self, name: str, system_prompt: str, llm: LLMClient) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm


class Orchestrator(Agent):
    """Decomposes a brief into 3-6 concrete, ordered sub-goals."""

    STAGE = "orchestrator"

    def run(self, state: RunState) -> RunState:
        model, reasoning = AGENT_MODELS[self.STAGE]
        response = self.llm.complete(
            messages=[{"role": "user", "content": state.brief}],
            system=self.system_prompt,
            model=model,
            reasoning_effort=reasoning,
        )
        sub_goals = self._parse(response)
        artifact = {"stage": self.STAGE, "agent": self.name, "sub_goals": sub_goals}
        state.artifacts.append(artifact)
        state.transcript.append(f"[{self.STAGE}] produced {len(sub_goals)} sub-goals")
        return state

    def _parse(self, raw: str) -> list[dict[str, str]]:
        text = _strip_markdown_fences(raw)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [{"id": "1", "goal": raw, "success_criterion": "see goal"}]

        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "sub_goals" in parsed:
            return parsed["sub_goals"]
        return [{"id": "1", "goal": raw, "success_criterion": "see goal"}]


class Researcher(Agent):
    """Gathers and synthesizes information for each sub-goal."""

    STAGE = "researcher"

    def run(self, state: RunState) -> RunState:
        sub_goals = _find_artifact(state, "orchestrator", "sub_goals")
        context = json.dumps({"brief": state.brief, "sub_goals": sub_goals}, indent=2)

        model, reasoning = AGENT_MODELS[self.STAGE]
        response = self.llm.complete(
            messages=[{"role": "user", "content": context}],
            system=self.system_prompt,
            model=model,
            reasoning_effort=reasoning,
        )
        findings = _parse_json_response(response)
        artifact = {"stage": self.STAGE, "agent": self.name, "findings": findings}
        state.artifacts.append(artifact)
        state.transcript.append(f"[{self.STAGE}] produced {len(findings)} finding(s)")
        return state


class Architect(Agent):
    """Designs the solution based on research and sub-goals."""

    STAGE = "architect"

    def run(self, state: RunState) -> RunState:
        sub_goals = _find_artifact(state, "orchestrator", "sub_goals")
        findings = _find_artifact(state, "researcher", "findings")
        context = json.dumps(
            {"brief": state.brief, "sub_goals": sub_goals, "research": findings},
            indent=2,
        )

        model, reasoning = AGENT_MODELS[self.STAGE]
        response = self.llm.complete(
            messages=[{"role": "user", "content": context}],
            system=self.system_prompt,
            model=model,
            reasoning_effort=reasoning,
        )
        design = _parse_json_response(response)
        if isinstance(design, list):
            design = {"raw": design}
        artifact = {"stage": self.STAGE, "agent": self.name, "design": design}
        state.artifacts.append(artifact)
        state.transcript.append(
            f"[{self.STAGE}] produced design with {len(design.get('components', []))} component(s)"
        )
        return state


class Worker(Agent):
    """Produces the actual deliverable from the design."""

    STAGE = "worker"

    def run(self, state: RunState) -> RunState:
        sub_goals = _find_artifact(state, "orchestrator", "sub_goals")
        findings = _find_artifact(state, "researcher", "findings")
        design = _find_artifact(state, "architect", "design")
        context = json.dumps(
            {
                "brief": state.brief,
                "sub_goals": sub_goals,
                "research": findings,
                "design": design,
            },
            indent=2,
        )

        model, reasoning = AGENT_MODELS[self.STAGE]
        response = self.llm.complete(
            messages=[{"role": "user", "content": context}],
            system=self.system_prompt,
            model=model,
            reasoning_effort=reasoning,
        )
        artifact = {
            "stage": self.STAGE,
            "agent": self.name,
            "deliverable": response,
        }
        state.artifacts.append(artifact)
        state.transcript.append(
            f"[{self.STAGE}] produced {len(response)} character(s) of output"
        )
        return state


# ── helpers ──────────────────────────────────────────────────────────


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```[^\n]*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    return text.strip()


def _parse_json_response(raw: str) -> list | dict:
    text = _strip_markdown_fences(raw)
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {"raw": raw}


def _find_artifact(state: RunState, stage: str, key: str) -> list | dict | None:
    for a in state.artifacts:
        if a.get("stage") == stage:
            return a.get(key)
    return None
