"""Club endpoints — search and network graph."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.club import (
    ClubNetworkExpandResponse,
    ClubNetworkResponse,
    ClubSearchResponse,
)
from app.schemas.filters import TransferFilters
from app.services.club_service import (
    get_club_network,
    get_club_network_expanded,
    search_clubs,
)

router = APIRouter(prefix="/api/v1", tags=["clubs"])


@router.get("/clubs/search", response_model=ClubSearchResponse)
def club_search(
    q: str = Query(..., min_length=2, description="Search query, min 2 characters"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ClubSearchResponse:
    """Search clubs by name for the network graph selector."""
    results = search_clubs(db, q, limit)
    return ClubSearchResponse(clubs=results)


@router.get("/clubs/{club_id}/network", response_model=ClubNetworkResponse)
def club_network(
    club_id: int,
    filters: TransferFilters = Depends(),
    db: Session = Depends(get_db),
) -> ClubNetworkResponse:
    """Return network graph data for a club."""
    result = get_club_network(db, club_id, filters)
    if result is None:
        raise HTTPException(status_code=404, detail="Club not found")
    return result


@router.get("/clubs/{club_id}/network/{country_id}", response_model=ClubNetworkExpandResponse)
def club_network_expanded(
    club_id: int,
    country_id: int,
    filters: TransferFilters = Depends(),
    db: Session = Depends(get_db),
) -> ClubNetworkExpandResponse:
    """Return expanded club-level edges for a country within a club's network."""
    result = get_club_network_expanded(db, club_id, country_id, filters)
    if result is None:
        raise HTTPException(status_code=404, detail="Club or country not found")
    return result
