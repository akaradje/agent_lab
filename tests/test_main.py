from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent_lab.main import main
from agent_lab.state import RunState


def _mock_state() -> RunState:
    state = RunState(brief="test brief")
    state.status = "complete"
    state.artifacts = [
        {"stage": "orchestrator", "agent": "Orch", "sub_goals": []},
        {"stage": "worker", "agent": "Worker", "deliverable": "print('hi')"},
    ]
    state.transcript = ["[orchestrator] done", "[worker] done"]
    return state


def _mock_main_deps(state, tmp_dir, argv, mock_print=False):
    """Patch sys.argv, LLMClient, and run/resume_pipeline in one call.

    Returns (out_path, patches_dict) so the caller can inspect mock calls.
    """
    out = Path(tmp_dir) / "out.json"
    final_argv = [*argv, "--output", str(out)]
    patches = {
        "sys.argv": patch.object(sys, "argv", final_argv),
        "llm_client": patch("agent_lab.main.LLMClient"),
        "run_pipeline": patch("agent_lab.main.run_pipeline", return_value=state),
        "resume_pipeline": patch("agent_lab.main.resume_pipeline", return_value=state),
    }
    if mock_print:
        patches["print"] = patch("builtins.print")

    return out, patches


class TestMainBrief:
    """Tests for the --brief CLI path."""

    def test_brief_with_yes_runs_and_writes_output(self) -> None:
        state = _mock_state()

        with TemporaryDirectory() as tmp:
            out, p = _mock_main_deps(state, tmp, ["main", "--brief", "hello", "--yes"])
            with p["sys.argv"], p["llm_client"], p["run_pipeline"] as mock_run:
                main()

            mock_run.assert_called_once()
            assert out.exists()
            loaded = RunState.load(out)
            assert loaded.status == "complete"

    def test_brief_prints_cost_report(self) -> None:
        state = _mock_state()

        with TemporaryDirectory() as tmp:
            args = ["main", "--brief", "hello", "--yes"]
            out, p = _mock_main_deps(state, tmp, args, mock_print=True)
            with p["sys.argv"], p["llm_client"], p["run_pipeline"], p["print"] as mp:
                main()

            printed = "".join(str(a) for call in mp.call_args_list for a in call[0])
            assert "Cost Report" in printed

    def test_brief_uses_default_output_path(self) -> None:
        state = _mock_state()

        with TemporaryDirectory() as tmp:
            out, p = _mock_main_deps(state, tmp, ["main", "--brief", "x", "--yes"])
            with p["sys.argv"], p["llm_client"], p["run_pipeline"]:
                main()
            assert out.exists()


class TestMainResume:
    """Tests for the --resume CLI path."""

    def test_resume_loads_state_and_resumes(self) -> None:
        state = _mock_state()
        state.status = "rejected_at_gate_final"

        with TemporaryDirectory() as tmp:
            in_path = Path(tmp) / "in.json"
            state.save(in_path)

            out, p = _mock_main_deps(state, tmp, ["main", "--resume", str(in_path), "--yes"])
            with p["sys.argv"], p["llm_client"], p["resume_pipeline"] as mock_resume:
                main()

            mock_resume.assert_called_once()
            assert out.exists()

    def test_resume_prints_state_summary(self) -> None:
        state = _mock_state()
        state.status = "rejected_at_gate_final"

        with TemporaryDirectory() as tmp:
            in_path = Path(tmp) / "in.json"
            state.save(in_path)

            args = ["main", "--resume", str(in_path), "--yes"]
            out, p = _mock_main_deps(state, tmp, args, mock_print=True)
            with p["sys.argv"], p["llm_client"], p["resume_pipeline"], p["print"] as mp:
                main()

            printed = "".join(str(a) for call in mp.call_args_list for a in call[0])
            assert "Loaded run:" in printed
            assert "rejected_at_gate_final" in printed
            assert "Resume complete" in printed

    def test_resume_prints_output_path(self) -> None:
        state = _mock_state()

        with TemporaryDirectory() as tmp:
            in_path = Path(tmp) / "in.json"
            state.save(in_path)

            args = ["main", "--resume", str(in_path), "--yes"]
            out, p = _mock_main_deps(state, tmp, args, mock_print=True)
            with p["sys.argv"], p["llm_client"], p["resume_pipeline"], p["print"] as mp:
                main()

            printed = "".join(str(a) for call in mp.call_args_list for a in call[0])
            assert str(out) in printed


class TestMainErrors:
    """Tests for CLI error handling."""

    def test_no_args_exits_with_error(self) -> None:
        with patch.object(sys, "argv", ["main"]):
            with patch("agent_lab.main.LLMClient"):
                try:
                    main()
                except SystemExit as exc:
                    assert exc.code != 0
                else:
                    raise AssertionError("Expected SystemExit")

    def test_mutually_exclusive_args_exits_with_error(self) -> None:
        with patch.object(sys, "argv", ["main", "--brief", "x", "--resume", "y.json"]):
            with patch("agent_lab.main.LLMClient"):
                try:
                    main()
                except SystemExit as exc:
                    assert exc.code != 0
                else:
                    raise AssertionError("Expected SystemExit")
