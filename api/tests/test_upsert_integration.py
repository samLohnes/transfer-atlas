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
