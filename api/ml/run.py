"""CLI entry point for the grading pipeline.

Run with: `python -m ml.run [--dry-run] [--recalibrate]`

Flags:
    --dry-run       Compute scores and log the grade distribution without
                    writing to the database. Useful for previewing the effect
                    of config changes before activating a new ScoringVersion.

    --recalibrate   Force fresh calibration of the value-trajectory annual
                    rates from PlayerValuation history, ignoring the cache on
                    the currently-active ScoringVersion. Default behaviour:
                    reuse cached rates when present.
"""

import argparse
import logging
import sys

from app.database import SessionLocal
from ml.grade import grade_all


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute and persist transfer grades for every qualifying TransferFeature row."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and log grades without writing to the database.",
    )
    parser.add_argument(
        "--recalibrate",
        action="store_true",
        help="Force fresh value-trajectory rate calibration from PlayerValuation history.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.info(
        "=== Grading pipeline (dry_run=%s, recalibrate=%s) ===",
        args.dry_run, args.recalibrate,
    )

    session = SessionLocal()
    try:
        n = grade_all(session, dry_run=args.dry_run, recalibrate=args.recalibrate)
        logger.info("=== Pipeline complete. %d grades produced. ===", n)
    except Exception:
        logger.exception("Grading pipeline failed.")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
