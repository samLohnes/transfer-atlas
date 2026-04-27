"""Live-Postgres integration tests for pipeline.upsert.

These run against the dev database (configured by DATABASE_URL or via the
just test-pipeline recipe) because INSERT ... ON CONFLICT is not exercised
the same way under SQLite. Skipped automatically if DATABASE_URL points at
sqlite or is unset.
"""

import os

import pytest
from sqlalchemy import (
    BigInteger, Column, Integer, MetaData, String, Table, UniqueConstraint,
    create_engine, select,
)
from sqlalchemy.orm import Session

DB_URL = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DB_URL.startswith("postgresql"),
    reason="upsert helper requires PostgreSQL; set DATABASE_URL to run.",
)


@pytest.fixture()
def pg_session():
    engine = create_engine(DB_URL)
    metadata = MetaData()
    test_tbl = Table(
        "_upsert_test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("nat_a", Integer, nullable=False),
        Column("nat_b", String(20), nullable=False),
        Column("payload_int", Integer, nullable=False),
        Column("payload_big", BigInteger, nullable=True),
        UniqueConstraint("nat_a", "nat_b", name="_upsert_test_natkey"),
    )
    metadata.drop_all(engine, [test_tbl])
    metadata.create_all(engine, [test_tbl])
    session = Session(engine)
    try:
        yield session, test_tbl
    finally:
        session.close()
        metadata.drop_all(engine, [test_tbl])
        engine.dispose()


def test_first_insert_returns_all_inserted(pg_session):
    from pipeline.upsert import upsert_chunk
    session, tbl = pg_session
    rows = [
        {"nat_a": 1, "nat_b": "x", "payload_int": 10, "payload_big": 100},
        {"nat_a": 1, "nat_b": "y", "payload_int": 20, "payload_big": 200},
    ]
    inserted, updated = upsert_chunk(
        session, tbl, rows,
        conflict_columns=["nat_a", "nat_b"],
        update_columns=["payload_int", "payload_big"],
    )
    session.commit()
    assert (inserted, updated) == (2, 0)
    assert session.scalar(select(tbl).where(tbl.c.nat_a == 1)) is not None


def test_unchanged_rows_count_as_updates_zero(pg_session):
    """Re-running with identical payload writes nothing — change detection works."""
    from pipeline.upsert import upsert_chunk
    session, tbl = pg_session
    rows = [{"nat_a": 1, "nat_b": "x", "payload_int": 10, "payload_big": 100}]
    upsert_chunk(session, tbl, rows,
                 conflict_columns=["nat_a", "nat_b"],
                 update_columns=["payload_int", "payload_big"])
    session.commit()
    inserted, updated = upsert_chunk(
        session, tbl, rows,
        conflict_columns=["nat_a", "nat_b"],
        update_columns=["payload_int", "payload_big"],
    )
    session.commit()
    assert (inserted, updated) == (0, 0)


def test_changed_payload_counts_as_update(pg_session):
    """A real change writes through and is reported as an update."""
    from pipeline.upsert import upsert_chunk
    session, tbl = pg_session
    upsert_chunk(session, tbl, [{"nat_a": 1, "nat_b": "x", "payload_int": 10, "payload_big": 100}],
                 conflict_columns=["nat_a", "nat_b"],
                 update_columns=["payload_int", "payload_big"])
    session.commit()
    inserted, updated = upsert_chunk(
        session, tbl, [{"nat_a": 1, "nat_b": "x", "payload_int": 11, "payload_big": 100}],
        conflict_columns=["nat_a", "nat_b"],
        update_columns=["payload_int", "payload_big"],
    )
    session.commit()
    assert (inserted, updated) == (0, 1)


def test_change_in_any_column_triggers_update(pg_session):
    """The partial-change-detection bug fix — payload_big alone changing must write."""
    from pipeline.upsert import upsert_chunk
    session, tbl = pg_session
    upsert_chunk(session, tbl, [{"nat_a": 1, "nat_b": "x", "payload_int": 10, "payload_big": 100}],
                 conflict_columns=["nat_a", "nat_b"],
                 update_columns=["payload_int", "payload_big"])
    session.commit()
    inserted, updated = upsert_chunk(
        session, tbl, [{"nat_a": 1, "nat_b": "x", "payload_int": 10, "payload_big": 999}],
        conflict_columns=["nat_a", "nat_b"],
        update_columns=["payload_int", "payload_big"],
    )
    session.commit()
    assert (inserted, updated) == (0, 1)
    from sqlalchemy import select
    row = session.execute(select(tbl).where(tbl.c.nat_a == 1)).one()
    assert row.payload_big == 999


def test_intra_chunk_duplicate_keys_collapse_cleanly(pg_session):
    """Two rows with the same natural key in one chunk must not raise; last wins."""
    from pipeline.upsert import upsert_chunk
    session, tbl = pg_session
    rows = [
        {"nat_a": 1, "nat_b": "x", "payload_int": 10, "payload_big": 100},
        {"nat_a": 1, "nat_b": "x", "payload_int": 20, "payload_big": 200},  # dup
    ]
    # Postgres CardinalityViolation: ON CONFLICT cannot affect row a second time.
    # The helper must dedupe pre-flight, so we expect a clean single insert.
    inserted, updated = upsert_chunk(
        session, tbl, rows,
        conflict_columns=["nat_a", "nat_b"],
        update_columns=["payload_int", "payload_big"],
    )
    session.commit()
    assert (inserted, updated) == (1, 0)
    from sqlalchemy import select
    row = session.execute(select(tbl).where(tbl.c.nat_a == 1)).one()
    # Last-wins semantics: payload_int should be 20
    assert row.payload_int == 20


def test_appearance_club_id_change_alone_writes_through():
    """Regression: TODO.md flagged that change detection skipped club_id changes.

    Verifies via the live ingest path: write an appearance, then re-run the same
    chunk with only club_id changed, and confirm the row was updated.
    """
    import os, csv, tempfile
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("requires Postgres")

    # This test runs against the live dev DB and assumes `just pipeline` has been
    # run at least once so player + club rows exist. We pick the first appearance
    # row in the DB, mutate just its club_id, and re-ingest a fixture CSV.
    # Implemented inline to avoid a heavyweight fixture; intentionally minimal.
    from app.models import Appearance, Player, Club
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as s:
        existing = s.query(Appearance).first()
        assert existing is not None, "run `just pipeline` first"
        player = s.get(Player, existing.player_id)
        # Find a different club to swap to
        other_club = s.query(Club).filter(Club.id != existing.club_id).first()
        assert other_club is not None
        original_club_id = existing.club_id
        target_club_id = other_club.id
        original_tm_player = player.transfermarkt_id
        original_tm_club = (s.query(Club).get(original_club_id)).transfermarkt_id
        target_tm_club = other_club.transfermarkt_id
        original_game_id = existing.game_id
        original_date = existing.date

    # Build a single-row CSV with a different player_club_id but identical stats.
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with open(td_path / "appearances.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "appearance_id", "player_id", "game_id", "player_club_id",
                "competition_id", "date", "minutes_played", "goals", "assists",
                "yellow_cards", "red_cards",
            ])
            w.writeheader()
            w.writerow({
                "appearance_id": "ignored",
                "player_id": original_tm_player,
                "game_id": original_game_id,
                "player_club_id": target_tm_club,
                "competition_id": "GB1",
                "date": original_date.isoformat(),
                "minutes_played": existing.minutes_played,
                "goals": existing.goals, "assists": existing.assists,
                "yellow_cards": existing.yellow_cards, "red_cards": existing.red_cards,
            })

        from pipeline.ingest_appearances import ingest_appearances
        with Session(engine) as s:
            ingest_appearances(s, td_path)
            s.commit()

        with Session(engine) as s:
            row = s.query(Appearance).filter_by(
                player_id=existing.player_id, game_id=original_game_id,
            ).one()
            assert row.club_id == target_club_id, "club_id change must persist"

        # Restore original to keep DB clean for re-runs
        with Session(engine) as s:
            row = s.query(Appearance).filter_by(
                player_id=existing.player_id, game_id=original_game_id,
            ).one()
            row.club_id = original_club_id
            s.commit()
