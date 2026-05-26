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

    def test_timeout_with_buffered_output_does_not_raise(self) -> None:
        """Regression: when a script prints to stdout/stderr and then exceeds
        the timeout, subprocess captures the output as str (text=True). The
        timeout branch used to call .decode() on it and raise AttributeError.
        """
        sandbox = Sandbox(timeout_seconds=1)
        code = (
            "import sys, time\n"
            "print('out before sleep', flush=True)\n"
            "sys.stderr.write('err before sleep\\n')\n"
            "sys.stderr.flush()\n"
            "time.sleep(10)\n"
        )
        result = sandbox._execute(code)

        assert result.timed_out is True
        assert result.exit_code == -1
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)


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

    def test_extract_code_with_inner_backticks_in_string_literal(self) -> None:
        """Regression: code that itself manipulates markdown fences (a
        common pattern in this project's deliverables) contains the literal
        characters ``` inside string literals. The OLD extractor matched
        the first inner ``` as the closing fence and truncated the code
        mid-string, producing a SyntaxError when the Sandbox ran it.
        The new extractor requires the closing ``` to be alone on a line."""
        deliverable = (
            "Here is the harness:\n"
            "```python\n"
            "def strip_fences(response: str) -> str:\n"
            '    code = response.strip()\n'
            '    if code.startswith("```python"):\n'
            "        code = code[9:].strip()\n"
            '    if code.endswith("```"):\n'
            "        code = code[:-3].strip()\n"
            "    return code\n"
            "```\n"
            "End of deliverable."
        )
        result = extract_code_from_deliverable(deliverable)

        # All inner-backtick lines must survive intact
        assert 'if code.startswith("```python"):' in result
        assert 'if code.endswith("```"):' in result
        # The extracted code must parse — this is what the Sandbox would do
        compile(result, "<extracted>", "exec")

    def test_extract_code_with_inner_backticks_must_run(self) -> None:
        """End-to-end check: the extracted code, when executed by Python,
        must run without SyntaxError. This is exactly the path that failed
        in the RESEARCH_BRIEF_01 run."""
        deliverable = (
            "```python\n"
            'TEMPLATE = "wrap me in ``` fences"\n'
            "print(TEMPLATE)\n"
            "```"
        )
        code = extract_code_from_deliverable(deliverable)
        ns: dict = {}
        exec(compile(code, "<extracted>", "exec"), ns)
        # The TEMPLATE constant should survive intact, backticks and all.
        assert ns["TEMPLATE"] == "wrap me in ``` fences"

    def test_extract_no_fences_treats_whole_text_as_code(self) -> None:
        """Explicit case: no fences anywhere — extractor returns the whole
        deliverable (stripped) as code."""
        deliverable = "def foo():\n    return 42\n\nfoo()"
        result = extract_code_from_deliverable(deliverable)
        assert result == "def foo():\n    return 42\n\nfoo()"

    def test_extract_multiple_fences_takes_first_complete_block(self) -> None:
        """When there are multiple fenced blocks, return the first whose
        closing fence is on its own line — not a longer greedy span that
        would include the second block's code."""
        deliverable = (
            "```python\n"
            "x = 1\n"
            "```\n"
            "Some prose between blocks.\n"
            "```python\n"
            "y = 2\n"
            "```"
        )
        result = extract_code_from_deliverable(deliverable)
        assert result == "x = 1"
        assert "y = 2" not in result

    def test_extract_closing_fence_with_trailing_whitespace(self) -> None:
        """A closing fence followed by whitespace (still alone on its line)
        is still a valid closing fence."""
        deliverable = "```python\nprint('ok')\n```   \n"
        result = extract_code_from_deliverable(deliverable)
        assert result == "print('ok')"
