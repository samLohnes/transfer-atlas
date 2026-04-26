"""Ingestion for the Transfermarkt appearances CSV — per-match player stats.

Kept in its own module because the appearances source (~1.8M records) is the
largest single CSV in the pipeline and its logic is self-contained. Shares the
chunked-upsert pattern and the `_safe_*` / schema-validation helpers used by
`ingest.py`.
"""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import insert
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

logger = logging.getLogger(__name__)

# At CHUNK_SIZE=10_000, logging every 10 chunks surfaces progress every 100K rows.
PROGRESS_EVERY_N_CHUNKS = 10


def ingest_appearances(session: Session, data_dir: Path) -> int:
    """Upsert all appearance rows from appearances.csv.

    Returns total number of rows successfully ingested (inserted + updated +
    unchanged). Rows whose player_id or player_club_id cannot be resolved
    against our DB (e.g. clubs outside tracked leagues) are skipped with a
    running count surfaced in the final log.
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

    # Pre-load existing appearances keyed by the (player_id, game_id) natural key
    # so the ingest is idempotent and we can skip UPDATE when nothing changed.
    existing: dict[tuple[int, str], tuple[int, int, int, int, int, int]] = {
        (r.player_id, r.game_id): (
            r.id, r.minutes_played, r.goals, r.assists, r.yellow_cards, r.red_cards,
        )
        for r in session.query(
            Appearance.id, Appearance.player_id, Appearance.game_id,
            Appearance.minutes_played, Appearance.goals, Appearance.assists,
            Appearance.yellow_cards, Appearance.red_cards,
        ).all()
    }
    logger.info("Loaded %d existing appearance keys for dedup.", len(existing))

    inserted = 0
    updated = 0
    unchanged = 0
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
            logger.info("Processing appearance records (chunked, batched)...")

        new_records: list[dict] = []
        update_records: list[tuple[int, dict]] = []

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

            competition_id = _safe_str(getattr(row, "competition_id", None))
            minutes_played = _coerce_int_default(getattr(row, "minutes_played", None))
            goals = _coerce_int_default(getattr(row, "goals", None))
            assists = _coerce_int_default(getattr(row, "assists", None))
            yellow_cards = _coerce_int_default(getattr(row, "yellow_cards", None))
            red_cards = _coerce_int_default(getattr(row, "red_cards", None))

            key = (player_id, game_id)
            if key in existing:
                aid, old_min, old_g, old_a, old_y, old_r = existing[key]
                if (old_min == minutes_played and old_g == goals
                        and old_a == assists and old_y == yellow_cards
                        and old_r == red_cards):
                    unchanged += 1
                    continue
                update_records.append((aid, {
                    "club_id": club_id,
                    "competition_id": competition_id,
                    "date": game_date,
                    "minutes_played": minutes_played,
                    "goals": goals,
                    "assists": assists,
                    "yellow_cards": yellow_cards,
                    "red_cards": red_cards,
                }))
                updated += 1
            else:
                new_records.append({
                    "player_id": player_id,
                    "game_id": game_id,
                    "club_id": club_id,
                    "competition_id": competition_id,
                    "date": game_date,
                    "minutes_played": minutes_played,
                    "goals": goals,
                    "assists": assists,
                    "yellow_cards": yellow_cards,
                    "red_cards": red_cards,
                })
                # Sentinel — prevents re-insert if the same key appears again in a later chunk
                existing[key] = (-1, minutes_played, goals, assists, yellow_cards, red_cards)
                inserted += 1

        if new_records:
            session.execute(insert(Appearance), new_records)

        for aid, fields in update_records:
            session.query(Appearance).filter(Appearance.id == aid).update(fields)

        if new_records or update_records:
            session.flush()

        if chunk_idx % PROGRESS_EVERY_N_CHUNKS == 0:
            logger.info(
                "  ... chunk %d: %d seen, %d inserted, %d updated, %d unchanged, "
                "%d missing-player, %d missing-club, %d bad-date, %d no-game-id",
                chunk_idx, total_seen, inserted, updated, unchanged,
                skipped_missing_player, skipped_missing_club,
                skipped_bad_date, skipped_no_game_id,
            )

    session.commit()
    processed = inserted + updated + unchanged
    logger.info(
        "Appearances ingested: %d rows (%d inserted, %d updated, %d unchanged). "
        "Skipped: %d missing-player, %d missing-club, %d bad-date, %d no-game-id. "
        "Seen: %d.",
        processed, inserted, updated, unchanged,
        skipped_missing_player, skipped_missing_club,
        skipped_bad_date, skipped_no_game_id, total_seen,
    )
    return processed
