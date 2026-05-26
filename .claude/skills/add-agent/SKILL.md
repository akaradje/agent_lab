---
name: add-agent
description: Use when adding a new agent to the pipeline, or modifying an existing agent's role or prompt. Ensures the new agent follows the budget, format-validation, and scope rules and does not break the bounded QA loop.
---

# Adding or modifying a pipeline agent

Follow these steps in order. Do not skip the checklist at the end.

## 1. Define the role before writing code

A new agent needs a one-sentence role and an explicit output format.
If you cannot state the output format precisely, the agent is not ready
to build. Add the role to `specs/AGENT_ROLES.md`.

## 2. Write the prompt as a separate file

Create `specs/prompts/<name>.md`. The prompt MUST:
- State the single role and forbid scope expansion.
- Declare the exact output format (prefer JSON for anything a later stage
  parses).
- Tell the agent that "I don't know" / "the input is unusable" is a valid,
  preferred response over fabrication.

## 3. Implement on the `Agent` base class

The new agent subclasses `Agent`. It receives the budgeted `LLMClient` —
it must NOT import or call the `openai` SDK directly. One `run()` method.

## 4. Validate output

After the LLM call, parse and validate the output against the declared
format. On malformed output: retry exactly once, then raise — never let
malformed data flow downstream.

## 5. Wire into the pipeline deliberately

Adding an agent to `pipeline.py` changes cost and latency. If the agent
sits inside the QA loop, confirm `MAX_QA_ROUNDS` still bounds total calls.
Never introduce an unbounded loop.

## 6. Test

Add `tests/test_<name>.py` with a mocked `LLMClient`. Cover: normal output,
malformed-then-retry, and (if applicable) the "input unusable" path.

## Checklist before considering it done

- [ ] Role recorded in `AGENT_ROLES.md`
- [ ] Prompt file created with explicit output format
- [ ] No direct SDK calls — uses budgeted `LLMClient`
- [ ] Output is validated; malformed output fails loudly
- [ ] Loop bounds (`MAX_QA_ROUNDS`) still hold
- [ ] Test file added and passing
- [ ] No new v1-out-of-scope capability introduced
