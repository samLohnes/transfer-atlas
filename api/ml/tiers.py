"""Fee-tier percentile boundaries per position group.

Builds the 5 EUR-cent boundaries (0–25, 25–50, 50–75, 75–90, 90–100 percentiles)
for each position group from the qualifying TransferFeature rows, then persists
one FeeTierThreshold row per (scoring_version, position_group, tier).

The asymmetric upper tiers (75-90, 90-100) capture that the most expensive
transfers are a distinct population and shouldn't be lumped with mid-priced ones.
"""

import logging
from collections import defaultdict
from typing import Sequence

import numpy as np
from sqlalchemy.orm import Session

from app.models import FeeTierThreshold, TransferFeature

logger = logging.getLogger(__name__)


def compute_tier_boundaries(
    session: Session, config: dict,
) -> dict[str, list[tuple[int, int | None, str]]]:
    """Compute fee-tier boundaries from TransferFeature data (pure read; no writes).

    Returns an in-memory cache keyed by scoring_group:
        {scoring_group: [(lower_eur, upper_eur, label), ...]}
    where `upper_eur` is None for the top tier (open-ended). The scoring step
    resolves each transfer's tier from this cache via `lookup_tier`.

    `scoring_group` = `position_subgroup or position_group` so MID splits into
    DM/CM/AM and DEF splits into CB/FB, while GK and FWD stay at the
    position_group level (their position_subgroup collapses back to the group).
    """
    boundaries = config["fee_tiers"]["boundaries"]  # e.g. [0, 25, 50, 75, 90, 100]
    labels: Sequence[str] = config["fee_tiers"]["labels"]
    if len(boundaries) != len(labels) + 1:
        raise ValueError(
            f"fee_tiers config malformed: {len(boundaries)} boundaries vs {len(labels)} labels."
        )

    fees_by_sg: dict[str, list[int]] = defaultdict(list)
    rows = (
        session.query(
            TransferFeature.position_group,
            TransferFeature.position_subgroup,
            TransferFeature.entry_fee_eur,
        )
        .filter(
            TransferFeature.position_group.is_not(None),
            TransferFeature.entry_fee_eur.is_not(None),
        )
        .all()
    )
    for pg, psg, fee in rows:
        scoring_group = psg or pg
        fees_by_sg[scoring_group].append(int(fee))

    cache: dict[str, list[tuple[int, int | None, str]]] = {}
    for sg, fees in fees_by_sg.items():
        if not fees:
            continue
        arr = np.array(fees, dtype=np.int64)
        percentile_values = [int(np.percentile(arr, p)) for p in boundaries[1:-1]]

        tier_rows: list[tuple[int, int | None, str]] = []
        prev = int(arr.min())
        for i, label in enumerate(labels):
            upper = percentile_values[i] if i < len(percentile_values) else None
            tier_rows.append((prev, upper, label))
            prev = upper if upper is not None else prev
        cache[sg] = tier_rows

    logger.info("Fee tiers computed for %d scoring group(s).", len(cache))
    return cache


def persist_tier_thresholds(
    session: Session,
    scoring_version_id: int,
    cache: dict[str, list[tuple[int, int | None, str]]],
) -> int:
    """Write one FeeTierThreshold row per (scoring_group, tier) for the given scoring run.

    Note: the table column is named `position_group` for legacy reasons but now
    holds `scoring_group` values (DM/CM/AM/CB/FB plus the unchanged GK/FWD), so
    callers must look up by scoring_group rather than the raw position_group.
    """
    persist_rows: list[dict] = []
    for sg, tier_rows in cache.items():
        for i, (lower, upper, label) in enumerate(tier_rows, start=1):
            persist_rows.append({
                "scoring_version_id": scoring_version_id,
                "position_group": sg,
                "tier": i,
                "lower_fee_eur": lower,
                "upper_fee_eur": upper,
                "label": label,
            })
    if persist_rows:
        session.execute(FeeTierThreshold.__table__.insert(), persist_rows)
        session.flush()
    logger.info("FeeTierThreshold rows written: %d", len(persist_rows))
    return len(persist_rows)


def lookup_tier(
    cache: dict[str, list[tuple[int, int | None, str]]],
    scoring_group: str,
    fee_eur: int,
) -> tuple[int, str] | None:
    """Resolve a fee to its (tier_index_1based, label) within the scoring group.

    `scoring_group` is `position_subgroup or position_group` (DM/CM/AM/CB/FB
    plus the unchanged GK/FWD). Returns None when the group has no recorded
    tiers (e.g. no qualifying transfers, unusual on real data).
    """
    tiers = cache.get(scoring_group)
    if not tiers:
        return None
    for i, (lower, upper, label) in enumerate(tiers, start=1):
        if upper is None or fee_eur < upper:
            return i, label
    # Shouldn't reach — top tier has upper=None and matches anything ≥ its lower.
    last_idx = len(tiers)
    return last_idx, tiers[-1][2]
