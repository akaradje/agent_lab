import pytest

from agent_lab.budget import BudgetExceededError, BudgetTracker


class TestBudgetTracker:
    def test_initial_state(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        assert bt.total_tokens == 0
        assert bt.total_cost == 0.0

    def test_remaining_initial(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        tokens_left, usd_left = bt.remaining()
        assert tokens_left == 100_000
        assert usd_left == 1.00

    def test_record_single_call_flash(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        bt.record("deepseek-v4-flash", input_tokens=1000, output_tokens=500)

        # Flash: $0.14/M input, $0.28/M output
        expected_cost = (1000 / 1e6) * 0.14 + (500 / 1e6) * 0.28
        assert bt.total_tokens == 1500
        assert bt.total_cost == pytest.approx(expected_cost)

    def test_record_single_call_pro(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        bt.record("deepseek-v4-pro", input_tokens=2000, output_tokens=1000)

        # Pro: $0.44/M input, $0.87/M output
        expected_cost = (2000 / 1e6) * 0.44 + (1000 / 1e6) * 0.87
        assert bt.total_tokens == 3000
        assert bt.total_cost == pytest.approx(expected_cost)

    def test_accumulates_across_calls(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        bt.record("deepseek-v4-flash", input_tokens=1000, output_tokens=500)
        bt.record("deepseek-v4-pro", input_tokens=2000, output_tokens=1000)

        cost_flash = (1000 / 1e6) * 0.14 + (500 / 1e6) * 0.28
        cost_pro = (2000 / 1e6) * 0.44 + (1000 / 1e6) * 0.87
        assert bt.total_tokens == 4500
        assert bt.total_cost == pytest.approx(cost_flash + cost_pro)

    def test_remaining_after_calls(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        bt.record("deepseek-v4-flash", input_tokens=10_000, output_tokens=5_000)

        tokens_left, usd_left = bt.remaining()
        assert tokens_left == 85_000
        expected_cost = (10000 / 1e6) * 0.14 + (5000 / 1e6) * 0.28
        assert usd_left == pytest.approx(1.00 - expected_cost)

    def test_token_ceiling_exceeded(self) -> None:
        bt = BudgetTracker(max_tokens=1000, max_usd=100.00)
        with pytest.raises(BudgetExceededError) as exc:
            bt.record("deepseek-v4-flash", input_tokens=600, output_tokens=500)
        assert "Token ceiling" in str(exc.value)
        assert exc.value.tokens == 1100

    def test_usd_ceiling_exceeded(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=0.001)
        with pytest.raises(BudgetExceededError) as exc:
            # Flash: (1000/1e6)*0.14 + (10000/1e6)*0.28 ≈ 0.00014 + 0.0028 = 0.00294 > 0.001
            bt.record("deepseek-v4-flash", input_tokens=1000, output_tokens=10000)
        assert "USD ceiling" in str(exc.value)

    def test_ceiling_checked_after_accumulation(self) -> None:
        """Each call checks ceilings after adding, so a call that crosses
        the line is rejected even if the tracker was below ceiling before."""
        bt = BudgetTracker(max_tokens=100_000, max_usd=0.01)
        # First call: well under ceiling
        bt.record("deepseek-v4-flash", input_tokens=1000, output_tokens=1000)
        # Second call: crosses USD ceiling
        with pytest.raises(BudgetExceededError):
            bt.record("deepseek-v4-pro", input_tokens=10_000, output_tokens=10_000)
        # State should reflect both calls (the second was recorded before check)
        assert bt.total_tokens == 22_000

    def test_unknown_model_raises_key_error(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        with pytest.raises(KeyError):
            bt.record("nonexistent-model", input_tokens=100, output_tokens=100)

    def test_call_count_increments(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        assert bt.call_count == 0
        bt.record("deepseek-v4-flash", input_tokens=100, output_tokens=50)
        assert bt.call_count == 1
        bt.record("deepseek-v4-pro", input_tokens=200, output_tokens=100)
        assert bt.call_count == 2

    def test_summary_contains_key_fields(self) -> None:
        bt = BudgetTracker(max_tokens=100_000, max_usd=1.00)
        bt.record("deepseek-v4-flash", input_tokens=1000, output_tokens=500)
        bt.record("deepseek-v4-pro", input_tokens=2000, output_tokens=1000)

        report = bt.summary()
        assert "Cost Report" in report
        assert "2" in report  # call count
        assert "3,000" in report  # input tokens
        assert "1,500" in report  # output tokens
        assert "4,500" in report  # total tokens
        assert "100,000" in report  # ceiling

    def test_summary_with_no_calls(self) -> None:
        bt = BudgetTracker(max_tokens=50_000, max_usd=0.50)
        report = bt.summary()
        assert "Cost Report" in report
        assert "0" in report  # call count
        assert "50,000" in report  # ceiling


class TestBudgetSoftWarning:
    """80% soft-warning: logs once to transcript when threshold is crossed.
    The run continues — only the hard ceiling stops it."""

    def test_warning_fires_when_threshold_crossed(self) -> None:
        transcript: list[str] = []
        bt = BudgetTracker(max_tokens=10_000, max_usd=10.00, transcript=transcript)

        # 5,000 tokens (50%) — well under threshold; no warning
        bt.record("deepseek-v4-flash", input_tokens=3000, output_tokens=2000)
        assert transcript == []

        # 8,500 tokens cumulative (85%) — crosses 80%; warning fires
        bt.record("deepseek-v4-flash", input_tokens=2000, output_tokens=1500)
        assert len(transcript) == 1
        assert "[budget] WARNING" in transcript[0]
        assert "8,500" in transcript[0]
        assert "10,000" in transcript[0]

    def test_warning_fires_only_once(self) -> None:
        transcript: list[str] = []
        bt = BudgetTracker(max_tokens=10_000, max_usd=10.00, transcript=transcript)

        bt.record("deepseek-v4-flash", input_tokens=4500, output_tokens=4000)  # 85%
        bt.record("deepseek-v4-flash", input_tokens=300, output_tokens=200)    # 90%
        # Only one warning despite continued growth above threshold
        warnings = [t for t in transcript if "[budget] WARNING" in t]
        assert len(warnings) == 1

    def test_no_warning_below_threshold(self) -> None:
        transcript: list[str] = []
        bt = BudgetTracker(max_tokens=10_000, max_usd=10.00, transcript=transcript)

        # 7,900 tokens (79%) — just under 80%
        bt.record("deepseek-v4-flash", input_tokens=4000, output_tokens=3900)
        assert transcript == []

    def test_warning_does_not_stop_run(self) -> None:
        """A soft warning is informational. The next record() must succeed
        as long as the hard ceiling is not crossed."""
        transcript: list[str] = []
        bt = BudgetTracker(max_tokens=10_000, max_usd=10.00, transcript=transcript)

        bt.record("deepseek-v4-flash", input_tokens=4500, output_tokens=4000)  # 85%
        # Next call still well under hard ceiling — must NOT raise
        bt.record("deepseek-v4-flash", input_tokens=300, output_tokens=200)
        assert bt.total_tokens == 9000  # all calls accepted

    def test_attach_transcript_after_construction(self) -> None:
        """Pipeline attaches the transcript AFTER the BudgetTracker is created
        in main.py. The warning must still land in the attached transcript."""
        bt = BudgetTracker(max_tokens=10_000, max_usd=10.00)  # no transcript yet
        transcript: list[str] = []
        bt.attach_transcript(transcript)

        bt.record("deepseek-v4-flash", input_tokens=5000, output_tokens=4000)  # 90%
        assert len(transcript) == 1
        assert "[budget] WARNING" in transcript[0]

    def test_no_transcript_attached_still_no_crash(self) -> None:
        """If no transcript is attached, crossing the threshold must not
        raise — the warning is simply not logged."""
        bt = BudgetTracker(max_tokens=10_000, max_usd=10.00)  # no transcript
        # Should not raise
        bt.record("deepseek-v4-flash", input_tokens=5000, output_tokens=4000)
        assert bt.total_tokens == 9000
