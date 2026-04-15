"""Transfer window ordering utilities."""

import re


def window_sort_key(window: str) -> tuple[int, int]:
    """Return a sort key for chronological ordering of transfer windows.

    Summer comes before Winter in the same football season:
    Summer 2015, Winter 2016, Summer 2016, Winter 2017, ...
    """
    match = re.match(r"(Summer|Winter)\s+(\d{4})", window)
    if not match:
        return (0, 0)

    season_type, year_str = match.group(1), int(match.group(2))

    if season_type == "Summer":
        return (year_str, 0)
    else:  # Winter
        return (year_str, 1)


def get_windows_in_range(
    all_windows: list[str], start: str | None, end: str | None
) -> list[str] | None:
    """Filter windows to those within the specified range, inclusive.

    Returns None if no filtering should be applied (both start and end are None).
    """
    if start is None and end is None:
        return None

    sorted_windows = sorted(all_windows, key=window_sort_key)
    start_key = window_sort_key(start) if start else (0, 0)
    end_key = window_sort_key(end) if end else (9999, 1)

    return [w for w in sorted_windows if start_key <= window_sort_key(w) <= end_key]
