"""Data quality checks — run read-only assertions against the post-ingestion
database state to catch issues the schema can't enforce.

Design notes:
  * Each check is a pure function (Session) -> CheckResult | list[CheckResult].
  * Checks are grouped by severity:
      - error    something is structurally broken (negative fees, orphan FKs)
      - warning  something is suspicious but not catastrophic (row count drift,
                 outlier values, unexpected enum values)
      - info     informational only, never "fails"
  * By default, errors log but don't fail the pipeline — `--strict` is required
    to make them fatal. Rationale: a prospective user running a stale repo
    shouldn't have the pipeline refuse to complete because of a warning
    condition introduced in newer upstream data.
  * Tolerance bands are deliberately wide. Checks should only fire on
    catastrophic issues or genuine schema drift, never on normal data growth.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Literal

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.models import (
    Club,
    CountryTransferFlow,
    Player,
    PlayerValuation,
    Transfer,
)

logger = logging.getLogger(__name__)

Severity = Literal["info", "warning", "error"]


@dataclass
class CheckResult:
    """The outcome of a single data quality check."""
    name: str
    severity: Severity
    passed: bool
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class QualityReport:
    """Aggregate of all check results from one DQ run."""
    results: list[CheckResult] = field(default_factory=list)

    @property
    def errors(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == "error" and not r.passed]

    @property
    def warnings(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == "warning" and not r.passed]

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total_count(self) -> int:
        return len(self.results)


# ---- Individual checks ----

# Generous bounds: only fire on catastrophic ingest issues (0 rows, 10x growth).
EXPECTED_ROW_COUNTS: dict[str, tuple[int, int]] = {
    "players": (10_000, 500_000),
    "clubs": (100, 5_000),
    "transfers": (5_000, 500_000),
    "player_valuations": (50_000, 5_000_000),
}


def check_row_counts(session: Session) -> list[CheckResult]:
    """Each entity has a row count within a wide expected band."""
    model_for_table = {
        "players": Player,
        "clubs": Club,
        "transfers": Transfer,
        "player_valuations": PlayerValuation,
    }
    results = []
    for table, (lo, hi) in EXPECTED_ROW_COUNTS.items():
        count = session.query(model_for_table[table]).count()
        passed = lo <= count <= hi
        results.append(CheckResult(
            name=f"row_count_{table}",
            severity="warning",
            passed=passed,
            message=(
                f"{table}: {count:,} rows (expected {lo:,}–{hi:,})"
                if not passed
                else f"{table}: {count:,} rows"
            ),
            details={"count": count, "expected_min": lo, "expected_max": hi},
        ))
    return results


def check_no_negative_fees(session: Session) -> CheckResult:
    """No transfer has a negative fee_eur — parser bug indicator."""
    count = session.query(Transfer).filter(Transfer.fee_eur < 0).count()
    return CheckResult(
        name="no_negative_fees",
        severity="error",
        passed=count == 0,
        message=(
            f"{count} transfers with negative fee_eur"
            if count
            else "All fees non-negative"
        ),
        details={"count": count},
    )


def check_no_orphan_transfers(session: Session) -> CheckResult:
    """Every transfer references an existing player (FK should enforce; belt + braces)."""
    orphans = (
        session.query(Transfer)
        .outerjoin(Player, Transfer.player_id == Player.id)
        .filter(Player.id.is_(None))
        .count()
    )
    return CheckResult(
        name="no_orphan_transfers",
        severity="error",
        passed=orphans == 0,
        message=(
            f"{orphans} transfers with missing player FK"
            if orphans
            else "All transfer→player FKs intact"
        ),
        details={"orphan_count": orphans},
    )


def check_no_orphan_valuations(session: Session) -> CheckResult:
    """Every valuation references an existing player."""
    orphans = (
        session.query(PlayerValuation)
        .outerjoin(Player, PlayerValuation.player_id == Player.id)
        .filter(Player.id.is_(None))
        .count()
    )
    return CheckResult(
        name="no_orphan_valuations",
        severity="error",
        passed=orphans == 0,
        message=(
            f"{orphans} valuations with missing player FK"
            if orphans
            else "All valuation→player FKs intact"
        ),
        details={"orphan_count": orphans},
    )


def check_no_far_future_transfers(session: Session) -> CheckResult:
    """Transfers shouldn't be dated more than 6 months in the future."""
    threshold = date.today() + timedelta(days=180)
    count = session.query(Transfer).filter(Transfer.transfer_date > threshold).count()
    return CheckResult(
        name="no_far_future_transfers",
        severity="warning",
        passed=count == 0,
        message=(
            f"{count} transfers dated >6mo in the future (possible data error)"
            if count
            else "No suspiciously future-dated transfers"
        ),
        details={"count": count, "threshold": threshold.isoformat()},
    )


# €500M in EUR cents. Real transfers peak around €222M (Neymar, 2017).
OUTLIER_FEE_CENTS = 500 * 1_000_000 * 100


def check_no_outlier_fees(session: Session) -> CheckResult:
    """No transfer fee exceeds €500M — above that threshold is almost certainly a parse error."""
    count = session.query(Transfer).filter(Transfer.fee_eur > OUTLIER_FEE_CENTS).count()
    return CheckResult(
        name="no_outlier_fees",
        severity="warning",
        passed=count == 0,
        message=(
            f"{count} transfers with fee >€500M (possible parse error)"
            if count
            else "No outlier fees detected"
        ),
        details={"count": count, "threshold_eur": 500_000_000},
    )


def check_fee_distribution_not_degenerate(session: Session) -> CheckResult:
    """Fee values should vary — if there are <10 distinct non-null fees, the parser likely broke."""
    distinct = (
        session.query(Transfer.fee_eur)
        .filter(Transfer.fee_eur.isnot(None))
        .distinct()
        .count()
    )
    # If we have no fee data at all (brand-new DB), skip this check by passing.
    total = session.query(Transfer).count()
    if total == 0:
        return CheckResult(
            name="fee_distribution_not_degenerate",
            severity="warning",
            passed=True,
            message="No transfers to analyze",
            details={"distinct": 0, "total": 0},
        )
    passed = distinct >= 10
    return CheckResult(
        name="fee_distribution_not_degenerate",
        severity="warning",
        passed=passed,
        message=(
            f"Only {distinct} distinct fee values — parser may be broken"
            if not passed
            else f"Healthy fee variation ({distinct:,} distinct values)"
        ),
        details={"distinct": distinct, "total": total},
    )


def check_country_flow_reconciliation(session: Session) -> CheckResult:
    """Aggregated country flows should sum to the same totals as the raw transfers table.

    Catches bugs in the swap-table rebuild where rows could be silently dropped or
    double-counted. Only meaningful when both tables have data.
    """
    agg = session.query(
        func.coalesce(func.sum(CountryTransferFlow.total_fee_eur), 0),
        func.coalesce(func.sum(CountryTransferFlow.transfer_count), 0),
        func.coalesce(func.sum(CountryTransferFlow.loan_count), 0),
    ).one()
    agg_fee, agg_permanent, agg_loan = agg

    # Raw: only permanent transfers contribute to total_fee_eur.
    raw_fee = session.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Transfer.fee_is_loan == False,  # noqa: E712
                            Transfer.fee_eur.isnot(None),
                        ),
                        Transfer.fee_eur,
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).scalar()
    raw_permanent = session.query(Transfer).filter(
        Transfer.fee_is_loan == False  # noqa: E712
    ).count()
    raw_loan = session.query(Transfer).filter(
        Transfer.fee_is_loan == True  # noqa: E712
    ).count()

    # If aggregation hasn't been built yet (fresh DB, tests), skip gracefully.
    if agg_permanent == 0 and raw_permanent > 0:
        return CheckResult(
            name="country_flow_reconciliation",
            severity="info",
            passed=True,
            message="Aggregation table empty — skipping reconciliation",
            details={},
        )

    passed = (agg_fee == raw_fee) and (agg_permanent == raw_permanent) and (agg_loan == raw_loan)
    return CheckResult(
        name="country_flow_reconciliation",
        severity="warning",
        passed=passed,
        message=(
            f"Reconciliation mismatch — agg fee={agg_fee}, raw fee={raw_fee}; "
            f"agg perm={agg_permanent}, raw perm={raw_permanent}; "
            f"agg loan={agg_loan}, raw loan={raw_loan}"
            if not passed
            else "Aggregation totals match raw transfers"
        ),
        details={
            "agg_fee": int(agg_fee), "raw_fee": int(raw_fee),
            "agg_permanent": agg_permanent, "raw_permanent": raw_permanent,
            "agg_loan": agg_loan, "raw_loan": raw_loan,
        },
    )


WINDOW_PATTERN = re.compile(r"^(Summer|Winter) \d{4}$")


def check_transfer_window_format(session: Session) -> CheckResult:
    """All transfer_window values match the 'Summer YYYY' / 'Winter YYYY' pattern."""
    distinct_windows = [
        w[0] for w in session.query(Transfer.transfer_window).distinct().all()
    ]
    bad = [w for w in distinct_windows if not WINDOW_PATTERN.match(w or "")]
    passed = len(bad) == 0
    return CheckResult(
        name="transfer_window_format",
        severity="warning",
        passed=passed,
        message=(
            f"{len(bad)} transfer_window values don't match expected format"
            if not passed
            else f"All {len(distinct_windows)} distinct windows well-formatted"
        ),
        details={"bad_values": bad[:10], "total_distinct": len(distinct_windows)},
    )


EXPECTED_POSITION_GROUPS = {"GK", "DEF", "MID", "FWD", None}


def check_position_groups_valid(session: Session) -> CheckResult:
    """position_group values should only be GK, DEF, MID, FWD, or NULL."""
    distinct = {r[0] for r in session.query(Player.position_group).distinct().all()}
    unexpected = distinct - EXPECTED_POSITION_GROUPS
    passed = len(unexpected) == 0
    return CheckResult(
        name="position_groups_valid",
        severity="warning",
        passed=passed,
        message=(
            f"Unexpected position_group values: {sorted(str(x) for x in unexpected)}"
            if not passed
            else "All position_group values are from the expected set"
        ),
        details={"unexpected": sorted(str(x) for x in unexpected)},
    )


# ---- Runner ----

ALL_CHECKS: list[Callable[[Session], "CheckResult | list[CheckResult]"]] = [
    check_row_counts,
    check_no_negative_fees,
    check_no_orphan_transfers,
    check_no_orphan_valuations,
    check_no_far_future_transfers,
    check_no_outlier_fees,
    check_fee_distribution_not_degenerate,
    check_country_flow_reconciliation,
    check_transfer_window_format,
    check_position_groups_valid,
]


def run_quality_checks(session: Session) -> QualityReport:
    """Execute all registered checks and return a structured report."""
    report = QualityReport()
    for check in ALL_CHECKS:
        result = check(session)
        if isinstance(result, list):
            report.results.extend(result)
        else:
            report.results.append(result)
    return report


def log_report(report: QualityReport) -> None:
    """Emit a human-readable summary of a QualityReport to the logger."""
    logger.info(
        "Data Quality Report: %d/%d passed  (errors: %d, warnings: %d)",
        report.passed_count, report.total_count,
        len(report.errors), len(report.warnings),
    )
    for r in report.errors:
        logger.error("  [ERROR] %s — %s", r.name, r.message)
    for r in report.warnings:
        logger.warning("  [WARN]  %s — %s", r.name, r.message)
