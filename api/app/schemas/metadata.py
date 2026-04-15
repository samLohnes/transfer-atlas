"""Pipeline metadata response schemas."""

from datetime import datetime

from pydantic import BaseModel


class MetadataResponse(BaseModel):
    """Pipeline metadata for the data freshness indicator."""

    last_ingestion_at: datetime
    records_processed: int
    source_commit_hash: str | None
