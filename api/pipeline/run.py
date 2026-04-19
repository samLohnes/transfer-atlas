"""Pipeline entry point — orchestrates all ingestion steps."""

import argparse
import logging
import sys
from pathlib import Path
from app.database import SessionLocal, engine
from app.models import PipelineMetadata
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
from pipeline.quality import log_report, run_quality_checks

# Add the api/ directory to sys.path so imports work when run as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _is_data_unchanged(commit_hash: str | None) -> bool:
    """Return True if the stored commit hash matches the given one (skip ingestion)."""
    if not commit_hash:
        return False
    session = SessionLocal()
    try:
        meta = session.query(PipelineMetadata).first()
        return meta is not None and meta.source_commit_hash == commit_hash
    finally:
        session.close()


def main() -> None:
    """Run the full data pipeline."""
    parser = argparse.ArgumentParser(description="TransferAtlas data pipeline")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run ingestion even if the source commit hash is unchanged",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code if any data quality check fails (default: log only)",
    )
    args = parser.parse_args()

    logger.info("=== TransferAtlas Data Pipeline ===")

    total_records = 0

    try:
        # Check source commit hash before downloading anything
        commit_hash = get_dataset_commit_hash()
        logger.info("Dataset commit: %s", commit_hash or "unknown")

        if not args.force and _is_data_unchanged(commit_hash):
            logger.info(
                "Source data unchanged (commit %s). Skipping ingestion. "
                "Pass --force to re-run.", commit_hash
            )
            return

        # Step 1: Fetch data
        logger.info("Step 1/8: Fetching datasets...")
        data_dir = fetch_datasets()

        # Step 2: Ingest competitions (resolves league transfermarkt_ids + builds comp→country map)
        logger.info("Step 2/8: Processing competitions...")
        session = SessionLocal()
        try:
            comp_country_map = ingest_competitions(session, data_dir)
        finally:
            session.close()

        # Step 3: Ingest players
        logger.info("Step 3/8: Ingesting players...")
        session = SessionLocal()
        try:
            total_records += ingest_players(session, data_dir)
        finally:
            session.close()

        # Step 4: Ingest clubs
        logger.info("Step 4/8: Ingesting clubs...")
        session = SessionLocal()
        try:
            total_records += ingest_clubs(session, data_dir, comp_country_map)
        finally:
            session.close()

        # Step 5: Ingest transfers
        logger.info("Step 5/8: Ingesting transfers...")
        session = SessionLocal()
        try:
            total_records += ingest_transfers(session, data_dir)
        finally:
            session.close()

        # Step 6: Ingest valuations
        logger.info("Step 6/8: Ingesting valuations...")
        session = SessionLocal()
        try:
            total_records += ingest_valuations(session, data_dir)
        finally:
            session.close()

        # Step 7: Rebuild aggregations
        logger.info("Step 7/8: Rebuilding aggregation tables...")
        rebuild_country_flows(engine)
        rebuild_club_summaries(engine)

        # Update metadata
        session = SessionLocal()
        try:
            update_metadata(session, total_records, commit_hash)
        finally:
            session.close()

        # Step 8: Data quality checks
        logger.info("Step 8/8: Running data quality checks...")
        session = SessionLocal()
        try:
            report = run_quality_checks(session)
            log_report(report)
            if args.strict and report.errors:
                logger.error(
                    "Pipeline completed with %d failing quality check(s). "
                    "--strict enabled → exiting with error code.",
                    len(report.errors),
                )
                sys.exit(2)
        finally:
            session.close()

        logger.info("=== Pipeline complete. %d total records processed. ===", total_records)

    except Exception:
        logger.exception("Pipeline failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
