"""Service for country transfer flow queries."""

from sqlalchemy import case, func
from sqlalchemy.orm import Session, aliased

from app.models import Club, Country, CountryTransferFlow, Player, Transfer
from app.schemas.filters import TransferFilters
from app.schemas.flow import CountryFlowSummary, CountryFlowsResponse, FlowItem
from app.services.transfer_query import apply_transfer_filters, get_all_windows
from app.services.windows import get_windows_in_range


def get_country_flows(db: Session, filters: TransferFilters) -> CountryFlowsResponse:
    """Get country-to-country flows, using fast path or slow path based on filters."""
    if filters.needs_raw_transfers:
        return _slow_path(db, filters)
    return _fast_path(db, filters)


def _fast_path(db: Session, filters: TransferFilters) -> CountryFlowsResponse:
    """Query pre-aggregated CountryTransferFlow table (no player filters)."""
    FromCountry = aliased(Country, name="from_country")
    ToCountry = aliased(Country, name="to_country")

    query = (
        db.query(
            CountryTransferFlow.from_country_id,
            FromCountry.name.label("from_name"),
            CountryTransferFlow.to_country_id,
            ToCountry.name.label("to_name"),
            func.sum(CountryTransferFlow.total_fee_eur).label("total_fee_eur"),
            func.sum(CountryTransferFlow.transfer_count).label("transfer_count"),
            func.sum(CountryTransferFlow.loan_count).label("loan_count"),
        )
        .join(FromCountry, FromCountry.id == CountryTransferFlow.from_country_id)
        .join(ToCountry, ToCountry.id == CountryTransferFlow.to_country_id)
        .filter(FromCountry.in_scope == True, ToCountry.in_scope == True)  # noqa: E712
    )

    # Time range
    all_windows = get_all_windows(db)
    windows = get_windows_in_range(all_windows, filters.window_start, filters.window_end)
    if windows is not None:
        query = query.filter(CountryTransferFlow.transfer_window.in_(windows))

    # Country filter — only flows involving at least one of the specified countries
    if filters.country_id_list:
        from sqlalchemy import or_
        query = query.filter(or_(
            CountryTransferFlow.from_country_id.in_(filters.country_id_list),
            CountryTransferFlow.to_country_id.in_(filters.country_id_list),
        ))

    query = query.group_by(
        CountryTransferFlow.from_country_id,
        FromCountry.name,
        CountryTransferFlow.to_country_id,
        ToCountry.name,
    )

    rows = query.all()
    return _build_response(rows)


def _slow_path(db: Session, filters: TransferFilters) -> CountryFlowsResponse:
    """Query raw Transfer table with Player join for position/age filters."""
    FromClub = aliased(Club, name="from_club")
    ToClub = aliased(Club, name="to_club")
    FromCountry = aliased(Country, name="from_country")
    ToCountry = aliased(Country, name="to_country")

    query = (
        db.query(
            FromClub.country_id.label("from_country_id"),
            FromCountry.name.label("from_name"),
            ToClub.country_id.label("to_country_id"),
            ToCountry.name.label("to_name"),
            func.coalesce(
                func.sum(case((Transfer.fee_is_loan == False, Transfer.fee_eur), else_=0)),  # noqa: E712
                0,
            ).label("total_fee_eur"),
            func.count().filter(Transfer.fee_is_loan == False).label("transfer_count"),  # noqa: E712
            func.count().filter(Transfer.fee_is_loan == True).label("loan_count"),  # noqa: E712
        )
        .join(Player, Transfer.player_id == Player.id)
        .join(FromClub, Transfer.from_club_id == FromClub.id)
        .join(ToClub, Transfer.to_club_id == ToClub.id)
        .join(FromCountry, FromClub.country_id == FromCountry.id)
        .join(ToCountry, ToClub.country_id == ToCountry.id)
        .filter(FromCountry.in_scope == True, ToCountry.in_scope == True)  # noqa: E712
    )

    query = apply_transfer_filters(query, filters, db)

    # Country filter
    if filters.country_id_list:
        from sqlalchemy import or_
        query = query.filter(or_(
            FromClub.country_id.in_(filters.country_id_list),
            ToClub.country_id.in_(filters.country_id_list),
        ))

    query = query.group_by(
        FromClub.country_id,
        FromCountry.name,
        ToClub.country_id,
        ToCountry.name,
    )

    rows = query.all()
    return _build_response(rows)


def _build_response(rows: list) -> CountryFlowsResponse:
    """Build the response from query rows."""
    flows = []
    spent_by_country: dict[int, tuple[str, int]] = {}
    received_by_country: dict[int, tuple[str, int]] = {}

    for row in rows:
        fee = int(row.total_fee_eur or 0)
        flows.append(FlowItem(
            from_country_id=row.from_country_id,
            from_country_name=row.from_name,
            to_country_id=row.to_country_id,
            to_country_name=row.to_name,
            total_fee_eur=fee,
            transfer_count=int(row.transfer_count or 0),
            loan_count=int(row.loan_count or 0),
        ))

        # to_country is the buyer (spender)
        cid = row.to_country_id
        prev = spent_by_country.get(cid, (row.to_name, 0))
        spent_by_country[cid] = (row.to_name, prev[1] + fee)

        # from_country is the seller (receiver)
        cid = row.from_country_id
        prev = received_by_country.get(cid, (row.from_name, 0))
        received_by_country[cid] = (row.from_name, prev[1] + fee)

    all_ids = set(spent_by_country.keys()) | set(received_by_country.keys())
    summaries = []
    for cid in all_ids:
        name = spent_by_country.get(cid, received_by_country.get(cid, ("", 0)))[0]
        spent = spent_by_country.get(cid, ("", 0))[1]
        received = received_by_country.get(cid, ("", 0))[1]
        summaries.append(CountryFlowSummary(
            country_id=cid,
            country_name=name,
            total_spent_eur=spent,
            total_received_eur=received,
            net_spend_eur=spent - received,
        ))

    return CountryFlowsResponse(flows=flows, country_summaries=summaries)
