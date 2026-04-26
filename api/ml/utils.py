"""Pure-math helpers for the scoring pipeline.

No DB access, no I/O — every function here is deterministic and side-effect-free
so it's trivial to unit test and reason about.
"""

import math
from decimal import Decimal

import numpy as np

# Letter-grade boundaries (inclusive lower bound). Score must be in [0, 100].
LETTER_GRADE_BANDS = [
    (Decimal("85"), "A"),
    (Decimal("78"), "B+"),
    (Decimal("70"), "B"),
    (Decimal("62"), "C+"),
    (Decimal("55"), "C"),
    (Decimal("40"), "D"),
    (Decimal("0"), "F"),
]

# `worth_the_fee` threshold mirrors the C lower bound (chosen by the user — see plans/phase2/main.md).
WORTH_THE_FEE_THRESHOLD = Decimal("55")


def sigmoid_to_100(value: float, scale: float) -> float:
    """Logistic sigmoid scaled to a 0-100 score.

    `1 / (1 + exp(-scale * value)) * 100`. At value == 0 returns 50.

    Used for value_trajectory_score (scale 0.05) and financial_return_score
    (scale 2.0), per scoring_config.json. Values clamped before exp() to avoid
    overflow on extreme outliers.
    """
    z = max(-500.0, min(500.0, scale * value))
    return 100.0 / (1.0 + math.exp(-z))


def weighted_average(components: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Weighted average over the non-None components only.

    Weights of NULL components are dropped and the remaining weights re-normalize
    implicitly (we divide by the sum of the still-present weights). This is how
    the pipeline handles GK transfers (production omitted), in-progress transfers
    (financial_return omitted), and players with no valuation data
    (value_trajectory omitted).

    Returns None when every component is NULL — caller decides what to do (either
    skip the row or treat as ungradeable).
    """
    num = 0.0
    den = 0.0
    for k, v in components.items():
        if v is None:
            continue
        w = weights.get(k, 0.0)
        if w <= 0:
            continue
        num += v * w
        den += w
    if den == 0:
        return None
    return num / den


def percentile_rank(value: float, distribution: np.ndarray) -> float | None:
    """Mean-rank percentile of `value` within an ascending-sorted distribution.

    Matches `scipy.stats.percentileofscore(..., kind='mean')`: averages the
    strict-less and ≤ ranks, scaled to 100. The median of a 5-element array
    therefore lands at exactly the 50th percentile, which is what the scoring
    layer assumes when bucketing into fee tiers and reporting "Nth percentile".
    """
    if distribution.size == 0:
        return None
    strict = int(np.searchsorted(distribution, value, side="left"))
    inclusive = int(np.searchsorted(distribution, value, side="right"))
    return ((strict + inclusive) / 2 / distribution.size) * 100.0


def derive_letter_grade(composite: Decimal | float) -> str:
    """Map a 0-100 composite score to its letter grade per plan §main.md."""
    s = composite if isinstance(composite, Decimal) else Decimal(str(composite))
    for floor, letter in LETTER_GRADE_BANDS:
        if s >= floor:
            return letter
    return "F"


def is_worth_the_fee(composite: Decimal | float) -> bool:
    """True when the composite clears the C threshold (>= 55). Mirrors plan §main.md."""
    s = composite if isinstance(composite, Decimal) else Decimal(str(composite))
    return s >= WORTH_THE_FEE_THRESHOLD


def clip_score(value: float) -> float:
    """Clip any computed score to the [0, 100] band before persistence."""
    return max(0.0, min(100.0, value))
