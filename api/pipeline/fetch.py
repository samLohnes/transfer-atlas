"""Download Transfermarkt Datasets CSV files."""

import gzip
import logging
import shutil
import subprocess
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "transfermarkt-datasets"

# CSV files to download from the dataset repo
CSV_FILES = [
    "transfers",
    "players",
    "clubs",
    "competitions",
    "player_valuations",
]

BASE_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"


def fetch_datasets() -> Path:
    """Download all required CSV files and return the data directory path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for name in CSV_FILES:
        csv_path = DATA_DIR / f"{name}.csv"
        url = f"{BASE_URL}/{name}.csv.gz"
        logger.info("Downloading %s ...", name)

        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()

        gz_path = DATA_DIR / f"{name}.csv.gz"
        with open(gz_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Decompress
        with gzip.open(gz_path, "rb") as gz_in, open(csv_path, "wb") as csv_out:
            shutil.copyfileobj(gz_in, csv_out)

        gz_path.unlink()
        logger.info("  → %s ready (%d bytes)", name, csv_path.stat().st_size)

    return DATA_DIR


def get_dataset_commit_hash() -> str | None:
    """Get the latest commit hash of the dataset repo's master branch."""
    try:
        resp = requests.get(
            "https://api.github.com/repos/dcaribou/transfermarkt-datasets/commits/master",
            headers={"Accept": "application/vnd.github.sha"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.text.strip()[:40]
    except Exception:
        logger.warning("Could not fetch dataset commit hash")
    return None
