"""Grade endpoints — single-transfer detail, rankings, club comparison, scoring info."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transfer
from app.schemas.grade import (
    ClubComparisonResponse, GradeDetail, ScoringInfoResponse, TopGradesResponse,
)
from app.services.grade_service import (
    get_club_comparison, get_scoring_info, get_top_grades, get_transfer_grade_detail,
)

router = APIRouter(prefix="/api/v1", tags=["grades"])

# Categorical filter values accepted by /grades/top
CATEGORIES = ("best", "worst")
POSITION_GROUPS = ("GK", "DEF", "MID", "FWD")
MAX_TOP_LIMIT = 25
MAX_CLUB_COMPARISON_IDS = 3


@router.get("/transfers/{transfer_id}/grade", response_model=GradeDetail)
def transfer_grade(transfer_id: int, db: Session = Depends(get_db)):
    """Full grade with per-component breakdown. 404 if no transfer; 204 if not gradeable."""
    detail = get_transfer_grade_detail(db, transfer_id)
    if detail is not None:
        return detail
    # No grade row — disambiguate between "transfer doesn't exist" and "not gradeable"
    exists = db.query(Transfer.id).filter(Transfer.id == transfer_id).first() is not None
    if not exists:
        raise HTTPException(status_code=404, detail="Transfer not found")
    # Transfer exists but isn't gradeable (free transfer, loan, or unscored)
    return Response(status_code=204)


@router.get("/grades/top", response_model=TopGradesResponse)
def top_grades(
    category: str = Query("best", description="best or worst"),
    limit: int = Query(10, ge=1, le=MAX_TOP_LIMIT),
    offset: int = Query(0, ge=0),
    position_group: str | None = Query(None, description="GK, DEF, MID, or FWD"),
    country_id: int | None = Query(None),
    fee_min: int | None = Query(None, ge=0, description="EUR cents"),
    fee_max: int | None = Query(None, ge=0, description="EUR cents"),
    window_start: str | None = Query(None, description='e.g. "Summer 2020"'),
    window_end: str | None = Query(None),
    completed_only: bool = Query(True),
    db: Session = Depends(get_db),
) -> TopGradesResponse:
    """Best- or worst-graded transfers with optional filters."""
    if category not in CATEGORIES:
        raise HTTPException(
            status_code=400, detail=f"category must be one of {CATEGORIES}",
        )
    if position_group is not None and position_group not in POSITION_GROUPS:
        raise HTTPException(
            status_code=400, detail=f"position_group must be one of {POSITION_GROUPS}",
        )

    transfers, total = get_top_grades(
        db,
        category=category,
        limit=limit,
        offset=offset,
        position_group=position_group,
        country_id=country_id,
        fee_min=fee_min,
        fee_max=fee_max,
        window_start=window_start,
        window_end=window_end,
        completed_only=completed_only,
    )
    return TopGradesResponse(category=category, total=total, transfers=transfers)


@router.get("/grades/club-comparison", response_model=ClubComparisonResponse)
def club_comparison(
    # Optional at the FastAPI layer so we can return 400 (not 422) for the
    # missing case, matching the rest of this endpoint's validation errors.
    club_ids: str | None = Query(None, description="Comma-separated club IDs, max 3"),
    window_start: str | None = Query(None),
    window_end: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ClubComparisonResponse:
    """Side-by-side report cards for up to 3 clubs."""
    if not club_ids:
        raise HTTPException(status_code=400, detail="club_ids is required")
    parts = [p.strip() for p in club_ids.split(",") if p.strip()]
    if not parts:
        raise HTTPException(status_code=400, detail="club_ids is required")
    if len(parts) > MAX_CLUB_COMPARISON_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"club_ids accepts at most {MAX_CLUB_COMPARISON_IDS} ids",
        )
    try:
        ids = [int(p) for p in parts]
    except ValueError:
        raise HTTPException(status_code=400, detail="club_ids must be integers")

    cards = get_club_comparison(db, ids, window_start=window_start, window_end=window_end)
    return ClubComparisonResponse(clubs=cards)


@router.get("/grades/scoring-info", response_model=ScoringInfoResponse)
def scoring_info(db: Session = Depends(get_db)) -> ScoringInfoResponse:
    """Active scoring version snapshot + grade distribution. Developer diagnostic."""
    info = get_scoring_info(db)
    if info is None:
        raise HTTPException(
            status_code=404,
            detail="No active scoring version — run the grading pipeline first.",
        )
    return ScoringInfoResponse(**info)
