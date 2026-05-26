# DEEPSEEK_REFERENCE.md

Provider facts for this project. Pulled from DeepSeek's docs as of late
May 2026. Verify pricing against the live docs before relying on it —
DeepSeek V4 Pro is mid-promo and its price changes after 2026-05-31.

## API access

- DeepSeek V4 supports the OpenAI ChatCompletions API. Use the `openai`
  Python SDK with `base_url="https://api.deepseek.com"`.
- Key: environment variable `DEEPSEEK_API_KEY`.
- Models: `deepseek-v4-pro` (stronger reasoning) and `deepseek-v4-flash`
  (faster, cheaper). Both support a 1M-token context window.
- The older `deepseek-chat` / `deepseek-reasoner` aliases are being retired
  (after 2026-07-24). Use the explicit `deepseek-v4-*` IDs.

## Reasoning modes

V4 models support three modes via the `reasoning_effort` parameter:
- Non-think — fast responses, lowest cost.
- Think High — logical analysis. Use for design/review agents.
- Think Max — maximum effort, highest cost. Use sparingly.

Thinking is also toggled via an `extra_body={"thinking": {"type": ...}}`
field on the ChatCompletions call. Check the current DeepSeek docs for the
exact parameter shape when implementing `llm_client.py`.

## Pricing — VERIFY BEFORE USE, PROMO ACTIVE

Approximate, USD per million tokens, as of late May 2026:
- `deepseek-v4-flash`: ~$0.14 input / ~$0.28 output.
- `deepseek-v4-pro`: ~$0.44 input / ~$0.87 output — this is a discounted
  promo rate. The price is scheduled to change after 2026-05-31.

Because of this, `config.py` keeps prices as named constants with a comment.
When the promo ends, the user edits those constants in one place.

## Model routing for this project

| Agent        | Model               | Reasoning   |
|--------------|---------------------|-------------|
| Orchestrator | deepseek-v4-flash   | Non-think   |
| Researcher   | deepseek-v4-flash   | Think High  |
| Architect    | deepseek-v4-pro     | Think High  |
| Worker       | deepseek-v4-flash   | Think High  |
| Critic       | deepseek-v4-pro     | Think High  |
| Sandbox      | deepseek-v4-flash   | Non-think   |

Rationale: DeepSeek recommends defaulting to Flash and escalating to Pro
only where it measurably helps. Pro is reserved for the two agents whose
job is hard reasoning — designing the solution and adversarially reviewing
it. If a run's quality is poor, the first experiment is to move Worker to
Pro and re-measure, before moving everything to Pro.
