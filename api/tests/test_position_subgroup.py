"""Mapping from Transfermarkt sub_position string to scoring subgroup label."""

import pytest

from ml.utils import position_subgroup


@pytest.mark.parametrize("sub_position,position_group,expected", [
    ("Defensive Midfield", "MID", "DM"),
    ("Central Midfield", "MID", "CM"),
    ("Right Midfield", "MID", "CM"),
    ("Left Midfield", "MID", "CM"),
    ("Attacking Midfield", "MID", "AM"),
    ("Centre-Back", "DEF", "CB"),
    ("Right-Back", "DEF", "FB"),
    ("Left-Back", "DEF", "FB"),
    ("Goalkeeper", "GK", "GK"),
    ("Centre-Forward", "FWD", "FWD"),
    ("Left Winger", "FWD", "FWD"),
    ("Right Winger", "FWD", "FWD"),
    ("Second Striker", "FWD", "FWD"),
    (None, "MID", "MID"),  # unknown sub_position → fall back to position_group
    ("", "MID", "MID"),
    ("Sweeper", "DEF", "DEF"),  # unmapped sub_position → fall back
])
def test_subgroup_mapping(sub_position, position_group, expected):
    assert position_subgroup(sub_position, position_group) == expected
