"""Direct unit tests for `pipeline/ingest.py` helpers and `pipeline/parse.py` parsers.

Pins the contract so the polars rewrite in PR 2 has a parity target. These tests
do not require any fixtures — they exercise pure functions.
"""

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
from pipeline.parse import (
    derive_transfer_window,
    normalize_season,
    parse_fee,
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


# --------------------------------------------------------------------------- #
# Parser tests — pipeline/parse.py
# --------------------------------------------------------------------------- #


class TestParseFee:
    @pytest.mark.parametrize("value,expected", [
        # None / empty → undisclosed
        (None, (None, False, False)),
        ("", (None, False, False)),
        # Sentinel undisclosed
        ("-", (None, False, False)),
        ("?", (None, False, False)),
        # End of loan → exclude entirely
        ("End of loan", (None, False, True)),
        ("end of loan", (None, False, True)),
        # Loan transfer with no explicit fee → 0, is_loan
        ("loan transfer", (0, True, False)),
        # Loan with explicit fee → cents, is_loan
        ("Loan fee:€1.50m", (150_000_000, True, False)),
        # Free transfer
        ("Free transfer", (0, False, False)),
        ("free", (0, False, False)),
        # Structured numeric with suffix
        ("€25M", (2_500_000_000, False, False)),
        ("€500k", (50_000_000, False, False)),
        ("€500Th.", (50_000_000, False, False)),
        # Pure numeric
        ("1500000.000", (150_000_000, False, False)),
    ])
    def test_cases(self, value, expected):
        assert parse_fee(value) == expected


class TestDeriveTransferWindow:
    @pytest.mark.parametrize("transfer_date,season,expected", [
        # Summer months 6–12
        (date(2023, 6, 1), None, "Summer 2023"),
        (date(2023, 8, 15), None, "Summer 2023"),
        (date(2023, 12, 31), None, "Summer 2023"),
        # Winter months 1–5
        (date(2024, 1, 15), None, "Winter 2024"),
        (date(2024, 5, 31), None, "Winter 2024"),
        # Date null → fallback to season string
        (None, "23/24", "Summer 2023"),
        (None, "2024/2025", "Summer 2024"),
        # Both null → None
        (None, None, None),
        (None, "", None),
        # Malformed season → None
        (None, "garbage", None),
    ])
    def test_cases(self, transfer_date, season, expected):
        assert derive_transfer_window(transfer_date, season) == expected


class TestNormalizeSeason:
    @pytest.mark.parametrize("value,expected", [
        ("23/24", "2023-2024"),
        ("2023/2024", "2023-2024"),
        ("23-24", "2023-2024"),
        # Two-digit cutoff at 80: <80 → 2000s, >=80 → 1900s
        ("79/80", "2079-1980"),
        ("80/81", "1980-1981"),
        ("99/00", "1999-2000"),
        # Empty / malformed → None
        (None, None),
        ("", None),
        ("garbage", None),
    ])
    def test_cases(self, value, expected):
        assert normalize_season(value) == expected
