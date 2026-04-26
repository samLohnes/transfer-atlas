"""Player-related response schemas."""

from pydantic import BaseModel

from app.schemas.grade import GradeBrief, PlayerGradeSummary


class PlayerSearchItem(BaseModel):
    """A player search result."""

    player_id: int
    player_name: str
    position: str | None
    position_group: str | None
    nationality: str | None


class PlayerSearchResponse(BaseModel):
    """Player search results."""

    players: list[PlayerSearchItem]


class PlayerTransfer(BaseModel):
    """A transfer in the player's history."""

    transfer_id: int
    from_club_id: int
    from_club_name: str
    to_club_id: int
    to_club_name: str
    fee_eur: int | None
    fee_is_loan: bool
    transfer_date: str | None
    transfer_window: str
    season: str
    grade: GradeBrief | None = None


class PlayerValuationPoint(BaseModel):
    """A single market valuation data point."""

    date: str
    value_eur: int


class PlayerDetailResponse(BaseModel):
    """Full player profile."""

    player_id: int
    name: str
    date_of_birth: str | None
    position: str | None
    position_group: str | None
    nationality: str | None
    transfermarkt_url: str | None
    transfers: list[PlayerTransfer]
    valuations: list[PlayerValuationPoint]
    grade_summary: PlayerGradeSummary | None = None
