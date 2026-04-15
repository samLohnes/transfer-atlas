"""Pipeline metadata endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PipelineMetadata
from app.schemas.metadata import MetadataResponse

router = APIRouter(prefix="/api/v1", tags=["metadata"])


@router.get("/metadata", response_model=MetadataResponse)
def get_metadata(db: Session = Depends(get_db)) -> MetadataResponse:
    """Return pipeline metadata for the data freshness indicator."""
    meta = db.query(PipelineMetadata).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Pipeline has never run")
    return MetadataResponse(
        last_ingestion_at=meta.last_ingestion_at,
        records_processed=meta.records_processed,
        source_commit_hash=meta.source_commit_hash,
    )
