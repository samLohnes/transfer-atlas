"""Natural language explanation strings for the four scoring components,
plus a one-line summary used by the API's grades-rankings endpoint.

All templates are short (< ~100 chars where practical) and intentionally simple
to keep the rendering deterministic. The summary generator picks the strongest
positive or negative signal from the components and pairs it with a financial
outcome (for complete transfers) or a tenure phrase (for in-progress).
"""

from __future__ import annotations

from decimal import Decimal


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_fee_eur(cents: int | None) -> str:
    """Render an EUR-cent amount as a compact human string ('€75M', '€1.5M', '€500K').

    Mirrors the web frontend's `formatFee` semantics for backend-rendered text.
    """
    if cents is None:
        return "—"
    eur = cents / 100
    abs_eur = abs(eur)
    sign = "-" if eur < 0 else ""
    if abs_eur >= 1_000_000:
        whole = abs_eur / 1_000_000
        if whole >= 100 or whole == int(whole):
            return f"{sign}€{int(whole)}M"
        return f"{sign}€{whole:.1f}M"
    if abs_eur >= 1_000:
        return f"{sign}€{int(abs_eur / 1_000)}K"
    return f"{sign}€{abs_eur:.0f}"


def _pct(value: Decimal | float | None, decimals: int = 0) -> str:
    """Render a numeric percentage compactly ('87%', '12.5%')."""
    if value is None:
        return "—"
    f = float(value)
    if decimals == 0:
        return f"{int(round(f))}%"
    return f"{f:.{decimals}f}%"


# ---------------------------------------------------------------------------
# Component explanations
# ---------------------------------------------------------------------------


def explain_minutes(minutes_pct: Decimal | float | None) -> str | None:
    """Tier the minutes_pct into one of four template buckets, or None if missing."""
    if minutes_pct is None:
        return None
    pct = float(minutes_pct)
    pct_text = _pct(pct)
    if pct > 80:
        return f"First-choice starter, played {pct_text} of minutes"
    if pct >= 50:
        return f"Regular contributor, played {pct_text} of available minutes"
    if pct >= 30:
        return f"Rotation player, {pct_text} of available minutes"
    return f"Peripheral player, only {pct_text} of available minutes"


def explain_production(
    is_goalkeeper: bool,
    goal_contributions_per_90: Decimal | float | None,
    percentile: float | None,
    position_group: str | None,
    fee_tier_label: str | None,
) -> str | None:
    """Production explanation. None when there is genuinely no data; specific GK message otherwise."""
    if is_goalkeeper:
        return "Production N/A for goalkeepers — evaluated on availability"
    if goal_contributions_per_90 is None or percentile is None:
        return None
    ga = float(goal_contributions_per_90)
    pos = position_group or "?"
    tier = fee_tier_label or "—"
    return f"{ga:.2f} G+A/90, {int(round(percentile))}th percentile for {pos} in {tier} tier"


def explain_value_trajectory(
    value_change_pct: Decimal | float | None,
    expected_value_change_pct: float | None,
    value_at_transfer_cents: int | None,
    value_at_departure_cents: int | None,
    tenure_days: int | None,
) -> str | None:
    """Spec-defined four-quadrant template based on (actual, expected) percent comparison."""
    if value_change_pct is None or expected_value_change_pct is None:
        return "No valuation data available"

    actual = float(value_change_pct)
    expected = float(expected_value_change_pct)
    diff = actual - expected
    abs_diff_text = f"{abs(diff):.0f}"

    if actual > 0 and diff >= 0:
        formatted_start = format_fee_eur(value_at_transfer_cents)
        formatted_end = format_fee_eur(value_at_departure_cents)
        return (
            f"Market value up {actual:.0f}% ({formatted_start} → {formatted_end}), "
            f"{abs_diff_text}% above expected"
        )
    if actual > 0 and diff < 0:
        return f"Market value up {actual:.0f}%, but {abs_diff_text}% below expected for age profile"
    if actual <= 0 and diff > 0:
        return (
            f"Market value down {abs(actual):.0f}%, but {abs_diff_text}% above expected for age profile"
        )
    # actual <= 0 and diff <= 0 → declined and underperformed
    tenure_years_text = (
        f"{(tenure_days / 365.25):.1f}-year" if tenure_days else "this"
    )
    return f"Market value declined {abs(actual):.0f}% during {tenure_years_text} stint"


def explain_financial_return(
    is_complete: bool,
    exit_fee_ratio: Decimal | float | None,
    expected_exit_ratio: Decimal | float | None,
    exit_ratio_vs_expected: Decimal | float | None,
    age_at_departure: Decimal | float | None,
) -> str | None:
    """Financial return explanation. Distinguishes in-progress, missing-data, and complete cases."""
    if not is_complete:
        return "Transfer still in progress — no exit value yet"
    if exit_fee_ratio is None or expected_exit_ratio is None:
        return None

    actual = float(exit_fee_ratio) * 100
    expected = float(expected_exit_ratio) * 100
    age_text = f"{float(age_at_departure):.1f}" if age_at_departure is not None else "—"
    base = f"Sold for {actual:.0f}% of purchase price at age {age_text} (expected: {expected:.0f}%)"
    if exit_ratio_vs_expected is not None:
        delta = float(exit_ratio_vs_expected)
        if delta > 0:
            return base + " — above expectations"
        if delta < 0:
            return base + " — below expectations"
    return base


# ---------------------------------------------------------------------------
# One-line summary (used by the rankings API in Task 5)
# ---------------------------------------------------------------------------


def generate_summary_line(
    is_complete: bool,
    minutes_score: float | None,
    production_score: float | None,
    value_trajectory_score: float | None,
    financial_return_score: float | None,
    minutes_pct: Decimal | float | None,
    goals: int | None,
    assists: int | None,
    value_change_pct: Decimal | float | None,
    exit_fee_ratio: Decimal | float | None,
    tenure_days: int | None,
) -> str:
    """Two-clause summary: the most extreme component, then a financial/tenure clause.

    Heuristic-based per spec — pick the highest- or lowest-signal component as
    the lead clause, and append a financial outcome (complete) or tenure
    (in-progress) clause.
    """
    # Find the most extreme component score (most positive or most negative wrt 50)
    candidates = {
        "minutes": minutes_score,
        "production": production_score,
        "value_trajectory": value_trajectory_score,
        "financial_return": financial_return_score,
    }
    extreme_key: str | None = None
    extreme_distance = -1.0
    for k, v in candidates.items():
        if v is None:
            continue
        d = abs(v - 50.0)
        if d > extreme_distance:
            extreme_distance = d
            extreme_key = k

    lead = _summary_lead(
        extreme_key, candidates,
        minutes_pct=minutes_pct, goals=goals, assists=assists,
        value_change_pct=value_change_pct,
    )
    tail = _summary_tail(
        is_complete=is_complete,
        exit_fee_ratio=exit_fee_ratio,
        tenure_days=tenure_days,
        value_change_pct=value_change_pct,
    )
    if not lead and not tail:
        return "Insufficient data"
    if not lead:
        return tail
    if not tail:
        return lead
    return f"{lead}, {tail}"


def _summary_lead(
    extreme_key: str | None,
    candidates: dict[str, float | None],
    *,
    minutes_pct,
    goals,
    assists,
    value_change_pct,
) -> str | None:
    """Render the leading clause based on which component had the strongest signal."""
    if extreme_key == "minutes" and minutes_pct is not None:
        pct = float(minutes_pct)
        if pct < 30:
            return f"Only {pct:.0f}% of minutes played"
        return f"Played {pct:.0f}% of minutes"
    if extreme_key == "production" and (goals is not None or assists is not None):
        g = goals or 0
        a = assists or 0
        if g + a == 0:
            return "0 goals or assists"
        return f"{g} goals, {a} assists"
    if extreme_key == "value_trajectory" and value_change_pct is not None:
        v = float(value_change_pct)
        if v >= 100:
            return "Market value more than doubled"
        if v >= 50:
            return f"Market value up {v:.0f}%"
        if v <= -40:
            return f"Market value dropped {abs(v):.0f}%"
        if v <= 0:
            return f"Market value held flat ({v:.0f}%)"
        return f"Market value up {v:.0f}%"
    if extreme_key == "financial_return":
        return None  # handled by tail clause when complete
    return None


def _summary_tail(
    *,
    is_complete: bool,
    exit_fee_ratio,
    tenure_days,
    value_change_pct,
) -> str | None:
    """Render the trailing clause: financial outcome (complete) or tenure (in-progress)."""
    if is_complete and exit_fee_ratio is not None:
        ratio_pct = float(exit_fee_ratio) * 100
        if ratio_pct >= 150:
            return f"sold for {int(ratio_pct)}% of purchase price"
        if ratio_pct >= 100:
            return f"sold for {int(ratio_pct)}% of fee"
        if ratio_pct > 0:
            return f"sold at {int(100 - ratio_pct)}% loss"
        return "sold for free"
    if not is_complete and tenure_days:
        years = tenure_days / 365.25
        return f"after {years:.0f} year{'s' if years >= 1.5 else ''} (still at club)"
    return None
