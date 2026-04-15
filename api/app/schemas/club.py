"""Club-related response schemas."""

from pydantic import BaseModel


class ClubSearchItem(BaseModel):
    """A club search result."""

    club_id: int
    club_name: str
    country_name: str
    league_name: str | None


class ClubSearchResponse(BaseModel):
    """Club search results."""

    clubs: list[ClubSearchItem]


class CenterClub(BaseModel):
    """The center club in a network graph."""

    club_id: int
    club_name: str
    country_id: int | None = None
    country_name: str | None = None


class CountryEdge(BaseModel):
    """An aggregated edge to a country in the network graph."""

    country_id: int
    country_name: str
    total_spent_eur: int
    total_received_eur: int
    transfer_count: int


class ClubNetworkResponse(BaseModel):
    """Network graph data for a club."""

    center_club: CenterClub
    country_edges: list[CountryEdge]


class NetworkTransfer(BaseModel):
    """A transfer within a network graph edge."""

    transfer_id: int
    player_name: str
    player_transfermarkt_url: str | None
    fee_eur: int | None
    fee_is_loan: bool
    direction: str
    position_group: str | None
    transfer_window: str


class ClubEdge(BaseModel):
    """An edge to a specific club within the network graph."""

    club_id: int
    club_name: str
    total_spent_eur: int
    total_received_eur: int
    transfer_count: int
    transfers: list[NetworkTransfer]


class CountryInfo(BaseModel):
    """Country info for the network expansion view."""

    country_id: int
    country_name: str


class ClubNetworkExpandResponse(BaseModel):
    """Expanded club-level edges for a country."""

    center_club: CenterClub
    country: CountryInfo
    club_edges: list[ClubEdge]


class WindowItem(BaseModel):
    """A transfer window option for the time slider."""

    label: str
    value: str


class WindowsResponse(BaseModel):
    """Available transfer windows."""

    windows: list[WindowItem]
