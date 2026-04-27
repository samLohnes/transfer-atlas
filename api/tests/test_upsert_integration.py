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
