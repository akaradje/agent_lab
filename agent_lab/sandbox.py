"""Sandboxed code execution with human-approval gating.

Runs code in a subprocess with a wall-clock timeout and captured output.
Requires explicit human approval before any execution (rule 3).

Limitation: subprocess isolation does not provide network or filesystem
containment. The recommended hardening is to run inside a container or VM
(Docker, Firecracker, or Windows Sandbox). This module documents where
container isolation would plug in — search for CONTAINER-UPGRADE.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from dataclasses import dataclass


class SandboxApprovalDeniedError(Exception):
    """Raised when a human rejects execution at the approval prompt."""


class SandboxTimeoutError(Exception):
    """Raised when code execution exceeds the wall-clock timeout."""


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


DEFAULT_TIMEOUT_SECONDS = 30


class Sandbox:
    """Runs code in a subprocess. Always approval-gated (rule 3).

    When called from the pipeline, the pipeline's human gate handles approval
    and the sandbox is invoked with *pre_approved=True*. When used standalone,
    the sandbox prompts directly.
    """

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, code: str, *, pre_approved: bool = False) -> SandboxResult:
        """Execute *code* in a subprocess.

        If *pre_approved* is False (the default), prompts the human to review
        the code and type ``approve`` before execution proceeds.  The prompt
        goes to stdout / stdin and is intentionally not configurable — rule 3
        requires an explicit human decision.
        """
        if not pre_approved:
            self._request_approval(code)
        return self._execute(code)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _request_approval(self, code: str) -> None:
        self._display_code(code)
        response = input("\nApprove execution? [approve / reject]: ").strip().lower()
        if response != "approve":
            raise SandboxApprovalDeniedError(
                f"Execution rejected (response was '{response}')."
            )

    @staticmethod
    def _display_code(code: str) -> None:
        separator = "=" * 60
        print(f"\n{separator}")
        print("SANDBOX — code awaiting approval:")
        print(separator)
        print(code)
        print(separator)

    def _execute(self, code: str) -> SandboxResult:
        # CONTAINER-UPGRADE: replace the subprocess call with a container
        # runtime (e.g. `docker run --rm --network none ...`) to add
        # network and filesystem isolation.
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            return SandboxResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            # subprocess.run was called with text=True, so exc.stdout/stderr
            # are str when present. Do not call .decode() — it raises
            # AttributeError on str.
            return SandboxResult(
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                exit_code=-1,
                timed_out=True,
            )


def extract_code_from_deliverable(deliverable: str) -> str:
    """Best-effort extraction of Python code from a Worker deliverable.

    Handles two common patterns:
    1. A fenced code block (```python ... ```).
    2. Plain-text that is already code.
    """
    stripped = deliverable.strip()
    marker = "```python"
    if marker in stripped:
        start = stripped.index(marker) + len(marker)
        # Find closing fence after the opening
        rest = stripped[start:]
        end = rest.find("```")
        if end != -1:
            return textwrap.dedent(rest[:end]).strip()
        # No closing fence — take everything after the opener
        return textwrap.dedent(rest).strip()
    # If there's a ``` without python marker, try that
    if "```" in stripped:
        start = stripped.index("```") + 3
        rest = stripped[start:]
        # Skip a language tag line if present
        if "\n" in rest:
            first_newline = rest.index("\n")
            maybe_lang = rest[:first_newline].strip()
            if maybe_lang and not maybe_lang.startswith(" "):
                rest = rest[first_newline + 1 :]
        end = rest.find("```")
        if end != -1:
            return textwrap.dedent(rest[:end]).strip()
        return textwrap.dedent(rest).strip()
    return stripped
