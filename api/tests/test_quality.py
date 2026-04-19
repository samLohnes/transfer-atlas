"""Tests for pipeline.quality data quality checks.

Each check gets a happy-path test (clean data → passes) and a failure test
(seeded-bad data → fails with the expected severity and details).
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from app.models import (
    CountryTransferFlow,
    Player,
    PlayerValuation,
    Transfer,
)
from pipeline.quality import (
    CheckResult,
    QualityReport,
    check_country_flow_reconciliation,
    check_fee_distribution_not_degenerate,
    check_no_far_future_transfers,
    check_no_negative_fees,
    check_no_orphan_transfers,
    check_no_orphan_valuations,
    check_no_outlier_fees,
    check_position_groups_valid,
    check_row_counts,
    check_transfer_window_format,
    run_quality_checks,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _add_transfer(session, **overrides):
    """Helper: add a transfer with sensible defaults, then flush."""
    defaults = dict(
        player_id=1, from_club_id=1, to_club_id=2,
        fee_eur=1_000_000_00, fee_is_loan=False,
        transfer_window="Summer 2023", transfer_date=date(2023, 7, 1),
        season="2023-2024",
    )
    defaults.update(overrides)
    t = Transfer(**defaults)
    session.add(t)
    session.flush()
    return t


class TestRowCounts:
    """check_row_counts should warn only when a table is way outside expected bounds."""

    def test_empty_db_fails_all(self, seeded_session):
        """A freshly-seeded (no transfers/valuations) DB has zero counts, fails bounds."""
        results = check_row_counts(seeded_session)
        # Every table should fail its lower bound since seeded_session has tiny counts
        assert all(not r.passed for r in results)
        assert all(r.severity == "warning" for r in results)

    def test_all_results_have_structured_details(self, seeded_session):
        """Every row-count result carries count + expected bounds in details."""
        results = check_row_counts(seeded_session)
        for r in results:
            assert "count" in r.details
            assert "expected_min" in r.details
            assert "expected_max" in r.details


class TestNoNegativeFees:
    """check_no_negative_fees is an error-level invariant."""

    def test_clean_data_passes(self, seeded_session):
        _add_transfer(seeded_session, fee_eur=5_000_000_000)
        result = check_no_negative_fees(seeded_session)
        assert result.passed
        assert result.severity == "error"

    def test_negative_fee_fails(self, seeded_session):
        _add_transfer(seeded_session, fee_eur=-100)
        result = check_no_negative_fees(seeded_session)
        assert not result.passed
        assert result.severity == "error"
        assert result.details["count"] == 1


class TestOrphanTransfers:
    """check_no_orphan_transfers detects transfers whose player_id no longer exists.

    SQLite doesn't enforce FKs by default, so we can reliably trigger orphans for the test.
    """

    def test_clean_data_passes(self, seeded_session):
        _add_transfer(seeded_session, player_id=1)
        result = check_no_orphan_transfers(seeded_session)
        assert result.passed

    def test_orphan_transfer_fails(self, seeded_session):
        # Player 999 does not exist in seeded_session
        _add_transfer(seeded_session, player_id=999)
        result = check_no_orphan_transfers(seeded_session)
        assert not result.passed
        assert result.severity == "error"
        assert result.details["orphan_count"] == 1


class TestOrphanValuations:
    def test_clean_data_passes(self, seeded_session):
        seeded_session.add(PlayerValuation(player_id=1, valuation_eur=100, valuation_date=date(2023, 6, 1)))
        seeded_session.flush()
        result = check_no_orphan_valuations(seeded_session)
        assert result.passed

    def test_orphan_valuation_fails(self, seeded_session):
        seeded_session.add(PlayerValuation(player_id=999, valuation_eur=100, valuation_date=date(2023, 6, 1)))
        seeded_session.flush()
        result = check_no_orphan_valuations(seeded_session)
        assert not result.passed
        assert result.severity == "error"


class TestFarFutureTransfers:
    def test_no_future_transfers_passes(self, seeded_session):
        _add_transfer(seeded_session, transfer_date=date(2023, 7, 1))
        result = check_no_far_future_transfers(seeded_session)
        assert result.passed
        assert result.severity == "warning"

    def test_far_future_transfer_fails(self, seeded_session):
        far_future = date.today() + timedelta(days=400)
        _add_transfer(seeded_session, transfer_date=far_future)
        result = check_no_far_future_transfers(seeded_session)
        assert not result.passed
        assert result.details["count"] == 1


class TestOutlierFees:
    def test_reasonable_fees_pass(self, seeded_session):
        _add_transfer(seeded_session, fee_eur=200_000_000_00)  # €200M
        result = check_no_outlier_fees(seeded_session)
        assert result.passed

    def test_outlier_fee_fails(self, seeded_session):
        _add_transfer(seeded_session, fee_eur=600_000_000_00)  # €600M (impossible)
        result = check_no_outlier_fees(seeded_session)
        assert not result.passed
        assert result.severity == "warning"


class TestFeeDistribution:
    def test_empty_db_skips(self, seeded_session):
        """No transfers → check passes (nothing to analyze)."""
        result = check_fee_distribution_not_degenerate(seeded_session)
        assert result.passed

    def test_varied_fees_pass(self, seeded_session):
        for i in range(15):
            _add_transfer(
                seeded_session, player_id=1, to_club_id=2,
                transfer_date=date(2023, 1, 1) + timedelta(days=i),
                fee_eur=(i + 1) * 1_000_000_00,
            )
        result = check_fee_distribution_not_degenerate(seeded_session)
        assert result.passed
        assert result.details["distinct"] >= 10

    def test_degenerate_fees_fail(self, seeded_session):
        """All fees identical → parser probably broken, check fails."""
        for i in range(15):
            _add_transfer(
                seeded_session, player_id=1, to_club_id=2,
                transfer_date=date(2023, 1, 1) + timedelta(days=i),
                fee_eur=1_000_000_00,  # identical
            )
        result = check_fee_distribution_not_degenerate(seeded_session)
        assert not result.passed


class TestCountryFlowReconciliation:
    def test_both_empty_passes(self, seeded_session):
        """Empty DB → trivially reconciles."""
        result = check_country_flow_reconciliation(seeded_session)
        assert result.passed

    def test_skips_when_agg_not_built(self, seeded_session):
        """When transfers exist but aggregation wasn't run, returns info (not warning)."""
        _add_transfer(seeded_session, fee_eur=5_000_000_00, fee_is_loan=False)
        result = check_country_flow_reconciliation(seeded_session)
        assert result.passed
        assert result.severity == "info"

    def test_matching_totals_pass(self, seeded_session):
        _add_transfer(seeded_session, fee_eur=5_000_000_00, fee_is_loan=False)
        # Manually populate aggregation to match
        seeded_session.add(CountryTransferFlow(
            from_country_id=1, to_country_id=2, transfer_window="Summer 2023",
            total_fee_eur=5_000_000_00, transfer_count=1, loan_count=0,
        ))
        seeded_session.flush()
        result = check_country_flow_reconciliation(seeded_session)
        assert result.passed

    def test_mismatched_totals_fail(self, seeded_session):
        _add_transfer(seeded_session, fee_eur=5_000_000_00, fee_is_loan=False)
        # Aggregation deliberately wrong
        seeded_session.add(CountryTransferFlow(
            from_country_id=1, to_country_id=2, transfer_window="Summer 2023",
            total_fee_eur=9_000_000_00, transfer_count=1, loan_count=0,
        ))
        seeded_session.flush()
        result = check_country_flow_reconciliation(seeded_session)
        assert not result.passed
        assert result.severity == "warning"


class TestTransferWindowFormat:
    def test_valid_windows_pass(self, seeded_session):
        _add_transfer(seeded_session, transfer_window="Summer 2023")
        result = check_transfer_window_format(seeded_session)
        assert result.passed

    def test_invalid_window_fails(self, seeded_session):
        _add_transfer(seeded_session, transfer_window="Q2 2023")
        result = check_transfer_window_format(seeded_session)
        assert not result.passed
        assert "Q2 2023" in result.details["bad_values"]


class TestPositionGroupsValid:
    def test_expected_groups_pass(self, seeded_session):
        # seeded_session players already have FWD/MID/DEF
        result = check_position_groups_valid(seeded_session)
        assert result.passed

    def test_unexpected_group_fails(self, seeded_session):
        seeded_session.add(Player(
            id=99, name="Hybrid", transfermarkt_id="999", position_group="WING",
        ))
        seeded_session.flush()
        result = check_position_groups_valid(seeded_session)
        assert not result.passed
        assert "WING" in result.details["unexpected"]


class TestRunQualityChecks:
    """Integration: the runner executes all checks and builds a report."""

    def test_runner_executes_all_checks(self, seeded_session):
        report = run_quality_checks(seeded_session)
        assert isinstance(report, QualityReport)
        # Should have row_count_* (4) + other checks (9) = 13 results
        assert report.total_count == 13
        # Every result is a CheckResult
        assert all(isinstance(r, CheckResult) for r in report.results)

    def test_report_categorizes_by_severity(self, seeded_session):
        # Inject one error (orphan transfer) and confirm it's in report.errors
        _add_transfer(seeded_session, player_id=999)
        report = run_quality_checks(seeded_session)
        assert any(r.name == "no_orphan_transfers" for r in report.errors)
        # Errors list shouldn't include warnings
        assert all(r.severity == "error" for r in report.errors)
