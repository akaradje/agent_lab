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
        # The model may wrap the JSON in markdown fences; strip them.
        # Anchored to start/end only — internal backticks are left alone.
        text = raw.strip()
        text = re.sub(r"^```[^\n]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
        text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: wrap the raw text as a single sub-goal.
            return [{"id": "1", "goal": raw, "success_criterion": "see goal"}]

        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "sub_goals" in parsed:
            return parsed["sub_goals"]
        return [{"id": "1", "goal": raw, "success_criterion": "see goal"}]
