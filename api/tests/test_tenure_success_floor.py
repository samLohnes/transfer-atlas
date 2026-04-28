"""Tenure-success floor on value_trajectory and financial_return components."""

from types import SimpleNamespace

from ml.scoring import score_financial_return, score_value_trajectory


def _feature(tenure_days, minutes_pct, **kw):
    """Minimal SimpleNamespace stub of TransferFeature for the floor tests."""
    base = dict(
        tenure_days=tenure_days,
        minutes_pct=minutes_pct,
        position_group="GK",
        age_at_transfer=26.0,
        age_at_departure=None,
        value_change_pct=-50.0,
        exit_ratio_vs_expected=-0.4,
    )
    base.update(kw)
    return SimpleNamespace(**base)


FLOOR = {"min_tenure_days": 1460, "min_minutes_pct": 70.0, "floor_score": 70.0}
DEFAULT_RATES = {"GK": {"under_21": 0.0, "21_23": 0.0, "23_25": 0.0, "25_27": 0.0,
                        "27_29": 0.0, "29_31": 0.0, "31_plus": 0.0}}


def test_value_trajectory_floored_when_long_tenure_high_minutes():
    """5 years at Liverpool, 90% minutes — value collapsed but stint is success."""
    f = _feature(tenure_days=5 * 365, minutes_pct=90.0)
    score, _ = score_value_trajectory(f, DEFAULT_RATES, scale=0.05, floor_config=FLOOR)
    assert score is not None
    assert score >= 70.0  # floored at 70


def test_value_trajectory_unfloored_when_short_tenure():
    """2 years at the club — floor doesn't apply, raw sigmoid wins."""
    f = _feature(tenure_days=2 * 365, minutes_pct=90.0)
    score, _ = score_value_trajectory(f, DEFAULT_RATES, scale=0.05, floor_config=FLOOR)
    assert score is not None
    assert score < 70.0


def test_value_trajectory_unfloored_when_low_minutes():
    """Long stint but a fringe player — floor doesn't apply."""
    f = _feature(tenure_days=5 * 365, minutes_pct=40.0)
    score, _ = score_value_trajectory(f, DEFAULT_RATES, scale=0.05, floor_config=FLOOR)
    assert score is not None
    assert score < 70.0


def test_financial_return_floored_when_long_tenure_high_minutes():
    """Sold for €0 after 7 years — floor lifts financial_return to B."""
    f = _feature(tenure_days=7 * 365, minutes_pct=80.0, exit_ratio_vs_expected=-0.6)
    score = score_financial_return(f, scale=1.0, floor_config=FLOOR)
    assert score is not None
    assert score >= 70.0


def test_financial_return_null_when_in_progress():
    """In-progress transfers have null exit_ratio_vs_expected — floor cannot apply."""
    f = _feature(tenure_days=5 * 365, minutes_pct=90.0, exit_ratio_vs_expected=None)
    score = score_financial_return(f, scale=1.0, floor_config=FLOOR)
    assert score is None


def test_floor_config_empty_disables_the_floor():
    """When floor_config is empty/missing, raw scores pass through."""
    f = _feature(tenure_days=5 * 365, minutes_pct=90.0)
    score, _ = score_value_trajectory(f, DEFAULT_RATES, scale=0.05, floor_config={})
    # Empty floor_config → defaults kick in (min_tenure_days=1460, etc.) so this
    # transfer DOES qualify and gets floored. Test the "explicit no-floor" case
    # by passing a config that excludes the transfer.
    no_floor = {"min_tenure_days": 99999, "min_minutes_pct": 99.0, "floor_score": 70.0}
    score, _ = score_value_trajectory(f, DEFAULT_RATES, scale=0.05, floor_config=no_floor)
    assert score is not None
    assert score < 70.0
