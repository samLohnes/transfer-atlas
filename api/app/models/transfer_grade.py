"""TransferGrade model — composite grade + component scores for a transfer."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransferGrade(Base):
    """A percentile-based composite grade (0-100) with four component sub-scores and explanations."""

    __tablename__ = "transfer_grades"
    __table_args__ = (
        CheckConstraint(
            "composite_score >= 0 AND composite_score <= 100",
            name="ck_transfer_grades_composite_score_range",
        ),
        Index("ix_transfer_grades_composite_score", "composite_score"),
        Index(
            "ix_transfer_grades_is_complete_composite",
            "is_complete",
            "composite_score",
        ),
        Index("ix_transfer_grades_scoring_version_id", "scoring_version_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transfer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transfers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    composite_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    letter_grade: Mapped[str] = mapped_column(String(2), nullable=False)
    worth_the_fee: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    minutes_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    minutes_explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    production_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    production_explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    value_trajectory_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    value_trajectory_explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    financial_return_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    financial_return_explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scoring_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scoring_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    graded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    transfer: Mapped["Transfer"] = relationship()
    scoring_version: Mapped["ScoringVersion"] = relationship()


from app.models.transfer import Transfer  # noqa: E402
from app.models.scoring_versions import ScoringVersion  # noqa: E402
