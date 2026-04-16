"""Benchmark: iterrows vs itertuples + chunked reads on synthetic data.

Run: python3 tests/bench_ingest.py
"""

import csv
import tempfile
import time
from pathlib import Path

import pandas as pd


def generate_synthetic_csv(path: Path, n_rows: int) -> None:
    """Generate a transfers-shaped CSV with n_rows rows."""
    fieldnames = [
        "player_id", "transfer_date", "transfer_season", "from_club_id",
        "to_club_id", "from_club_name", "to_club_name", "transfer_fee",
        "market_value_in_eur", "player_name",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n_rows):
            writer.writerow({
                "player_id": str(i % 50000),
                "transfer_date": "2023-07-01",
                "transfer_season": "23/24",
                "from_club_id": str(i % 1000),
                "to_club_id": str((i + 500) % 1000),
                "from_club_name": f"Club {i % 1000}",
                "to_club_name": f"Club {(i + 500) % 1000}",
                "transfer_fee": f"{(i * 100000) % 50000000}.000" if i % 3 != 0 else "",
                "market_value_in_eur": f"{(i * 200000) % 80000000}.000",
                "player_name": f"Player {i}",
            })


def bench_iterrows(csv_path: Path) -> tuple[int, float]:
    """Old approach: read_csv + iterrows."""
    df = pd.read_csv(csv_path, low_memory=False)
    count = 0
    t0 = time.perf_counter()
    for _, row in df.iterrows():
        # Simulate field access pattern from ingest_transfers
        _ = str(row.get("transfer_fee", "")) if pd.notna(row.get("transfer_fee")) else None
        _ = str(int(row["player_id"])) if pd.notna(row.get("player_id")) else None
        _ = str(int(row["from_club_id"])) if pd.notna(row.get("from_club_id")) else None
        _ = str(int(row["to_club_id"])) if pd.notna(row.get("to_club_id")) else None
        _ = str(row.get("transfer_season", "")) if pd.notna(row.get("transfer_season")) else None
        count += 1
    elapsed = time.perf_counter() - t0
    return count, elapsed


def bench_itertuples_chunked(csv_path: Path, chunk_size: int = 10_000) -> tuple[int, float]:
    """New approach: read_csv(chunksize) + itertuples."""
    count = 0
    t0 = time.perf_counter()
    for chunk in pd.read_csv(csv_path, low_memory=False, chunksize=chunk_size):
        for row in chunk.itertuples(index=False):
            # Same field access pattern, using getattr
            val = getattr(row, "transfer_fee", None)
            _ = str(val) if pd.notna(val) and val != "" else None
            val = getattr(row, "player_id", None)
            _ = str(int(val)) if pd.notna(val) else None
            val = getattr(row, "from_club_id", None)
            _ = str(int(val)) if pd.notna(val) else None
            val = getattr(row, "to_club_id", None)
            _ = str(int(val)) if pd.notna(val) else None
            val = getattr(row, "transfer_season", None)
            _ = str(val) if pd.notna(val) and val != "" else None
            count += 1
    elapsed = time.perf_counter() - t0
    return count, elapsed


def main() -> None:
    """Run benchmarks at multiple scales."""
    for n_rows in [10_000, 100_000, 500_000]:
        print(f"\n{'='*50}")
        print(f"  {n_rows:,} rows")
        print(f"{'='*50}")

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "transfers.csv"
            generate_synthetic_csv(csv_path, n_rows)
            size_mb = csv_path.stat().st_size / 1024 / 1024
            print(f"  CSV size: {size_mb:.1f} MB")

            count_old, t_old = bench_iterrows(csv_path)
            print(f"  iterrows:          {t_old:6.2f}s  ({count_old:,} rows)")

            count_new, t_new = bench_itertuples_chunked(csv_path)
            print(f"  itertuples+chunked:{t_new:6.2f}s  ({count_new:,} rows)")

            speedup = t_old / t_new if t_new > 0 else float("inf")
            print(f"  Speedup: {speedup:.1f}x")


if __name__ == "__main__":
    main()
