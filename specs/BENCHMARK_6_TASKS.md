# BENCHMARK_6_TASKS.md

The fixed 6-task benchmark for the Critic-stringency experiment. This is
the "exam" all three reviewer techniques face in Step B, so it is defined
explicitly here rather than left to the Worker to invent.

Each task below specifies: the function, the mock_solution (the candidate
code the reviewer must judge), what bug it carries (if any), and what the
hidden tests must check. Calibration: 2 correct, 2 obvious-bug,
2 subtle-bug.

The harness must compute `ground_truth_passes` by actually running the
hidden tests against the mock_solution — the "expected" column below is
what that computation should yield, stated so you can verify by hand.

---

## Task 1 — `sum_list` — CORRECT

- Function: `sum_list(nums)` returns the sum of a list of numbers.
- mock_solution: a correct implementation using a loop or `sum()`.
- Hidden tests: `sum_list([1,2,3]) == 6`; `sum_list([]) == 0`;
  `sum_list([-1,1]) == 0`.
- Expected ground_truth_passes: **True**.

## Task 2 — `count_vowels` — CORRECT

- Function: `count_vowels(s)` returns how many vowels (a,e,i,o,u, case-
  insensitive) are in a string.
- mock_solution: a correct implementation.
- Hidden tests: `count_vowels("hello") == 2`; `count_vowels("") == 0`;
  `count_vowels("XYZ") == 0`; `count_vowels("AEIOU") == 5`.
- Expected ground_truth_passes: **True**.

## Task 3 — `average` — OBVIOUS BUG (crash)

- Function: `average(nums)` returns the arithmetic mean of a list.
- mock_solution: `return sum(nums) / len(nums)` — no empty-list guard.
- Bug: obvious. On `[]` it raises `ZeroDivisionError`. Any reviewer that
  considers the empty case at all will catch it.
- Hidden tests: `average([2,4]) == 3`; and `average([])` must return `0`
  (or a defined value) without raising.
- Expected ground_truth_passes: **False** (crashes on the empty test).

## Task 4 — `first_word` — OBVIOUS BUG (wrong output)

- Function: `first_word(s)` returns the first whitespace-separated word.
- mock_solution: `return s.split()[0].lower()` — wrongly lowercases.
- Bug: obvious. The result is visibly altered; the spec never asks for
  lowercasing. A direct example check catches it immediately.
- Hidden tests: `first_word("Hello world") == "Hello"`;
  `first_word("ONE two") == "ONE"`.
- Expected ground_truth_passes: **False** (case is wrong).

## Task 5 — `merge_intervals` — SUBTLE BUG (input mutation)

- Function: `merge_intervals(intervals)` merges overlapping `[start,end]`
  pairs, returns the merged list sorted by start.
- mock_solution: a correct-looking implementation that does
  `merged = [intervals[0]]` (aliases the caller's interval) and later
  `merged[-1][1] = max(...)` — mutating the caller's input list.
- Bug: subtle. Return value is CORRECT for the usual examples, so a
  reviewer skimming output sees nothing wrong. The defect only shows when
  a test inspects whether the input list was mutated. This is the exact
  bug the project's own Critic missed earlier — known to be genuinely
  subtle.
- Hidden tests: a correctness check
  `merge_intervals([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]`; AND a
  mutation check — build `data = [[1,3],[2,6]]`, call `merge_intervals
  (data)`, then assert `data == [[1,3],[2,6]]` (input unchanged).
- Expected ground_truth_passes: **False** (fails the mutation test).

## Task 6 — `is_sorted` — SUBTLE BUG (off-by-one boundary)

- Function: `is_sorted(nums)` returns True if the list is in
  non-decreasing order.
- mock_solution: loops `for i in range(len(nums) - 2)` and compares
  `nums[i] <= nums[i+1]`. The `- 2` should be `- 1`: the last adjacent
  pair is never checked.
- Bug: subtle. The function is right for almost every list; it only fails
  when the sole ordering violation is in the final pair. Reading the code,
  `range(len(nums) - 2)` looks plausible.
- Hidden tests: `is_sorted([1,2,3]) == True`; `is_sorted([1,2,1]) ==
  False` (violation in the middle — a weak reviewer passes this);
  `is_sorted([1,5,4]) == False` (violation ONLY in the last pair — this
  is the test the buggy code fails).
- Expected ground_truth_passes: **False** (fails the last-pair test).

---

## Summary table — verify the calibration by hand

| Task | Function         | Category    | ground_truth_passes |
|------|------------------|-------------|---------------------|
| 1    | sum_list         | correct     | True                |
| 2    | count_vowels     | correct     | True                |
| 3    | average          | obvious bug | False               |
| 4    | first_word       | obvious bug | False               |
| 5    | merge_intervals  | subtle bug  | False               |
| 6    | is_sorted        | subtle bug  | False               |

So a perfect reviewer would approve tasks 1-2 and reject tasks 3-6.
2 of the 6 mock_solutions pass their hidden tests.

## Why this calibration discriminates between techniques (Step B)

- Tasks 3-4 (obvious): even a weak reviewer should catch these. If a
  technique misses them, it is clearly too lenient.
- Tasks 5-6 (subtle): these are the discriminators. A Rule-Based Checklist
  catches them only if the checklist explicitly asks about input mutation
  and boundary conditions. A Chain-of-Thought reviewer may reason its way
  there. Consensus voting catches them if at least 2 of 3 reviewers do.
  The spread in how techniques handle tasks 5-6 IS the research signal.
- Tasks 1-2 (correct): these catch the opposite failure. A technique that
  rejects a correct solution produces a False Rejection — too strict.

## Note on mock verdicts (Step A only)

For Step A, each task also needs `mock_verdict_initial` /
`mock_verdict_revised` for the reference `mock_review` test double. These
can be simple — Step A only proves the plumbing. A reasonable default:
mock_verdict_initial rejects tasks 3-6 and approves 1-2, so a Step A run
prints a sensible-looking table. These mock verdicts are discarded in
Step B, where the real review_fn judges the same mock_solutions itself.
