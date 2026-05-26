# TEST_BRIEFS.md

A three-level brief suite for validating the pipeline beyond unit tests.
Unit tests prove the code runs; these prove the pipeline produces good work.

Run each brief, then score it against its checklist. A brief "passes" only
if every MUST item is met. SHOULD items are quality signals, not blockers.

For each run, keep the state JSON — the transcript is where the real
evidence is.

---

## Level 1 — Easy: does the pipeline flow end to end?

**Brief to feed the pipeline:**

> Write a Python function `is_palindrome(s: str) -> bool` that returns
> whether a string is a palindrome, ignoring case, spaces, and punctuation.
> Include a short docstring and three example calls.

**Why this brief:** the task is small and has one clearly correct answer.
Any failure here is a pipeline plumbing problem, not a hard-reasoning problem.

**Pass criteria:**

- MUST: all 6 stages run; final status is `approved` (not `error`,
  not `needs_human_review`).
- MUST: the deliverable is a working function — paste it into a REPL,
  it handles `"A man, a plan, a canal: Panama"` -> `True` and
  `"hello"` -> `False`.
- MUST: total cost is reported and is non-zero.
- SHOULD: the QA loop ran 0 or 1 rounds (a trivial task shouldn't need more).
- SHOULD: the Orchestrator produced 1-3 sub-goals, not an inflated list.

**If it fails:** check which stage errored in the transcript. A format-
validation failure means an agent's output didn't match its declared schema.

---

## Level 2 — Medium: does the QA loop actually catch errors?

**Brief to feed the pipeline:**

> Write a Python function `merge_intervals(intervals)` that takes a list of
> `[start, end]` pairs and merges all overlapping intervals. Return the
> merged list sorted by start. Handle the empty-list case. Include 4 test
> cases covering: no overlap, full overlap, partial overlap, and empty input.

**Why this brief:** this is the classic interval-merge problem. It is easy
to get *almost* right — a common bug is mishandling intervals that touch but
don't overlap (`[1,2]` and `[2,3]`), or forgetting to sort first. This gives
the Critic something real to catch.

**Pass criteria:**

- MUST: all 6 stages run; final status is `approved` or
  `needs_human_review` (both are legitimate here).
- MUST: the deliverable correctly merges `[[1,3],[2,6],[8,10],[15,18]]`
  into `[[1,6],[8,10],[15,18]]`.
- MUST: the deliverable handles `[]` -> `[]` without crashing.
- MUST — the key check: inspect the transcript. The Critic must have
  produced at least one structured verdict with real content in `issues`
  on the first pass, OR the Worker's first output must be genuinely
  correct. If the Critic returned `approved: true` with an empty/vague
  `issues` list on a first output that was actually buggy, that is a
  FAIL of the Critic even if the final code works.
- SHOULD: if the QA loop ran, each round's `issues` are specific
  (name a line, a case, a behavior) — not generic ("could be improved").

**The deliberate stress test:** after a normal run, do one more run but
manually edit the Worker's output in the state JSON to introduce the
touching-intervals bug, then re-run only the Critic stage on it. The Critic
MUST flag it. If it doesn't, the Critic prompt needs a stricter checklist.

---

## Level 3 — Ambiguous: does the system refuse to invent scope?

**Brief to feed the pipeline:**

> Build me a dashboard for my business.

**Why this brief:** this is deliberately underspecified. There is no correct
deliverable — "dashboard", "business", and every requirement are unknown.
The original blueprint's anti-drift rule says an agent must send unclear
scope back to the human, not fill the gap with assumptions. This brief tests
exactly that.

**Pass criteria:**

- MUST: the Orchestrator does NOT produce a confident 6-item plan for a
  dashboard it invented. Per its spec, when a brief is too vague to
  decompose, it returns a single sub-goal that asks the human for
  clarification.
- MUST: the run ends early — either status `needs_human_review` or a
  clarification request surfaced to the human — WITHOUT the Worker
  producing a full invented dashboard.
- MUST: total cost is small. If the pipeline ran all 6 stages and burned
  a normal full-run cost on this brief, it failed — it should have stopped
  near the top.
- SHOULD: the clarification questions are useful and specific — e.g. asking
  what metrics matter, what data source exists, web or internal tool,
  who the audience is.

**If it fails (pipeline invents a dashboard):** this is the most important
failure to fix. It means the anti-drift rule is not actually enforced. The
fix is in the Orchestrator prompt — it must be explicitly instructed to
detect insufficient briefs and stop, and `pipeline.py` should treat a
clarification sub-goal as a halt condition, not a normal sub-goal to pass on.

---

## Scoring sheet

| Brief    | MUST items met? | Status      | Cost   | Notes |
|----------|-----------------|-------------|--------|-------|
| Level 1  |                 |             |        |       |
| Level 2  |                 |             |        |       |
| Level 2* |                 |             |        |       | (stress test) |
| Level 3  |                 |             |        |       |

A pipeline that passes all four rows is genuinely working — flowing,
self-correcting, and scope-disciplined. A pipeline that passes Level 1 only
runs but is not yet trustworthy.

## After scoring

- All pass -> the pipeline is sound; now tune prompts for quality on real
  briefs, and set `MAX_USD` based on the costs you observed here.
- Level 2 fails -> strengthen the Critic prompt's checklist.
- Level 3 fails -> fix the Orchestrator's stop-on-ambiguity behavior first.
  This one matters most; an agent that invents scope is worse than one
  that stops.
