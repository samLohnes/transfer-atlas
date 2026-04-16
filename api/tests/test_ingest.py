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
    SchemaValidationError,
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
        assert count == 4  # 4 valid, 1 with empty player_id skipped

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

    def test_skips_empty_player_id(self, db_session, data_dir):
        """Players with empty player_id are skipped entirely."""
        ingest_players(db_session, data_dir)
        # Only 4 players inserted; the empty-ID row does not appear
        assert db_session.query(Player).count() == 4

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


@pytest.fixture()
def clubs_setup(db_session):
    """Seed countries and leagues needed for club ingestion tests."""
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
    return {"england": england, "spain": spain, "other": other, "comp_map": comp_map}


class TestIngestClubs:
    """Verify club ingestion with country resolution."""

    def test_inserts_clubs(self, db_session, data_dir, clubs_setup):
        """All valid clubs are inserted."""
        count = ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])
        # 5 valid clubs (3 regular + Swansea override + Mystery Club), 1 empty-id skipped
        assert count == 5
        assert db_session.query(Club).count() == 5

    def test_country_resolution(self, db_session, data_dir, clubs_setup):
        """Clubs are assigned correct countries via competition map."""
        ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])

        club_a = db_session.query(Club).filter(Club.transfermarkt_id == "10").first()
        club_b = db_session.query(Club).filter(Club.transfermarkt_id == "20").first()
        assert club_a.country_id == clubs_setup["england"].id
        assert club_b.country_id == clubs_setup["spain"].id

    def test_country_override(self, db_session, data_dir, clubs_setup):
        """Clubs in COUNTRY_OVERRIDES use the override country, not the competition's."""
        ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])
        swansea = db_session.query(Club).filter(Club.transfermarkt_id == "40").first()
        # Swansea's GB1 competition would give England anyway, but the override forces it
        assert swansea.country_id == clubs_setup["england"].id

    def test_unknown_competition_falls_back_to_other(self, db_session, data_dir, clubs_setup):
        """Clubs with an unknown competition_id are assigned to 'Other'."""
        ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])
        mystery = db_session.query(Club).filter(Club.transfermarkt_id == "50").first()
        assert mystery.country_id == clubs_setup["other"].id

    def test_skips_empty_club_id(self, db_session, data_dir, clubs_setup):
        """Clubs with empty club_id are skipped entirely."""
        ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])
        assert db_session.query(Club).count() == 5

    def test_upsert_updates_existing(self, db_session, data_dir, clubs_setup):
        """Running ingest twice updates existing clubs without duplicating."""
        ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])
        ingest_clubs(db_session, data_dir, clubs_setup["comp_map"])
        assert db_session.query(Club).count() == 5


class TestIngestTransfers:
    """Verify transfer ingestion with fee parsing and skip logic."""

    def test_inserts_valid_transfers(self, seeded_session, data_dir):
        """Valid transfers are inserted, all invalid variants are skipped."""
        count = ingest_transfers(seeded_session, data_dir)
        # 3 fully-valid + 1 missing-date-but-valid-season = 4 processed
        assert count == 4

        transfers = seeded_session.query(Transfer).all()
        assert len(transfers) == 4

    def test_fee_parsing(self, seeded_session, data_dir):
        """Fees are correctly parsed from numeric strings to cents."""
        ingest_transfers(seeded_session, data_dir)
        # Use natural key to identify specific transfers
        t1 = seeded_session.query(Transfer).filter(
            Transfer.player_id == 1, Transfer.transfer_date == date(2023, 7, 1)
        ).first()
        t2 = seeded_session.query(Transfer).filter(
            Transfer.player_id == 2, Transfer.transfer_date == date(2024, 1, 15)
        ).first()
        t3 = seeded_session.query(Transfer).filter(
            Transfer.player_id == 3, Transfer.transfer_date == date(2023, 8, 15)
        ).first()

        # 50000000.000 → 5_000_000_000 cents
        assert t1.fee_eur == 5_000_000_000
        # 0.000 → 0 cents (free)
        assert t2.fee_eur == 0
        # Empty → None (undisclosed)
        assert t3.fee_eur is None

    def test_window_derivation(self, seeded_session, data_dir):
        """Transfer windows are correctly derived from dates."""
        ingest_transfers(seeded_session, data_dir)
        t1 = seeded_session.query(Transfer).filter(
            Transfer.player_id == 1, Transfer.transfer_date == date(2023, 7, 1)
        ).first()
        t2 = seeded_session.query(Transfer).filter(
            Transfer.player_id == 2, Transfer.transfer_date == date(2024, 1, 15)
        ).first()
        t3 = seeded_session.query(Transfer).filter(
            Transfer.player_id == 3, Transfer.transfer_date == date(2023, 8, 15)
        ).first()

        assert t1.transfer_window == "Summer 2023"  # July
        assert t2.transfer_window == "Winter 2024"  # January
        assert t3.transfer_window == "Summer 2023"  # August

    def test_window_fallback_to_season(self, seeded_session, data_dir):
        """When date is missing but season is present, window is derived from season."""
        ingest_transfers(seeded_session, data_dir)
        # Player 200, from_club=20, to_club=10, no date, season=22/23
        t = seeded_session.query(Transfer).filter(
            Transfer.player_id == 2,
            Transfer.from_club_id == 2,
            Transfer.to_club_id == 1,
            Transfer.transfer_date.is_(None),
        ).first()
        assert t is not None
        assert t.transfer_window == "Summer 2022"
        assert t.season == "2022-2023"

    def test_season_normalization(self, seeded_session, data_dir):
        """Seasons are normalized to YYYY-YYYY format."""
        ingest_transfers(seeded_session, data_dir)
        # All transfers from 23/24 or 22/23 seasons
        seasons = {t.season for t in seeded_session.query(Transfer).all()}
        assert seasons == {"2023-2024", "2022-2023"}

    def test_skips_unknown_player(self, seeded_session, data_dir):
        """Transfers referencing unknown players are skipped."""
        ingest_transfers(seeded_session, data_dir)
        # Player 999 doesn't exist — no transfer should reference a non-existent player_id
        all_player_ids = {t.player_id for t in seeded_session.query(Transfer).all()}
        assert 999 not in all_player_ids

    def test_skips_unknown_from_club(self, seeded_session, data_dir):
        """Transfers where from_club doesn't exist are skipped."""
        ingest_transfers(seeded_session, data_dir)
        all_from = {t.from_club_id for t in seeded_session.query(Transfer).all()}
        # Club 9999 doesn't exist as an internal ID
        assert all(fid in {1, 2, 3} for fid in all_from)

    def test_skips_unknown_to_club(self, seeded_session, data_dir):
        """Transfers where to_club doesn't exist are skipped."""
        ingest_transfers(seeded_session, data_dir)
        all_to = {t.to_club_id for t in seeded_session.query(Transfer).all()}
        assert all(tid in {1, 2, 3} for tid in all_to)

    def test_skips_empty_player_id(self, seeded_session, data_dir):
        """Transfers with empty player_id are skipped."""
        ingest_transfers(seeded_session, data_dir)
        # Only 4 rows pass through; confirm by total count
        assert seeded_session.query(Transfer).count() == 4

    def test_skips_empty_club_id(self, seeded_session, data_dir):
        """Transfers with empty from_club_id or to_club_id are skipped."""
        ingest_transfers(seeded_session, data_dir)
        assert seeded_session.query(Transfer).count() == 4

    def test_skips_when_no_window_derivable(self, seeded_session, data_dir):
        """Transfers with no date AND no season are skipped (no window)."""
        ingest_transfers(seeded_session, data_dir)
        # Player 300 has one valid transfer (2023-08-15) and one invalid (no date/season)
        p3_transfers = seeded_session.query(Transfer).filter(Transfer.player_id == 3).all()
        assert len(p3_transfers) == 1
        assert p3_transfers[0].transfer_date == date(2023, 8, 15)

    def test_upsert_updates_existing(self, seeded_session, data_dir):
        """Running ingest twice updates existing transfers without duplicating."""
        ingest_transfers(seeded_session, data_dir)
        ingest_transfers(seeded_session, data_dir)
        assert seeded_session.query(Transfer).count() == 4

    def test_unchanged_values_preserve_data(self, seeded_session, data_dir):
        """When a re-run has identical data, transfer rows are preserved."""
        ingest_transfers(seeded_session, data_dir)
        before = {
            (t.player_id, t.transfer_date, t.from_club_id, t.to_club_id):
                (t.id, t.fee_eur, t.fee_is_loan, t.transfer_window, t.season)
            for t in seeded_session.query(Transfer).all()
        }
        ingest_transfers(seeded_session, data_dir)
        after = {
            (t.player_id, t.transfer_date, t.from_club_id, t.to_club_id):
                (t.id, t.fee_eur, t.fee_is_loan, t.transfer_window, t.season)
            for t in seeded_session.query(Transfer).all()
        }
        assert before == after


class TestIngestValuations:
    """Verify valuation ingestion with skip logic."""

    def test_inserts_valid_valuations(self, seeded_session, data_dir):
        """Valid valuations are inserted, invalid variants are skipped."""
        count = ingest_valuations(seeded_session, data_dir)
        # 3 fully valid; skipped: missing value, unknown player, missing date, empty id
        assert count == 3

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

    def test_skips_missing_date(self, seeded_session, data_dir):
        """Valuations with empty date are skipped."""
        ingest_valuations(seeded_session, data_dir)
        # Player 100 has two valid valuations (the one with missing date is skipped)
        p1_vals = seeded_session.query(PlayerValuation).filter(
            PlayerValuation.player_id == 1
        ).all()
        assert len(p1_vals) == 2

    def test_skips_unknown_player(self, seeded_session, data_dir):
        """Valuations referencing unknown players are skipped."""
        ingest_valuations(seeded_session, data_dir)
        all_player_ids = {v.player_id for v in seeded_session.query(PlayerValuation).all()}
        assert 999 not in all_player_ids

    def test_skips_empty_player_id(self, seeded_session, data_dir):
        """Valuations with empty player_id are skipped."""
        ingest_valuations(seeded_session, data_dir)
        # Only 3 valuations total; empty-id row did not create one
        assert seeded_session.query(PlayerValuation).count() == 3

    def test_upsert_updates_existing(self, seeded_session, data_dir):
        """Running ingest twice updates existing valuations without duplicating."""
        ingest_valuations(seeded_session, data_dir)
        ingest_valuations(seeded_session, data_dir)
        assert seeded_session.query(PlayerValuation).count() == 3

    def test_unchanged_value_preserves_data(self, seeded_session, data_dir):
        """When a re-run has identical values, rows remain correct (no-op UPDATE)."""
        ingest_valuations(seeded_session, data_dir)
        # Snapshot IDs and values
        before = {
            (v.player_id, v.valuation_date): (v.id, v.valuation_eur)
            for v in seeded_session.query(PlayerValuation).all()
        }
        # Re-run with same data — all rows should be "unchanged"
        ingest_valuations(seeded_session, data_dir)
        after = {
            (v.player_id, v.valuation_date): (v.id, v.valuation_eur)
            for v in seeded_session.query(PlayerValuation).all()
        }
        # IDs and values must match exactly — no rows modified
        assert before == after

    def test_changed_value_updates_record(self, seeded_session, data_dir, tmp_path):
        """When a valuation's value changes between runs, the record is updated."""
        from tests.conftest import write_csv

        ingest_valuations(seeded_session, data_dir)
        original = seeded_session.query(PlayerValuation).filter(
            PlayerValuation.player_id == 1,
            PlayerValuation.valuation_date == date(2023, 6, 1),
        ).first()
        assert original.valuation_eur == 6_000_000_000

        # Rewrite the valuations CSV with a different value for player 100 on 2023-06-01
        write_csv(data_dir / "player_valuations.csv", [
            "player_id", "date", "market_value_in_eur",
        ], [
            {"player_id": "100", "date": "2023-06-01", "market_value_in_eur": "99000000.0"},
        ])
        ingest_valuations(seeded_session, data_dir)
        updated = seeded_session.query(PlayerValuation).filter(
            PlayerValuation.player_id == 1,
            PlayerValuation.valuation_date == date(2023, 6, 1),
        ).first()
        assert updated.valuation_eur == 9_900_000_000  # 99M * 100


class TestSchemaValidation:
    """Verify ingest functions fail fast when upstream CSV schema changes."""

    def test_transfers_missing_required_column_raises(self, seeded_session, data_dir):
        """Removing a required column from transfers.csv raises SchemaValidationError."""
        from tests.conftest import write_csv
        # Rewrite without `transfer_fee` — should fail fast
        write_csv(data_dir / "transfers.csv", [
            "player_id", "transfer_date", "transfer_season",
            "from_club_id", "to_club_id",
        ], [
            {"player_id": "100", "transfer_date": "2023-07-01",
             "transfer_season": "23/24", "from_club_id": "10", "to_club_id": "20"},
        ])
        with pytest.raises(SchemaValidationError, match="transfer_fee"):
            ingest_transfers(seeded_session, data_dir)

    def test_valuations_missing_required_column_raises(self, seeded_session, data_dir):
        """Removing a required column from player_valuations.csv raises SchemaValidationError."""
        from tests.conftest import write_csv
        write_csv(data_dir / "player_valuations.csv", [
            "player_id", "date",  # missing market_value_in_eur
        ], [
            {"player_id": "100", "date": "2023-06-01"},
        ])
        with pytest.raises(SchemaValidationError, match="market_value_in_eur"):
            ingest_valuations(seeded_session, data_dir)

    def test_players_missing_required_column_raises(self, db_session, data_dir):
        """Removing a required column from players.csv raises SchemaValidationError."""
        from tests.conftest import write_csv
        write_csv(data_dir / "players.csv", [
            "player_id", "name",  # missing several required columns
        ], [
            {"player_id": "100", "name": "Player One"},
        ])
        with pytest.raises(SchemaValidationError):
            ingest_players(db_session, data_dir)

    def test_extra_column_warns_but_succeeds(self, seeded_session, data_dir, caplog):
        """Unexpected new columns log a warning but don't fail the ingest."""
        from tests.conftest import write_csv
        import logging
        # Add an unexpected column to player_valuations
        write_csv(data_dir / "player_valuations.csv", [
            "player_id", "date", "market_value_in_eur", "new_upstream_field",
        ], [
            {"player_id": "100", "date": "2023-06-01",
             "market_value_in_eur": "60000000.0", "new_upstream_field": "foo"},
        ])
        with caplog.at_level(logging.WARNING):
            count = ingest_valuations(seeded_session, data_dir)
        assert count == 1
        assert any("new_upstream_field" in rec.message for rec in caplog.records)

    def test_valid_schema_passes_silently(self, seeded_session, data_dir, caplog):
        """When all required columns are present and nothing unexpected, no warnings."""
        import logging
        with caplog.at_level(logging.WARNING):
            ingest_transfers(seeded_session, data_dir)
        # No warnings about missing or unexpected columns
        schema_warnings = [r for r in caplog.records if "column" in r.message.lower()]
        assert schema_warnings == []


class TestFullPipelineE2E:
    """End-to-end pipeline test: runs all 5 ingest functions in sequence against
    fixture CSVs, starting from a minimal seed (countries + leagues only).

    This catches composition bugs that unit tests miss — ordering issues, FK
    resolution across steps, data flowing correctly from one function to the next.

    Does NOT exercise `rebuild_country_flows`/`rebuild_club_summaries` because
    their swap-table SQL uses PostgreSQL-specific features (ALTER INDEX RENAME,
    DROP CASCADE). Aggregation E2E requires a real PostgreSQL connection.
    """

    def test_full_ingest_chain_from_scratch(self, minimal_session, data_dir):
        """Run the full ingest chain and verify the resulting database state."""
        # Step 1: competitions — returns comp_id → (country_name, country_id) map
        comp_map = ingest_competitions(minimal_session, data_dir)
        assert "GB1" in comp_map
        assert "ES1" in comp_map
        assert comp_map["GB1"][0] == "England"
        assert comp_map["ES1"][0] == "Spain"

        # League transfermarkt_ids should be populated
        pl = minimal_session.query(League).filter(League.name == "Premier League").first()
        assert pl.transfermarkt_id == "GB1"

        # Step 2: players
        players_count = ingest_players(minimal_session, data_dir)
        assert players_count == 4  # fixture has 5 rows, one empty id

        # Step 3: clubs — uses the comp_map from step 1
        clubs_count = ingest_clubs(minimal_session, data_dir, comp_map)
        assert clubs_count == 5  # fixture has 6 rows, one empty id

        # Step 4: transfers — depends on players + clubs existing from steps 2 & 3
        transfers_count = ingest_transfers(minimal_session, data_dir)
        assert transfers_count == 4

        # Step 5: valuations — depends on players from step 2
        vals_count = ingest_valuations(minimal_session, data_dir)
        assert vals_count == 3

    def test_transfer_fks_resolve_correctly(self, minimal_session, data_dir):
        """Verify that transfers link to the correct players and clubs after full ingest."""
        comp_map = ingest_competitions(minimal_session, data_dir)
        ingest_players(minimal_session, data_dir)
        ingest_clubs(minimal_session, data_dir, comp_map)
        ingest_transfers(minimal_session, data_dir)

        # The €50M Player One transfer from Club A → Club B
        player_one = minimal_session.query(Player).filter(
            Player.transfermarkt_id == "100"
        ).first()
        club_a = minimal_session.query(Club).filter(Club.transfermarkt_id == "10").first()
        club_b = minimal_session.query(Club).filter(Club.transfermarkt_id == "20").first()

        t = minimal_session.query(Transfer).filter(
            Transfer.player_id == player_one.id,
            Transfer.transfer_date == date(2023, 7, 1),
        ).first()
        assert t is not None
        assert t.from_club_id == club_a.id
        assert t.to_club_id == club_b.id
        assert t.fee_eur == 5_000_000_000  # €50M in cents

    def test_valuation_fks_resolve_correctly(self, minimal_session, data_dir):
        """Verify valuations link to the correct players after full ingest."""
        comp_map = ingest_competitions(minimal_session, data_dir)
        ingest_players(minimal_session, data_dir)
        ingest_clubs(minimal_session, data_dir, comp_map)
        ingest_valuations(minimal_session, data_dir)

        player_one = minimal_session.query(Player).filter(
            Player.transfermarkt_id == "100"
        ).first()

        vals = minimal_session.query(PlayerValuation).filter(
            PlayerValuation.player_id == player_one.id
        ).order_by(PlayerValuation.valuation_date).all()
        assert len(vals) == 2
        assert vals[0].valuation_eur == 6_000_000_000  # €60M
        assert vals[1].valuation_eur == 5_500_000_000  # €55M

    def test_club_country_resolution_via_competition(self, minimal_session, data_dir):
        """Verify clubs are assigned to the correct country via their competition map."""
        comp_map = ingest_competitions(minimal_session, data_dir)
        ingest_clubs(minimal_session, data_dir, comp_map)

        # Club A plays in GB1 (Premier League) → should be England
        club_a = minimal_session.query(Club).filter(Club.transfermarkt_id == "10").first()
        england = minimal_session.query(Country).filter(Country.name == "England").first()
        assert club_a.country_id == england.id

        # Club B plays in ES1 (LaLiga) → should be Spain
        club_b = minimal_session.query(Club).filter(Club.transfermarkt_id == "20").first()
        spain = minimal_session.query(Country).filter(Country.name == "Spain").first()
        assert club_b.country_id == spain.id

    def test_rerun_is_idempotent(self, minimal_session, data_dir):
        """Running the full pipeline twice produces the same result as running it once."""
        comp_map = ingest_competitions(minimal_session, data_dir)
        ingest_players(minimal_session, data_dir)
        ingest_clubs(minimal_session, data_dir, comp_map)
        ingest_transfers(minimal_session, data_dir)
        ingest_valuations(minimal_session, data_dir)

        # Snapshot row counts
        first_run = {
            "players": minimal_session.query(Player).count(),
            "clubs": minimal_session.query(Club).count(),
            "transfers": minimal_session.query(Transfer).count(),
            "valuations": minimal_session.query(PlayerValuation).count(),
        }

        # Re-run everything
        comp_map = ingest_competitions(minimal_session, data_dir)
        ingest_players(minimal_session, data_dir)
        ingest_clubs(minimal_session, data_dir, comp_map)
        ingest_transfers(minimal_session, data_dir)
        ingest_valuations(minimal_session, data_dir)

        second_run = {
            "players": minimal_session.query(Player).count(),
            "clubs": minimal_session.query(Club).count(),
            "transfers": minimal_session.query(Transfer).count(),
            "valuations": minimal_session.query(PlayerValuation).count(),
        }

        assert first_run == second_run
