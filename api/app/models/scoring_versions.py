"""ScoringVersion model — snapshot of the scoring formula used for a grading run."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScoringVersion(Base):
    """One row per ml.run invocation. Records config, weights, calibrated rates, and activation state."""

    __tablename__ = "scoring_versions"
    __table_args__ = (
        # Only one scoring version may be active at a time — enforced via partial unique index.
        Index(
            "uq_scoring_versions_is_active",
            "is_active",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    total_scored: Mapped[int] = mapped_column(Integer, nullable=False)
    formula_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    component_weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    calibrated_rates: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
