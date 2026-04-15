"""Service for club search and network graph queries."""

from sqlalchemy import func, literal, or_
from sqlalchemy.orm import Session

from app.models import Club, Country, League, Player, Transfer
from app.schemas.club import (
    CenterClub,
    ClubEdge,
    ClubNetworkExpandResponse,
    ClubNetworkResponse,
    ClubSearchItem,
    CountryEdge,
    CountryInfo,
    NetworkTransfer,
)
from app.schemas.filters import TransferFilters
from app.services.transfer_query import apply_transfer_filters


def search_clubs(db: Session, q: str, limit: int) -> list[ClubSearchItem]:
    """Search clubs by name using case-insensitive ILIKE."""
    rows = (
        db.query(Club.id, Club.name, Country.name.label("country_name"), League.name.label("league_name"))
        .join(Country, Club.country_id == Country.id)
        .outerjoin(League, Club.current_league_id == League.id)
        .filter(Club.name.ilike(f"%{q}%"))
        .order_by(Club.name)
        .limit(limit)
        .all()
    )
    return [
        ClubSearchItem(club_id=r.id, club_name=r.name, country_name=r.country_name, league_name=r.league_name)
        for r in rows
    ]


def get_club_network(db: Session, club_id: int, filters: TransferFilters) -> ClubNetworkResponse | None:
    """Get country-level network edges for a club."""
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        return None

    country = db.query(Country).filter(Country.id == club.country_id).first()

    # Query transfers where this club is buyer or seller
    # Bought: club is to_club → counterparty is from_club
    # Sold: club is from_club → counterparty is to_club
    bought_query = (
        db.query(
            Club.country_id.label("counter_country_id"),
            func.coalesce(func.sum(Transfer.fee_eur), 0).label("spent"),
            literal(0).label("received"),
            func.count().label("count"),
        )
        .join(Club, Transfer.from_club_id == Club.id)
        .join(Player, Transfer.player_id == Player.id)
        .filter(Transfer.to_club_id == club_id)
    )
    bought_query = apply_transfer_filters(bought_query, filters, db)
    bought_query = bought_query.group_by(Club.country_id)

    sold_query = (
        db.query(
            Club.country_id.label("counter_country_id"),
            literal(0).label("spent"),
            func.coalesce(func.sum(Transfer.fee_eur), 0).label("received"),
            func.count().label("count"),
        )
        .join(Club, Transfer.to_club_id == Club.id)
        .join(Player, Transfer.player_id == Player.id)
        .filter(Transfer.from_club_id == club_id)
    )
    sold_query = apply_transfer_filters(sold_query, filters, db)
    sold_query = sold_query.group_by(Club.country_id)

    bought_rows = bought_query.all()
    sold_rows = sold_query.all()

    # Merge by country
    edges_map: dict[int, dict] = {}
    for r in bought_rows:
        cid = r.counter_country_id
        if cid not in edges_map:
            edges_map[cid] = {"spent": 0, "received": 0, "count": 0}
        edges_map[cid]["spent"] += int(r.spent or 0)
        edges_map[cid]["count"] += int(r.count or 0)

    for r in sold_rows:
        cid = r.counter_country_id
        if cid not in edges_map:
            edges_map[cid] = {"spent": 0, "received": 0, "count": 0}
        edges_map[cid]["received"] += int(r.received or 0)
        edges_map[cid]["count"] += int(r.count or 0)

    # Get country names
    country_names = {
        c.id: c.name for c in db.query(Country).filter(Country.id.in_(edges_map.keys())).all()
    }

    country_edges = [
        CountryEdge(
            country_id=cid,
            country_name=country_names.get(cid, "Unknown"),
            total_spent_eur=data["spent"],
            total_received_eur=data["received"],
            transfer_count=data["count"],
        )
        for cid, data in edges_map.items()
    ]

    return ClubNetworkResponse(
        center_club=CenterClub(
            club_id=club.id,
            club_name=club.name,
            country_id=club.country_id,
            country_name=country.name if country else None,
        ),
        country_edges=country_edges,
    )


def get_club_network_expanded(
    db: Session, club_id: int, country_id: int, filters: TransferFilters,
) -> ClubNetworkExpandResponse | None:
    """Get club-level edges for a specific country within a club's network."""
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        return None

    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        return None

    # Get all transfers between center club and clubs in the target country
    counter_clubs = db.query(Club.id).filter(Club.country_id == country_id).subquery()

    # Bought from clubs in target country
    bought_query = (
        db.query(Transfer)
        .join(Player, Transfer.player_id == Player.id)
        .filter(
            Transfer.to_club_id == club_id,
            Transfer.from_club_id.in_(db.query(counter_clubs)),
        )
    )
    bought_query = apply_transfer_filters(bought_query, filters, db)
    bought_transfers = bought_query.all()

    # Sold to clubs in target country
    sold_query = (
        db.query(Transfer)
        .join(Player, Transfer.player_id == Player.id)
        .filter(
            Transfer.from_club_id == club_id,
            Transfer.to_club_id.in_(db.query(counter_clubs)),
        )
    )
    sold_query = apply_transfer_filters(sold_query, filters, db)
    sold_transfers = sold_query.all()

    if not bought_transfers and not sold_transfers:
        return ClubNetworkExpandResponse(
            center_club=CenterClub(club_id=club.id, club_name=club.name),
            country=CountryInfo(country_id=country.id, country_name=country.name),
            club_edges=[],
        )

    # Build club edges
    club_data: dict[int, dict] = {}

    # Load player and club names
    player_ids = {t.player_id for t in bought_transfers + sold_transfers}
    players = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}

    counter_club_ids = (
        {t.from_club_id for t in bought_transfers} | {t.to_club_id for t in sold_transfers}
    )
    counter_clubs_map = {c.id: c for c in db.query(Club).filter(Club.id.in_(counter_club_ids)).all()}

    for t in bought_transfers:
        cid = t.from_club_id
        if cid not in club_data:
            c = counter_clubs_map.get(cid)
            club_data[cid] = {"name": c.name if c else "Unknown", "spent": 0, "received": 0, "count": 0, "transfers": []}
        club_data[cid]["spent"] += int(t.fee_eur or 0)
        club_data[cid]["count"] += 1
        p = players.get(t.player_id)
        club_data[cid]["transfers"].append(NetworkTransfer(
            transfer_id=t.id,
            player_name=p.name if p else "Unknown",
            player_transfermarkt_url=p.transfermarkt_url if p else None,
            fee_eur=t.fee_eur,
            fee_is_loan=t.fee_is_loan,
            direction="bought",
            position_group=p.position_group if p else None,
            transfer_window=t.transfer_window,
        ))

    for t in sold_transfers:
        cid = t.to_club_id
        if cid not in club_data:
            c = counter_clubs_map.get(cid)
            club_data[cid] = {"name": c.name if c else "Unknown", "spent": 0, "received": 0, "count": 0, "transfers": []}
        club_data[cid]["received"] += int(t.fee_eur or 0)
        club_data[cid]["count"] += 1
        p = players.get(t.player_id)
        club_data[cid]["transfers"].append(NetworkTransfer(
            transfer_id=t.id,
            player_name=p.name if p else "Unknown",
            player_transfermarkt_url=p.transfermarkt_url if p else None,
            fee_eur=t.fee_eur,
            fee_is_loan=t.fee_is_loan,
            direction="sold",
            position_group=p.position_group if p else None,
            transfer_window=t.transfer_window,
        ))

    club_edges = [
        ClubEdge(
            club_id=cid,
            club_name=data["name"],
            total_spent_eur=data["spent"],
            total_received_eur=data["received"],
            transfer_count=data["count"],
            transfers=data["transfers"],
        )
        for cid, data in club_data.items()
    ]

    return ClubNetworkExpandResponse(
        center_club=CenterClub(club_id=club.id, club_name=club.name),
        country=CountryInfo(country_id=country.id, country_name=country.name),
        club_edges=club_edges,
    )
