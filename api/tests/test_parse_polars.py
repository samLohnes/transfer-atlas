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
