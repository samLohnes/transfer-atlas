"""Shared test fixtures for pipeline tests."""

import csv
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure api/ is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Stub out app.config and app.database before any model imports to avoid
# pulling in pydantic_settings (not installed in test env).
import types

config_mod = types.ModuleType("app.config")
config_mod.settings = type("Settings", (), {"database_url": "sqlite:///:memory:"})()  # type: ignore[attr-defined]
sys.modules["app.config"] = config_mod

from app.database import Base
from app.models import Club, Country, League, Player


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database with all tables, yield a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def minimal_session(db_session):
    """Session with only countries + leagues — the state after migrations/seed, before any pipeline run.

    Used by end-to-end tests that run the full ingest chain from scratch.
    """
    england = Country(id=1, name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
    spain = Country(id=2, name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
    other = Country(id=3, name="Other", iso_code="OTH", latitude=0.0, longitude=0.0, in_scope=False)
    db_session.add_all([england, spain, other])
    db_session.flush()

    pl = League(id=1, name="Premier League", country_id=1, tier=1)
    laliga = League(id=2, name="LaLiga", country_id=2, tier=1)
    db_session.add_all([pl, laliga])
    db_session.flush()

    db_session.commit()
    return db_session


@pytest.fixture()
def seeded_session(db_session):
    """Session with baseline countries, leagues, players, and clubs for transfer/valuation tests."""
    # Countries
    england = Country(id=1, name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
    spain = Country(id=2, name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
    other = Country(id=3, name="Other", iso_code="OTH", latitude=0.0, longitude=0.0, in_scope=False)
    db_session.add_all([england, spain, other])
    db_session.flush()

    # Leagues
    pl = League(id=1, name="Premier League", country_id=1, tier=1, transfermarkt_id="GB1")
    laliga = League(id=2, name="LaLiga", country_id=2, tier=1, transfermarkt_id="ES1")
    db_session.add_all([pl, laliga])
    db_session.flush()

    # Players
    p1 = Player(id=1, name="Player One", transfermarkt_id="100", position_group="FWD")
    p2 = Player(id=2, name="Player Two", transfermarkt_id="200", position_group="MID")
    p3 = Player(id=3, name="Player Three", transfermarkt_id="300", position_group="DEF")
    db_session.add_all([p1, p2, p3])
    db_session.flush()

    # Clubs
    c1 = Club(id=1, name="Club A", country_id=1, transfermarkt_id="10", current_league_id=1)
    c2 = Club(id=2, name="Club B", country_id=2, transfermarkt_id="20", current_league_id=2)
    c3 = Club(id=3, name="Club C", country_id=1, transfermarkt_id="30", current_league_id=1)
    db_session.add_all([c1, c2, c3])
    db_session.flush()

    db_session.commit()
    return db_session


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write a list of dicts to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture()
def data_dir(tmp_path):
    """Create a temporary data directory with small CSV fixtures."""
    # competitions.csv
    write_csv(tmp_path / "competitions.csv", ["competition_id", "name", "country_name"], [
        {"competition_id": "GB1", "name": "Premier League", "country_name": "England"},
        {"competition_id": "ES1", "name": "LaLiga", "country_name": "Spain"},
    ])

    # players.csv — includes empty player_id (should be skipped)
    write_csv(tmp_path / "players.csv", [
        "player_id", "name", "date_of_birth", "position", "sub_position",
        "country_of_citizenship", "url",
    ], [
        {"player_id": "100", "name": "Player One", "date_of_birth": "1995-06-15",
         "position": "attack", "sub_position": "Centre-Forward",
         "country_of_citizenship": "England", "url": "/player-one/100"},
        {"player_id": "200", "name": "Player Two", "date_of_birth": "1998-01-20",
         "position": "midfield", "sub_position": "Central Midfield",
         "country_of_citizenship": "Spain", "url": "/player-two/200"},
        {"player_id": "300", "name": "Player Three", "date_of_birth": "2000-03-10",
         "position": "defender", "sub_position": "Centre-Back",
         "country_of_citizenship": "England", "url": "/player-three/300"},
        {"player_id": "400", "name": "Player Four", "date_of_birth": "",
         "position": "", "sub_position": "",
         "country_of_citizenship": "", "url": ""},
        # Empty player_id — should be skipped silently
        {"player_id": "", "name": "No ID Player", "date_of_birth": "",
         "position": "", "sub_position": "",
         "country_of_citizenship": "", "url": ""},
    ])

    # clubs.csv — includes Swansea (country override) and a club with unknown competition
    write_csv(tmp_path / "clubs.csv", [
        "club_id", "name", "domestic_competition_id", "url",
    ], [
        {"club_id": "10", "name": "Club A", "domestic_competition_id": "GB1", "url": "/club-a"},
        {"club_id": "20", "name": "Club B", "domestic_competition_id": "ES1", "url": "/club-b"},
        {"club_id": "30", "name": "Club C", "domestic_competition_id": "GB1", "url": "/club-c"},
        # Country override — Swansea City is Welsh but plays in England
        {"club_id": "40", "name": "Swansea City", "domestic_competition_id": "GB1", "url": "/swansea"},
        # Unknown competition — should fall back to "Other"
        {"club_id": "50", "name": "Mystery Club", "domestic_competition_id": "XX9", "url": "/mystery"},
        # Empty club_id — should be skipped
        {"club_id": "", "name": "No ID Club", "domestic_competition_id": "GB1", "url": ""},
    ])

    # transfers.csv — covers all skip paths
    write_csv(tmp_path / "transfers.csv", [
        "player_id", "transfer_date", "transfer_season", "from_club_id", "to_club_id",
        "from_club_name", "to_club_name", "transfer_fee", "market_value_in_eur", "player_name",
    ], [
        # Paid transfer (valid)
        {"player_id": "100", "transfer_date": "2023-07-01", "transfer_season": "23/24",
         "from_club_id": "10", "to_club_id": "20", "from_club_name": "Club A",
         "to_club_name": "Club B", "transfer_fee": "50000000.000",
         "market_value_in_eur": "60000000.000", "player_name": "Player One"},
        # Free transfer (valid)
        {"player_id": "200", "transfer_date": "2024-01-15", "transfer_season": "23/24",
         "from_club_id": "20", "to_club_id": "30", "from_club_name": "Club B",
         "to_club_name": "Club C", "transfer_fee": "0.000",
         "market_value_in_eur": "10000000.000", "player_name": "Player Two"},
        # Undisclosed fee (valid)
        {"player_id": "300", "transfer_date": "2023-08-15", "transfer_season": "23/24",
         "from_club_id": "30", "to_club_id": "10", "from_club_name": "Club C",
         "to_club_name": "Club A", "transfer_fee": "",
         "market_value_in_eur": "5000000.000", "player_name": "Player Three"},
        # Unknown player — should be skipped
        {"player_id": "999", "transfer_date": "2023-07-01", "transfer_season": "23/24",
         "from_club_id": "10", "to_club_id": "20", "from_club_name": "Club A",
         "to_club_name": "Club B", "transfer_fee": "1000000.000",
         "market_value_in_eur": "", "player_name": "Unknown Player"},
        # Unknown from_club — should be skipped
        {"player_id": "100", "transfer_date": "2023-09-01", "transfer_season": "23/24",
         "from_club_id": "9999", "to_club_id": "20", "from_club_name": "Ghost Club",
         "to_club_name": "Club B", "transfer_fee": "2000000.000",
         "market_value_in_eur": "", "player_name": "Player One"},
        # Unknown to_club — should be skipped
        {"player_id": "100", "transfer_date": "2023-10-01", "transfer_season": "23/24",
         "from_club_id": "10", "to_club_id": "9999", "from_club_name": "Club A",
         "to_club_name": "Ghost Club", "transfer_fee": "3000000.000",
         "market_value_in_eur": "", "player_name": "Player One"},
        # Empty player_id — should be skipped
        {"player_id": "", "transfer_date": "2023-07-01", "transfer_season": "23/24",
         "from_club_id": "10", "to_club_id": "20", "from_club_name": "Club A",
         "to_club_name": "Club B", "transfer_fee": "1000000.000",
         "market_value_in_eur": "", "player_name": ""},
        # Empty from_club_id — should be skipped
        {"player_id": "200", "transfer_date": "2023-07-01", "transfer_season": "23/24",
         "from_club_id": "", "to_club_id": "20", "from_club_name": "",
         "to_club_name": "Club B", "transfer_fee": "1000000.000",
         "market_value_in_eur": "", "player_name": "Player Two"},
        # Missing date but valid season — derives window from season (Summer)
        {"player_id": "200", "transfer_date": "", "transfer_season": "22/23",
         "from_club_id": "20", "to_club_id": "10", "from_club_name": "Club B",
         "to_club_name": "Club A", "transfer_fee": "500000.000",
         "market_value_in_eur": "", "player_name": "Player Two"},
        # Missing both date and season — should be skipped (no window derivable)
        {"player_id": "300", "transfer_date": "", "transfer_season": "",
         "from_club_id": "30", "to_club_id": "20", "from_club_name": "Club C",
         "to_club_name": "Club B", "transfer_fee": "100000.000",
         "market_value_in_eur": "", "player_name": "Player Three"},
    ])

    # player_valuations.csv — covers all skip paths
    write_csv(tmp_path / "player_valuations.csv", [
        "player_id", "date", "market_value_in_eur",
    ], [
        {"player_id": "100", "date": "2023-06-01", "market_value_in_eur": "60000000.0"},
        {"player_id": "100", "date": "2024-01-01", "market_value_in_eur": "55000000.0"},
        {"player_id": "200", "date": "2023-06-01", "market_value_in_eur": "10000000.0"},
        # Missing value — should be skipped
        {"player_id": "200", "date": "2024-01-01", "market_value_in_eur": ""},
        # Unknown player — should be skipped
        {"player_id": "999", "date": "2023-06-01", "market_value_in_eur": "5000000.0"},
        # Missing date — should be skipped
        {"player_id": "100", "date": "", "market_value_in_eur": "70000000.0"},
        # Empty player_id — should be skipped
        {"player_id": "", "date": "2023-06-01", "market_value_in_eur": "1000000.0"},
    ])

    return tmp_path
