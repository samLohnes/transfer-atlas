"""add player sub_position

Revision ID: 68548aabccf4
Revises: c03383132b81
"""
from alembic import op
import sqlalchemy as sa


revision = "68548aabccf4"
down_revision = "c03383132b81"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("sub_position", sa.String(length=30), nullable=True),
    )
    op.create_index("ix_players_sub_position", "players", ["sub_position"])


def downgrade() -> None:
    op.drop_index("ix_players_sub_position", table_name="players")
    op.drop_column("players", "sub_position")
