"""Component scoring functions for the transfer grading pipeline.

Each function maps a TransferFeature row to a 0-100 score for one of the four
components, returning None when the necessary input is unavailable. The grading
orchestrator (`grade.py`) combines them via `compose_scores`, which uses
`utils.weighted_average` to redistribute NULL components' weights proportionally.

No DB writes happen in this module — pure computation only.
"""

from collections import defaultdict

import numpy as np
from sqlalchemy.orm import Session

from app.models import TransferFeature
from ml.calibrate import expected_trajectory_pct
from ml.tiers import lookup_tier
from ml.utils import clip_score, percentile_rank, sigmoid_to_100, weighted_average

GK_POSITION = "GK"


# ---------------------------------------------------------------------------
# Distribution builders
# ---------------------------------------------------------------------------


def build_minutes_distribution(session: Session) -> dict[str, np.ndarray]:
    """{position_group: ascending-sorted ndarray of minutes_pct} across all features.

    Includes both completed and in-progress transfers, per spec — minutes
    contribution is evaluable regardless of departure status.
    """
    rows = (
        session.query(TransferFeature.position_group, TransferFeature.minutes_pct)
        .filter(
            TransferFeature.position_group.is_not(None),
            TransferFeature.minutes_pct.is_not(None),
        )
        .all()
    )
    by_pg: dict[str, list[float]] = defaultdict(list)
    for pg, mp in rows:
        by_pg[pg].append(float(mp))
    return {pg: np.sort(np.array(v, dtype=np.float64)) for pg, v in by_pg.items()}


def build_production_distribution(
    session: Session,
    tier_cache: dict,
) -> dict[tuple[str, int], np.ndarray]:
    """{(position_group, tier_index): sorted ndarray of g+a/90} across all features.

    GK rows are excluded — production score is NULL for goalkeepers.
    """
    rows = (
        session.query(
            TransferFeature.position_group,
            TransferFeature.entry_fee_eur,
            TransferFeature.goal_contributions_per_90,
        )
        .filter(
            TransferFeature.position_group.is_not(None),
            TransferFeature.position_group != GK_POSITION,
            TransferFeature.entry_fee_eur.is_not(None),
            TransferFeature.goal_contributions_per_90.is_not(None),
        )
        .all()
    )
    by_key: dict[tuple[str, int], list[float]] = defaultdict(list)
    for pg, fee, ga90 in rows:
        tier_info = lookup_tier(tier_cache, pg, int(fee))
        if tier_info is None:
            continue
        by_key[(pg, tier_info[0])].append(float(ga90))
    return {k: np.sort(np.array(v, dtype=np.float64)) for k, v in by_key.items()}


# ---------------------------------------------------------------------------
# Per-component scoring
# ---------------------------------------------------------------------------


def score_minutes(
    feature_row: TransferFeature,
    minutes_dists: dict[str, np.ndarray],
) -> float | None:
    """Mean-rank percentile of minutes_pct within position group."""
    if feature_row.minutes_pct is None or feature_row.position_group is None:
        return None
    dist = minutes_dists.get(feature_row.position_group)
    if dist is None or dist.size == 0:
        return None
    rank = percentile_rank(float(feature_row.minutes_pct), dist)
    return clip_score(rank) if rank is not None else None


def score_production(
    feature_row: TransferFeature,
    production_dists: dict[tuple[str, int], np.ndarray],
    tier_cache: dict,
    min_group_size: int = 20,
) -> tuple[float | None, int | None, str | None]:
    """Returns (score, tier_index, tier_label).

    Falls back through three comparison groups in order:
        1. (position_group, exact tier) — used if it has ≥ min_group_size
        2. (position_group, tier±1) concatenated
        3. position_group only (all tiers combined)

    GK transfers always return (None, None, None) — production is N/A for them
    per spec, and the weight is redistributed via `compose_scores`.
    """
    if (
        feature_row.position_group is None
        or feature_row.position_group == GK_POSITION
        or feature_row.entry_fee_eur is None
        or feature_row.goal_contributions_per_90 is None
    ):
        return None, None, None

    pg = feature_row.position_group
    tier_info = lookup_tier(tier_cache, pg, int(feature_row.entry_fee_eur))
    if tier_info is None:
        return None, None, None
    tier_idx, label = tier_info
    ga90 = float(feature_row.goal_contributions_per_90)

    # 1. Native bucket
    dist = production_dists.get((pg, tier_idx))
    if dist is not None and dist.size >= min_group_size:
        rank = percentile_rank(ga90, dist)
        return (clip_score(rank) if rank is not None else None), tier_idx, label

    # 2. Widen to immediate neighbours
    pieces = [
        d for d in (
            production_dists.get((pg, tier_idx - 1)),
            production_dists.get((pg, tier_idx)),
            production_dists.get((pg, tier_idx + 1)),
        )
        if d is not None and d.size > 0
    ]
    if pieces:
        widened = np.sort(np.concatenate(pieces))
        if widened.size >= min_group_size:
            rank = percentile_rank(ga90, widened)
            return (clip_score(rank) if rank is not None else None), tier_idx, label

    # 3. Position-only fallback
    pg_pieces = [v for k, v in production_dists.items() if k[0] == pg and v.size > 0]
    if pg_pieces:
        all_pg = np.sort(np.concatenate(pg_pieces))
        rank = percentile_rank(ga90, all_pg)
        return (clip_score(rank) if rank is not None else None), tier_idx, label

    return None, tier_idx, label


def score_value_trajectory(
    feature_row: TransferFeature,
    calibrated_rates: dict,
    scale: float,
) -> tuple[float | None, float | None]:
    """Returns (score, expected_pct_as_percentage_or_None).

    Compares the actual `value_change_pct` to the compounded expected change
    over the stint duration (per the calibrated/default annual rate table).
    Uses age_at_departure when available; otherwise derives it from tenure_days
    so in-progress transfers still get a value-trajectory score.
    """
    if (
        feature_row.value_change_pct is None
        or feature_row.position_group is None
        or feature_row.age_at_transfer is None
        or feature_row.tenure_days is None
        or feature_row.tenure_days <= 0
    ):
        return None, None

    age_start = float(feature_row.age_at_transfer)
    if feature_row.age_at_departure is not None:
        age_end = float(feature_row.age_at_departure)
    else:
        age_end = age_start + (feature_row.tenure_days / 365.25)

    expected_fraction = expected_trajectory_pct(
        feature_row.position_group, age_start, age_end, calibrated_rates,
    )
    expected_pct = expected_fraction * 100.0
    diff = float(feature_row.value_change_pct) - expected_pct
    return clip_score(sigmoid_to_100(diff, scale)), expected_pct


def score_financial_return(feature_row: TransferFeature, scale: float) -> float | None:
    """Sigmoid mapping of `exit_ratio_vs_expected`. None for in-progress transfers."""
    if feature_row.exit_ratio_vs_expected is None:
        return None
    return clip_score(sigmoid_to_100(float(feature_row.exit_ratio_vs_expected), scale))


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------


def compose_scores(
    minutes_score: float | None,
    production_score: float | None,
    value_trajectory_score: float | None,
    financial_return_score: float | None,
    weights: dict[str, float],
) -> float | None:
    """Weighted average of non-NULL components; NULL components' weights drop.

    `weighted_average` handles the redistribution: when production is NULL (GK),
    or financial_return is NULL (in-progress), or value_trajectory is NULL
    (no valuation data), the remaining weights effectively re-normalize.
    """
    return weighted_average(
        {
            "minutes": minutes_score,
            "production": production_score,
            "value_trajectory": value_trajectory_score,
            "financial_return": financial_return_score,
        },
        weights,
    )
