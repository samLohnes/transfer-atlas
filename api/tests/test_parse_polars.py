"""Parity tests: polars expressions in pipeline/parse_polars.py must produce
identical results to the Python originals in pipeline/parse.py for every input
covered by the helper unit tests.
"""

from datetime import date

import polars as pl
import pytest

from pipeline.parse import (
    derive_transfer_window,
    normalize_season,
    parse_fee,
)
from pipeline.parse_polars import (
    derive_transfer_window_expr,
    normalize_season_expr,
    parse_fee_expr,
)


# Same input set as test_ingest_helpers.TestParseFee
PARSE_FEE_INPUTS = [
    None,
    "",
    "-",
    "?",
    "End of loan",
    "end of loan",
    "loan transfer",
    "Loan fee:€1.50m",
    "Free transfer",
    "free",
    "€25M",
    "€500k",
    "€500Th.",
    "1500000.000",
]


class TestParseFeeParity:
    @pytest.mark.parametrize("value", PARSE_FEE_INPUTS)
    def test_matches_python(self, value):
        py_result = parse_fee(value)  # (fee_eur, is_loan, exclude)
        df = pl.DataFrame({"fee": [value]}, schema={"fee": pl.String})
        result = df.with_columns(parse_fee_expr(pl.col("fee")).alias("parsed"))
        unnested = result.unnest("parsed")
        row = unnested.row(0, named=True)
        assert (row["fee_eur"], row["is_loan"], row["exclude"]) == py_result, (
            f"polars parse_fee({value!r}) = "
            f"({row['fee_eur']}, {row['is_loan']}, {row['exclude']}); "
            f"python = {py_result}"
        )


WINDOW_INPUTS: list[tuple[date | None, str | None]] = [
    (date(2023, 6, 1), None),
    (date(2023, 8, 15), None),
    (date(2023, 12, 31), None),
    (date(2024, 1, 15), None),
    (date(2024, 5, 31), None),
    (None, "23/24"),
    (None, "2024/2025"),
    (None, None),
    (None, ""),
    (None, "garbage"),
]


class TestDeriveTransferWindowParity:
    @pytest.mark.parametrize("transfer_date,season", WINDOW_INPUTS)
    def test_matches_python(self, transfer_date, season):
        py_result = derive_transfer_window(transfer_date, season)
        df = pl.DataFrame(
            {"d": [transfer_date], "s": [season]},
            schema={"d": pl.Date, "s": pl.String},
        )
        result = df.with_columns(
            derive_transfer_window_expr(pl.col("d"), pl.col("s")).alias("w")
        )
        polars_result = result.row(0, named=True)["w"]
        assert polars_result == py_result, (
            f"polars window({transfer_date}, {season!r}) = {polars_result!r}; "
            f"python = {py_result!r}"
        )


SEASON_INPUTS = [
    "23/24",
    "2023/2024",
    "23-24",
    "79/80",
    "80/81",
    "99/00",
    None,
    "",
    "garbage",
]


class TestNormalizeSeasonParity:
    @pytest.mark.parametrize("value", SEASON_INPUTS)
    def test_matches_python(self, value):
        py_result = normalize_season(value)
        df = pl.DataFrame({"s": [value]}, schema={"s": pl.String})
        result = df.with_columns(normalize_season_expr(pl.col("s")).alias("n"))
        polars_result = result.row(0, named=True)["n"]
        assert polars_result == py_result, (
            f"polars normalize_season({value!r}) = {polars_result!r}; "
            f"python = {py_result!r}"
        )
