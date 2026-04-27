"""Postgres ON CONFLICT-based upsert helper.

Replaces the pre-load-dict + sentinel pattern in ingest.py / ingest_appearances.py.
Single round-trip per chunk; xmax in the RETURNING clause distinguishes inserts
(xmax = 0) from updates (xmax > 0).
"""

from typing import Any

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


def upsert_chunk(
    session: Session,
    table: Any,                          # SQLAlchemy Table or mapped class
    rows: list[dict],
    conflict_columns: list[str],
    update_columns: list[str],
    only_if_changed: bool = True,
) -> tuple[int, int]:
    """Upsert `rows` into `table` using INSERT … ON CONFLICT DO UPDATE.

    Returns (inserted_count, updated_count). When only_if_changed=True, rows
    whose update_columns all match existing values are no-ops (returned
    rowcount excludes them).
    """
    if not rows:
        return (0, 0)

    # Collapse intra-chunk duplicates on the conflict key — last occurrence wins.
    # Postgres raises CardinalityViolation if the same conflict target appears
    # twice in one statement.
    seen: dict[tuple, dict] = {}
    for r in rows:
        key = tuple(r[col] for col in conflict_columns)
        seen[key] = r
    rows = list(seen.values())

    target = table.__table__ if hasattr(table, "__table__") else table
    stmt = pg_insert(target).values(rows)
    excluded = stmt.excluded

    set_map = {col: excluded[col] for col in update_columns}

    if only_if_changed:
        change_clauses = [
            text(f'{target.name}.{col} IS DISTINCT FROM EXCLUDED.{col}')
            for col in update_columns
        ]
        where_changed = or_(*change_clauses)
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=set_map,
            where=where_changed,
        )
    else:
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=set_map,
        )

    stmt = stmt.returning(text("xmax = 0 AS inserted"))
    result = session.execute(stmt)
    flags = [bool(row[0]) for row in result]

    inserted = sum(1 for f in flags if f)
    updated = len(flags) - inserted
    return (inserted, updated)
