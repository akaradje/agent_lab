import os

from openai import OpenAI

from agent_lab.budget import BudgetTracker


class LLMClient:
    """Thin wrapper over the DeepSeek API (OpenAI-compatible)."""

    def __init__(self, budget: BudgetTracker) -> None:
        api_key = os.environ["DEEPSEEK_API_KEY"]
        self._client = OpenAI(
            base_url="https://api.deepseek.com",
            api_key=api_key,
        )
        self._budget = budget

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        model: str,
        reasoning_effort: str | None = None,
    ) -> str:
        msgs: list[dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        kwargs: dict = {"model": model, "messages": msgs}
        if reasoning_effort:
            kwargs["extra_body"] = {"reasoning_effort": reasoning_effort}

        response = self._client.chat.completions.create(**kwargs)

        usage = response.usage
        if usage:
            self._budget.record(
                model=model,
                input_tokens=usage.prompt_tokens or 0,
                output_tokens=usage.completion_tokens or 0,
            )

        content = response.choices[0].message.content
        return content if content is not None else ""
