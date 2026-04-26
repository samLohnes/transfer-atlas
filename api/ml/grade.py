"""Grading pipeline orchestrator.

Coordinates the nine-step run from plan §task-04:

    1. Load scoring_config.json
    2. Create a new (inactive) ScoringVersion row
    3. Calibrate value-trajectory rates from PlayerValuation (or reuse cache)
    4. Compute fee-tier boundaries; persist FeeTierThreshold rows
    5. Build minutes_pct percentile distributions per position group
    6. Build goal_contributions_per_90 percentile distributions per (pos, tier)
    7. Score every TransferFeature row (all four components + composite)
    8. Upsert TransferGrade rows, attaching scoring_version_id
    9. Activate the new ScoringVersion (and deactivate prior ones) in a single tx

`--dry-run` skips every DB write but produces the same logging.
`--recalibrate` forces fresh rate calibration regardless of any active version.
"""

import json
import logging
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import ScoringVersion, TransferFeature, TransferGrade
from ml.calibrate import calibrate_value_rates
from ml.explain import (
    explain_financial_return,
    explain_minutes,
    explain_production,
    explain_value_trajectory,
)
from ml.scoring import (
    GK_POSITION,
    build_minutes_distribution,
    build_production_distribution,
    compose_scores,
    score_financial_return,
    score_minutes,
    score_production,
    score_value_trajectory,
)
from ml.tiers import compute_tier_boundaries, persist_tier_thresholds
from ml.utils import clip_score, derive_letter_grade, is_worth_the_fee

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "scoring_config.json"
VERSION_PREFIX = "v1.0"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def grade_all(session: Session, dry_run: bool = False, recalibrate: bool = False) -> int:
    """Run the full grading pipeline. Returns the count of grades written.

    `dry_run=True` runs the full computation and logs the distribution but
    writes nothing to the database (useful for previewing config changes).
    """
    config = _load_config()
    weights = config["component_weights"]
    sigmoid_scales = config["sigmoid_scales"]
    min_group = int(config.get("min_comparison_group_size", 20))

    # Step 2 — create the version row up front so its id is the FK target for
    # FeeTierThreshold and TransferGrade rows produced by this run.
    if dry_run:
        scoring_version_id = -1
        version_str = f"dry-run-{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    else:
        scoring_version = _create_scoring_version(session, config)
        scoring_version_id = scoring_version.id
        version_str = scoring_version.version
    logger.info("Scoring version: %s (id=%s, dry_run=%s)", version_str, scoring_version_id, dry_run)

    # Step 3 — calibrate (or reuse cached) rates
    calibrated_rates = _resolve_calibrated_rates(session, config, recalibrate=recalibrate)
    if not dry_run:
        scoring_version.calibrated_rates = calibrated_rates
        session.flush()

    # Step 4 — fee-tier boundaries
    tier_cache = compute_tier_boundaries(session, config)
    if not dry_run:
        persist_tier_thresholds(session, scoring_version_id, tier_cache)

    # Steps 5 & 6 — distribution caches
    minutes_dists = build_minutes_distribution(session)
    production_dists = build_production_distribution(session, tier_cache)

    # Step 7 — score every TransferFeature row
    grade_rows: list[dict] = []
    for feature_row in _iter_feature_rows(session):
        grade_row = _score_one(
            feature_row=feature_row,
            minutes_dists=minutes_dists,
            production_dists=production_dists,
            tier_cache=tier_cache,
            calibrated_rates=calibrated_rates,
            weights=weights,
            sigmoid_scales=sigmoid_scales,
            min_group=min_group,
            scoring_version_id=scoring_version_id,
        )
        if grade_row is not None:
            grade_rows.append(grade_row)

    # Step 8 — persist (skipped in dry-run)
    if not dry_run:
        _upsert_grade_rows(session, grade_rows)
        scoring_version.total_scored = len(grade_rows)
        scoring_version.notes = _summarise_notes(grade_rows)

    # Step 9 — flip is_active in a single transaction
    if not dry_run:
        _activate_scoring_version(session, scoring_version_id)
        session.commit()

    _log_distribution(grade_rows, dry_run=dry_run)
    return len(grade_rows)


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _create_scoring_version(session: Session, config: dict) -> ScoringVersion:
    """Insert an inactive ScoringVersion row and return it (with id populated)."""
    version_str = _generate_version_string(session)
    sv = ScoringVersion(
        version=version_str,
        scored_at=datetime.now(timezone.utc),
        total_scored=0,
        formula_config=config,
        component_weights=config["component_weights"],
        calibrated_rates={},  # filled in after calibration
        is_active=False,
    )
    session.add(sv)
    session.flush()
    return sv


def _generate_version_string(session: Session) -> str:
    """Generate a unique version string per `v1.0.{YYYYMMDD}.{HHMMSS}` (UTC)."""
    now = datetime.now(timezone.utc)
    base = f"{VERSION_PREFIX}.{now:%Y%m%d}.{now:%H%M%S}"
    # If two runs land in the same UTC second, append `-1`, `-2`, ...
    suffix = 0
    candidate = base
    while session.query(ScoringVersion).filter_by(version=candidate).first():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def _resolve_calibrated_rates(
    session: Session, config: dict, recalibrate: bool,
) -> dict[str, dict[str, float]]:
    """Use the active scoring version's cached rates unless `recalibrate` is set."""
    if not recalibrate:
        active = session.query(ScoringVersion).filter_by(is_active=True).first()
        if active and active.calibrated_rates:
            logger.info("Reusing calibrated rates from active version %s.", active.version)
            return active.calibrated_rates
    return calibrate_value_rates(session, config)


def _iter_feature_rows(session: Session) -> Iterable[TransferFeature]:
    """Stream features in chunks to keep memory bounded for large datasets."""
    return session.query(TransferFeature).yield_per(1000)


# ---------------------------------------------------------------------------
# Per-row scoring
# ---------------------------------------------------------------------------


def _score_one(
    *,
    feature_row: TransferFeature,
    minutes_dists,
    production_dists,
    tier_cache,
    calibrated_rates,
    weights,
    sigmoid_scales,
    min_group: int,
    scoring_version_id: int,
) -> dict | None:
    """Build the TransferGrade dict for one feature row, or None if ungradeable."""
    is_complete = feature_row.exit_fee_eur is not None
    is_gk = feature_row.position_group == GK_POSITION

    # Component scores
    minutes = score_minutes(feature_row, minutes_dists)
    production, tier_idx, tier_label = score_production(
        feature_row, production_dists, tier_cache, min_group_size=min_group,
    )
    value_trajectory, expected_value_pct = score_value_trajectory(
        feature_row, calibrated_rates, sigmoid_scales["value_trajectory"],
    )
    financial_return = score_financial_return(
        feature_row, sigmoid_scales["financial_return"],
    )

    composite = compose_scores(
        minutes, production, value_trajectory, financial_return, weights,
    )
    if composite is None:
        # No components produced a score — skip rather than write a meaningless row.
        return None
    composite = clip_score(composite)
    composite_dec = Decimal(str(composite)).quantize(Decimal("0.01"))

    return {
        "transfer_id": feature_row.transfer_id,
        "composite_score": composite_dec,
        "letter_grade": derive_letter_grade(composite_dec),
        "worth_the_fee": is_worth_the_fee(composite_dec),
        "is_complete": is_complete,
        "minutes_score": _quantize_score(minutes),
        "minutes_explanation": explain_minutes(feature_row.minutes_pct),
        "production_score": _quantize_score(production),
        "production_explanation": explain_production(
            is_goalkeeper=is_gk,
            goal_contributions_per_90=feature_row.goal_contributions_per_90,
            percentile=production,
            position_group=feature_row.position_group,
            fee_tier_label=tier_label,
        ),
        "value_trajectory_score": _quantize_score(value_trajectory),
        "value_trajectory_explanation": explain_value_trajectory(
            value_change_pct=feature_row.value_change_pct,
            expected_value_change_pct=expected_value_pct,
            value_at_transfer_cents=feature_row.value_at_transfer,
            value_at_departure_cents=feature_row.value_at_departure,
            tenure_days=feature_row.tenure_days,
        ),
        "financial_return_score": _quantize_score(financial_return),
        "financial_return_explanation": explain_financial_return(
            is_complete=is_complete,
            exit_fee_ratio=feature_row.exit_fee_ratio,
            expected_exit_ratio=feature_row.expected_exit_ratio,
            exit_ratio_vs_expected=feature_row.exit_ratio_vs_expected,
            age_at_departure=feature_row.age_at_departure,
        ),
        "scoring_version_id": scoring_version_id,
        "graded_at": datetime.now(timezone.utc),
    }


def _quantize_score(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _upsert_grade_rows(session: Session, rows: list[dict]) -> int:
    """Bulk upsert TransferGrade rows with ON CONFLICT(transfer_id) DO UPDATE."""
    if not rows:
        return 0
    stmt = pg_insert(TransferGrade).values(rows)
    update_cols = {col: stmt.excluded[col] for col in rows[0] if col != "transfer_id"}
    stmt = stmt.on_conflict_do_update(
        index_elements=["transfer_id"],
        set_=update_cols,
    )
    session.execute(stmt)
    session.flush()
    return len(rows)


def _activate_scoring_version(session: Session, new_version_id: int) -> None:
    """Atomic two-statement update: deactivate all others, then activate the new one.

    Driven by a partial unique index on `is_active = true` (only one active row
    allowed). Order matters — we deactivate first to free the index, then mark
    the new run active.
    """
    session.execute(
        update(ScoringVersion)
        .where(ScoringVersion.id != new_version_id)
        .values(is_active=False)
    )
    session.execute(
        update(ScoringVersion)
        .where(ScoringVersion.id == new_version_id)
        .values(is_active=True)
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _summarise_notes(rows: list[dict]) -> str:
    """One-line summary stored on `ScoringVersion.notes`."""
    counts = Counter(r["letter_grade"] for r in rows)
    ordered = ["A", "B+", "B", "C+", "C", "D", "F"]
    parts = [f"{g}={counts.get(g, 0)}" for g in ordered]
    return f"Scored {len(rows)} transfers. Distribution: {', '.join(parts)}."


def _log_distribution(rows: list[dict], dry_run: bool) -> None:
    """Emit grade distribution + per-position-group score summaries."""
    counts = Counter(r["letter_grade"] for r in rows)
    ordered = ["A", "B+", "B", "C+", "C", "D", "F"]
    distribution_str = ", ".join(f"{g}={counts.get(g, 0)}" for g in ordered)
    prefix = "DRY-RUN " if dry_run else ""
    logger.info("%sGrade distribution (%d total): %s", prefix, len(rows), distribution_str)

    # Per-position breakdown: median composite by position group
    by_pg: dict[str, list[float]] = {}
    for r in rows:
        # We don't have position_group in the grade row; pull from explanation context if needed.
        # For the per-position log, derive from `is_complete` / explanation patterns is messy —
        # instead, we trust the caller to log this elsewhere if needed. (See dedicated query
        # in the validation script.)
        pass
    # NOTE: a proper per-position breakdown joins TransferGrade with TransferFeature on
    # transfer_id and groups by position_group — implemented in the validation tool, not here,
    # because it requires a session round-trip we don't want to force in dry-run.