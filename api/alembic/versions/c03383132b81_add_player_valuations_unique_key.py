"""add player_valuations unique key

Revision ID: c03383132b81
Revises: 9bb26f3fe65b
"""
from alembic import op


revision = "c03383132b81"
down_revision = "9bb26f3fe65b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop any duplicate (player_id, valuation_date) rows before adding the
    # constraint — keep the row with the highest id (most recently ingested).
    op.execute("""
        DELETE FROM player_valuations a
         USING player_valuations b
         WHERE a.player_id = b.player_id
           AND a.valuation_date = b.valuation_date
           AND a.id < b.id
    """)
    op.create_unique_constraint(
        "uq_player_valuations_player_date",
        "player_valuations",
        ["player_id", "valuation_date"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_player_valuations_player_date",
        "player_valuations",
        type_="unique",
    )
