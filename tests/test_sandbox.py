from unittest.mock import patch

import pytest

from agent_lab.sandbox import (
    Sandbox,
    SandboxApprovalDeniedError,
    extract_code_from_deliverable,
)


class TestSandboxExecute:
    """Tests for the subprocess execution path (_execute)."""

    def test_benign_script_runs_and_returns_output(self) -> None:
        sandbox = Sandbox()
        result = sandbox._execute("print('hello from sandbox')")

        assert result.stdout.strip() == "hello from sandbox"
        assert result.exit_code == 0
        assert not result.timed_out

    def test_stderr_is_captured(self) -> None:
        sandbox = Sandbox()
        code = "import sys; sys.stderr.write('an error line\\n')"
        result = sandbox._execute(code)

        assert "an error line" in result.stderr
        assert result.exit_code == 0

    def test_non_zero_exit_code_captured(self) -> None:
        sandbox = Sandbox()
        result = sandbox._execute("raise SystemExit(42)")

        assert result.exit_code == 42
        assert not result.timed_out

    def test_timeout_kills_execution(self) -> None:
        sandbox = Sandbox(timeout_seconds=1)
        code = "import time; time.sleep(10)"
        result = sandbox._execute(code)

        assert result.timed_out
        assert result.exit_code == -1

    def test_timeout_default_is_30_seconds(self) -> None:
        sandbox = Sandbox()
        assert sandbox.timeout_seconds == 30


class TestSandboxApproval:
    """Tests for the human-approval gate."""

    def test_run_with_pre_approved_true_skips_prompt(self) -> None:
        sandbox = Sandbox()
        result = sandbox.run("print('hi')", pre_approved=True)

        assert result.stdout.strip() == "hi"
        assert result.exit_code == 0

    @patch("builtins.input")
    def test_run_without_pre_approved_prompts(self, mock_input) -> None:
        mock_input.return_value = "approve"
        sandbox = Sandbox()
        result = sandbox.run("print(42)", pre_approved=False)

        assert result.exit_code == 0
        assert "42" in result.stdout
        mock_input.assert_called_once()

    @patch("builtins.input")
    def test_run_rejected_raises_approval_denied(self, mock_input) -> None:
        mock_input.return_value = "reject"
        sandbox = Sandbox()

        with pytest.raises(SandboxApprovalDeniedError, match="rejected"):
            sandbox.run("print('bad')", pre_approved=False)

    @patch("builtins.input")
    def test_run_rejected_does_not_execute_code(self, mock_input) -> None:
        """A rejection must never execute the code (rule 3)."""
        mock_input.return_value = "reject"
        sandbox = Sandbox()

        with pytest.raises(SandboxApprovalDeniedError):
            sandbox.run("import os; os.system('echo pwned')", pre_approved=False)

    @patch("builtins.input")
    def test_approval_case_insensitive(self, mock_input) -> None:
        mock_input.return_value = "  APPROVE  "
        sandbox = Sandbox()
        result = sandbox.run("print('ok')", pre_approved=False)

        assert result.exit_code == 0


class TestExtractCodeFromDeliverable:
    """Tests for code extraction from Worker deliverables."""

    def test_extract_fenced_python_block(self) -> None:
        deliverable = "Here is code:\n```python\nprint('hello')\n```\nDone."
        result = extract_code_from_deliverable(deliverable)
        assert result == "print('hello')"

    def test_extract_plain_text_no_fence(self) -> None:
        code = "print('plain')"
        result = extract_code_from_deliverable(code)
        assert result == "print('plain')"

    def test_extract_multiple_fences_returns_first(self) -> None:
        deliverable = "```python\nx = 1\n```\nMore text.\n```python\ny = 2\n```"
        result = extract_code_from_deliverable(deliverable)
        assert result == "x = 1"

    def test_extract_unclosed_fence_returns_content_after_opener(self) -> None:
        deliverable = "```python\nprint('no close fence')"
        result = extract_code_from_deliverable(deliverable)
        assert result == "print('no close fence')"

    def test_extract_fence_without_language_tag(self) -> None:
        deliverable = "```\nprint('no lang')\n```"
        result = extract_code_from_deliverable(deliverable)
        assert result == "print('no lang')"

    def test_extract_dedents_indented_code(self) -> None:
        deliverable = "```python\n    print('indented')\n    x = 1\n```"
        result = extract_code_from_deliverable(deliverable)
        assert result == "print('indented')\nx = 1"

    def test_extract_empty_deliverable(self) -> None:
        result = extract_code_from_deliverable("")
        assert result == ""
