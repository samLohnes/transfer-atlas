"""Player endpoints — search and detail."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Club, Player, PlayerValuation, Transfer
from app.schemas.player import (
    PlayerDetailResponse,
    PlayerSearchItem,
    PlayerSearchResponse,
    PlayerTransfer,
    PlayerValuationPoint,
)

router = APIRouter(prefix="/api/v1", tags=["players"])


@router.get("/players/search", response_model=PlayerSearchResponse)
def player_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PlayerSearchResponse:
    """Search players by name."""
    rows = (
        db.query(Player)
        .filter(Player.name.ilike(f"%{q}%"))
        .order_by(Player.name)
        .limit(limit)
        .all()
    )
    return PlayerSearchResponse(
        players=[
            PlayerSearchItem(
                player_id=p.id,
                player_name=p.name,
                position=p.position,
                position_group=p.position_group,
                nationality=p.nationality,
            )
            for p in rows
        ]
    )


@router.get("/players/{player_id}", response_model=PlayerDetailResponse)
def player_detail(
    player_id: int,
    db: Session = Depends(get_db),
) -> PlayerDetailResponse:
    """Return player profile with transfer history and valuations."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Transfer history
    from sqlalchemy.orm import aliased
    FromClub = aliased(Club, name="from_club")
    ToClub = aliased(Club, name="to_club")

    transfers = (
        db.query(
            Transfer.id,
            Transfer.from_club_id,
            FromClub.name.label("from_club_name"),
            Transfer.to_club_id,
            ToClub.name.label("to_club_name"),
            Transfer.fee_eur,
            Transfer.fee_is_loan,
            Transfer.transfer_date,
            Transfer.transfer_window,
            Transfer.season,
        )
        .join(FromClub, Transfer.from_club_id == FromClub.id)
        .join(ToClub, Transfer.to_club_id == ToClub.id)
        .filter(Transfer.player_id == player.id)
        .order_by(Transfer.transfer_date.asc().nullslast())
        .all()
    )

    # Valuations
    valuations = (
        db.query(PlayerValuation.valuation_date, PlayerValuation.valuation_eur)
        .filter(PlayerValuation.player_id == player.id)
        .order_by(PlayerValuation.valuation_date.asc())
        .all()
    )

    return PlayerDetailResponse(
        player_id=player.id,
        name=player.name,
        date_of_birth=player.date_of_birth.isoformat() if player.date_of_birth else None,
        position=player.position,
        position_group=player.position_group,
        nationality=player.nationality,
        transfermarkt_url=player.transfermarkt_url,
        transfers=[
            PlayerTransfer(
                transfer_id=t.id,
                from_club_id=t.from_club_id,
                from_club_name=t.from_club_name,
                to_club_id=t.to_club_id,
                to_club_name=t.to_club_name,
                fee_eur=t.fee_eur,
                fee_is_loan=t.fee_is_loan,
                transfer_date=t.transfer_date.isoformat() if t.transfer_date else None,
                transfer_window=t.transfer_window,
                season=t.season,
            )
            for t in transfers
        ],
        valuations=[
            PlayerValuationPoint(
                date=v.valuation_date.isoformat(),
                value_eur=v.valuation_eur,
            )
            for v in valuations
        ],
    )
