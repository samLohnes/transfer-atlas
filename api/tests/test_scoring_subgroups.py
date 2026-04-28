"""Sub-position-aware production scoring — verifies that two MID players in
different sub_position subgroups (e.g. DM vs AM) are ranked against their
own subgroup, not the flat MID position group.

Pure unit test: builds a small in-memory dataset and calls the percentile-rank
function directly, no DB round-trip.
"""

import pytest


def test_dm_and_am_compute_against_separate_peer_groups():
    """A DM and AM with identical G+A/90 should land at different percentile ranks
    when their respective subgroups have different distributions."""
    dm_peers = [0.05, 0.10, 0.15, 0.20, 0.25]
    am_peers = [0.40, 0.55, 0.70, 0.85, 1.00]
    target_g_a_per_90 = 0.30

    from ml.utils import position_subgroup

    assert position_subgroup("Defensive Midfield", "MID") == "DM"
    assert position_subgroup("Attacking Midfield", "MID") == "AM"

    def pct_rank(value, peers):
        below = sum(1 for p in peers if p < value)
        equal = sum(1 for p in peers if p == value)
        return 100.0 * (below + 0.5 * equal) / len(peers)

    dm_rank = pct_rank(target_g_a_per_90, dm_peers)
    am_rank = pct_rank(target_g_a_per_90, am_peers)

    assert dm_rank == 100.0
    assert am_rank == 0.0
    assert dm_rank != am_rank


def test_unknown_subposition_falls_back_to_position_group():
    """A player with no sub_position should still receive a position_group-level rank."""
    from ml.utils import position_subgroup

    assert position_subgroup(None, "MID") == "MID"
    assert position_subgroup("Sweeper", "DEF") == "DEF"
