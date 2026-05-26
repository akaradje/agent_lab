# RESEARCH_BRIEF_01.md

The first real research brief for the pipeline. This is **Step A** of a
two-step plan: the pipeline builds and validates the harness SKELETON
under a deterministic test double. **Step B** (run by the human, outside
this pipeline) plugs in a real-LLM reviewer in a separate file and runs
the actual experiment on the same benchmark.

Feed the "Brief" section below to the pipeline. The rest of this file is
context for you, the human — not for the pipeline.

The 6 benchmark tasks are NOT invented by the Worker — they are defined
in `specs/BENCHMARK_6_TASKS.md`, which the Brief references explicitly.

---

## Why this brief is scoped this way

The full research question compares review techniques (Rule-Based Checklist,
Chain-of-Thought, Consensus Voting) on Pass Rate, False Approvals, and
False Rejections. Building the harness AND running real reviewers in one
pipeline pass is too much — too many things can fail at once, and a single
deliverable that big is hard to debug.

So the plan is two steps:

- **Step A — this brief.** The pipeline builds a harness SKELETON. Both
  candidate solutions and the reference reviewer (`mock_review`) are
  deterministic test doubles. The point is to prove the plumbing:
  bounded loop, hidden-test execution, ground-truth comparison, metric
  schema, JSON output, and that `review_fn` is genuinely a pluggable
  parameter. No research conclusion comes out of Step A.
- **Step B — outside this pipeline, run by the human.** A real-LLM
  reviewer lives in a SEPARATE file (this keeps `openai` etc. out of the
  harness). Step B imports `run_experiment` from the harness and passes
  in the real `review_fn`. The benchmark, `solve()`, the loop, and the
  metric calculation are all unchanged from Step A.

Mocked vs pluggable — the controlled-experiment line:

- `solve()` is MOCKED and STAYS mocked in Step B. The candidate code under
  review must be identical across every reviewer technique compared later;
  that is the controlled variable.
- `review()` is the variable under study and is therefore PLUGGABLE. Step
  A ships one reference implementation (`mock_review`) only so the
  pipeline can execute the harness end to end. Step B replaces it.

---

## Brief — give this to the pipeline

> Build a Python experiment harness SKELETON for measuring how strict a
> code-reviewing "Critic" should be. This is Step A of a two-step plan:
> prove the harness plumbing under a deterministic test double. Step B
> (run by the user later, outside this pipeline) imports this harness and
> plugs in a real-LLM reviewer from a SEPARATE file.
>
> **The mocked / pluggable line:**
>
> - `solve()` is MOCKED and stays mocked even in Step B. The candidate
>   code under review is the controlled variable — it must be identical
>   across all reviewer techniques compared later.
> - `review()` is a PLUGGABLE PARAMETER. The harness takes `review_fn` as
>   an argument and just calls `review_fn(solution, task, round_index)`,
>   expecting a verdict dict `{"approved": bool, "issues": [...]}`. The
>   harness does NOT assume `review_fn` is mocked or real.
> - For Step A the brief ships ONE reference implementation,
>   `mock_review`, used solely to exercise the harness end to end. It is
>   a test double and implements NO technique. It is not a research
>   result.
>
> **What to build:**
>
> 1. **The benchmark — 6 tasks specified in `specs/BENCHMARK_6_TASKS.md`.**
>    The Worker MUST implement EXACTLY those 6 tasks as written in that
>    spec: same function names, same `mock_solution` bodies (including
>    the bugs the spec spells out), same `hidden_tests`. The Worker
>    writes the Python; it does NOT design the benchmark. Each task is a
>    dict carrying:
>    - `id` and `prompt` (description, for documentation only).
>    - `hidden_tests`: the assert-based tests from
>      `specs/BENCHMARK_6_TASKS.md`.
>    - `mock_solution`: the candidate code from
>      `specs/BENCHMARK_6_TASKS.md`, preserving the bug where the spec
>      states there is one.
>    - `mock_revision`: a FIXED pre-written revised candidate used if
>      `review_fn` rejects on round 1. The Worker writes this — its
>      contents are not constrained by the spec.
>    - `mock_verdict_initial` / `mock_verdict_revised`: FIXED pre-written
>      reviewer verdicts used ONLY by the reference `mock_review` in
>      Step A. Reasonable default: reject tasks 3-6 on round 1, approve
>      1-2; revised verdicts approve everything. Step B's real
>      `review_fn` ignores these fields.
>    - `ground_truth_passes`: computed by the harness at benchmark setup
>      by executing `hidden_tests` against `mock_solution`. This value
>      must NOT be declared in the source — it is the harness's job to
>      derive it. Expected pattern under the spec: tasks 1-2 produce
>      `True`, tasks 3-6 produce `False` — 2 of 6 pass.
>
>    The calibration encoded in the spec (2 correct, 2 obvious-bug,
>    2 subtle-bug) is the controlled "exam" all reviewer techniques face
>    in Step B. Inventing a different benchmark per run breaks the
>    comparison.
>
> 2. A `solve(task, round_index)` step: returns `task["mock_solution"]`
>    on round 1 and `task["mock_revision"]` on later rounds. No LLM call.
>    No network. This function does not change between Step A and Step B.
>
> 3. A reference `mock_review(solution, task, round_index)`: returns
>    `task["mock_verdict_initial"]` on round 1 and
>    `task["mock_verdict_revised"]` on later rounds. This is a test
>    double — it implements no technique and is NOT a research result.
>    It exists only so the pipeline can run the harness end to end in
>    Step A.
>
> 4. A `run_experiment(review_fn)` function — the pluggable entry point.
>    It executes the benchmark, calls `solve` and `review_fn` per task
>    with a bounded revise loop capped at `MAX_REVIEW_ROUNDS` (default 3),
>    runs `hidden_tests` against the final solution, computes metrics,
>    writes `harness_metrics.json`, prints a metrics table, and returns
>    the metrics dict. `review_fn` must be a parameter — the harness
>    must NOT reference `mock_review` anywhere except in the `__main__`
>    block.
>
> 5. A `__main__` guard at the bottom of the file: when run as a script
>    (`python <harness>.py`), it calls `run_experiment` with
>    `review_fn=mock_review`. This is the ONLY place in the harness that
>    references `mock_review` (other than its own definition). Step B
>    will `import run_experiment` from this file and pass a real-LLM
>    `review_fn` from a separate file — without editing the harness.
>
> 6. Metrics report (printed table AND `harness_metrics.json`):
>    - per-task: pass/fail (from running `hidden_tests` against the
>      final solution), `ground_truth_passes`, final reviewer verdict
>      (approved/rejected), number of review rounds used.
>    - **Pass Rate** — fraction of the 6 tasks whose final solution
>      passes hidden tests.
>    - **False Approvals** — count of tasks where the final reviewer
>      verdict was "approved" but `ground_truth_passes` is `False`
>      (Critic too lenient).
>    - **False Rejections** — count of tasks where the final reviewer
>      verdict was "rejected" but `ground_truth_passes` is `True`
>      (Critic too strict).
>    - **token count** and **estimated cost** — 0 under `mock_review`;
>      print the fields anyway so Step B's metric schema is identical.
>
> **Constraints:**
> - The harness file imports NO network module. No `openai`, `anthropic`,
>   `requests`, `urllib.request`, `httpx`. The real-LLM reviewer in Step
>   B lives in a SEPARATE file the user writes themselves.
> - The revise loop MUST be bounded by `MAX_REVIEW_ROUNDS`. No unbounded
>   `while`.
> - `review_fn` is a parameter of `run_experiment`. The only reference
>   to `mock_review` outside its own definition is inside the `__main__`
>   guard.
> - Output `harness_metrics.json` next to the harness script.
>
> **What NOT to do in this brief:**
> - Do not invent your own benchmark tasks. The 6 tasks are fixed in
>   `specs/BENCHMARK_6_TASKS.md` and the Worker copies them.
> - Do not implement Chain-of-Thought, Consensus Voting, or any actual
>   review technique. `mock_review` is the only reviewer this brief
>   ships and it implements no technique.
> - Do not call any LLM from the harness file. Do not import any HTTP
>   client or network module.
> - Do not build a UI, a database, or a config system beyond simple
>   constants.

---

## Deliverables (what a complete Step A run should produce)

1. A single runnable Python file — the harness.
2. The 6-task benchmark embedded in the harness, matching
   `specs/BENCHMARK_6_TASKS.md` task-for-task (function names,
   mock_solutions including their bugs, hidden_tests), plus the derived
   `ground_truth_passes` per task.
3. A printed metrics table from `python <harness>.py` + a written
   `harness_metrics.json` next to the script.

## Evaluation metrics — how YOU judge if Step A succeeded

Step A succeeds when the skeleton is sound — NOT when any reviewer
technique has been compared. Judge it on:

- **MUST: the harness implements all 6 specified tasks.** Function
  names, `mock_solution` bodies (with the same bugs), and `hidden_tests`
  match `specs/BENCHMARK_6_TASKS.md` task-for-task. The Worker did not
  invent its own benchmark.
- **MUST: a run under `mock_review` produces the expected
  `ground_truth_passes` pattern.** The harness computes
  `ground_truth_passes` by actually executing `hidden_tests` against
  each `mock_solution`. The result MUST be: tasks 1-2 `True`, tasks 3-6
  `False`. Any other pattern means a task was implemented wrong or the
  computation is wrong.
- **MUST: False Approvals and False Rejections are computed against
  `ground_truth_passes`.** Trace one task by hand: a "False Approval"
  is a row where the final verdict says approved AND
  `ground_truth_passes` is `False`; a "False Rejection" is the
  opposite.
- **MUST: `review_fn` is genuinely pluggable.** The harness must NOT
  reference `mock_review` outside its own definition and the `__main__`
  guard. Importing `run_experiment` from the file and calling it with a
  different `review_fn` must work without editing the harness.
- **MUST: a grep of the harness file finds no network imports.**
  Searching for `openai`, `anthropic`, `requests`, `urllib.request`,
  `httpx` in the harness file returns nothing.
- **MUST: skeleton runs under `mock_review` with no API key set.**
  `python <harness>.py` completes without error, prints a metrics
  table, writes `harness_metrics.json`, and never hits the network.
- **MUST: the revise loop is bounded.** Inspect the code — the loop is
  capped by `MAX_REVIEW_ROUNDS`. No unbounded `while` around any
  `review_fn` call.
- **MUST: token count and cost are zero.** Under `mock_review` there
  is no LLM call. If the harness reports non-zero tokens or cost in
  Step A, something other than the reviewer is calling a model.

## What this brief does NOT answer

It does NOT tell you which review technique is best. The numbers from
Step A reflect the pre-written `mock_verdict_*` values, not any
reviewer behavior. The real comparison happens in Step B, when the
human imports `run_experiment` and passes in real-LLM `review_fn`
implementations from a separate file.

## After this run

- Skeleton sound -> proceed to Step B: write a real-LLM reviewer in a
  separate file, import `run_experiment`, and run it with that
  `review_fn`. Later add CoT / Consensus Voting reviewers the same way.
- Skeleton broken -> the transcript shows which stage failed; fix and
  re-run before adding any real reviewer. Do not plug a real LLM into
  a broken skeleton.
