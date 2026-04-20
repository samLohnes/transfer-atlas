"""phase 2 grading schema

Revision ID: 9bb26f3fe65b
Revises: aa9be6b2875f
Create Date: 2026-04-19 00:00:00.000000

Adds the data model for the transfer grading system:
- Seven new columns on the existing players table.
- New tables: scoring_versions, fee_tier_thresholds, appearances, transfer_grades, transfer_features.
- FK ordering: scoring_versions is created before anything that references it
  (fee_tier_thresholds, transfer_grades); downgrade reverses.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9bb26f3fe65b"
down_revision: Union[str, None] = "aa9be6b2875f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---- 1. Extend players table with phase 2 columns ----
    op.add_column("players", sa.Column("height_in_cm", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("foot", sa.String(length=10), nullable=True))
    op.add_column(
        "players",
        sa.Column("international_caps", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "players",
        sa.Column("international_goals", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column("players", sa.Column("current_market_value_eur", sa.BigInteger(), nullable=True))
    op.add_column("players", sa.Column("peak_market_value_eur", sa.BigInteger(), nullable=True))
    op.add_column("players", sa.Column("contract_expiration_date", sa.Date(), nullable=True))

    # Drop the server defaults after backfilling existing rows — application code sets these.
    op.alter_column("players", "international_caps", server_default=None)
    op.alter_column("players", "international_goals", server_default=None)

    # ---- 2. scoring_versions (must exist before anything that references it) ----
    op.create_table(
        "scoring_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_scored", sa.Integer(), nullable=False),
        sa.Column("formula_config", sa.JSON(), nullable=False),
        sa.Column("component_weights", sa.JSON(), nullable=False),
        sa.Column("calibrated_rates", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_scoring_versions_version"),
    )
    # Enforce "at most one active scoring version" at the DB level via a partial unique index.
    op.create_index(
        "uq_scoring_versions_is_active",
        "scoring_versions",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    # ---- 3. fee_tier_thresholds (FK → scoring_versions CASCADE) ----
    op.create_table(
        "fee_tier_thresholds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scoring_version_id", sa.Integer(), nullable=False),
        sa.Column("position_group", sa.String(length=3), nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.Column("lower_fee_eur", sa.BigInteger(), nullable=False),
        sa.Column("upper_fee_eur", sa.BigInteger(), nullable=True),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["scoring_version_id"], ["scoring_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scoring_version_id",
            "position_group",
            "tier",
            name="uq_fee_tier_thresholds_version_position_tier",
        ),
        sa.CheckConstraint(
            "tier BETWEEN 1 AND 5",
            name="ck_fee_tier_thresholds_tier_range",
        ),
    )
    op.create_index(
        "ix_fee_tier_thresholds_version_position",
        "fee_tier_thresholds",
        ["scoring_version_id", "position_group"],
        unique=False,
    )

    # ---- 4. appearances (FK → players CASCADE, clubs RESTRICT) ----
    op.create_table(
        "appearances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(length=50), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.String(length=50), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("minutes_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("yellow_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("red_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "game_id", name="uq_appearances_player_game"),
    )
    op.create_index(
        "ix_appearances_player_date",
        "appearances",
        ["player_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_appearances_club_date",
        "appearances",
        ["club_id", "date"],
        unique=False,
    )

    # ---- 5. transfer_grades (FK → transfers CASCADE, scoring_versions RESTRICT) ----
    op.create_table(
        "transfer_grades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("composite_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("letter_grade", sa.String(length=2), nullable=False),
        sa.Column("worth_the_fee", sa.Boolean(), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("minutes_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("minutes_explanation", sa.String(length=500), nullable=True),
        sa.Column("production_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("production_explanation", sa.String(length=500), nullable=True),
        sa.Column("value_trajectory_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("value_trajectory_explanation", sa.String(length=500), nullable=True),
        sa.Column("financial_return_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("financial_return_explanation", sa.String(length=500), nullable=True),
        sa.Column("scoring_version_id", sa.Integer(), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transfer_id"], ["transfers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scoring_version_id"], ["scoring_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transfer_id", name="uq_transfer_grades_transfer_id"),
        sa.CheckConstraint(
            "composite_score >= 0 AND composite_score <= 100",
            name="ck_transfer_grades_composite_score_range",
        ),
    )
    op.create_index(
        "ix_transfer_grades_composite_score",
        "transfer_grades",
        ["composite_score"],
        unique=False,
    )
    op.create_index(
        "ix_transfer_grades_is_complete_composite",
        "transfer_grades",
        ["is_complete", "composite_score"],
        unique=False,
    )
    op.create_index(
        "ix_transfer_grades_scoring_version_id",
        "transfer_grades",
        ["scoring_version_id"],
        unique=False,
    )

    # ---- 6. transfer_features (FK → transfers CASCADE) ----
    op.create_table(
        "transfer_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("tenure_days", sa.Integer(), nullable=True),
        sa.Column("total_appearances", sa.Integer(), nullable=True),
        sa.Column("total_minutes", sa.Integer(), nullable=True),
        sa.Column("minutes_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("goals_per_90", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("assists_per_90", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("goal_contributions_per_90", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("position_group", sa.String(length=3), nullable=True),
        sa.Column("fee_percentile", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("entry_fee_eur", sa.BigInteger(), nullable=True),
        sa.Column("exit_fee_eur", sa.BigInteger(), nullable=True),
        sa.Column("age_at_transfer", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("age_at_departure", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("value_at_transfer", sa.BigInteger(), nullable=True),
        sa.Column("peak_value_during_stint", sa.BigInteger(), nullable=True),
        sa.Column("value_at_departure", sa.BigInteger(), nullable=True),
        sa.Column("value_change_pct", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("exit_fee_ratio", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("expected_exit_ratio", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("exit_ratio_vs_expected", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("international_caps", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["transfer_id"], ["transfers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transfer_id", name="uq_transfer_features_transfer_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse order: drop tables that reference others first.
    op.drop_table("transfer_features")

    op.drop_index("ix_transfer_grades_scoring_version_id", table_name="transfer_grades")
    op.drop_index("ix_transfer_grades_is_complete_composite", table_name="transfer_grades")
    op.drop_index("ix_transfer_grades_composite_score", table_name="transfer_grades")
    op.drop_table("transfer_grades")

    op.drop_index("ix_appearances_club_date", table_name="appearances")
    op.drop_index("ix_appearances_player_date", table_name="appearances")
    op.drop_table("appearances")

    op.drop_index("ix_fee_tier_thresholds_version_position", table_name="fee_tier_thresholds")
    op.drop_table("fee_tier_thresholds")

    op.drop_index("uq_scoring_versions_is_active", table_name="scoring_versions")
    op.drop_table("scoring_versions")

    op.drop_column("players", "contract_expiration_date")
    op.drop_column("players", "peak_market_value_eur")
    op.drop_column("players", "current_market_value_eur")
    op.drop_column("players", "international_goals")
    op.drop_column("players", "international_caps")
    op.drop_column("players", "foot")
    op.drop_column("players", "height_in_cm")
