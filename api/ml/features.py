"""Feature engineering pipeline for the transfer grading system.

Computes one TransferFeature row per qualifying transfer (permanent, non-free,
with a non-null transfer_date). Two-pass design:

    Pass 1 — per-transfer computation:
        - identify the stint (transfer_date → next permanent departure or today)
        - minutes / production from Appearance, optionally filtered by a
          competition whitelist sourced from scoring_config.json
        - market value trajectory from PlayerValuation (closest valuation within
          a 90-day buffer; pre-transfer wins on tie)
        - exit fee ratio for completed transfers

    Pass 2 — peer-group expected exit ratio:
        - for each complete transfer, average the exit_fee_ratio of peers
          matching position_group + age_at_transfer (±2y) + age_at_departure (±2y)
        - widen the age windows by 1y up to ±5 if fewer than 10 peers
        - fall back to position-group-only if still under threshold

Run with: `python -m ml.features` from api/ (DATABASE_URL must be set).
"""

import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Appearance, Player, PlayerValuation, Transfer, TransferFeature

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "scoring_config.json"

# Spec: closest valuation within 90 days of stint start/end qualifies as "at transfer"/"at departure".
VALUE_BUFFER_DAYS = 90

# Exit-ratio peer matching: ±2y on each age, widened to ±5y, then fall back to position-only.
EXIT_RATIO_INITIAL_AGE_WINDOW = 2
EXIT_RATIO_MAX_AGE_WINDOW = 5
EXIT_RATIO_MIN_GROUP_SIZE = 10

# Numeric column ceilings, mirroring the migration. Values beyond these are clipped
# (with a logged warning) rather than allowed to overflow at INSERT time. The plan's
# precisions cover the overwhelming majority of real transfers; outliers come from
# cases like a player bought for €5K who later commands a €100M fee, which produces
# ratios past the schema's bounds.
VALUE_CHANGE_PCT_MAX = Decimal("99999.99")    # Numeric(7,2)
EXIT_RATIO_MAX = Decimal("999.9999")           # Numeric(7,4)

# Transfermarkt occasionally records loan-backs as permanent fee=0 transfers
# (e.g. Julián Álvarez 2022: River Plate → Man City paid, then a fee=0
# "permanent" Man City → River Plate the next day, then a fee=0 return to
# Man City five months later). When scanning for the real stint-end departure,
# skip any fee=0 permanent departure followed by a return to the same buying
# club within this window — those are misclassified loan-backs, not genuine
# exits. Genuine free transfers (Bosman exits) have no such return.
LOAN_BACK_RETURN_WINDOW_DAYS = 540


@dataclass
class StintInfo:
    """A player's tenure at a single buying club, derived from one entry transfer."""

    transfer_id: int
    player_id: int
    club_id: int
    transfer_date: date
    stint_end: date
    is_complete: bool
    entry_fee_eur: int
    exit_fee_eur: int | None  # None when in-progress (no permanent departure yet)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_features(session: Session) -> int:
    """Compute and upsert features for every qualifying transfer.

    Returns the count of feature rows written. Idempotent — re-running updates
    existing rows via ON CONFLICT(transfer_id) DO UPDATE.
    """
    config = _load_config()
    comp_whitelist = _load_competition_whitelist(config)
    today = date.today()

    qualifying = _load_qualifying_transfers(session)
    logger.info("Qualifying transfers (permanent, non-free, dated): %d", len(qualifying))
    if not qualifying:
        return 0

    player_meta = _load_player_meta(session, [t.player_id for t in qualifying])
    all_transfers_by_player = _load_all_transfers_by_player(session)
    fee_percentiles = _precompute_fee_percentiles(qualifying, player_meta)

    feature_rows: list[dict] = []
    for i, transfer in enumerate(qualifying, start=1):
        if i % 500 == 0 or i == len(qualifying):
            logger.info("Computing features for transfer %d / %d", i, len(qualifying))

        meta = player_meta.get(transfer.player_id)
        if meta is None:
            logger.debug("Skipping transfer %d — no Player record", transfer.id)
            continue

        stint = _build_stint(transfer, all_transfers_by_player.get(transfer.player_id, []), today)
        row = _compute_one(session, stint, meta, comp_whitelist, fee_percentiles)
        feature_rows.append(row)

    _populate_expected_exit_ratios(feature_rows)
    written = _upsert_feature_rows(session, feature_rows)
    session.commit()

    complete = sum(1 for r in feature_rows if r["exit_fee_ratio"] is not None)
    logger.info(
        "Wrote %d feature rows (%d complete, %d in-progress).",
        written, complete, written - complete,
    )
    return written


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Load scoring_config.json from the api/ml/ directory."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _load_competition_whitelist(config: dict) -> list[str]:
    """Returns the configured competition_id list, or [] if missing/empty (with warning)."""
    raw = config.get("minutes", {}).get("competition_whitelist") or []
    if not raw:
        logger.warning(
            "competition_whitelist is empty — minutes_pct will not be filtered "
            "to competitive first-team competitions. Friendlies/youth/reserves "
            "will inflate denominators. Populate scoring_config.json before grading."
        )
    return [str(c) for c in raw]


# ---------------------------------------------------------------------------
# Bulk loaders
# ---------------------------------------------------------------------------


def _load_qualifying_transfers(session: Session) -> list[Transfer]:
    """Permanent transfers with non-null fee > 0 and a known transfer_date."""
    return (
        session.query(Transfer)
        .filter(
            Transfer.fee_is_loan.is_(False),
            Transfer.fee_eur.is_not(None),
            Transfer.fee_eur > 0,
            Transfer.transfer_date.is_not(None),
        )
        .order_by(Transfer.transfer_date)
        .all()
    )


def _load_player_meta(session: Session, player_ids: Iterable[int]) -> dict[int, Player]:
    ids = sorted(set(player_ids))
    if not ids:
        return {}
    return {p.id: p for p in session.query(Player).filter(Player.id.in_(ids)).all()}


def _load_all_transfers_by_player(session: Session) -> dict[int, list[Transfer]]:
    """All dated transfers (loan + permanent) grouped by player, ordered by date."""
    out: dict[int, list[Transfer]] = {}
    rows = (
        session.query(Transfer)
        .filter(Transfer.transfer_date.is_not(None))
        .order_by(Transfer.player_id, Transfer.transfer_date)
        .all()
    )
    for r in rows:
        out.setdefault(r.player_id, []).append(r)
    return out


# ---------------------------------------------------------------------------
# Stint identification
# ---------------------------------------------------------------------------


def _build_stint(
    transfer: Transfer,
    player_transfers: Sequence[Transfer],
    today: date,
) -> StintInfo:
    """Derive the stint window for a single buying-club transfer.

    Stint ends at the chronologically next *permanent* (non-loan) transfer where
    the player leaves the buying club. Loan-out transfers do not end the stint;
    the player's loan-club appearances are naturally excluded by the
    `Appearance.club_id == stint.club_id` filter elsewhere.

    Heuristic for misclassified loan-backs: Transfermarkt sometimes records a
    loan-back as a permanent fee=0 transfer. We detect this by checking whether
    the player returns to the same buying club within
    `LOAN_BACK_RETURN_WINDOW_DAYS` of the candidate departure — if so we treat
    it as a sub-stint and look at the next permanent departure instead.
    """
    candidates = sorted(
        (
            t for t in player_transfers
            if (
                t.from_club_id == transfer.to_club_id
                and t.fee_is_loan is False
                and t.transfer_date is not None
                and t.transfer_date > transfer.transfer_date
            )
        ),
        key=lambda t: t.transfer_date,
    )

    departures = [
        d for d in candidates
        if not _is_misclassified_loan_back(d, transfer.to_club_id, player_transfers)
    ]

    if departures:
        dep = departures[0]
        return StintInfo(
            transfer_id=transfer.id,
            player_id=transfer.player_id,
            club_id=transfer.to_club_id,
            transfer_date=transfer.transfer_date,
            stint_end=dep.transfer_date,
            is_complete=True,
            entry_fee_eur=transfer.fee_eur,
            exit_fee_eur=dep.fee_eur,
        )

    return StintInfo(
        transfer_id=transfer.id,
        player_id=transfer.player_id,
        club_id=transfer.to_club_id,
        transfer_date=transfer.transfer_date,
        stint_end=today,
        is_complete=False,
        entry_fee_eur=transfer.fee_eur,
        exit_fee_eur=None,
    )


def _is_misclassified_loan_back(
    candidate: Transfer,
    buying_club_id: int,
    player_transfers: Sequence[Transfer],
) -> bool:
    """True when a fee=0 'permanent' departure is followed by a return to the buying club."""
    if candidate.fee_eur not in (None, 0):
        return False  # Real paid sale — never reclassify.
    window_end = candidate.transfer_date + timedelta(days=LOAN_BACK_RETURN_WINDOW_DAYS)
    return any(
        t.to_club_id == buying_club_id
        and t.transfer_date is not None
        and candidate.transfer_date < t.transfer_date <= window_end
        for t in player_transfers
    )


# ---------------------------------------------------------------------------
# Per-transfer feature row
# ---------------------------------------------------------------------------


def _compute_one(
    session: Session,
    stint: StintInfo,
    player: Player,
    comp_whitelist: list[str],
    fee_percentiles: dict[int, Decimal],
) -> dict:
    """Build the dict of TransferFeature column values for one stint."""
    total_minutes, total_appearances, goals, assists = _query_player_stint_totals(
        session, stint, comp_whitelist,
    )
    available_minutes = _query_available_minutes(session, stint, comp_whitelist)

    # NULL minutes/production when the player has zero appearance rows. The spec
    # distinguishes "we don't know" (NULL) from "they played and contributed
    # nothing" (0). Zero appearance rows means the former.
    has_appearance_data = total_appearances > 0
    minutes_pct = _safe_minutes_pct(total_minutes, available_minutes) if has_appearance_data else None
    g_per_90, a_per_90, ga_per_90 = (
        _per_90_metrics(total_minutes, goals, assists)
        if has_appearance_data
        else (None, None, None)
    )

    val_features = _compute_value_trajectory(session, stint)

    age_at_transfer = _years_between(player.date_of_birth, stint.transfer_date)
    age_at_departure = (
        _years_between(player.date_of_birth, stint.stint_end)
        if stint.is_complete
        else None
    )

    exit_fee_ratio: Decimal | None = None
    if stint.is_complete and stint.exit_fee_eur is not None and stint.entry_fee_eur > 0:
        raw = Decimal(stint.exit_fee_eur) / Decimal(stint.entry_fee_eur)
        exit_fee_ratio = _clip_decimal(
            raw, EXIT_RATIO_MAX, label=f"exit_fee_ratio for transfer {stint.transfer_id}"
        ).quantize(Decimal("0.0001"))

    return {
        "transfer_id": stint.transfer_id,
        "tenure_days": (stint.stint_end - stint.transfer_date).days,
        "total_appearances": total_appearances if has_appearance_data else None,
        "total_minutes": total_minutes if has_appearance_data else None,
        "minutes_pct": minutes_pct,
        "goals": goals if has_appearance_data else None,
        "assists": assists if has_appearance_data else None,
        "goals_per_90": g_per_90,
        "assists_per_90": a_per_90,
        "goal_contributions_per_90": ga_per_90,
        "position_group": player.position_group,
        "fee_percentile": fee_percentiles.get(stint.transfer_id),
        "entry_fee_eur": stint.entry_fee_eur,
        "exit_fee_eur": stint.exit_fee_eur,
        "age_at_transfer": age_at_transfer,
        "age_at_departure": age_at_departure,
        "value_at_transfer": val_features["value_at_transfer"],
        "peak_value_during_stint": val_features["peak_value_during_stint"],
        "value_at_departure": val_features["value_at_departure"],
        "value_change_pct": val_features["value_change_pct"],
        "exit_fee_ratio": exit_fee_ratio,
        "expected_exit_ratio": None,  # populated in pass 2
        "exit_ratio_vs_expected": None,  # populated in pass 2
        "international_caps": player.international_caps,
    }


# ---------------------------------------------------------------------------
# Minutes / production
# ---------------------------------------------------------------------------


def _query_player_stint_totals(
    session: Session, stint: StintInfo, comp_whitelist: list[str]
) -> tuple[int, int, int, int]:
    """Returns (total_minutes, total_appearances, total_goals, total_assists)."""
    q = session.query(
        func.coalesce(func.sum(Appearance.minutes_played), 0),
        func.count(Appearance.id),
        func.coalesce(func.sum(Appearance.goals), 0),
        func.coalesce(func.sum(Appearance.assists), 0),
    ).filter(
        Appearance.player_id == stint.player_id,
        Appearance.club_id == stint.club_id,
        Appearance.date >= stint.transfer_date,
        Appearance.date <= stint.stint_end,
    )
    if comp_whitelist:
        # IN (...) excludes NULLs implicitly, satisfying the spec's
        # "exclude NULL competition_id from numerator and denominator".
        q = q.filter(Appearance.competition_id.in_(comp_whitelist))
    mins, apps, g, a = q.one()
    return int(mins or 0), int(apps or 0), int(g or 0), int(a or 0)


def _query_available_minutes(
    session: Session, stint: StintInfo, comp_whitelist: list[str]
) -> int:
    """Available minutes = (distinct game_ids the buying club appeared in) × 90."""
    q = session.query(func.count(func.distinct(Appearance.game_id))).filter(
        Appearance.club_id == stint.club_id,
        Appearance.date >= stint.transfer_date,
        Appearance.date <= stint.stint_end,
    )
    if comp_whitelist:
        q = q.filter(Appearance.competition_id.in_(comp_whitelist))
    return int(q.scalar() or 0) * 90


def _safe_minutes_pct(total_minutes: int, available_minutes: int) -> Decimal | None:
    """Return clipped 0-100 pct, or None if no club appearance data is available."""
    if available_minutes <= 0:
        return None
    pct = (Decimal(total_minutes) / Decimal(available_minutes)) * Decimal(100)
    return min(pct, Decimal(100)).quantize(Decimal("0.01"))


def _per_90_metrics(
    total_minutes: int, goals: int, assists: int
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Return (g/90, a/90, (g+a)/90), or all-None when 0 minutes (no signal)."""
    if total_minutes <= 0:
        return None, None, None
    factor = Decimal(90) / Decimal(total_minutes)
    return (
        (Decimal(goals) * factor).quantize(Decimal("0.001")),
        (Decimal(assists) * factor).quantize(Decimal("0.001")),
        (Decimal(goals + assists) * factor).quantize(Decimal("0.001")),
    )


# ---------------------------------------------------------------------------
# Market value trajectory
# ---------------------------------------------------------------------------


def _compute_value_trajectory(session: Session, stint: StintInfo) -> dict:
    """Closest valuations to stint start/end (within ±90 days) plus peak during stint."""
    earliest = stint.transfer_date - timedelta(days=VALUE_BUFFER_DAYS)
    latest = stint.stint_end + timedelta(days=VALUE_BUFFER_DAYS)

    rows: list[tuple[date, int]] = (
        session.query(PlayerValuation.valuation_date, PlayerValuation.valuation_eur)
        .filter(
            PlayerValuation.player_id == stint.player_id,
            PlayerValuation.valuation_date >= earliest,
            PlayerValuation.valuation_date <= latest,
        )
        .all()
    )

    if not rows:
        return {
            "value_at_transfer": None,
            "peak_value_during_stint": None,
            "value_at_departure": None,
            "value_change_pct": None,
        }

    val_at_transfer = _closest_valuation(rows, stint.transfer_date)
    val_at_departure = _closest_valuation(rows, stint.stint_end)

    in_window = [v for d, v in rows if stint.transfer_date <= d <= stint.stint_end]
    peak = max(in_window) if in_window else None

    value_change_pct: Decimal | None = None
    if (
        val_at_transfer is not None
        and val_at_transfer > 0
        and val_at_departure is not None
    ):
        delta = Decimal(val_at_departure - val_at_transfer)
        raw = (delta / Decimal(val_at_transfer)) * Decimal(100)
        value_change_pct = _clip_decimal(
            raw, VALUE_CHANGE_PCT_MAX, label=f"value_change_pct for player {stint.player_id}"
        ).quantize(Decimal("0.01"))

    return {
        "value_at_transfer": val_at_transfer,
        "peak_value_during_stint": peak,
        "value_at_departure": val_at_departure,
        "value_change_pct": value_change_pct,
    }


def _closest_valuation(rows: Sequence[tuple[date, int]], target: date) -> int | None:
    """Pick the valuation with the date closest to `target`. On a tie, prefer pre-target."""
    if not rows:
        return None
    return min(
        rows,
        key=lambda r: (abs((r[0] - target).days), 0 if r[0] <= target else 1),
    )[1]


# ---------------------------------------------------------------------------
# Ages
# ---------------------------------------------------------------------------


def _years_between(dob: date | None, target: date) -> Decimal | None:
    """Decimal years (one decimal place) between dob and target. None if dob unknown."""
    if dob is None:
        return None
    days = (target - dob).days
    return (Decimal(days) / Decimal("365.25")).quantize(Decimal("0.1"))


def _clip_decimal(
    value: Decimal,
    max_magnitude: Decimal,
    label: str,
    allow_negative: bool = True,
) -> Decimal:
    """Clamp `value` to ±max_magnitude, logging a warning when clipping fires.

    Used to keep computed ratios/percentages within the Numeric column precisions
    in `transfer_features` rather than allow a single outlier (e.g. a player
    bought for €5K and sold for €100M) to crash the whole pipeline.
    """
    if value > max_magnitude:
        logger.warning("Clipping %s to %s (was %s)", label, max_magnitude, value)
        return max_magnitude
    if allow_negative and value < -max_magnitude:
        logger.warning("Clipping %s to %s (was %s)", label, -max_magnitude, value)
        return -max_magnitude
    return value


# ---------------------------------------------------------------------------
# Fee percentile (cross-transfer pre-computation)
# ---------------------------------------------------------------------------


def _precompute_fee_percentiles(
    qualifying: Sequence[Transfer], player_meta: dict[int, Player]
) -> dict[int, Decimal]:
    """Mean-rank percentile of each transfer's fee within its position_group.

    Uses the average of strict-less and ≤ ranks (matches scipy.stats.percentileofscore
    with kind='mean'): the median fee in a group lands at exactly the 50th percentile.
    Transfers whose player has no `position_group` are omitted (their feature row
    will store NULL for fee_percentile).
    """
    fees_by_group: dict[str, list[tuple[int, int]]] = {}
    for t in qualifying:
        meta = player_meta.get(t.player_id)
        if meta is None or meta.position_group is None:
            continue
        fees_by_group.setdefault(meta.position_group, []).append((t.id, t.fee_eur))

    out: dict[int, Decimal] = {}
    for entries in fees_by_group.values():
        sorted_fees = np.sort(np.array([e[1] for e in entries], dtype=np.int64))
        n = len(sorted_fees)
        for tid, fee in entries:
            strict = int(np.searchsorted(sorted_fees, fee, side="left"))
            inclusive = int(np.searchsorted(sorted_fees, fee, side="right"))
            pct = ((strict + inclusive) / 2 / n) * 100
            out[tid] = Decimal(str(pct)).quantize(Decimal("0.01"))
    return out


# ---------------------------------------------------------------------------
# Pass 2: peer-group expected exit ratio
# ---------------------------------------------------------------------------


def _populate_expected_exit_ratios(feature_rows: list[dict]) -> None:
    """Fill expected_exit_ratio + exit_ratio_vs_expected for completed transfers."""
    complete = [r for r in feature_rows if r["exit_fee_ratio"] is not None]
    if not complete:
        return

    df = pd.DataFrame(
        [
            {
                "transfer_id": r["transfer_id"],
                "position_group": r["position_group"],
                "age_at_transfer": float(r["age_at_transfer"]) if r["age_at_transfer"] is not None else np.nan,
                "age_at_departure": float(r["age_at_departure"]) if r["age_at_departure"] is not None else np.nan,
                "exit_fee_ratio": float(r["exit_fee_ratio"]),
            }
            for r in complete
        ]
    )

    for r in complete:
        peers = _find_peer_group(df, r)
        if peers.empty:
            continue
        expected = float(peers["exit_fee_ratio"].mean())
        actual = float(r["exit_fee_ratio"])
        expected_dec = _clip_decimal(
            Decimal(str(expected)), EXIT_RATIO_MAX,
            label=f"expected_exit_ratio for transfer {r['transfer_id']}",
        ).quantize(Decimal("0.0001"))
        vs_expected = _clip_decimal(
            Decimal(str(actual)) - Decimal(str(expected)), EXIT_RATIO_MAX,
            label=f"exit_ratio_vs_expected for transfer {r['transfer_id']}",
            allow_negative=True,
        ).quantize(Decimal("0.0001"))
        r["expected_exit_ratio"] = expected_dec
        r["exit_ratio_vs_expected"] = vs_expected


def _find_peer_group(df: pd.DataFrame, target: dict) -> pd.DataFrame:
    """Return peer transfers, widening age windows up to ±5y, then falling back to position-only."""
    pg = target["position_group"]
    age_t = float(target["age_at_transfer"]) if target["age_at_transfer"] is not None else None
    age_d = float(target["age_at_departure"]) if target["age_at_departure"] is not None else None
    self_id = target["transfer_id"]

    if pg is None or age_t is None or age_d is None:
        return df.iloc[0:0]

    base_mask = (
        (df["position_group"] == pg)
        & (df["transfer_id"] != self_id)
        & df["age_at_transfer"].notna()
        & df["age_at_departure"].notna()
    )

    for window in range(EXIT_RATIO_INITIAL_AGE_WINDOW, EXIT_RATIO_MAX_AGE_WINDOW + 1):
        peers = df[
            base_mask
            & ((df["age_at_transfer"] - age_t).abs() <= window)
            & ((df["age_at_departure"] - age_d).abs() <= window)
        ]
        if len(peers) >= EXIT_RATIO_MIN_GROUP_SIZE:
            return peers

    return df[base_mask]  # position-only fallback


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _upsert_feature_rows(session: Session, rows: list[dict]) -> int:
    """Bulk upsert with ON CONFLICT(transfer_id) DO UPDATE."""
    if not rows:
        return 0

    stmt = pg_insert(TransferFeature).values(rows)
    update_cols = {col: stmt.excluded[col] for col in rows[0] if col != "transfer_id"}
    stmt = stmt.on_conflict_do_update(
        index_elements=["transfer_id"],
        set_=update_cols,
    )
    session.execute(stmt)
    return len(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )
    session = SessionLocal()
    try:
        compute_features(session)
    finally:
        session.close()
