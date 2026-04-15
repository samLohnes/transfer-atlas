"""Country-related response schemas."""

from pydantic import BaseModel


class CountryItem(BaseModel):
    """A country with geographic coordinates."""

    id: int
    name: str
    iso_code: str
    latitude: float
    longitude: float


class CountriesResponse(BaseModel):
    """List of in-scope countries."""

    countries: list[CountryItem]


class CountrySummary(BaseModel):
    """Country with net spend data for the detail panel header."""

    id: int
    name: str
    iso_code: str
    net_spend_eur: int


class TopClub(BaseModel):
    """A club's aggregated spending or revenue."""

    club_id: int
    club_name: str
    total_spent_eur: int = 0
    total_received_eur: int = 0
    transfer_count: int


class TransferItem(BaseModel):
    """An individual transfer record."""

    transfer_id: int
    player_name: str
    player_transfermarkt_url: str | None
    from_club_name: str
    from_club_id: int
    to_club_name: str
    to_club_id: int
    fee_eur: int | None
    fee_is_loan: bool
    position_group: str | None
    transfer_window: str
    transfer_date: str | None


class PaginatedTransfers(BaseModel):
    """Paginated list of transfers."""

    items: list[TransferItem]
    total: int
    page: int
    page_size: int


class CountryDetailResponse(BaseModel):
    """Full country detail panel data."""

    country: CountrySummary
    top_buying_clubs: list[TopClub]
    top_selling_clubs: list[TopClub]
    transfers: PaginatedTransfers
