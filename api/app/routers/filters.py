"""Filter-related endpoints — available transfer windows."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transfer
from app.schemas.club import WindowItem, WindowsResponse
from app.services.windows import window_sort_key

router = APIRouter(prefix="/api/v1", tags=["filters"])


@router.get("/filters/windows", response_model=WindowsResponse)
def list_windows(db: Session = Depends(get_db)) -> WindowsResponse:
    """Return all available transfer windows sorted chronologically."""
    rows = db.query(Transfer.transfer_window).distinct().all()
    windows = sorted([r[0] for r in rows], key=window_sort_key)
    return WindowsResponse(
        windows=[WindowItem(label=w, value=w) for w in windows]
    )
