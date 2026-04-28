"""Ingestion for the Transfermarkt appearances CSV — per-match player stats.

Largest single CSV in the pipeline (~1.8M rows). Uses pipeline.upsert_chunk
for ON CONFLICT-based upserts; no client-side pre-load dict.
"""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Appearance, Club, Player
from pipeline.ingest import (
    CHUNK_SIZE,
    _coerce_int_default,
    _parse_date,
    _safe_int_str,
    _safe_str,
    _validate_schema,
)
from pipeline.upsert import upsert_chunk

logger = logging.getLogger(__name__)

PROGRESS_EVERY_N_CHUNKS = 10

APPEARANCE_UPDATE_COLS = [
    "club_id", "competition_id", "date", "minutes_played",
    "goals", "assists", "yellow_cards", "red_cards",
]


def ingest_appearances(session: Session, data_dir: Path) -> int:
    """Upsert all appearance rows from appearances.csv via ON CONFLICT.

    Returns total rows successfully ingested (inserts + updates + unchanged).
    """
    _validate_schema(data_dir / "appearances.csv")

    player_tm_map: dict[str, int] = {
        str(p.transfermarkt_id): p.id
        for p in session.query(Player.transfermarkt_id, Player.id).all()
        if p.transfermarkt_id
    }
    club_tm_map: dict[str, int] = {
        str(c.transfermarkt_id): c.id
        for c in session.query(Club.transfermarkt_id, Club.id).all()
        if c.transfermarkt_id
    }

    inserted_total = 0
    updated_total = 0
    skipped_missing_player = 0
    skipped_missing_club = 0
    skipped_no_game_id = 0
    skipped_bad_date = 0
    chunk_idx = 0
    total_seen = 0

    for chunk in pd.read_csv(
        data_dir / "appearances.csv", low_memory=False, chunksize=CHUNK_SIZE
    ):
        chunk_idx += 1
        if chunk_idx == 1:
            logger.info("Processing appearance records (chunked, ON CONFLICT)...")

        rows: list[dict] = []
        for row in chunk.itertuples(index=False):
            total_seen += 1

            player_tm = _safe_int_str(getattr(row, "player_id", None))
            if not player_tm or player_tm not in player_tm_map:
                skipped_missing_player += 1
                continue
            player_id = player_tm_map[player_tm]

            club_tm = _safe_int_str(getattr(row, "player_club_id", None))
            if not club_tm or club_tm not in club_tm_map:
                skipped_missing_club += 1
                continue
            club_id = club_tm_map[club_tm]

            game_id = _safe_str(getattr(row, "game_id", None))
            if not game_id:
                skipped_no_game_id += 1
                continue

            game_date = _parse_date(getattr(row, "date", None))
            if game_date is None:
                skipped_bad_date += 1
                continue

            rows.append({
                "player_id": player_id,
                "game_id": game_id,
                "club_id": club_id,
                "competition_id": _safe_str(getattr(row, "competition_id", None)),
                "date": game_date,
                "minutes_played": _coerce_int_default(getattr(row, "minutes_played", None)),
                "goals": _coerce_int_default(getattr(row, "goals", None)),
                "assists": _coerce_int_default(getattr(row, "assists", None)),
                "yellow_cards": _coerce_int_default(getattr(row, "yellow_cards", None)),
                "red_cards": _coerce_int_default(getattr(row, "red_cards", None)),
            })

        if rows:
            ins, upd = upsert_chunk(
                session, Appearance, rows,
                conflict_columns=["player_id", "game_id"],
                update_columns=APPEARANCE_UPDATE_COLS,
            )
            inserted_total += ins
            updated_total += upd
            session.flush()

        if chunk_idx % PROGRESS_EVERY_N_CHUNKS == 0:
            logger.info(
                "  ... chunk %d: %d seen, %d inserted, %d updated, %d skipped-player, "
                "%d skipped-club, %d bad-date, %d no-game-id",
                chunk_idx, total_seen, inserted_total, updated_total,
                skipped_missing_player, skipped_missing_club,
                skipped_bad_date, skipped_no_game_id,
            )

    session.commit()
    logger.info(
        "Appearances ingested: %d inserted, %d updated. Skipped: %d missing-player, "
        "%d missing-club, %d bad-date, %d no-game-id. Seen: %d.",
        inserted_total, updated_total,
        skipped_missing_player, skipped_missing_club,
        skipped_bad_date, skipped_no_game_id, total_seen,
    )
    return inserted_total + updated_total
