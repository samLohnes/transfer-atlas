"""Pipeline entry point — orchestrates all ingestion steps."""

import logging
import sys
from pathlib import Path

# Add the api/ directory to sys.path so imports work when run as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine
from pipeline.aggregate import rebuild_club_summaries, rebuild_country_flows
from pipeline.fetch import fetch_datasets, get_dataset_commit_hash
from pipeline.ingest import (
    ingest_clubs,
    ingest_competitions,
    ingest_players,
    ingest_transfers,
    ingest_valuations,
    update_metadata,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the full data pipeline."""
    logger.info("=== TransferAtlas Data Pipeline ===")

    total_records = 0

    try:
        # Step 1: Fetch data
        logger.info("Step 1/7: Fetching datasets...")
        data_dir = fetch_datasets()
        commit_hash = get_dataset_commit_hash()
        logger.info("Dataset commit: %s", commit_hash or "unknown")

        # Step 2: Ingest competitions (resolves league transfermarkt_ids + builds comp→country map)
        logger.info("Step 2/7: Processing competitions...")
        session = SessionLocal()
        try:
            comp_country_map = ingest_competitions(session, data_dir)
        finally:
            session.close()

        # Step 3: Ingest players
        logger.info("Step 3/7: Ingesting players...")
        session = SessionLocal()
        try:
            total_records += ingest_players(session, data_dir)
        finally:
            session.close()

        # Step 4: Ingest clubs
        logger.info("Step 4/7: Ingesting clubs...")
        session = SessionLocal()
        try:
            total_records += ingest_clubs(session, data_dir, comp_country_map)
        finally:
            session.close()

        # Step 5: Ingest transfers
        logger.info("Step 5/7: Ingesting transfers...")
        session = SessionLocal()
        try:
            total_records += ingest_transfers(session, data_dir)
        finally:
            session.close()

        # Step 6: Ingest valuations
        logger.info("Step 6/7: Ingesting valuations...")
        session = SessionLocal()
        try:
            total_records += ingest_valuations(session, data_dir)
        finally:
            session.close()

        # Step 7: Rebuild aggregations
        logger.info("Step 7/7: Rebuilding aggregation tables...")
        rebuild_country_flows(engine)
        rebuild_club_summaries(engine)

        # Update metadata
        session = SessionLocal()
        try:
            update_metadata(session, total_records, commit_hash)
        finally:
            session.close()

        logger.info("=== Pipeline complete. %d total records processed. ===", total_records)

    except Exception:
        logger.exception("Pipeline failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
