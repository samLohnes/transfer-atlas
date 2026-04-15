"""Pre-aggregation of transfer data using swap-table pattern."""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def rebuild_country_flows(engine: Engine) -> None:
    """Rebuild the country_transfer_flows table using a swap pattern."""
    logger.info("Rebuilding country transfer flows...")

    with engine.begin() as conn:
        # Clean up any leftover tables from prior failed runs
        conn.execute(text("DROP TABLE IF EXISTS country_transfer_flows_new CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS country_transfer_flows_old CASCADE"))

        conn.execute(text("""
            CREATE TABLE country_transfer_flows_new (
                id SERIAL PRIMARY KEY,
                from_country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE RESTRICT,
                to_country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE RESTRICT,
                transfer_window VARCHAR(20) NOT NULL,
                total_fee_eur BIGINT NOT NULL DEFAULT 0,
                transfer_count INTEGER NOT NULL DEFAULT 0,
                loan_count INTEGER NOT NULL DEFAULT 0
            )
        """))

        conn.execute(text("""
            INSERT INTO country_transfer_flows_new
                (from_country_id, to_country_id, transfer_window, total_fee_eur, transfer_count, loan_count)
            SELECT
                fc.country_id AS from_country_id,
                tc.country_id AS to_country_id,
                t.transfer_window,
                COALESCE(SUM(CASE WHEN NOT t.fee_is_loan AND t.fee_eur IS NOT NULL THEN t.fee_eur ELSE 0 END), 0),
                COUNT(*) FILTER (WHERE NOT t.fee_is_loan),
                COUNT(*) FILTER (WHERE t.fee_is_loan)
            FROM transfers t
            JOIN clubs fc ON t.from_club_id = fc.id
            JOIN clubs tc ON t.to_club_id = tc.id
            GROUP BY fc.country_id, tc.country_id, t.transfer_window
        """))

        conn.execute(text("""
            CREATE UNIQUE INDEX uq_country_flow_swap
            ON country_transfer_flows_new (from_country_id, to_country_id, transfer_window)
        """))

        # Swap atomically
        conn.execute(text("ALTER TABLE country_transfer_flows RENAME TO country_transfer_flows_old"))
        conn.execute(text("ALTER TABLE country_transfer_flows_new RENAME TO country_transfer_flows"))
        conn.execute(text("DROP TABLE country_transfer_flows_old CASCADE"))

        # Rename index to canonical name
        conn.execute(text("ALTER INDEX IF EXISTS uq_country_flow_swap RENAME TO uq_country_flow"))

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM country_transfer_flows")).scalar()
    logger.info("Country transfer flows rebuilt: %d rows.", count)


def rebuild_club_summaries(engine: Engine) -> None:
    """Rebuild the club_transfer_summaries table using a swap pattern."""
    logger.info("Rebuilding club transfer summaries...")

    with engine.begin() as conn:
        # Clean up any leftover tables from prior failed runs
        conn.execute(text("DROP TABLE IF EXISTS club_transfer_summaries_new CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS club_transfer_summaries_old CASCADE"))

        conn.execute(text("""
            CREATE TABLE club_transfer_summaries_new (
                id SERIAL PRIMARY KEY,
                club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE RESTRICT,
                transfer_window VARCHAR(20) NOT NULL,
                total_spent_eur BIGINT NOT NULL DEFAULT 0,
                total_received_eur BIGINT NOT NULL DEFAULT 0,
                players_bought INTEGER NOT NULL DEFAULT 0,
                players_sold INTEGER NOT NULL DEFAULT 0
            )
        """))

        conn.execute(text("""
            INSERT INTO club_transfer_summaries_new
                (club_id, transfer_window, total_spent_eur, total_received_eur, players_bought, players_sold)
            SELECT
                club_id,
                transfer_window,
                COALESCE(SUM(spent), 0),
                COALESCE(SUM(received), 0),
                COALESCE(SUM(bought), 0),
                COALESCE(SUM(sold), 0)
            FROM (
                SELECT
                    t.to_club_id AS club_id,
                    t.transfer_window,
                    CASE WHEN NOT t.fee_is_loan AND t.fee_eur IS NOT NULL THEN t.fee_eur ELSE 0 END AS spent,
                    0 AS received,
                    1 AS bought,
                    0 AS sold
                FROM transfers t
                UNION ALL
                SELECT
                    t.from_club_id AS club_id,
                    t.transfer_window,
                    0 AS spent,
                    CASE WHEN NOT t.fee_is_loan AND t.fee_eur IS NOT NULL THEN t.fee_eur ELSE 0 END AS received,
                    0 AS bought,
                    1 AS sold
                FROM transfers t
            ) combined
            GROUP BY club_id, transfer_window
        """))

        conn.execute(text("""
            CREATE UNIQUE INDEX uq_club_summary_swap
            ON club_transfer_summaries_new (club_id, transfer_window)
        """))

        # Swap
        conn.execute(text("ALTER TABLE club_transfer_summaries RENAME TO club_transfer_summaries_old"))
        conn.execute(text("ALTER TABLE club_transfer_summaries_new RENAME TO club_transfer_summaries"))
        conn.execute(text("DROP TABLE club_transfer_summaries_old CASCADE"))

        # Rename index
        conn.execute(text("ALTER INDEX IF EXISTS uq_club_summary_swap RENAME TO uq_club_summary"))

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM club_transfer_summaries")).scalar()
    logger.info("Club transfer summaries rebuilt: %d rows.", count)
