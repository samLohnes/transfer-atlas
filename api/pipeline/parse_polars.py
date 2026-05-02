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

    Mirrors the 7 priority-ordered branches of pipeline.parse.parse_fee exactly.
    Caller unnests via:
        df = df.with_columns(parse_fee_expr(pl.col("transfer_fee")).alias("_fee"))
        df = df.unnest("_fee")
    """
    s = col.cast(pl.String).str.strip_chars()
    s_lower = s.str.to_lowercase()

    # Branch predicates (same order as Python)
    is_empty = s.is_null() | (s.fill_null("") == "")
    is_eol = s_lower.str.contains("end of loan", literal=True)
    has_loan = s_lower.str.contains("loan", literal=True)
    has_loan_fee = s_lower.str.contains("loan fee", literal=True)
    is_free = (
        s_lower.str.contains("free transfer", literal=True)
        | (s_lower.fill_null("") == "free")
    )
    is_dash = s.fill_null("") == "-"
    is_question = s.fill_null("") == "?"

    # Numeric extraction: capture number and suffix from structured fee strings
    # Pattern matches optional currency symbol, digits/commas/dots, optional suffix
    num_str = s_lower.str.extract(r"[€$£]?\s*([\d.,]+)\s*(?:m|k|th\.?|mil\.?)?", 1)
    suffix_raw = s_lower.str.extract(r"[€$£]?\s*[\d.,]+\s*(m|k|th\.?|mil\.?)?", 1)

    # Normalize suffix: strip dots, lowercase ("Th." -> "th", "mil." -> "mil")
    suffix_norm = (
        suffix_raw.fill_null("")
        .str.replace_all(r"\.", "", literal=False)
        .str.to_lowercase()
    )

    # Comma-to-dot for European decimal notation ("1,50" -> "1.50")
    num_clean = num_str.str.replace_all(",", ".", literal=True)
    num_val = num_clean.cast(pl.Float64, strict=False)

    multiplier = (
        pl.when(suffix_norm == "m").then(pl.lit(1_000_000 * 100, dtype=pl.Int64))
        .when(suffix_norm == "mil").then(pl.lit(1_000_000 * 100, dtype=pl.Int64))
        .when(suffix_norm == "k").then(pl.lit(1_000 * 100, dtype=pl.Int64))
        .when(suffix_norm == "th").then(pl.lit(1_000 * 100, dtype=pl.Int64))
        .otherwise(pl.lit(100, dtype=pl.Int64))  # raw EUR -> cents
    )
    cents_from_match = (num_val * multiplier.cast(pl.Float64)).cast(pl.Int64, strict=False)

    # Pure numeric fallback: strip commas, parse as float (e.g. "1500000.000")
    pure_num = (
        (s.str.replace_all(",", "", literal=True).cast(pl.Float64, strict=False) * 100.0)
        .cast(pl.Int64, strict=False)
    )

    # fee_eur priority chain — mirrors parse_fee Python branch order
    fee_eur = (
        pl.when(is_empty).then(pl.lit(None, dtype=pl.Int64))
        .when(is_eol).then(pl.lit(None, dtype=pl.Int64))
        .when(has_loan & has_loan_fee).then(cents_from_match)
        .when(has_loan).then(pl.lit(0, dtype=pl.Int64))
        .when(is_free).then(pl.lit(0, dtype=pl.Int64))
        .when(is_dash | is_question).then(pl.lit(None, dtype=pl.Int64))
        .when(cents_from_match.is_not_null()).then(cents_from_match)
        .when(pure_num.is_not_null()).then(pure_num)
        .otherwise(pl.lit(None, dtype=pl.Int64))
    )

    is_loan_field = (
        pl.when(is_empty | is_eol).then(pl.lit(False))
        .when(has_loan).then(pl.lit(True))
        .otherwise(pl.lit(False))
    )

    # exclude is True only for "end of loan" (non-empty input)
    exclude_field = is_eol & ~is_empty

    return pl.struct(
        fee_eur=fee_eur,
        is_loan=is_loan_field,
        exclude=exclude_field,
    )


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
