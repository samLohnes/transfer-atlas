"""Grade-distribution validator + histogram generator.

Reads the active ScoringVersion and the TransferGrade table, prints a summary
of the global distribution + per-position breakdowns + per-component score
stats, and flags configurable health checks (concentration, tails, balance).

Run with: `python -m ml.validate [--histogram path/to/out.png]`
"""

import argparse
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ScoringVersion, TransferFeature, TransferGrade

logger = logging.getLogger(__name__)

LETTER_ORDER = ["A", "B+", "B", "C+", "C", "D", "F"]

# Health checks the validator flags as warnings (per task-09 spec).
MIN_TAIL_PCT = 5.0           # at least 5% of grades in A *and* in F
MAX_LETTER_CONCENTRATION = 40.0  # no single letter > 40% of total
HEALTHY_MEAN_RANGE = (50.0, 65.0)


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------


def _fetch_active_version(session: Session) -> ScoringVersion | None:
    return session.query(ScoringVersion).filter(ScoringVersion.is_active.is_(True)).first()


def _fetch_grades(session: Session) -> list[tuple]:
    """Pulls grade rows joined with feature.position_group for per-position breakdowns."""
    return (
        session.query(
            TransferGrade.composite_score,
            TransferGrade.letter_grade,
            TransferGrade.is_complete,
            TransferGrade.minutes_score,
            TransferGrade.production_score,
            TransferGrade.value_trajectory_score,
            TransferGrade.financial_return_score,
            TransferFeature.position_group,
        )
        .outerjoin(TransferFeature, TransferFeature.transfer_id == TransferGrade.transfer_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Distribution analysis
# ---------------------------------------------------------------------------


def _summarise(rows: list[tuple]) -> dict:
    """Compute the headline distribution statistics from the raw rows."""
    if not rows:
        return {"total": 0}

    composites = np.array([float(r[0]) for r in rows])
    letter_counts = Counter(r[1] for r in rows)
    completion = Counter("complete" if r[2] else "in_progress" for r in rows)

    by_position: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r[7] is not None:
            by_position[r[7]].append(float(r[0]))

    components: dict[str, list[float]] = {"minutes": [], "production": [], "value_trajectory": [], "financial_return": []}
    null_counts: dict[str, int] = {k: 0 for k in components}
    for _comp, _letter, _done, m, p, v, f, _pg in rows:
        for key, val in (("minutes", m), ("production", p), ("value_trajectory", v), ("financial_return", f)):
            if val is None:
                null_counts[key] += 1
            else:
                components[key].append(float(val))

    return {
        "total": len(rows),
        "composites": composites,
        "letter_counts": letter_counts,
        "completion": completion,
        "by_position": by_position,
        "components": components,
        "null_counts": null_counts,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> None:
    """Print an ASCII table aligned by the widest cell in each column."""
    cols = list(zip(*([headers] + rows)))
    widths = [max(len(str(cell)) for cell in col) for col in cols]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for r in rows:
        print(fmt.format(*r))


def _report(summary: dict, version: ScoringVersion | None) -> list[str]:
    """Print the distribution report and return a list of warning strings."""
    warnings: list[str] = []

    if summary["total"] == 0:
        msg = "No graded transfers found. Has the grading pipeline been run?"
        warnings.append(msg)
        print(msg)
        return warnings

    composites: np.ndarray = summary["composites"]
    total = summary["total"]

    print()
    print("=" * 64)
    print("Grade distribution validation")
    print("=" * 64)
    if version:
        print(f"Active version: {version.version}  ({total} grades, scored {version.scored_at:%Y-%m-%d %H:%M UTC})")
    else:
        print(f"WARNING: no active ScoringVersion. {total} grades but no version metadata.")
        warnings.append("No active ScoringVersion.")
    print()

    print(f"Mean:    {composites.mean():.2f}")
    print(f"Median:  {np.median(composites):.2f}")
    print(f"Stddev:  {composites.std():.2f}")
    completion = summary["completion"]
    print(f"Complete vs in-progress: {completion.get('complete', 0)} / {completion.get('in_progress', 0)}")
    print()

    print("Letter distribution:")
    rows = []
    for letter in LETTER_ORDER:
        n = summary["letter_counts"].get(letter, 0)
        pct = (n / total) * 100
        bar = "█" * int(pct / 2)  # 1 block per 2%
        rows.append((letter, str(n), f"{pct:5.1f}%", bar))
    _print_table(rows, ("grade", "n", "pct", "bar"))
    print()

    # Per-position breakdown
    pos_rows = []
    for pg in ("GK", "DEF", "MID", "FWD"):
        scores = summary["by_position"].get(pg, [])
        if not scores:
            pos_rows.append((pg, "0", "—", "—", "—"))
            continue
        arr = np.array(scores)
        pos_rows.append((
            pg, str(len(scores)), f"{arr.mean():.2f}", f"{np.median(arr):.2f}", f"{arr.std():.2f}",
        ))
    print("Per-position composite stats:")
    _print_table(pos_rows, ("pg", "n", "mean", "median", "stddev"))
    print()

    # Component coverage + means
    comp_rows = []
    for key in ("minutes", "production", "value_trajectory", "financial_return"):
        vals = summary["components"][key]
        nulls = summary["null_counts"][key]
        n = len(vals)
        coverage_pct = (n / total) * 100
        if vals:
            arr = np.array(vals)
            comp_rows.append((
                key, str(n), f"{coverage_pct:5.1f}%", str(nulls),
                f"{arr.mean():.2f}", f"{arr.std():.2f}",
            ))
        else:
            comp_rows.append((key, "0", "0.0%", str(nulls), "—", "—"))
    print("Component scores:")
    _print_table(comp_rows, ("component", "n", "coverage", "nulls", "mean", "stddev"))
    print()

    # Health checks
    a_pct = (summary["letter_counts"].get("A", 0) / total) * 100
    f_pct = (summary["letter_counts"].get("F", 0) / total) * 100
    if a_pct < MIN_TAIL_PCT:
        warnings.append(f"A-grade tail thin: {a_pct:.1f}% (< {MIN_TAIL_PCT}% target). Scoring may be too conservative.")
    if f_pct < MIN_TAIL_PCT:
        warnings.append(f"F-grade tail thin: {f_pct:.1f}% (< {MIN_TAIL_PCT}% target). Scoring may be too generous.")

    top_letter, top_n = summary["letter_counts"].most_common(1)[0]
    top_pct = (top_n / total) * 100
    if top_pct > MAX_LETTER_CONCENTRATION:
        warnings.append(
            f"Distribution concentrated: {top_letter} = {top_pct:.1f}% (> {MAX_LETTER_CONCENTRATION}% target). "
            "Consider tuning sigmoid scales / weights."
        )

    mean = composites.mean()
    if mean < HEALTHY_MEAN_RANGE[0] or mean > HEALTHY_MEAN_RANGE[1]:
        warnings.append(
            f"Mean composite ({mean:.1f}) outside healthy range {HEALTHY_MEAN_RANGE}. "
            "Calibrated rates or sigmoid scales may need adjustment."
        )

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("All health checks passed.")
    print()

    return warnings


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------


def _save_histogram(composites: np.ndarray, out_path: Path) -> None:
    """Render a 0-100 histogram with letter-grade boundary markers."""
    import matplotlib

    matplotlib.use("Agg")  # headless
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(composites, bins=50, color="#4ade80", edgecolor="#0e1f16", alpha=0.85)
    ax.set_xlabel("Composite score")
    ax.set_ylabel("Count")
    ax.set_title("Transfer grade distribution")
    ax.set_xlim(0, 100)

    # Letter-band markers
    band_colours = [
        (40, "#f97316", "D"),
        (55, "#fbbf24", "C"),
        (62, "#f59e0b", "C+"),
        (70, "#2dd4bf", "B"),
        (78, "#14b8a6", "B+"),
        (85, "#22c55e", "A"),
    ]
    for x, colour, label in band_colours:
        ax.axvline(x, color=colour, linestyle="--", alpha=0.55)
        ax.text(x, ax.get_ylim()[1] * 0.96, label, ha="center", va="top", fontsize=9, color=colour)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"Histogram written to {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the transfer grade distribution.")
    parser.add_argument(
        "--histogram",
        type=Path,
        default=None,
        help="Path to write a histogram PNG (e.g. api/models/grade_distribution.png).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any health check fails (useful for CI gating).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")

    session = SessionLocal()
    try:
        version = _fetch_active_version(session)
        rows = _fetch_grades(session)
        summary = _summarise(rows)
        warnings = _report(summary, version)
        if args.histogram and summary["total"] > 0:
            _save_histogram(summary["composites"], args.histogram)
    finally:
        session.close()

    return 1 if (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
