"""Service for country detail queries."""

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.models import Club, ClubTransferSummary, Country, Player, Transfer
from app.schemas.country import (
    CountryDetailResponse,
    CountrySummary,
    PaginatedTransfers,
    TopClub,
    TransferItem,
)
from app.schemas.filters import TransferFilters
from app.services.transfer_query import apply_transfer_filters, get_all_windows
from app.services.windows import get_windows_in_range


def get_country_detail(
    db: Session, country_id: int, filters: TransferFilters,
    sort_by: str, sort_order: str, page: int, page_size: int,
) -> CountryDetailResponse | None:
    """Build the country detail panel response."""
    country = db.query(Country).filter(Country.id == country_id, Country.in_scope == True).first()  # noqa: E712
    if not country:
        return None

    # Get clubs in this country
    club_ids = [c.id for c in db.query(Club.id).filter(Club.country_id == country_id).all()]
    if not club_ids:
        return CountryDetailResponse(
            country=CountrySummary(id=country.id, name=country.name, iso_code=country.iso_code, net_spend_eur=0),
            top_buying_clubs=[],
            top_selling_clubs=[],
            transfers=PaginatedTransfers(items=[], total=0, page=page, page_size=page_size),
        )

    # Determine window range
    all_windows = get_all_windows(db)
    windows = get_windows_in_range(all_windows, filters.window_start, filters.window_end)

    # Single query for all club summaries in this country
    summary_query = (
        db.query(
            ClubTransferSummary.club_id,
            Club.name.label("club_name"),
            func.sum(ClubTransferSummary.total_spent_eur).label("total_spent"),
            func.sum(ClubTransferSummary.total_received_eur).label("total_received"),
            func.sum(ClubTransferSummary.players_bought).label("bought_count"),
            func.sum(ClubTransferSummary.players_sold).label("sold_count"),
        )
        .join(Club, Club.id == ClubTransferSummary.club_id)
        .filter(ClubTransferSummary.club_id.in_(club_ids))
    )
    if windows is not None:
        summary_query = summary_query.filter(ClubTransferSummary.transfer_window.in_(windows))
    summary_query = summary_query.group_by(ClubTransferSummary.club_id, Club.name)
    all_summaries = summary_query.all()

    # Slice top 5 buyers and sellers from the same result set
    top_buyers = sorted(all_summaries, key=lambda r: -(r.total_spent or 0))[:5]
    top_sellers = sorted(all_summaries, key=lambda r: -(r.total_received or 0))[:5]

    # Transfers involving clubs in this country
    FromClub = aliased(Club, name="from_club")
    ToClub = aliased(Club, name="to_club")

    transfer_query = (
        db.query(
            Transfer.id,
            Player.name.label("player_name"),
            Player.transfermarkt_url.label("player_url"),
            FromClub.name.label("from_club_name"),
            Transfer.from_club_id,
            ToClub.name.label("to_club_name"),
            Transfer.to_club_id,
            Transfer.fee_eur,
            Transfer.fee_is_loan,
            Player.position_group,
            Transfer.transfer_window,
            Transfer.transfer_date,
        )
        .join(Player, Transfer.player_id == Player.id)
        .join(FromClub, Transfer.from_club_id == FromClub.id)
        .join(ToClub, Transfer.to_club_id == ToClub.id)
        .filter(
            (Transfer.from_club_id.in_(club_ids)) | (Transfer.to_club_id.in_(club_ids))
        )
    )

    transfer_query = apply_transfer_filters(transfer_query, filters, db)

    # Count total before pagination
    total = transfer_query.count()

    # Sorting
    sort_column_map = {
        "fee": Transfer.fee_eur,
        "date": Transfer.transfer_date,
        "player_name": Player.name,
    }
    sort_col = sort_column_map.get(sort_by, Transfer.fee_eur)
    if sort_order == "asc":
        transfer_query = transfer_query.order_by(sort_col.asc().nullslast())
    else:
        transfer_query = transfer_query.order_by(sort_col.desc().nullslast())

    # Pagination
    offset = (page - 1) * page_size
    rows = transfer_query.offset(offset).limit(page_size).all()

    # Compute net spend
    total_spent = sum(r.total_spent for r in top_buyers) if top_buyers else 0
    total_received = sum(r.total_received for r in top_sellers) if top_sellers else 0

    return CountryDetailResponse(
        country=CountrySummary(
            id=country.id,
            name=country.name,
            iso_code=country.iso_code,
            net_spend_eur=total_spent - total_received,
        ),
        top_buying_clubs=[
            TopClub(club_id=r.club_id, club_name=r.club_name, total_spent_eur=int(r.total_spent or 0), total_received_eur=int(r.total_received or 0), transfer_count=int(r.bought_count or 0))
            for r in top_buyers
        ],
        top_selling_clubs=[
            TopClub(club_id=r.club_id, club_name=r.club_name, total_spent_eur=int(r.total_spent or 0), total_received_eur=int(r.total_received or 0), transfer_count=int(r.sold_count or 0))
            for r in top_sellers
        ],
        transfers=PaginatedTransfers(
            items=[
                TransferItem(
                    transfer_id=r.id,
                    player_name=r.player_name,
                    player_transfermarkt_url=r.player_url,
                    from_club_name=r.from_club_name,
                    from_club_id=r.from_club_id,
                    to_club_name=r.to_club_name,
                    to_club_id=r.to_club_id,
                    fee_eur=r.fee_eur,
                    fee_is_loan=r.fee_is_loan,
                    position_group=r.position_group,
                    transfer_window=r.transfer_window,
                    transfer_date=r.transfer_date.isoformat() if r.transfer_date else None,
                )
                for r in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )
