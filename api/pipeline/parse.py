"""Fee parsing, transfer window derivation, and season normalization."""

import hashlib
import re
from datetime import date


def parse_fee(fee_str: str | None) -> tuple[int | None, bool, bool]:
    """Parse a Transfermarkt fee string into (fee_eur_cents, is_loan, exclude).

    Returns:
        Tuple of (fee in EUR cents or None, whether it's a loan, whether to exclude).
        Exclude is True for "End of loan" entries.
    """
    if fee_str is None or fee_str.strip() == "":
        return None, False, False

    s = fee_str.strip()
    s_lower = s.lower()

    # End of loan — exclude entirely
    if "end of loan" in s_lower:
        return None, False, True

    # Loan transfers
    is_loan = False
    if "loan" in s_lower:
        is_loan = True
        # "Loan fee:€1.50m" — extract the fee portion
        loan_fee_match = re.search(r"[€$£]?\s*([\d.,]+)\s*(m|k|th\.?|mil\.?)?", s_lower)
        if loan_fee_match and "loan fee" in s_lower:
            cents = _parse_numeric_fee(loan_fee_match.group(1), loan_fee_match.group(2))
            return cents, True, False
        # "loan transfer" with no fee
        return 0, True, False

    # Free transfer
    if "free transfer" in s_lower or "free" == s_lower:
        return 0, False, False

    # Dash means undisclosed
    if s == "-":
        return None, False, False

    # "?": undisclosed
    if s == "?":
        return None, False, False

    # Try parsing structured fee: "€25m", "€1.5M", "€500k", "€500Th."
    fee_match = re.search(r"[€$£]?\s*([\d.,]+)\s*(m|k|th\.?|mil\.?)?", s_lower)
    if fee_match:
        cents = _parse_numeric_fee(fee_match.group(1), fee_match.group(2))
        if cents is not None:
            return cents, False, False

    # Try pure numeric
    try:
        val = float(s.replace(",", ""))
        return int(val * 100), False, False
    except ValueError:
        pass

    # Unparsable
    return None, False, False


def _parse_numeric_fee(num_str: str, suffix: str | None) -> int | None:
    """Convert a numeric string + suffix (m/k/th) to EUR cents."""
    try:
        num_str = num_str.replace(",", ".")
        value = float(num_str)
    except ValueError:
        return None

    if suffix is None:
        # Raw EUR value
        return int(value * 100)

    suffix = suffix.lower().rstrip(".")
    if suffix == "m" or suffix == "mil":
        return int(value * 1_000_000 * 100)
    elif suffix == "k":
        return int(value * 1_000 * 100)
    elif suffix == "th":
        return int(value * 1_000 * 100)
    else:
        return int(value * 100)


def derive_transfer_window(transfer_date: date | None, transfer_season: str | None) -> str | None:
    """Derive transfer window string from transfer date or season.

    Returns strings like "Summer 2023" or "Winter 2024", or None if undeterminable.
    """
    if transfer_date is not None:
        month = transfer_date.month
        year = transfer_date.year
        if month in (6, 7, 8, 9, 10, 11, 12):
            return f"Summer {year}"
        elif month in (1, 2, 3, 4, 5):
            return f"Winter {year}"

    # Fallback: derive from season string
    if transfer_season:
        start_year = _parse_season_start_year(transfer_season)
        if start_year:
            return f"Summer {start_year}"

    return None


def normalize_season(transfer_season: str | None) -> str | None:
    """Convert season string to normalized format: '2023-2024'.

    Handles '23/24', '2023/2024', '23-24', etc.
    """
    if not transfer_season:
        return None

    s = transfer_season.strip()

    # Match patterns like "23/24" or "2023/2024" or "23-24"
    match = re.match(r"(\d{2,4})[/\-](\d{2,4})", s)
    if not match:
        return None

    start = match.group(1)
    end = match.group(2)

    if len(start) == 2:
        start_year = 2000 + int(start) if int(start) < 80 else 1900 + int(start)
    else:
        start_year = int(start)

    if len(end) == 2:
        end_year = 2000 + int(end) if int(end) < 80 else 1900 + int(end)
    else:
        end_year = int(end)

    return f"{start_year}-{end_year}"


def _parse_season_start_year(transfer_season: str) -> int | None:
    """Extract the start year from a season string."""
    match = re.match(r"(\d{2,4})[/\-]", transfer_season.strip())
    if not match:
        return None
    start = match.group(1)
    if len(start) == 2:
        return 2000 + int(start) if int(start) < 80 else 1900 + int(start)
    return int(start)


def generate_transfer_id(player_id: int, transfer_date: date | None, from_club_id: int, to_club_id: int) -> str:
    """Generate a deterministic hash ID for a transfer from its natural key."""
    date_str = transfer_date.isoformat() if transfer_date else "unknown"
    key = f"{player_id}:{date_str}:{from_club_id}:{to_club_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# Position group mapping from Transfermarkt's broad position field
POSITION_GROUP_MAP: dict[str, str] = {
    "goalkeeper": "GK",
    "defender": "DEF",
    "midfield": "MID",
    "attack": "FWD",
}


def derive_position_group(broad_position: str | None) -> str | None:
    """Map Transfermarkt broad position to position group code."""
    if not broad_position:
        return None
    return POSITION_GROUP_MAP.get(broad_position.strip().lower())
