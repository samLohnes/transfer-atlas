"""transfers natural key NULLS NOT DISTINCT

Revision ID: d92500feb23e
Revises: fa2ca76b5300

Drop and recreate the (player_id, transfer_date, from_club_id, to_club_id)
unique index with NULLS NOT DISTINCT so the ON CONFLICT path correctly matches
existing rows where transfer_date IS NULL. Without this, re-runs of the
pipeline would silently insert duplicate rows for transfers with no parsed
date (a real path — see derive_transfer_window's season-fallback case).

Postgres 15+ required.
"""
from alembic import op


revision = "d92500feb23e"
down_revision = "fa2ca76b5300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dedupe any NULL-date duplicate rows that may have been inserted by re-runs
    # of the pipeline against the old default-NULLS-DISTINCT index. Keep the row
    # with the highest id (the most recently ingested), drop older copies.
    op.execute("""
        DELETE FROM transfers a
         USING transfers b
         WHERE a.player_id = b.player_id
           AND a.from_club_id = b.from_club_id
           AND a.to_club_id = b.to_club_id
           AND a.transfer_date IS NULL AND b.transfer_date IS NULL
           AND a.id < b.id
    """)

    op.execute("DROP INDEX uq_transfers_natural_key")
    op.execute(
        "CREATE UNIQUE INDEX uq_transfers_natural_key "
        "ON transfers (player_id, transfer_date, from_club_id, to_club_id) "
        "NULLS NOT DISTINCT"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_transfers_natural_key")
    op.execute(
        "CREATE UNIQUE INDEX uq_transfers_natural_key "
        "ON transfers (player_id, transfer_date, from_club_id, to_club_id)"
    )
