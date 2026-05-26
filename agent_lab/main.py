from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from agent_lab.budget import BudgetTracker
from agent_lab.config import MAX_TOTAL_TOKENS, MAX_USD
from agent_lab.llm_client import LLMClient
from agent_lab.pipeline import resume_pipeline, run_pipeline
from agent_lab.state import RunState


def _yes_flag_allowed() -> bool:
    """--yes auto-approves both human gates. Per BUILD_PLAN Phase 5 this is
    permitted ONLY for tests. Allow it under pytest (PYTEST_CURRENT_TEST set
    by pytest itself) or with an explicit AGENT_LAB_ALLOW_YES=1 opt-in.
    """
    return (
        os.environ.get("AGENT_LAB_ALLOW_YES") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
    )


def _print_state_summary(state: RunState) -> None:
    """Print a summary of a loaded run state for the resume command."""
    print(f"\nLoaded run: {state.brief[:80]}...")
    print(f"  Status:     {state.status}")
    print(f"  Artifacts:  {len(state.artifacts)}")
    stages = [a.get("stage") for a in state.artifacts]
    print(f"  Stages:     {' -> '.join(stages) if stages else '(none)'}")
    print(f"  Transcript: {len(state.transcript)} entries")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Lab pipeline runner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--brief", help="Project brief to execute")
    mode.add_argument(
        "--resume",
        help="Resume from a saved run state JSON file",
    )
    parser.add_argument(
        "--output",
        default="run_output.json",
        help="Path to write the run state JSON (default: run_output.json)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve all human gates (for tests only, never the default)",
    )
    args = parser.parse_args()

    if args.yes and not _yes_flag_allowed():
        print(
            "ERROR: --yes auto-approves the human gate and is only available "
            "for tests. Set AGENT_LAB_ALLOW_YES=1 to override, or remove --yes "
            "and respond at the gate prompt.",
            file=sys.stderr,
        )
        sys.exit(2)

    budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
    llm = LLMClient(budget)

    if args.resume:
        resume_path = Path(args.resume)
        state = RunState.load(resume_path)
        _print_state_summary(state)
        state = resume_pipeline(state, llm, yes=args.yes)
        out_path = Path(args.output)
        state.save(out_path)
        print(f"\nResume complete. Status: {state.status}")
        print(f"Output written to {out_path}")
        return

    state = run_pipeline(args.brief, llm, yes=args.yes)
    state.save(Path(args.output))
    print(f"\nRun complete. Status: {state.status}")
    print(f"Artifacts: {len(state.artifacts)}")
    print(f"Output written to {args.output}")
    print(budget.summary())


if __name__ == "__main__":
    main()
