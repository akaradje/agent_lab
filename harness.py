"""Critic-stringency experiment harness — Step A skeleton.

The harness ships:
- A fixed 6-task BENCHMARK (specs/BENCHMARK_6_TASKS.md).
- A deterministic `solve(task, round_index)` test double.
- A deterministic `mock_review(solution, task, round_index)` test double.
- `run_experiment(review_fn)` — the pluggable entry point Step B imports.

`mock_review` is referenced only inside the `__main__` guard. No network
imports.
"""

import json

MAX_REVIEW_ROUNDS = 3

# Expected calibration pattern from specs/BENCHMARK_6_TASKS.md. Used as a
# refuse-to-run guard: if the benchmark's computed ground_truth_passes
# does not match, the harness raises rather than printing miscalibrated
# numbers.
EXPECTED_CALIBRATION: list[bool] = [True, True, False, False, False, False]

# ────────────────────────────── 6-task benchmark ──────────────────────────────

BENCHMARK = [
    # Task 1 — sum_list — CORRECT
    {
        "id": "1",
        "prompt": "sum_list(nums): return the sum of a list of numbers.",
        "hidden_tests": [
            "assert sum_list([1,2,3]) == 6",
            "assert sum_list([]) == 0",
            "assert sum_list([-1,1]) == 0",
        ],
        "mock_solution": "def sum_list(nums):\n    return sum(nums)",
        "mock_revision": "def sum_list(nums):\n    return sum(nums)",
        "mock_verdict_initial": {"approved": True, "issues": []},
        "mock_verdict_revised": {"approved": True, "issues": []},
    },
    # Task 2 — count_vowels — CORRECT
    {
        "id": "2",
        "prompt": "count_vowels(s): return the number of vowels (a,e,i,o,u, case-insensitive) in a string.",
        "hidden_tests": [
            "assert count_vowels('hello') == 2",
            "assert count_vowels('') == 0",
            "assert count_vowels('XYZ') == 0",
            "assert count_vowels('AEIOU') == 5",
        ],
        "mock_solution": "def count_vowels(s):\n    return sum(1 for ch in s.lower() if ch in 'aeiou')",
        "mock_revision": "def count_vowels(s):\n    return sum(1 for ch in s.lower() if ch in 'aeiou')",
        "mock_verdict_initial": {"approved": True, "issues": []},
        "mock_verdict_revised": {"approved": True, "issues": []},
    },
    # Task 3 — average — OBVIOUS BUG (crash on empty)
    {
        "id": "3",
        "prompt": "average(nums): return the arithmetic mean of a list. Must handle empty list gracefully.",
        "hidden_tests": [
            "assert average([2,4]) == 3",
            "assert average([]) == 0",
        ],
        "mock_solution": "def average(nums):\n    return sum(nums) / len(nums)",
        "mock_revision": "def average(nums):\n    return sum(nums) / len(nums) if nums else 0",
        "mock_verdict_initial": {"approved": False, "issues": ["Divides by zero on empty list"]},
        "mock_verdict_revised": {"approved": True, "issues": []},
    },
    # Task 4 — first_word — OBVIOUS BUG (lowercases output)
    {
        "id": "4",
        "prompt": "first_word(s): return the first whitespace-separated word, preserving case.",
        "hidden_tests": [
            "assert first_word('Hello world') == 'Hello'",
            "assert first_word('ONE two') == 'ONE'",
        ],
        "mock_solution": "def first_word(s):\n    return s.split()[0].lower()",
        "mock_revision": "def first_word(s):\n    return s.split()[0]",
        "mock_verdict_initial": {"approved": False, "issues": ["Lowercases the result – should preserve case"]},
        "mock_verdict_revised": {"approved": True, "issues": []},
    },
    # Task 5 — merge_intervals — SUBTLE BUG (mutates input)
    {
        "id": "5",
        "prompt": "merge_intervals(intervals): merge overlapping [start,end] pairs, return merged list sorted by start. Input must not be mutated.",
        "hidden_tests": [
            "assert merge_intervals([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]",
            "data = [[1,3],[2,6]]\nmerge_intervals(data)\nassert data == [[1,3],[2,6]]",
        ],
        "mock_solution": (
            "def merge_intervals(intervals):\n"
            "    intervals.sort(key=lambda x: x[0])\n"
            "    merged = [intervals[0]]\n"
            "    for start, end in intervals[1:]:\n"
            "        if start <= merged[-1][1]:\n"
            "            merged[-1][1] = max(merged[-1][1], end)\n"
            "        else:\n"
            "            merged.append([start, end])\n"
            "    return merged"
        ),
        "mock_revision": (
            "def merge_intervals(intervals):\n"
            "    sorted_intervals = sorted(intervals, key=lambda x: x[0])\n"
            "    merged = [list(sorted_intervals[0])]\n"
            "    for start, end in sorted_intervals[1:]:\n"
            "        if start <= merged[-1][1]:\n"
            "            merged[-1][1] = max(merged[-1][1], end)\n"
            "        else:\n"
            "            merged.append([start, end])\n"
            "    return merged"
        ),
        "mock_verdict_initial": {"approved": False, "issues": ["Input list is mutated by the function"]},
        "mock_verdict_revised": {"approved": True, "issues": []},
    },
    # Task 6 — is_sorted — SUBTLE BUG (off-by-one in range)
    {
        "id": "6",
        "prompt": "is_sorted(nums): return True if the list is in non-decreasing order.",
        "hidden_tests": [
            "assert is_sorted([1,2,3]) == True",
            "assert is_sorted([1,2,1]) == False",
            "assert is_sorted([1,5,4]) == False",
        ],
        "mock_solution": (
            "def is_sorted(nums):\n"
            "    for i in range(len(nums) - 2):\n"
            "        if nums[i] > nums[i+1]:\n"
            "            return False\n"
            "    return True"
        ),
        "mock_revision": (
            "def is_sorted(nums):\n"
            "    for i in range(len(nums) - 1):\n"
            "        if nums[i] > nums[i+1]:\n"
            "            return False\n"
            "    return True"
        ),
        "mock_verdict_initial": {"approved": False, "issues": ["Does not check the last adjacent pair"]},
        "mock_verdict_revised": {"approved": True, "issues": []},
    },
]

# ────────────────────────────── hidden test runner ──────────────────────────────


def _run_hidden_tests(solution_code: str, tests: list[str]) -> bool:
    """Each test must produce a truthy result without raising.

    Catching only AssertionError is insufficient: a bare expression like
    ``first_word("Hi") == "Hello"`` evaluates to False but does not raise,
    so wrong-output bugs would silently pass. Treating each test as a
    truthy condition closes that hole.

    Two test shapes are supported:
    - bare expression — evaluated; a False result fails the test.
    - statement (``assert ...`` or multi-line) — exec'd; raising fails it.
    """
    namespace: dict = {}
    try:
        exec(solution_code, namespace)
    except Exception:
        return False
    for test in tests:
        try:
            result = eval(test, namespace)
        except SyntaxError:
            try:
                exec(test, namespace)
            except Exception:
                return False
        except Exception:
            return False
        else:
            if not result:
                return False
    return True


# ────────────────────────────── deterministic doubles ──────────────────────────


def solve(task: dict, round_index: int) -> str:
    """Round 1 returns the original mock_solution; later rounds return mock_revision."""
    if round_index == 1:
        return task["mock_solution"]
    return task["mock_revision"]


def mock_review(solution: str, task: dict, round_index: int) -> dict:
    """Test-double reviewer: returns pre-written verdicts without inspecting the solution."""
    if round_index == 1:
        return task["mock_verdict_initial"]
    return task["mock_verdict_revised"]


# ────────────────────────────── experiment harness ──────────────────────────────


def run_experiment(review_fn) -> dict:
    """Run the benchmark using the given review function.

    Returns a metrics dictionary and writes ``harness_metrics.json``.
    Refuses to run if benchmark ground-truth does not match the
    expected calibration pattern — printing miscalibrated numbers
    silently is worse than a loud error.
    """
    # 1. Compute ground-truth correctness for each task.
    ground_truth_passes = [
        _run_hidden_tests(task["mock_solution"], task["hidden_tests"])
        for task in BENCHMARK
    ]

    # 2. Self-check the calibration before running anything else.
    if ground_truth_passes != EXPECTED_CALIBRATION:
        raise RuntimeError(
            "Benchmark calibration mismatch. "
            f"Expected {EXPECTED_CALIBRATION} but got {ground_truth_passes}. "
            "Refusing to run a miscalibrated benchmark."
        )

    # 3. Run the bounded review/revise loop for each task.
    results = []
    for idx, task in enumerate(BENCHMARK):
        round_num = 1
        solution = solve(task, round_num)
        final_verdict_approved = None
        rounds_used = 1

        while round_num <= MAX_REVIEW_ROUNDS:
            verdict = review_fn(solution, task, round_num)
            if verdict["approved"]:
                final_verdict_approved = True
                rounds_used = round_num
                break
            round_num += 1
            if round_num <= MAX_REVIEW_ROUNDS:
                solution = solve(task, round_num)
        else:
            final_verdict_approved = False
            rounds_used = MAX_REVIEW_ROUNDS

        final_passes = _run_hidden_tests(solution, task["hidden_tests"])
        gt_pass = ground_truth_passes[idx]

        results.append({
            "id": task["id"],
            "ground_truth_passes": gt_pass,
            "final_passes": final_passes,
            "final_verdict": "approved" if final_verdict_approved else "rejected",
            "rounds_used": rounds_used,
        })

    # 4. Aggregate metrics.
    pass_count = sum(1 for r in results if r["final_passes"])
    false_approvals = sum(
        1 for r in results
        if r["final_verdict"] == "approved" and not r["ground_truth_passes"]
    )
    false_rejections = sum(
        1 for r in results
        if r["final_verdict"] == "rejected" and r["ground_truth_passes"]
    )

    aggregates = {
        "pass_rate": pass_count / len(BENCHMARK),
        "false_approvals": false_approvals,
        "false_rejections": false_rejections,
        "token_count": 0,
        "estimated_cost": 0,
    }

    metrics = {"tasks": results, "aggregates": aggregates}

    with open("harness_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # 5. Print human-readable table.
    header = f"{'ID':>4} {'GT_pass':>8} {'Final_pass':>10} {'Verdict':>10} {'Rounds':>6}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for r in results:
        print(
            f"{r['id']:>4} {str(r['ground_truth_passes']):>8} "
            f"{str(r['final_passes']):>10} {r['final_verdict']:>10} {r['rounds_used']:>6}"
        )
    print(sep)
    print(f"Pass rate:        {aggregates['pass_rate']:.2f} ({pass_count}/{len(BENCHMARK)})")
    print(f"False approvals:  {aggregates['false_approvals']}")
    print(f"False rejections: {aggregates['false_rejections']}")
    print(f"Token count:      {aggregates['token_count']}")
    print(f"Estimated cost:   {aggregates['estimated_cost']}")

    return metrics


# ────────────────────────────── main guard ──────────────────────────────

if __name__ == "__main__":
    run_experiment(review_fn=mock_review)
