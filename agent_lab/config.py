# Hard ceilings — when any is hit, the run stops.
# Basis for MAX_TOTAL_TOKENS: a normal heavy research run (RESEARCH_BRIEF_01,
# Worker producing a ~17 KB harness with 3 QA rounds) used ~90k tokens. 250k
# leaves headroom for larger briefs while still catching a runaway loop —
# any actual loop would blow far past 250k well before it could do damage.
MAX_TOTAL_TOKENS = 250_000
MAX_USD = 1.00
MAX_QA_ROUNDS = 3

# USD per million tokens. DeepSeek V4 Pro is under a promo discount until
# 2026-05-31; update the dict entries below when pricing changes.
PRICING: dict[str, tuple[float, float]] = {
    "deepseek-v4-flash": (0.14, 0.28),
    "deepseek-v4-pro": (0.44, 0.87),
}

# Maps agent name -> (model, reasoning_effort).
AGENT_MODELS: dict[str, tuple[str, str]] = {
    "orchestrator": ("deepseek-v4-flash", "low"),
    "researcher": ("deepseek-v4-flash", "high"),
    "architect": ("deepseek-v4-pro", "high"),
    "worker": ("deepseek-v4-flash", "high"),
    "critic": ("deepseek-v4-pro", "high"),
    "sandbox": ("deepseek-v4-flash", "low"),
}
