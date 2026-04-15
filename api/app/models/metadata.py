"""PipelineMetadata model — tracks data freshness."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PipelineMetadata(Base):
    """Single-row table tracking the last successful pipeline run."""

    __tablename__ = "pipeline_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_ingestion_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False)
    source_commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
