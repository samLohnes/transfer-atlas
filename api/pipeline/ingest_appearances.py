"""Ingestion for the Transfermarkt appearances CSV — per-match player stats.

Largest single CSV in the pipeline (~1.8M rows). Uses polars for vectorized
CSV parse + ID resolution + type casting; pipeline.upsert_chunk for ON CONFLICT
upserts.
"""

import logging
from pathlib import Path

import polars as pl
from sqlalchemy.orm import Session

from app.models import Appearance, Club, Player
from pipeline.ingest import _validate_schema
from pipeline.upsert import upsert_chunk

logger = logging.getLogger(__name__)

CHUNK_SIZE = 10_000
PROGRESS_EVERY_N_CHUNKS = 10

APPEARANCE_UPDATE_COLS = [
    "club_id", "competition_id", "date", "minutes_played",
    "goals", "assists", "yellow_cards", "red_cards",
]


def _build_lookup(session: Session, model, prefix: str) -> pl.DataFrame:
    """Build a polars lookup DataFrame mapping transfermarkt_id (string) -> internal id.

    Returns a 2-column DataFrame with columns named `<prefix>_tm` and `<prefix>_id`.
    Rows with null transfermarkt_id are excluded.
    """
    rows = [
        (str(tm_id), pid)
        for tm_id, pid in session.query(model.transfermarkt_id, model.id).all()
        if tm_id is not None
    ]
    if not rows:
        return pl.DataFrame(
            schema={f"{prefix}_tm": pl.String, f"{prefix}_id": pl.Int64},
        )
    return pl.DataFrame(
        rows,
        schema={f"{prefix}_tm": pl.String, f"{prefix}_id": pl.Int64},
        orient="row",
    )


def ingest_appearances(session: Session, data_dir: Path) -> int:
    """Upsert all appearance rows from appearances.csv via vectorized polars.

    Returns total rows successfully ingested (inserts + updates).
    """
    _validate_schema(data_dir / "appearances.csv")

    player_lookup = _build_lookup(session, Player, "player")
    club_lookup = _build_lookup(session, Club, "club")

    df = pl.read_csv(
        data_dir / "appearances.csv",
        schema_overrides={
            "player_id": pl.String,
            "player_club_id": pl.String,
            "game_id": pl.String,
            "competition_id": pl.String,
            "date": pl.String,
            "minutes_played": pl.String,
            "goals": pl.String,
            "assists": pl.String,
            "yellow_cards": pl.String,
            "red_cards": pl.String,
        },
    )
    total_seen = df.height

    # Drop empty/null player_id rows.
    before = df.height
    df = df.filter(
        pl.col("player_id").is_not_null() & (pl.col("player_id") != "")
    )
    skipped_missing_player_empty = before - df.height

    # Drop empty/null player_club_id rows.
    before = df.height
    df = df.filter(
        pl.col("player_club_id").is_not_null() & (pl.col("player_club_id") != "")
    )
    skipped_missing_club_empty = before - df.height

    # Count rows where player_id doesn't resolve in lookup, then inner-join.
    skipped_missing_player_lookup = df.join(
        player_lookup, left_on="player_id", right_on="player_tm", how="anti"
    ).height
    df = df.join(
        player_lookup, left_on="player_id", right_on="player_tm", how="inner"
    )

    # Count rows where player_club_id doesn't resolve in lookup, then inner-join.
    skipped_missing_club_lookup = df.join(
        club_lookup, left_on="player_club_id", right_on="club_tm", how="anti"
    ).height
    df = df.join(
        club_lookup, left_on="player_club_id", right_on="club_tm", how="inner"
    )

    skipped_missing_player = skipped_missing_player_empty + skipped_missing_player_lookup
    skipped_missing_club = skipped_missing_club_empty + skipped_missing_club_lookup

    # Drop empty game_id.
    before = df.height
    df = df.filter(pl.col("game_id").is_not_null() & (pl.col("game_id") != ""))
    skipped_no_game_id = before - df.height

    # Parse date — null on failure, then drop bad dates.
    df = df.with_columns(
        pl.col("date").str.to_date(format="%Y-%m-%d", strict=False).alias("date_parsed")
    )
    before = df.height
    df = df.filter(pl.col("date_parsed").is_not_null())
    skipped_bad_date = before - df.height

    # Cast stat columns: coerce to int, fallback 0 for nulls/unparseable.
    df = df.with_columns([
        pl.col("minutes_played").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("goals").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("assists").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("yellow_cards").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("red_cards").cast(pl.Int64, strict=False).fill_null(0),
    ])

    # Resolve the integer ID columns produced by the joins. After joining with
    # player_lookup (which has `player_id` column), polars keeps the left CSV
    # `player_id` string column and renames the right's `player_id` to
    # `player_id_right`. Same pattern for `club_id`. Fall back gracefully if
    # polars resolves differently.
    schema = df.schema
    if schema.get("player_id_right") == pl.Int64:
        pid_col = "player_id_right"
    elif schema.get("player_id") == pl.Int64:
        pid_col = "player_id"
    else:
        pid_col = "player_id"

    if schema.get("club_id_right") == pl.Int64:
        cid_col = "club_id_right"
    elif schema.get("club_id") == pl.Int64:
        cid_col = "club_id"
    else:
        cid_col = "club_id"

    df_final = df.select([
        pl.col(pid_col).cast(pl.Int64).alias("player_id"),
        pl.col("game_id"),
        pl.col(cid_col).cast(pl.Int64).alias("club_id"),
        pl.col("competition_id"),
        pl.col("date_parsed").alias("date"),
        pl.col("minutes_played"),
        pl.col("goals"),
        pl.col("assists"),
        pl.col("yellow_cards"),
        pl.col("red_cards"),
    ])

    inserted_total = 0
    updated_total = 0

    if df_final.height > 0:
        chunk_idx = 0
        for slice_df in df_final.iter_slices(n_rows=CHUNK_SIZE):
            chunk_idx += 1
            rows = slice_df.to_dicts()
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
                    "  ... chunk %d: %d inserted, %d updated so far",
                    chunk_idx, inserted_total, updated_total,
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
