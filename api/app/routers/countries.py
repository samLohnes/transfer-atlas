"""Country endpoints — list and detail."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Country
from app.schemas.country import CountriesResponse, CountryDetailResponse, CountryItem
from app.schemas.filters import TransferFilters
from app.services.country_service import get_country_detail

router = APIRouter(prefix="/api/v1", tags=["countries"])


@router.get("/countries", response_model=CountriesResponse)
def list_countries(db: Session = Depends(get_db)) -> CountriesResponse:
    """Return all in-scope countries with geographic coordinates."""
    countries = db.query(Country).filter(Country.in_scope == True).order_by(Country.name).all()  # noqa: E712
    return CountriesResponse(
        countries=[
            CountryItem(
                id=c.id,
                name=c.name,
                iso_code=c.iso_code,
                latitude=float(c.latitude),
                longitude=float(c.longitude),
            )
            for c in countries
        ]
    )


@router.get("/countries/{country_id}/detail", response_model=CountryDetailResponse)
def country_detail(
    country_id: int,
    filters: TransferFilters = Depends(),
    sort_by: str = Query("fee", description="Sort by: fee, date, player_name"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CountryDetailResponse:
    """Return country detail panel data."""
    result = get_country_detail(db, country_id, filters, sort_by, sort_order, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Country not found or not in scope")
    return result
