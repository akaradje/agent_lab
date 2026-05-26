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
    """

    def __init__(self, max_tokens: int, max_usd: float) -> None:
        self._max_tokens = max_tokens
        self._max_usd = max_usd
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost = 0.0

    @property
    def total_tokens(self) -> int:
        return self._total_input_tokens + self._total_output_tokens

    @property
    def total_cost(self) -> float:
        return self._total_cost

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
