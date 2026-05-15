"""Tests for the CooperationLevel enum and the cooperation_level() helper."""

import pytest
from lle import World

from solver import CooperationLevel, cooperation_level


# ---------------------------------------------------------------------------
# Enum invariants
# ---------------------------------------------------------------------------

def test_cooperation_level_is_str_compatible():
    assert CooperationLevel.COOPERATIVE == "cooperative"
    assert CooperationLevel.FULLY_COUPLED == "fully_coupled"
    assert "asymmetric" == CooperationLevel.ASYMMETRIC


def test_cooperation_level_round_trips_through_string():
    for level in CooperationLevel:
        assert CooperationLevel(level.value) is level


def test_cooperative_subtypes_excludes_unsolvable_and_independent():
    subtypes = CooperationLevel.cooperative_subtypes()
    assert CooperationLevel.UNSOLVABLE not in subtypes
    assert CooperationLevel.INDEPENDENT not in subtypes
    assert set(subtypes) == set(CooperationLevel) - {
        CooperationLevel.UNSOLVABLE,
        CooperationLevel.INDEPENDENT,
    }


# ---------------------------------------------------------------------------
# Helper function against canonical LLE levels
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "level,t,expected",
    [
        (1, 10, CooperationLevel.INDEPENDENT),
        (2, 10, CooperationLevel.INDEPENDENT),
        (3, 10, CooperationLevel.ASYMMETRIC),
        (4, 10, CooperationLevel.FULLY_COUPLED),
    ],
)
def test_cooperation_level_classifies_lle_levels(level, t, expected):
    world = World.level(level)
    world.reset()
    assert cooperation_level(world, T_MAX=t) is expected


def test_cooperation_level_returns_enum_member_not_string():
    world = World.level(1)
    world.reset()
    result = cooperation_level(world, T_MAX=10)
    assert isinstance(result, CooperationLevel)
