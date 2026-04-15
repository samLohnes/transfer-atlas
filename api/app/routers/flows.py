"""Country transfer flow endpoint for the map view."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.filters import TransferFilters
from app.schemas.flow import CountryFlowsResponse
from app.services.flow_service import get_country_flows

router = APIRouter(prefix="/api/v1", tags=["flows"])


@router.get("/flows/countries", response_model=CountryFlowsResponse)
def country_flows(
    filters: TransferFilters = Depends(),
    db: Session = Depends(get_db),
) -> CountryFlowsResponse:
    """Return country-to-country transfer flow data for the map view."""
    return get_country_flows(db, filters)
