# RESEARCH_BRIEF_01.md

The first real research brief for the pipeline. Scoped deliberately small:
it builds a working experiment harness and validates ONE technique. Briefs
02 and 03 add the remaining techniques once the harness is proven.

Feed the "Brief" section below to the pipeline. The rest of this file is
context for you, the human — not for the pipeline.

---

## Why this brief is scoped this way

The full research question compares three Critic-stringency techniques on
Pass Rate and Cost. That is too much for one pipeline run — a single
deliverable that big is hard to debug and likely to fail midway.

So Brief 01 builds the **measurement harness** and wires in only technique
1 (Rule-Based Checklist). If the harness runs and produces real numbers for
one technique, it will produce them for three. Briefs 02 and 03 then add
CoT and Consensus Voting as small, low-risk increments.

Critical point: the answer to the research question must come from
**executing the harness and reading its printed metrics**, never from a
Critic agent's opinion of the code. The deliverable is a program that
runs and prints results.

---

## Brief — give this to the pipeline

> Build a runnable Python experiment harness that measures how strict a
> code-reviewing "Critic" should be. This brief covers the harness plus
> ONE review technique; later briefs add two more.
>
> **What to build:**
>
> 1. A small fixed benchmark of 6 short Python coding tasks. Each task has:
>    a prompt string, and a set of hidden `assert`-based unit tests that
>    define correct behavior. Tasks must vary in difficulty (2 easy, 2
>    medium, 2 with a known subtle-bug trap such as input mutation or an
>    off-by-one boundary).
>
> 2. A `solve(task)` step: calls an LLM once to produce a candidate
>    solution for a task.
>
> 3. A `review(solution, task)` step implementing **Technique 1 only —
>    Rule-Based Checklist**: the reviewer LLM is given a fixed numbered
>    checklist and must return a structured JSON verdict
>    `{"approved": bool, "issues": [...]}`.
>
> 4. A bounded revise loop: if the review rejects, the solver gets one
>    revision attempt with the issues fed back. The loop is capped at a
>    `MAX_REVIEW_ROUNDS` constant (default 3). It must be impossible for
>    the loop to run unbounded.
>
> 5. An evaluation step: run each task's hidden unit tests against the
>    final solution and record pass/fail.
>
> 6. A metrics report printed at the end: per-task pass/fail, overall
>    **Pass Rate** (fraction of the 6 tasks whose final solution passes
>    its hidden tests), total **token count** and **estimated cost**, and
>    the **number of review rounds** used per task.
>
> **Constraints:**
> - All LLM calls go through one wrapper function so token usage is
>   counted in one place. No uncounted calls.
> - The revise loop MUST be bounded by `MAX_REVIEW_ROUNDS`. No unbounded
>   `while`.
> - The harness must be parameterized so a future brief can plug in a
>   different `review()` implementation without rewriting the harness.
> - Output the metrics as both a printed table and a JSON file on disk.
>
> **What NOT to do in this brief:**
> - Do not implement Chain-of-Thought or Consensus Voting review yet.
> - Do not build a UI, a database, or a config system beyond simple
>   constants.

---

## Deliverables (what a complete run should produce)

1. A single runnable Python file (or small package) — the harness.
2. The 6-task benchmark with hidden unit tests, embedded or in a data file.
3. A printed metrics table + a metrics JSON file.

## Evaluation metrics — how YOU judge if the run succeeded

This brief succeeds if the harness itself is sound. Judge it on:

- **MUST: it runs.** `python <harness>` completes without error and prints
  a metrics table.
- **MUST: the loop is bounded.** Inspect the code — the revise loop is
  capped by `MAX_REVIEW_ROUNDS`. No unbounded `while` around an LLM call.
  This directly answers the "no infinite loop" part of your question.
- **MUST: metrics are real.** Pass Rate is computed by actually executing
  the hidden unit tests, not by asking an LLM. Token count is summed from
  the wrapper. Trace one task by hand to confirm.
- **MUST: the trap tasks discriminate.** At least one of the 2 subtle-bug
  tasks should be one where a naive solution fails its hidden tests — if
  all 6 tasks pass trivially, the benchmark is too easy to compare
  techniques later. 
- **SHOULD: the harness is pluggable.** The `review()` function is
  swappable — a later brief can drop in CoT without touching the harness.
- **SHOULD: cost is sane.** A full 6-task run is well under your pipeline's
  `MAX_USD` ceiling.

## What this brief does NOT answer yet

It does not tell you which technique is best — only Technique 1 is built.
It produces the *baseline* numbers (Rule-Based Checklist Pass Rate + Cost).
Brief 02 adds CoT and re-runs; Brief 03 adds Consensus Voting. Only after
all three are measured on the same 6-task benchmark can you compare them.

## After this run

- Harness sound -> proceed to RESEARCH_BRIEF_02 (add CoT review).
- Harness broken -> the transcript shows which stage failed; fix and re-run
  before adding techniques. Do not add techniques to a broken harness.
