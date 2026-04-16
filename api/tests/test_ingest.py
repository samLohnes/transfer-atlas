"""Tests for pipeline ingestion functions.

Validates that the ingest functions produce correct database state from CSV fixtures.
These tests capture current behavior so that performance refactors (chunked reads,
itertuples) can be verified to produce identical results.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Club, Country, League, Player, PlayerValuation, Transfer
from pipeline.ingest import (
    ingest_clubs,
    ingest_competitions,
    ingest_players,
    ingest_transfers,
    ingest_valuations,
)


class TestIngestPlayers:
    """Verify player ingestion produces correct records."""

    def test_inserts_valid_players(self, db_session, data_dir):
        """All valid players are inserted with correct fields."""
        count = ingest_players(db_session, data_dir)
        assert count == 4  # includes player with empty fields

        players = db_session.query(Player).order_by(Player.transfermarkt_id).all()
        assert len(players) == 4

        p1 = next(p for p in players if p.transfermarkt_id == "100")
        assert p1.name == "Player One"
        assert p1.date_of_birth == date(1995, 6, 15)
        assert p1.position == "Centre-Forward"
        assert p1.position_group == "FWD"
        assert p1.nationality == "England"

    def test_position_group_mapping(self, db_session, data_dir):
        """Position groups are correctly derived from broad positions."""
        ingest_players(db_session, data_dir)
        players = {p.transfermarkt_id: p for p in db_session.query(Player).all()}

        assert players["100"].position_group == "FWD"  # attack
        assert players["200"].position_group == "MID"  # midfield
        assert players["300"].position_group == "DEF"  # defender

    def test_handles_empty_fields(self, db_session, data_dir):
        """Players with empty optional fields are still ingested."""
        ingest_players(db_session, data_dir)
        p4 = db_session.query(Player).filter(Player.transfermarkt_id == "400").first()
        assert p4 is not None
        assert p4.date_of_birth is None
        assert p4.position_group is None

    def test_upsert_updates_existing(self, db_session, data_dir):
        """Running ingest twice updates existing records rather than duplicating."""
        ingest_players(db_session, data_dir)
        count = ingest_players(db_session, data_dir)
        assert count == 4
        assert db_session.query(Player).count() == 4

    def test_returns_count(self, db_session, data_dir):
        """Return value matches number of records processed."""
        count = ingest_players(db_session, data_dir)
        assert count == 4


class TestIngestCompetitions:
    """Verify competition ingestion and league matching."""

    def test_builds_country_map(self, db_session, data_dir):
        """Returns a competition_id → (country_name, country_id) mapping."""
        # Seed countries and leagues first
        england = Country(name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
        spain = Country(name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
        db_session.add_all([england, spain])
        db_session.flush()
        db_session.add_all([
            League(name="Premier League", country_id=england.id, tier=1),
            League(name="LaLiga", country_id=spain.id, tier=1),
        ])
        db_session.commit()

        comp_map = ingest_competitions(db_session, data_dir)
        assert "GB1" in comp_map
        assert "ES1" in comp_map
        assert comp_map["GB1"][0] == "England"
        assert comp_map["ES1"][0] == "Spain"

    def test_matches_leagues(self, db_session, data_dir):
        """Leagues get their transfermarkt_id populated."""
        england = Country(name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
        spain = Country(name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
        db_session.add_all([england, spain])
        db_session.flush()
        pl = League(name="Premier League", country_id=england.id, tier=1)
        laliga = League(name="LaLiga", country_id=spain.id, tier=1)
        db_session.add_all([pl, laliga])
        db_session.commit()

        ingest_competitions(db_session, data_dir)

        pl_refreshed = db_session.query(League).filter(League.name == "Premier League").first()
        assert pl_refreshed.transfermarkt_id == "GB1"


class TestIngestClubs:
    """Verify club ingestion with country resolution."""

    def test_inserts_clubs(self, db_session, data_dir):
        """All valid clubs are inserted."""
        # Seed required data
        england = Country(name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
        spain = Country(name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
        other = Country(name="Other", iso_code="OTH", latitude=0.0, longitude=0.0, in_scope=False)
        db_session.add_all([england, spain, other])
        db_session.flush()
        db_session.add_all([
            League(name="Premier League", country_id=england.id, tier=1, transfermarkt_id="GB1"),
            League(name="LaLiga", country_id=spain.id, tier=1, transfermarkt_id="ES1"),
        ])
        db_session.commit()

        comp_map = {"GB1": ("England", england.id), "ES1": ("Spain", spain.id)}
        count = ingest_clubs(db_session, data_dir, comp_map)
        assert count == 3
        assert db_session.query(Club).count() == 3

    def test_country_resolution(self, db_session, data_dir):
        """Clubs are assigned correct countries via competition map."""
        england = Country(name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
        spain = Country(name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
        other = Country(name="Other", iso_code="OTH", latitude=0.0, longitude=0.0, in_scope=False)
        db_session.add_all([england, spain, other])
        db_session.flush()
        db_session.add_all([
            League(name="Premier League", country_id=england.id, tier=1, transfermarkt_id="GB1"),
            League(name="LaLiga", country_id=spain.id, tier=1, transfermarkt_id="ES1"),
        ])
        db_session.commit()

        comp_map = {"GB1": ("England", england.id), "ES1": ("Spain", spain.id)}
        ingest_clubs(db_session, data_dir, comp_map)

        club_a = db_session.query(Club).filter(Club.transfermarkt_id == "10").first()
        club_b = db_session.query(Club).filter(Club.transfermarkt_id == "20").first()
        assert club_a.country_id == england.id
        assert club_b.country_id == spain.id

    def test_upsert_updates_existing(self, db_session, data_dir):
        """Running ingest twice updates existing clubs without duplicating."""
        england = Country(name="England", iso_code="ENG", latitude=51.5, longitude=-0.1, in_scope=True)
        spain = Country(name="Spain", iso_code="ESP", latitude=40.4, longitude=-3.7, in_scope=True)
        other = Country(name="Other", iso_code="OTH", latitude=0.0, longitude=0.0, in_scope=False)
        db_session.add_all([england, spain, other])
        db_session.flush()
        db_session.add_all([
            League(name="Premier League", country_id=england.id, tier=1, transfermarkt_id="GB1"),
            League(name="LaLiga", country_id=spain.id, tier=1, transfermarkt_id="ES1"),
        ])
        db_session.commit()

        comp_map = {"GB1": ("England", england.id), "ES1": ("Spain", spain.id)}
        ingest_clubs(db_session, data_dir, comp_map)
        ingest_clubs(db_session, data_dir, comp_map)
        assert db_session.query(Club).count() == 3


class TestIngestTransfers:
    """Verify transfer ingestion with fee parsing and skip logic."""

    def test_inserts_valid_transfers(self, seeded_session, data_dir):
        """Valid transfers are inserted, unknowns are skipped."""
        count = ingest_transfers(seeded_session, data_dir)
        assert count == 3  # 3 valid, 1 unknown player skipped

        transfers = seeded_session.query(Transfer).order_by(Transfer.transfer_date).all()
        assert len(transfers) == 3

    def test_fee_parsing(self, seeded_session, data_dir):
        """Fees are correctly parsed from numeric strings to cents."""
        ingest_transfers(seeded_session, data_dir)
        transfers = {
            t.player_id: t for t in seeded_session.query(Transfer).all()
        }

        # 50000000.000 → 5_000_000_000 cents
        assert transfers[1].fee_eur == 5_000_000_000
        # 0.000 → 0 cents (free)
        assert transfers[2].fee_eur == 0
        # Empty → None (undisclosed)
        assert transfers[3].fee_eur is None

    def test_window_derivation(self, seeded_session, data_dir):
        """Transfer windows are correctly derived from dates."""
        ingest_transfers(seeded_session, data_dir)
        transfers = {
            t.player_id: t for t in seeded_session.query(Transfer).all()
        }

        assert transfers[1].transfer_window == "Summer 2023"  # July
        assert transfers[2].transfer_window == "Winter 2024"  # January
        assert transfers[3].transfer_window == "Summer 2023"  # August

    def test_season_normalization(self, seeded_session, data_dir):
        """Seasons are normalized to YYYY-YYYY format."""
        ingest_transfers(seeded_session, data_dir)
        for t in seeded_session.query(Transfer).all():
            assert t.season == "2023-2024"

    def test_skips_unknown_player(self, seeded_session, data_dir):
        """Transfers referencing unknown players are skipped."""
        ingest_transfers(seeded_session, data_dir)
        # Player 999 doesn't exist, so that transfer is skipped
        assert seeded_session.query(Transfer).count() == 3

    def test_upsert_updates_existing(self, seeded_session, data_dir):
        """Running ingest twice updates existing transfers without duplicating."""
        ingest_transfers(seeded_session, data_dir)
        ingest_transfers(seeded_session, data_dir)
        assert seeded_session.query(Transfer).count() == 3


class TestIngestValuations:
    """Verify valuation ingestion with skip logic."""

    def test_inserts_valid_valuations(self, seeded_session, data_dir):
        """Valid valuations are inserted, missing/unknown are skipped."""
        count = ingest_valuations(seeded_session, data_dir)
        assert count == 3  # 3 valid, 1 missing value, 1 unknown player

        valuations = seeded_session.query(PlayerValuation).all()
        assert len(valuations) == 3

    def test_valuation_values(self, seeded_session, data_dir):
        """Valuations are correctly converted to cents."""
        ingest_valuations(seeded_session, data_dir)
        vals = seeded_session.query(PlayerValuation).filter(
            PlayerValuation.player_id == 1
        ).order_by(PlayerValuation.valuation_date).all()

        assert len(vals) == 2
        assert vals[0].valuation_eur == 6_000_000_000  # 60M * 100
        assert vals[0].valuation_date == date(2023, 6, 1)
        assert vals[1].valuation_eur == 5_500_000_000  # 55M * 100
        assert vals[1].valuation_date == date(2024, 1, 1)

    def test_skips_missing_value(self, seeded_session, data_dir):
        """Valuations with empty market_value_in_eur are skipped."""
        ingest_valuations(seeded_session, data_dir)
        # Player 200 has one valid and one empty valuation
        p2_vals = seeded_session.query(PlayerValuation).filter(
            PlayerValuation.player_id == 2
        ).all()
        assert len(p2_vals) == 1

    def test_upsert_updates_existing(self, seeded_session, data_dir):
        """Running ingest twice updates existing valuations without duplicating."""
        ingest_valuations(seeded_session, data_dir)
        ingest_valuations(seeded_session, data_dir)
        assert seeded_session.query(PlayerValuation).count() == 3
