from __future__ import annotations

import argparse
from pathlib import Path

from agent_lab.budget import BudgetTracker
from agent_lab.config import MAX_TOTAL_TOKENS, MAX_USD
from agent_lab.llm_client import LLMClient
from agent_lab.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Lab pipeline runner")
    parser.add_argument("--brief", required=True, help="Project brief to execute")
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

    budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
    llm = LLMClient(budget)
    state = run_pipeline(args.brief, llm, yes=args.yes)
    state.save(Path(args.output))
    print(f"Run complete. Status: {state.status}")
    print(f"Artifacts: {len(state.artifacts)}")
    print(f"Output written to {args.output}")


if __name__ == "__main__":
    main()
