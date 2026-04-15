"""Shared transfer query building with filter application."""

from datetime import date

from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Query, Session

from app.models import Club, Country, Player, Transfer
from app.schemas.filters import TransferFilters
from app.services.windows import get_windows_in_range


def get_all_windows(db: Session) -> list[str]:
    """Get all distinct transfer windows from the database."""
    rows = db.query(Transfer.transfer_window).distinct().all()
    return [r[0] for r in rows]


def apply_transfer_filters(
    query: Query,
    filters: TransferFilters,
    db: Session,
) -> Query:
    """Apply shared filters to a Transfer query. Assumes Transfer is already in the query."""
    # Time range
    all_windows = get_all_windows(db)
    windows = get_windows_in_range(all_windows, filters.window_start, filters.window_end)
    if windows is not None:
        query = query.filter(Transfer.transfer_window.in_(windows))

    # Transfer type
    if filters.transfer_type == "permanent":
        query = query.filter(Transfer.fee_is_loan == False)  # noqa: E712
    elif filters.transfer_type == "loan":
        query = query.filter(Transfer.fee_is_loan == True)  # noqa: E712

    # Fee range
    if filters.fee_min > 0:
        query = query.filter(Transfer.fee_eur >= filters.fee_min)
    if filters.fee_max is not None:
        query = query.filter(Transfer.fee_eur <= filters.fee_max)

    # Position group (requires Player join — caller must ensure join exists)
    if filters.position_groups:
        query = query.filter(Player.position_group.in_(filters.position_groups))

    # Age range (requires Player join + transfer_date)
    if filters.age_min is not None or filters.age_max is not None:
        # Compute age at transfer: years between player DOB and transfer date
        age_expr = extract("year", func.age(Transfer.transfer_date, Player.date_of_birth))

        if filters.age_min is not None:
            query = query.filter(
                and_(
                    Player.date_of_birth.isnot(None),
                    Transfer.transfer_date.isnot(None),
                    age_expr >= filters.age_min,
                )
            )
        if filters.age_max is not None:
            query = query.filter(
                and_(
                    Player.date_of_birth.isnot(None),
                    Transfer.transfer_date.isnot(None),
                    age_expr <= filters.age_max,
                )
            )

    return query
