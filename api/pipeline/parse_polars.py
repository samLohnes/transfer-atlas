"""Polars-expression equivalents of pipeline/parse.py.

Used by the polars-vectorized ingest sites (ingest_appearances,
ingest_valuations, ingest_transfers) to push per-row Python parsing into
vectorized polars operations. The Python originals in pipeline/parse.py remain
the canonical reference and are still used by ingest_players / ingest_clubs.

Each function takes a polars expression (a String column) and returns a polars
expression that produces the parsed value(s).
"""

import polars as pl


def parse_fee_expr(col: pl.Expr) -> pl.Expr:
    """Vectorized parse_fee.

    Returns a Struct expression with three fields:
        fee_eur: Int64 (cents) or null
        is_loan: Bool
        exclude: Bool

    Caller unnests via:
        df = df.with_columns(parse_fee_expr(pl.col("transfer_fee")).alias("_fee"))
        df = df.unnest("_fee")
    """
    raise NotImplementedError  # implemented in Task 4


def derive_transfer_window_expr(date_col: pl.Expr, season_col: pl.Expr) -> pl.Expr:
    """Vectorized derive_transfer_window.

    Returns a String expression: 'Summer YYYY' / 'Winter YYYY' / null.
    """
    raise NotImplementedError  # implemented in Task 5


def normalize_season_expr(col: pl.Expr) -> pl.Expr:
    """Vectorized normalize_season.

    Returns a String expression: 'YYYY-YYYY' or null.
    """
    raise NotImplementedError  # implemented in Task 6
