from unittest.mock import MagicMock, patch

import pytest

from agent_lab.budget import BudgetExceededError, BudgetTracker
from agent_lab.llm_client import LLMClient


def _make_mock_response(content: str, prompt_tokens: int, completion_tokens: int) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


class TestLLMClient:
    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_returns_content(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("hello", 10, 5)
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            result = client.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-v4-flash",
            )
        assert result == "hello"

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_records_usage(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("ok", prompt_tokens=100, completion_tokens=50)
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            client.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-v4-flash",
            )
        assert bt.total_tokens == 150

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_includes_system_message(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("ok", 10, 5)
        target = client._client.chat.completions
        with patch.object(target, "create", return_value=mock_resp) as create_mock:
            client.complete(
                messages=[{"role": "user", "content": "hi"}],
                system="You are helpful.",
                model="deepseek-v4-flash",
            )
        called_messages = create_mock.call_args[1]["messages"]
        assert called_messages[0] == {"role": "system", "content": "You are helpful."}
        assert called_messages[1] == {"role": "user", "content": "hi"}

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_passes_reasoning_effort(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("ok", 10, 5)
        target = client._client.chat.completions
        with patch.object(target, "create", return_value=mock_resp) as create_mock:
            client.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-v4-pro",
                reasoning_effort="think-high",
            )
        assert create_mock.call_args[1]["extra_body"] == {"reasoning_effort": "think-high"}

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_no_reasoning_effort_when_none(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("ok", 10, 5)
        target = client._client.chat.completions
        with patch.object(target, "create", return_value=mock_resp) as create_mock:
            client.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-v4-flash",
                reasoning_effort=None,
            )
        assert "extra_body" not in create_mock.call_args[1]

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_propagates_budget_exceeded(self) -> None:
        bt = BudgetTracker(max_tokens=10, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("ok", prompt_tokens=20, completion_tokens=5)
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            with pytest.raises(BudgetExceededError):
                client.complete(
                    messages=[{"role": "user", "content": "hi"}],
                    model="deepseek-v4-flash",
                )

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_handles_none_usage(self) -> None:
        """Usage may be None in some API responses — should not crash."""
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response("ok", 0, 0)
        mock_resp.usage = None
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            result = client.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-v4-flash",
            )
        assert result == "ok"
        assert bt.total_tokens == 0

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_handles_none_content(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        client = LLMClient(budget=bt)

        mock_resp = _make_mock_response(None, 10, 5)  # type: ignore[arg-type]
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            result = client.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-v4-flash",
            )
        assert result == ""

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_complete_missing_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(KeyError):
                LLMClient(budget=BudgetTracker(max_tokens=100, max_usd=1.0))
