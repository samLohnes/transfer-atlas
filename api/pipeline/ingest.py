"""Database ingestion steps for each entity type."""

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models import (
    Club,
    Country,
    League,
    PipelineMetadata,
    Player,
    PlayerValuation,
    Transfer,
)
from pipeline.parse import (
    derive_position_group,
    derive_transfer_window,
    normalize_season,
    parse_fee,
)
from pipeline.upsert import upsert_chunk

logger = logging.getLogger(__name__)

# Clubs that play in a different country's league system
COUNTRY_OVERRIDES: dict[str, str] = {
    "Swansea City": "England",
    "Cardiff City": "England",
    "Newport County": "England",
    "Wrexham": "England",
    "AS Monaco": "France",
    "FC Vaduz": "Switzerland",
}

# Dataset country names that differ from our seeded names
COUNTRY_ALIASES: dict[str, str | None] = {
    "United Kingdom": None,  # Ambiguous — resolve via competition
    "Korea, South": "South Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
}

# ISO 3166-1 alpha-3 codes for countries likely to appear in the dataset
ISO_CODES: dict[str, str] = {
    "Afghanistan": "AFG", "Albania": "ALB", "Algeria": "DZA", "Andorra": "AND",
    "Angola": "AGO", "Antigua and Barbuda": "ATG", "Argentina": "ARG",
    "Armenia": "ARM", "Australia": "AUS", "Austria": "AUT", "Azerbaijan": "AZE",
    "Bahrain": "BHR", "Bangladesh": "BGD", "Barbados": "BRB", "Belarus": "BLR",
    "Belgium": "BEL", "Belize": "BLZ", "Benin": "BEN", "Bermuda": "BMU",
    "Bolivia": "BOL", "Bosnia-Herzegovina": "BIH", "Bosnia and Herzegovina": "BIH",
    "Botswana": "BWA", "Brazil": "BRA", "Brunei": "BRN", "Bulgaria": "BGR",
    "Burkina Faso": "BFA", "Burundi": "BDI", "Cambodia": "KHM",
    "Cameroon": "CMR", "Canada": "CAN", "Cape Verde": "CPV",
    "Central African Republic": "CAF", "Chad": "TCD", "Chile": "CHL",
    "China": "CHN", "Colombia": "COL", "Comoros": "COM", "Congo": "COG",
    "Congo DR": "COD", "Costa Rica": "CRI", "Croatia": "HRV", "Cuba": "CUB",
    "Curacao": "CUW", "Cyprus": "CYP", "Czech Republic": "CZE", "Czechia": "CZE",
    "Denmark": "DNK", "Djibouti": "DJI", "Dominican Republic": "DOM",
    "DR Congo": "COD", "Ecuador": "ECU", "Egypt": "EGY", "El Salvador": "SLV",
    "England": "ENG", "Equatorial Guinea": "GNQ", "Eritrea": "ERI",
    "Estonia": "EST", "Eswatini": "SWZ", "Ethiopia": "ETH",
    "Faroe Islands": "FRO", "Fiji": "FJI", "Finland": "FIN", "France": "FRA",
    "Gabon": "GAB", "Gambia": "GMB", "Georgia": "GEO", "Germany": "DEU",
    "Ghana": "GHA", "Gibraltar": "GIB", "Greece": "GRC", "Grenada": "GRD",
    "Guadeloupe": "GLP", "Guatemala": "GTM", "Guinea": "GIN",
    "Guinea-Bissau": "GNB", "Guyana": "GUY", "Haiti": "HTI",
    "Honduras": "HND", "Hong Kong": "HKG", "Hungary": "HUN", "Iceland": "ISL",
    "India": "IND", "Indonesia": "IDN", "Iran": "IRN", "Iraq": "IRQ",
    "Ireland": "IRL", "Israel": "ISR", "Italy": "ITA", "Ivory Coast": "CIV",
    "Jamaica": "JAM", "Japan": "JPN", "Jordan": "JOR", "Kazakhstan": "KAZ",
    "Kenya": "KEN", "Kosovo": "XKX", "Kuwait": "KWT", "Kyrgyzstan": "KGZ",
    "Laos": "LAO", "Latvia": "LVA", "Lebanon": "LBN", "Lesotho": "LSO",
    "Liberia": "LBR", "Libya": "LBY", "Liechtenstein": "LIE",
    "Lithuania": "LTU", "Luxembourg": "LUX", "Madagascar": "MDG",
    "Malawi": "MWI", "Malaysia": "MYS", "Mali": "MLI", "Malta": "MLT",
    "Martinique": "MTQ", "Mauritania": "MRT", "Mauritius": "MUS",
    "Mexico": "MEX", "Moldova": "MDA", "Monaco": "MCO", "Mongolia": "MNG",
    "Montenegro": "MNE", "Morocco": "MAR", "Mozambique": "MOZ",
    "Myanmar": "MMR", "Namibia": "NAM", "Nepal": "NPL", "Netherlands": "NLD",
    "New Caledonia": "NCL", "New Zealand": "NZL", "Nicaragua": "NIC",
    "Niger": "NER", "Nigeria": "NGA", "North Korea": "PRK",
    "North Macedonia": "MKD", "Northern Ireland": "NIR", "Norway": "NOR",
    "Oman": "OMN", "Pakistan": "PAK", "Palestine": "PSE", "Panama": "PAN",
    "Papua New Guinea": "PNG", "Paraguay": "PRY", "Peru": "PER",
    "Philippines": "PHL", "Poland": "POL", "Portugal": "PRT",
    "Puerto Rico": "PRI", "Qatar": "QAT", "Romania": "ROU", "Russia": "RUS",
    "Rwanda": "RWA", "Réunion": "REU", "Samoa": "WSM",
    "Saudi Arabia": "SAU", "Scotland": "SCO", "Senegal": "SEN",
    "Serbia": "SRB", "Sierra Leone": "SLE", "Singapore": "SGP",
    "Slovakia": "SVK", "Slovenia": "SVN", "Solomon Islands": "SLB",
    "Somalia": "SOM", "South Africa": "ZAF", "South Korea": "KOR",
    "South Sudan": "SSD", "Spain": "ESP", "Sri Lanka": "LKA",
    "St. Kitts & Nevis": "KNA", "Sudan": "SDN", "Suriname": "SUR",
    "Sweden": "SWE", "Switzerland": "CHE", "Syria": "SYR",
    "São Tomé and Príncipe": "STP",
    "Tahiti": "PYF", "Taiwan": "TWN", "Tajikistan": "TJK",
    "Tanzania": "TZA", "Thailand": "THA", "Timor-Leste": "TLS",
    "Togo": "TGO", "Tonga": "TON", "Trinidad and Tobago": "TTO",
    "Tunisia": "TUN", "Turkey": "TUR", "Turkmenistan": "TKM",
    "Uganda": "UGA", "Ukraine": "UKR", "United Arab Emirates": "ARE",
    "United States": "USA", "Uruguay": "URY", "Uzbekistan": "UZB",
    "Vanuatu": "VUT", "Venezuela": "VEN", "Vietnam": "VNM", "Wales": "WAL",
    "Yemen": "YEM", "Zambia": "ZMB", "Zimbabwe": "ZWE",
    "Other": "OTH",
}

CHUNK_SIZE = 10_000

# CSV schema expectations per entity.
#   required — columns we actually read during ingest; missing any raises an error.
#   known    — the broader set of columns expected to exist upstream (including
#              ones we don't use). Columns outside this set trigger a warning
#              so we notice when Transfermarkt adds something new.
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "competitions.csv": {"competition_id", "name", "country_name"},
    "players.csv": {
        "player_id", "name", "date_of_birth", "position", "sub_position",
        "country_of_citizenship", "url",
    },
    "clubs.csv": {"club_id", "name", "domestic_competition_id", "url"},
    "transfers.csv": {
        "player_id", "transfer_date", "transfer_season",
        "from_club_id", "to_club_id", "transfer_fee",
    },
    "player_valuations.csv": {"player_id", "date", "market_value_in_eur"},
    "appearances.csv": {
        "player_id", "game_id", "player_club_id", "competition_id", "date",
        "minutes_played", "goals", "assists", "yellow_cards", "red_cards",
    },
}

KNOWN_COLUMNS: dict[str, set[str]] = {
    "competitions.csv": {
        "competition_id", "competition_code", "name", "sub_type", "type",
        "country_id", "country_name", "domestic_league_code", "confederation",
        "total_clubs", "url",
    },
    "players.csv": {
        "player_id", "first_name", "last_name", "name", "last_season",
        "current_club_id", "player_code", "country_of_birth", "city_of_birth",
        "country_of_citizenship", "date_of_birth", "sub_position", "position",
        "foot", "height_in_cm", "contract_expiration_date", "agent_name",
        "image_url", "international_caps", "international_goals",
        "current_national_team_id", "url", "current_club_domestic_competition_id",
        "current_club_name", "market_value_in_eur", "highest_market_value_in_eur",
    },
    "clubs.csv": {
        "club_id", "club_code", "name", "domestic_competition_id",
        "total_market_value", "squad_size", "average_age", "foreigners_number",
        "foreigners_percentage", "national_team_players", "stadium_name",
        "stadium_seats", "net_transfer_record", "coach_name", "last_season",
        "filename", "url",
    },
    "transfers.csv": {
        "player_id", "transfer_date", "transfer_season", "from_club_id",
        "to_club_id", "from_club_name", "to_club_name", "transfer_fee",
        "market_value_in_eur", "player_name",
    },
    "player_valuations.csv": {
        "player_id", "date", "market_value_in_eur", "current_club_name",
        "current_club_id", "player_club_domestic_competition_id",
    },
    "appearances.csv": {
        "appearance_id", "player_id", "game_id", "player_club_id",
        "player_current_club_id", "player_name", "competition_id", "date",
        "yellow_cards", "red_cards", "goals", "assists", "minutes_played",
    },
}


class SchemaValidationError(RuntimeError):
    """Raised when a CSV's schema doesn't match expectations."""


def _validate_schema(csv_path: Path) -> None:
    """Check that a CSV has all required columns. Warn on truly new columns."""
    filename = csv_path.name
    required = REQUIRED_COLUMNS.get(filename)
    if required is None:
        return  # No schema defined — skip validation

    # Read just the header (fast, no data load)
    header_df = pd.read_csv(csv_path, nrows=0)
    actual = set(header_df.columns)

    missing = required - actual
    if missing:
        raise SchemaValidationError(
            f"{filename}: missing required columns {sorted(missing)}. "
            f"Upstream schema may have changed."
        )

    known = KNOWN_COLUMNS.get(filename, required)
    new_columns = actual - known
    if new_columns:
        logger.warning(
            "%s: new upstream columns detected (not yet used): %s",
            filename, sorted(new_columns),
        )


def _safe_str(value: object) -> str | None:
    """Convert a value to string, returning None for NaN/empty."""
    if pd.isna(value) or value == "":
        return None
    return str(value)


def _safe_int_str(value: object) -> str | None:
    """Convert a numeric value to its int string form (e.g. 100.0 → '100')."""
    if pd.isna(value):
        return None
    return str(int(value))


def _coerce_int_nullable(value: object) -> int | None:
    """Coerce a value to int, preserving None for NaN/missing (unlike `_coerce_int_default`)."""
    if value is None or pd.isna(value) or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _coerce_int_default(value: object, default: int = 0) -> int:
    """Coerce a value to int, falling back to `default` for NaN/missing/unparseable."""
    if value is None or pd.isna(value) or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _normalize_foot(value: object) -> str | None:
    """Normalize preferred-foot to title case ('Left', 'Right', 'Both'). Unknown → None."""
    if value is None or pd.isna(value) or value == "":
        return None
    s = str(value).strip().lower()
    if s in ("left", "right", "both"):
        return s.title()
    return None


def _market_value_to_cents(value: object) -> int | None:
    """Convert a EUR numeric (e.g. 75000000.0) to EUR cents (7500000000). NaN/empty → None."""
    if value is None or pd.isna(value) or value == "":
        return None
    try:
        return int(float(value) * 100)
    except (ValueError, TypeError):
        return None


def _parse_date(value: object) -> date | None:
    """Parse a date value, tolerating malformed strings via pandas' `errors='coerce'`."""
    if value is None or pd.isna(value) or value == "":
        return None
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.date()


def _get_or_create_country(session: Session, name: str, country_cache: dict[str, int]) -> int:
    """Get country ID by name, creating it as out-of-scope if needed."""
    resolved_name = COUNTRY_ALIASES.get(name, name)
    if resolved_name is None:
        # Ambiguous — use Other
        resolved_name = "Other"

    if resolved_name in country_cache:
        return country_cache[resolved_name]

    country = session.query(Country).filter(Country.name == resolved_name).first()
    if country:
        country_cache[resolved_name] = country.id
        return country.id

    # Create new out-of-scope country
    iso = ISO_CODES.get(resolved_name, resolved_name[:3].upper())
    # Ensure uniqueness — increment suffix until no collision
    base_iso = iso
    suffix = 1
    while session.query(Country).filter(Country.iso_code == iso).first():
        iso = f"{base_iso[:2]}{suffix}"
        suffix += 1

    new_country = Country(
        name=resolved_name,
        iso_code=iso,
        latitude=0.0,
        longitude=0.0,
        in_scope=False,
    )
    session.add(new_country)
    session.flush()
    country_cache[resolved_name] = new_country.id
    logger.info("  Created out-of-scope country: %s (id=%d)", resolved_name, new_country.id)
    return new_country.id


def ingest_competitions(session: Session, data_dir: Path) -> dict[str, tuple[str, int]]:
    """Load competitions and match to seeded leagues. Returns comp_id → (country_name, country_id) map."""
    _validate_schema(data_dir / "competitions.csv")
    df = pd.read_csv(data_dir / "competitions.csv")
    logger.info("Processing %d competitions...", len(df))

    country_cache: dict[str, int] = {}

    # Build competition_id → (country_name, country_id) mapping
    comp_country_map: dict[str, tuple[str, int]] = {}
    for row in df.itertuples(index=False):
        comp_id = str(row.competition_id)
        country_name = _safe_str(getattr(row, "country_name", None))
        if country_name:
            country_id = _get_or_create_country(session, country_name, country_cache)
            comp_country_map[comp_id] = (country_name, country_id)

    # Match competitions to our seeded leagues and populate transfermarkt_id
    leagues = session.query(League).all()
    league_name_map: dict[str, League] = {l.name: l for l in leagues}

    for row in df.itertuples(index=False):
        comp_id = str(row.competition_id)
        comp_name = _safe_str(getattr(row, "name", None)) or ""

        if comp_name in league_name_map:
            league = league_name_map[comp_name]
            if league.transfermarkt_id is None:
                league.transfermarkt_id = comp_id
                logger.info("  Matched league '%s' → transfermarkt_id=%s", comp_name, comp_id)

    session.commit()
    logger.info("Competitions processed. %d competition-country mappings built.", len(comp_country_map))
    return comp_country_map


def ingest_players(session: Session, data_dir: Path) -> int:
    """Upsert all players from players.csv. Returns count of records processed."""
    _validate_schema(data_dir / "players.csv")

    # Load existing players keyed by transfermarkt_id for in-memory dedup
    existing_players: dict[str, int] = {
        str(p.transfermarkt_id): p.id
        for p in session.query(Player.transfermarkt_id, Player.id).all()
        if p.transfermarkt_id
    }

    count = 0
    for chunk in pd.read_csv(data_dir / "players.csv", low_memory=False, chunksize=CHUNK_SIZE):
        new_records: list[dict] = []
        update_records: list[tuple[int, dict]] = []

        for row in chunk.itertuples(index=False):
            tm_id = _safe_int_str(getattr(row, "player_id", None))
            if not tm_id:
                continue

            name = _safe_str(getattr(row, "name", None)) or "Unknown"
            dob = None
            dob_raw = getattr(row, "date_of_birth", None)
            if pd.notna(dob_raw) and dob_raw != "":
                try:
                    dob = pd.to_datetime(dob_raw).date()
                except Exception:
                    pass

            sub_position = _safe_str(getattr(row, "sub_position", None))
            broad_position = _safe_str(getattr(row, "position", None))
            position_group = derive_position_group(broad_position)
            nationality = _safe_str(getattr(row, "country_of_citizenship", None))
            url = _safe_str(getattr(row, "url", None))

            fields = {
                "name": name,
                "date_of_birth": dob,
                "position": sub_position,
                "sub_position": sub_position or None,
                "position_group": position_group,
                "nationality": nationality,
                "transfermarkt_url": url,
                "height_in_cm": _coerce_int_nullable(getattr(row, "height_in_cm", None)),
                "foot": _normalize_foot(getattr(row, "foot", None)),
                "international_caps": _coerce_int_nullable(getattr(row, "international_caps", None)),
                "international_goals": _coerce_int_nullable(getattr(row, "international_goals", None)),
                "current_market_value_eur": _market_value_to_cents(
                    getattr(row, "market_value_in_eur", None)
                ),
                "peak_market_value_eur": _market_value_to_cents(
                    getattr(row, "highest_market_value_in_eur", None)
                ),
                "contract_expiration_date": _parse_date(
                    getattr(row, "contract_expiration_date", None)
                ),
            }

            if tm_id in existing_players:
                update_records.append((existing_players[tm_id], fields))
            else:
                fields["transfermarkt_id"] = tm_id
                new_records.append(fields)
                # Track so later chunks see this as existing
                # ID is unknown until flush, but we only need to prevent re-insert
                existing_players[tm_id] = -1  # sentinel

            count += 1

        # Bulk insert new records
        if new_records:
            session.execute(insert(Player), new_records)

        # Update existing records individually (only on re-runs)
        for player_id, fields in update_records:
            session.query(Player).filter(Player.id == player_id).update(fields)

        if new_records or update_records:
            session.flush()
            logger.info("  ... %d players processed", count)

    session.commit()
    logger.info("Players ingested: %d records.", count)
    return count


def ingest_clubs(
    session: Session,
    data_dir: Path,
    comp_country_map: dict[str, tuple[str, int]],
) -> int:
    """Upsert all clubs from clubs.csv. Returns count of records processed."""
    _validate_schema(data_dir / "clubs.csv")
    df = pd.read_csv(data_dir / "clubs.csv", low_memory=False)
    logger.info("Ingesting %d clubs...", len(df))

    country_cache: dict[str, int] = {}
    # Pre-populate cache from DB
    for c in session.query(Country).all():
        country_cache[c.name] = c.id

    # Build league transfermarkt_id → league.id map
    league_tm_map: dict[str, int] = {}
    for l in session.query(League).all():
        if l.transfermarkt_id:
            league_tm_map[l.transfermarkt_id] = l.id

    # Load existing clubs for dedup
    existing_clubs: dict[str, int] = {
        str(c.transfermarkt_id): c.id
        for c in session.query(Club.transfermarkt_id, Club.id).all()
        if c.transfermarkt_id
    }

    count = 0
    new_records: list[dict] = []
    update_records: list[tuple[int, dict]] = []

    for row in df.itertuples(index=False):
        tm_id = _safe_int_str(getattr(row, "club_id", None))
        if not tm_id:
            continue

        name = _safe_str(getattr(row, "name", None)) or "Unknown"
        url = _safe_str(getattr(row, "url", None))
        comp_id = _safe_str(getattr(row, "domestic_competition_id", None))

        # Resolve country
        country_id: int | None = None
        if name in COUNTRY_OVERRIDES:
            override_country = COUNTRY_OVERRIDES[name]
            country_id = _get_or_create_country(session, override_country, country_cache)
        elif comp_id and comp_id in comp_country_map:
            _, country_id = comp_country_map[comp_id]
        else:
            country_id = _get_or_create_country(session, "Other", country_cache)

        # Resolve league
        league_id: int | None = None
        if comp_id and comp_id in league_tm_map:
            league_id = league_tm_map[comp_id]

        if tm_id in existing_clubs:
            update_records.append((existing_clubs[tm_id], {
                "name": name,
                "current_league_id": league_id,
                "transfermarkt_url": url,
                # Don't update country_id — it's permanent
            }))
        else:
            new_records.append({
                "name": name,
                "country_id": country_id,
                "current_league_id": league_id,
                "transfermarkt_id": tm_id,
                "transfermarkt_url": url,
            })
            existing_clubs[tm_id] = -1

        count += 1

    # Bulk insert new
    if new_records:
        session.execute(insert(Club), new_records)

    # Update existing
    for club_id, fields in update_records:
        session.query(Club).filter(Club.id == club_id).update(fields)

    session.commit()
    logger.info("Clubs ingested: %d records.", count)
    return count


def ingest_transfers(session: Session, data_dir: Path) -> int:
    """Upsert transfers via ON CONFLICT on (player_id, transfer_date, from_club_id, to_club_id).

    Matches the existing uq_transfers_natural_key unique index. Returns total
    rows processed (inserts + updates).
    """
    _validate_schema(data_dir / "transfers.csv")

    player_tm_map: dict[str, int] = {
        str(p.transfermarkt_id): p.id
        for p in session.query(Player.transfermarkt_id, Player.id).all()
        if p.transfermarkt_id
    }
    club_tm_map: dict[str, int] = {
        str(c.transfermarkt_id): c.id
        for c in session.query(Club.transfermarkt_id, Club.id).all()
        if c.transfermarkt_id
    }

    inserted_total = 0
    updated_total = 0
    skipped = 0
    excluded_loans = 0
    chunk_idx = 0
    total_seen = 0

    for chunk in pd.read_csv(data_dir / "transfers.csv", low_memory=False, chunksize=CHUNK_SIZE):
        chunk_idx += 1
        if chunk_idx == 1:
            logger.info("Processing transfer records (chunked, ON CONFLICT)...")

        rows: list[dict] = []

        for row in chunk.itertuples(index=False):
            total_seen += 1

            # Parse fee — parse_fee may flag the row as an exclude (loan returns)
            fee_str = _safe_str(getattr(row, "transfer_fee", None))
            fee_cents, is_loan, exclude = parse_fee(fee_str)
            if exclude:
                excluded_loans += 1
                continue

            # Resolve player
            player_tm_id = _safe_int_str(getattr(row, "player_id", None))
            if not player_tm_id or player_tm_id not in player_tm_map:
                skipped += 1
                continue
            player_id = player_tm_map[player_tm_id]

            # Resolve clubs
            from_club_tm = _safe_int_str(getattr(row, "from_club_id", None))
            to_club_tm = _safe_int_str(getattr(row, "to_club_id", None))
            if not from_club_tm or not to_club_tm:
                skipped += 1
                continue
            from_club_id = club_tm_map.get(from_club_tm)
            to_club_id = club_tm_map.get(to_club_tm)
            if not from_club_id or not to_club_id:
                skipped += 1
                continue

            # Parse date
            transfer_date: date | None = None
            transfer_date_raw = getattr(row, "transfer_date", None)
            if pd.notna(transfer_date_raw) and transfer_date_raw != "":
                try:
                    transfer_date = pd.to_datetime(transfer_date_raw).date()
                except Exception:
                    pass

            # Derive window and season
            season_raw = _safe_str(getattr(row, "transfer_season", None))
            window = derive_transfer_window(transfer_date, season_raw)
            season = normalize_season(season_raw)

            if not window or not season:
                skipped += 1
                continue

            rows.append({
                "player_id": player_id,
                "from_club_id": from_club_id,
                "to_club_id": to_club_id,
                "transfer_date": transfer_date,
                "fee_eur": fee_cents,
                "fee_is_loan": is_loan,
                "transfer_window": window,
                "season": season,
            })

        if rows:
            ins, upd = upsert_chunk(
                session, Transfer, rows,
                conflict_columns=["player_id", "transfer_date", "from_club_id", "to_club_id"],
                update_columns=["fee_eur", "fee_is_loan", "transfer_window", "season"],
            )
            inserted_total += ins
            updated_total += upd
            session.flush()

        if chunk_idx % 5 == 0:
            logger.info("  ... %d transfer chunks processed", chunk_idx)

    session.commit()
    logger.info(
        "Transfers ingested: %d inserted, %d updated. Skipped: %d. Excluded loan returns: %d. Seen: %d.",
        inserted_total, updated_total, skipped, excluded_loans, total_seen,
    )
    return inserted_total + updated_total


def ingest_valuations(session: Session, data_dir: Path) -> int:
    """Upsert player_valuations rows via ON CONFLICT (player_id, valuation_date).

    Returns total rows successfully ingested. valuation_eur is stored in cents
    (the column name is historical — actual unit is cents, matching Transfer.fee_eur).
    """
    _validate_schema(data_dir / "player_valuations.csv")

    player_tm_map: dict[str, int] = {
        str(p.transfermarkt_id): p.id
        for p in session.query(Player.transfermarkt_id, Player.id).all()
        if p.transfermarkt_id
    }

    inserted_total = 0
    updated_total = 0
    skipped = 0
    chunk_idx = 0
    total_seen = 0

    for chunk in pd.read_csv(
        data_dir / "player_valuations.csv", low_memory=False, chunksize=CHUNK_SIZE
    ):
        chunk_idx += 1
        rows: list[dict] = []

        for row in chunk.itertuples(index=False):
            total_seen += 1

            player_tm_id = _safe_int_str(getattr(row, "player_id", None))
            if not player_tm_id or player_tm_id not in player_tm_map:
                skipped += 1
                continue
            player_id = player_tm_map[player_tm_id]

            val_eur = getattr(row, "market_value_in_eur", None)
            if pd.isna(val_eur) or val_eur == "":
                skipped += 1
                continue
            val_cents = int(float(val_eur) * 100)

            val_date = None
            date_raw = getattr(row, "date", None)
            if pd.notna(date_raw) and date_raw != "":
                try:
                    val_date = pd.to_datetime(date_raw).date()
                except Exception:
                    skipped += 1
                    continue
            else:
                skipped += 1
                continue

            rows.append({
                "player_id": player_id,
                "valuation_eur": val_cents,
                "valuation_date": val_date,
            })

        if rows:
            ins, upd = upsert_chunk(
                session, PlayerValuation, rows,
                conflict_columns=["player_id", "valuation_date"],
                update_columns=["valuation_eur"],
            )
            inserted_total += ins
            updated_total += upd
            session.flush()

        if chunk_idx % 5 == 0:
            logger.info("  ... %d valuation chunks processed", chunk_idx)

    session.commit()
    logger.info(
        "Valuations ingested: %d inserted, %d updated. Skipped: %d. Seen: %d.",
        inserted_total, updated_total, skipped, total_seen,
    )
    return inserted_total + updated_total


def update_metadata(session: Session, total_records: int, commit_hash: str | None) -> None:
    """Update the single-row pipeline metadata."""
    meta = session.query(PipelineMetadata).first()
    now = datetime.utcnow()
    if meta:
        meta.last_ingestion_at = now
        meta.records_processed = total_records
        meta.source_commit_hash = commit_hash
    else:
        session.add(PipelineMetadata(
            last_ingestion_at=now,
            records_processed=total_records,
            source_commit_hash=commit_hash,
        ))
    session.commit()
    logger.info("Pipeline metadata updated: %d records at %s", total_records, now.isoformat())
