"""add transfer_features position_subgroup

Revision ID: fa2ca76b5300
Revises: 68548aabccf4
"""
from alembic import op
import sqlalchemy as sa


revision = "fa2ca76b5300"
down_revision = "68548aabccf4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transfer_features",
        sa.Column("position_subgroup", sa.String(length=3), nullable=True),
    )
    op.create_index("ix_transfer_features_position_subgroup", "transfer_features", ["position_subgroup"])


def downgrade() -> None:
    op.drop_index("ix_transfer_features_position_subgroup", table_name="transfer_features")
    op.drop_column("transfer_features", "position_subgroup")
