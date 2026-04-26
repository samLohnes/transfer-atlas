"""Annualized value-trajectory rate calibration + per-stint expected-change computation.

Two responsibilities:

1. `calibrate_value_rates(session, config)` — read PlayerValuation history and
   compute median annual value change per (position_group × age_band). Buckets
   under `calibration_min_samples` fall back to the config's `default_value_rates`.

2. `expected_trajectory_pct(position_group, age_at_transfer, age_at_end, rates)`
   — compound the calibrated annual rates across a stint, prorating partial
   years at age-band boundaries. Used by the value-trajectory component to
   compare actual `value_change_pct` against this baseline.
"""

import logging
from collections import defaultdict
from decimal import Decimal

import numpy as np
from sqlalchemy.orm import Session

from app.models import Player, PlayerValuation

logger = logging.getLogger(__name__)


# Age-band ranges per plan §task-04. Ordered from youngest → oldest.
# Each entry is (band_key, lower_bound_inclusive, upper_bound_exclusive).
AGE_BANDS: list[tuple[str, float, float]] = [
    ("under_21", 0.0, 21.0),
    ("21_23", 21.0, 23.0),
    ("23_25", 23.0, 25.0),
    ("25_27", 25.0, 27.0),
    ("27_29", 27.0, 29.0),
    ("29_31", 29.0, 31.0),
    ("31_plus", 31.0, float("inf")),
]


def age_band(age_years: float) -> str:
    """Return the band key (e.g. '23_25') containing this age."""
    for key, lo, hi in AGE_BANDS:
        if lo <= age_years < hi:
            return key
    return "31_plus"  # safety net for ages above the table; shouldn't trip in practice


def _band_upper(band_key: str) -> float:
    for key, _lo, hi in AGE_BANDS:
        if key == band_key:
            return hi
    return float("inf")


def calibrate_value_rates(session: Session, config: dict) -> dict[str, dict[str, float]]:
    """Compute calibrated annual value-change rates from PlayerValuation history.

    Algorithm:
        - Pull every player's valuation timeseries (player_id, date, eur cents).
        - For each consecutive pair (val_a, val_b) with val_a > 0 and date_b > date_a:
            annual_rate = (val_b / val_a) ** (1 / elapsed_years) - 1
          Bucket by (position_group, age_band_at_date_a).
        - For each bucket with ≥ calibration_min_samples observations, use the
          median annual rate. Otherwise fall back to config['default_value_rates'].

    Returns a {position_group: {age_band: rate_as_fraction}} dict suitable for
    snapshotting into ScoringVersion.calibrated_rates.
    """
    min_samples = int(config.get("calibration_min_samples", 30))
    defaults: dict[str, dict[str, float]] = config["default_value_rates"]

    # Pull player → (position_group, dob)
    player_rows = (
        session.query(Player.id, Player.position_group, Player.date_of_birth)
        .filter(Player.position_group.is_not(None), Player.date_of_birth.is_not(None))
        .all()
    )
    player_meta = {p.id: (p.position_group, p.date_of_birth) for p in player_rows}

    # Pull valuations grouped per player, sorted by date
    by_player: dict[int, list[tuple]] = defaultdict(list)
    for v in session.query(
        PlayerValuation.player_id, PlayerValuation.valuation_date, PlayerValuation.valuation_eur,
    ).order_by(PlayerValuation.player_id, PlayerValuation.valuation_date).all():
        by_player[v.player_id].append((v.valuation_date, v.valuation_eur))

    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for player_id, history in by_player.items():
        meta = player_meta.get(player_id)
        if meta is None:
            continue
        position_group, dob = meta
        for (d_a, val_a), (d_b, val_b) in zip(history, history[1:]):
            if val_a <= 0 or val_b <= 0:
                continue
            elapsed_days = (d_b - d_a).days
            if elapsed_days <= 0:
                continue
            elapsed_years = elapsed_days / 365.25
            try:
                annual_rate = (val_b / val_a) ** (1 / elapsed_years) - 1
            except (OverflowError, ZeroDivisionError, ValueError):
                continue
            age_at_a = (d_a - dob).days / 365.25
            band_key = age_band(age_at_a)
            buckets[(position_group, band_key)].append(annual_rate)

    # Build the result dict: start from defaults, override where calibration succeeded.
    out: dict[str, dict[str, float]] = {pg: dict(rates) for pg, rates in defaults.items()}
    calibrated_count = 0
    fallback_count = 0
    for pg in defaults.keys():
        for band_key, _lo, _hi in AGE_BANDS:
            samples = buckets.get((pg, band_key), [])
            if len(samples) >= min_samples:
                out[pg][band_key] = float(np.median(samples))
                calibrated_count += 1
            else:
                fallback_count += 1

    logger.info(
        "Calibration: %d buckets calibrated (≥ %d samples), %d fell back to defaults.",
        calibrated_count, min_samples, fallback_count,
    )
    return out


def expected_trajectory_pct(
    position_group: str,
    age_at_transfer: Decimal | float,
    age_at_end: Decimal | float,
    rates: dict[str, dict[str, float]],
) -> float:
    """Expected fractional value change over [age_at_transfer, age_at_end] for a position group.

    Compounds the per-band annual rates, prorating partial years at band edges.
    Example (MID, 22.5 → 26.3): year 1 in 21-23 (+10%), 2y in 23-25 (+5% each),
    0.8y in 25-27 (+2%) → (1.10 × 1.05² × 1.02^0.8) - 1 ≈ 0.224 (22.4%).

    Returns 0.0 when the position is unknown or the interval is non-positive.
    """
    pg_rates = rates.get(position_group)
    if pg_rates is None:
        return 0.0

    start = float(age_at_transfer)
    end = float(age_at_end)
    if end <= start:
        return 0.0

    multiplier = 1.0
    cursor = start
    # Bound the loop iterations to AGE_BANDS length × 2 as a safety net against
    # any pathological input that fails to advance the cursor.
    for _ in range(len(AGE_BANDS) * 2):
        if cursor >= end:
            break
        band_key = age_band(cursor)
        band_top = _band_upper(band_key)
        years_in_band = min(end, band_top) - cursor
        if years_in_band <= 0:
            break
        rate = pg_rates.get(band_key, 0.0)
        multiplier *= (1.0 + rate) ** years_in_band
        cursor += years_in_band

    return multiplier - 1.0
