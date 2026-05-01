"""Direct unit tests for `pipeline/ingest.py` helpers and `pipeline/parse.py` parsers.

Pins the contract so the polars rewrite in PR 2 has a parity target. These tests
do not require any fixtures — they exercise pure functions.
"""

import math
from datetime import date

import pandas as pd
import pytest

from pipeline.ingest import (
    _coerce_int_default,
    _coerce_int_nullable,
    _market_value_to_cents,
    _normalize_foot,
    _parse_date,
    _safe_int_str,
    _safe_str,
)


class TestSafeStr:
    @pytest.mark.parametrize("value,expected", [
        (None, None),
        ("", None),
        ("foo", "foo"),
        (123, "123"),
        (float("nan"), None),
        (pd.NA, None),
    ])
    def test_cases(self, value, expected):
        assert _safe_str(value) == expected


class TestSafeIntStr:
    @pytest.mark.parametrize("value,expected", [
        (None, None),
        (float("nan"), None),
        (123.0, "123"),
        ("123", "123"),
        (123, "123"),
    ])
    def test_cases(self, value, expected):
        assert _safe_int_str(value) == expected


class TestCoerceIntDefault:
    @pytest.mark.parametrize("value,expected", [
        (None, 0),
        ("", 0),
        ("abc", 0),
        ("5", 5),
        (5.7, 5),
        (5, 5),
        (float("nan"), 0),
    ])
    def test_default_zero(self, value, expected):
        assert _coerce_int_default(value) == expected

    def test_custom_default(self):
        assert _coerce_int_default(None, default=42) == 42
        assert _coerce_int_default("abc", default=42) == 42
        assert _coerce_int_default("9", default=42) == 9


class TestCoerceIntNullable:
    @pytest.mark.parametrize("value,expected", [
        (None, None),
        ("", None),
        ("abc", None),
        ("5", 5),
        (5.7, 5),
        (5, 5),
        (float("nan"), None),
    ])
    def test_cases(self, value, expected):
        assert _coerce_int_nullable(value) == expected


class TestNormalizeFoot:
    @pytest.mark.parametrize("value,expected", [
        ("left", "Left"),
        ("LEFT", "Left"),
        ("Left", "Left"),
        ("right", "Right"),
        ("RIGHT", "Right"),
        ("both", "Both"),
        ("Both", "Both"),
        (None, None),
        ("", None),
        ("foot", None),
        ("unknown", None),
    ])
    def test_cases(self, value, expected):
        assert _normalize_foot(value) == expected


class TestMarketValueToCents:
    @pytest.mark.parametrize("value,expected", [
        (None, None),
        ("", None),
        (1000.0, 100000),
        (0, 0),
        (1e9, 100_000_000_000),
        ("abc", None),
    ])
    def test_cases(self, value, expected):
        assert _market_value_to_cents(value) == expected


class TestParseDate:
    @pytest.mark.parametrize("value,expected", [
        ("2023-04-15", date(2023, 4, 15)),
        ("04/15/2023", date(2023, 4, 15)),
        ("not a date", None),
        (None, None),
        ("", None),
    ])
    def test_cases(self, value, expected):
        assert _parse_date(value) == expected

    def test_datetime_input(self):
        """Pandas Timestamp input should be accepted (some upstream paths pass it)."""
        ts = pd.Timestamp("2023-04-15")
        assert _parse_date(ts) == date(2023, 4, 15)
