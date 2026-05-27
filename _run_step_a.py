"""Driver: run Step A through the full pipeline, bypassing the CLI to
avoid shell-tokenization issues with the long multi-line brief."""

from pathlib import Path

from agent_lab.budget import BudgetTracker
from agent_lab.config import MAX_TOTAL_TOKENS, MAX_USD
from agent_lab.llm_client import LLMClient
from agent_lab.pipeline import run_pipeline


def main() -> None:
    brief = Path("_brief_step_a.txt").read_text(encoding="utf-8")
    budget = BudgetTracker(max_tokens=MAX_TOTAL_TOKENS, max_usd=MAX_USD)
    llm = LLMClient(budget=budget)
    state = run_pipeline(brief, llm, yes=True)
    Path("run_output_step_a.json").write_text(
        __import__("json").dumps(
            {
                "brief": state.brief,
                "artifacts": state.artifacts,
                "transcript": state.transcript,
                "status": state.status,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nRun complete. Status: {state.status}")
    print(f"Artifacts: {len(state.artifacts)}")
    print(budget.summary())


if __name__ == "__main__":
    main()
