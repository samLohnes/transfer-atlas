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


def test_transfer_null_date_does_not_duplicate_on_rerun():
    """Regression: Postgres treats NULLs as distinct under default unique-index
    semantics, so an ON CONFLICT path on a tuple containing a NULL key would
    insert duplicates instead of matching. Migration to NULLS NOT DISTINCT
    fixes this. Verifies via direct upsert_chunk usage against the live transfers
    table — round-trips two identical NULL-date rows and asserts only one
    survives.
    """
    import os

    if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("requires Postgres")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SASession

    from app.models import Club, Player, Transfer
    from pipeline.upsert import upsert_chunk

    # conftest stubs app.config to SQLite, so build an engine directly from
    # DATABASE_URL like the appearances integration test above does.
    engine = create_engine(os.environ["DATABASE_URL"])
    session = SASession(engine)
    try:
        # Pick any two existing club ids to reference (FK satisfied) and any one player.
        from_club = session.query(Club).first()
        to_club = (
            session.query(Club)
            .filter(Club.id != from_club.id)
            .first()
        )
        player = session.query(Player).first()
        assert from_club and to_club and player, "run `just pipeline` first"

        sentinel = {
            "player_id": player.id,
            "from_club_id": from_club.id,
            "to_club_id": to_club.id,
            "transfer_date": None,
            "fee_eur": None,
            "fee_is_loan": False,
            "transfer_window": "Summer 1900",  # unique sentinel window so we can clean up
            "season": "1900",
        }

        # Round 1: insert
        ins, upd = upsert_chunk(
            session, Transfer, [sentinel],
            conflict_columns=["player_id", "transfer_date", "from_club_id", "to_club_id"],
            update_columns=["fee_eur", "fee_is_loan", "transfer_window", "season"],
        )
        session.commit()
        assert (ins, upd) == (1, 0)

        # Round 2: same row again — must match the existing NULL-date row, not insert a dup.
        ins2, upd2 = upsert_chunk(
            session, Transfer, [sentinel],
            conflict_columns=["player_id", "transfer_date", "from_club_id", "to_club_id"],
            update_columns=["fee_eur", "fee_is_loan", "transfer_window", "season"],
        )
        session.commit()
        assert (ins2, upd2) == (0, 0), (
            f"NULL-date upsert produced (ins={ins2}, upd={upd2}); expected (0, 0). "
            "Migration to NULLS NOT DISTINCT may not have applied."
        )

        # Verify there's exactly one row matching the sentinel.
        count = (
            session.query(Transfer)
            .filter(
                Transfer.player_id == player.id,
                Transfer.from_club_id == from_club.id,
                Transfer.to_club_id == to_club.id,
                Transfer.transfer_date.is_(None),
                Transfer.transfer_window == "Summer 1900",
            )
            .count()
        )
        assert count == 1, f"expected exactly 1 sentinel row, found {count}"

    finally:
        # Clean up the sentinel row(s).
        session.query(Transfer).filter(
            Transfer.transfer_window == "Summer 1900"
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
        engine.dispose()
