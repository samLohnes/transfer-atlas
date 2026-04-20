"""FeeTierThreshold model — fee-percentile boundaries per position group for production scoring."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FeeTierThreshold(Base):
    """One row per (scoring_version, position_group, tier). Rewritten each ml.run."""

    __tablename__ = "fee_tier_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "scoring_version_id",
            "position_group",
            "tier",
            name="uq_fee_tier_thresholds_version_position_tier",
        ),
        Index(
            "ix_fee_tier_thresholds_version_position",
            "scoring_version_id",
            "position_group",
        ),
        CheckConstraint(
            "tier BETWEEN 1 AND 5",
            name="ck_fee_tier_thresholds_tier_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scoring_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scoring_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    position_group: Mapped[str] = mapped_column(String(3), nullable=False)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    lower_fee_eur: Mapped[int] = mapped_column(BigInteger, nullable=False)
    upper_fee_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    label: Mapped[str] = mapped_column(String(20), nullable=False)

    scoring_version: Mapped["ScoringVersion"] = relationship()


from app.models.scoring_versions import ScoringVersion  # noqa: E402
