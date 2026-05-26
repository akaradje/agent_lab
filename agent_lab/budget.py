from agent_lab.config import PRICING


class BudgetExceededError(Exception):
    """Raised when a token or cost ceiling is crossed."""

    def __init__(self, message: str, tokens: int, cost: float) -> None:
        super().__init__(message)
        self.tokens = tokens
        self.cost = cost


class BudgetTracker:
    """Tracks cumulative token usage and cost across all LLM calls in a run.

    Looks up per-model pricing from config.PRICING and raises BudgetExceeded
    when either the token ceiling or the USD ceiling is crossed.

    Soft warning: when cumulative token usage crosses WARNING_THRESHOLD of
    max_tokens, a single warning line is appended to the attached transcript
    (if any). The run is NOT stopped — only the hard ceiling stops it.
    """

    WARNING_THRESHOLD = 0.8

    def __init__(
        self,
        max_tokens: int,
        max_usd: float,
        transcript: list[str] | None = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._max_usd = max_usd
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost = 0.0
        self._call_count = 0
        self._transcript = transcript
        self._warning_emitted = False

    def attach_transcript(self, transcript: list[str]) -> None:
        """Attach a transcript list to receive soft-warning messages.

        Called by the pipeline after RunState is created so the BudgetTracker
        (constructed earlier in main.py) can log the 80% warning to the run's
        actual transcript.
        """
        self._transcript = transcript

    @property
    def total_tokens(self) -> int:
        return self._total_input_tokens + self._total_output_tokens

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def call_count(self) -> int:
        return self._call_count

    def remaining(self) -> tuple[int, float]:
        return (
            self._max_tokens - self.total_tokens,
            round(self._max_usd - self._total_cost, 6),
        )

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        input_price, output_price = PRICING[model]
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        call_cost = input_cost + output_cost

        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cost += call_cost
        self._call_count += 1

        self._maybe_emit_soft_warning()

        if self.total_tokens > self._max_tokens:
            raise BudgetExceededError(
                f"Token ceiling {self._max_tokens} exceeded: {self.total_tokens}",
                self.total_tokens,
                round(self._total_cost, 6),
            )
        if self._total_cost > self._max_usd:
            raise BudgetExceededError(
                f"USD ceiling ${self._max_usd:.2f} exceeded: ${self._total_cost:.6f}",
                self.total_tokens,
                round(self._total_cost, 6),
            )

    def _maybe_emit_soft_warning(self) -> None:
        """Append a single warning line when 80% of max_tokens is crossed.
        Fires at most once per run; subsequent crossings are no-ops."""
        if self._warning_emitted:
            return
        threshold = self._max_tokens * self.WARNING_THRESHOLD
        if self.total_tokens < threshold:
            return
        self._warning_emitted = True
        pct = round(self.total_tokens / self._max_tokens * 100)
        msg = (
            f"[budget] WARNING: {self.total_tokens:,} tokens used "
            f"(~{pct}% of ceiling {self._max_tokens:,}); soft-warning only — "
            f"run continues but consider trimming the next prompt"
        )
        if self._transcript is not None:
            self._transcript.append(msg)

    def summary(self) -> str:
        """Return a human-readable cost report for the end of a run."""
        tokens_remaining, usd_remaining = self.remaining()
        lines = [
            "-" * 40,
            " Cost Report",
            "-" * 40,
            f"  LLM calls:          {self._call_count}",
            f"  Input tokens:       {self._total_input_tokens:,}",
            f"  Output tokens:      {self._total_output_tokens:,}",
            f"  Total tokens:       {self.total_tokens:,}  (ceiling: {self._max_tokens:,})",
            f"  Total cost:         ${self._total_cost:.6f}  (ceiling: ${self._max_usd:.2f})",
            f"  Remaining tokens:   {tokens_remaining:,}",
            f"  Remaining budget:   ${usd_remaining:.6f}",
            "-" * 40,
        ]
        return "\n".join(lines)
