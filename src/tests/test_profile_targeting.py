"""
Tests for profile targeting in cooperative generators.

Verifies that RandomCooperativeGenerator, ConstrainedRandomCooperativeGenerator,
and ConstructiveCooperativeGenerator correctly accept the --profile argument
and that accepted levels match the requested profile.
"""

import pytest
from lle import World

from generators.constrained_random_cooperative_generator import ConstrainedRandomCooperativeGenerator
from generators.constructive_cooperative_generator import ConstructiveCooperativeGenerator
from generators.random_cooperative_generator import RandomCooperativeGenerator
from solver.cooperation_profile_analyzer import CooperationProfileAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def analyze_profile(world: World, t_max: int = 10):
    world.reset()
    return CooperationProfileAnalyzer(world, T_MAX=t_max).analyze()


def make_random_cooperative(**kwargs):
    defaults = dict(size=(5, 5), agents=2, lasers=1, t_max=12, max_attempts=500, seed=7)
    defaults.update(kwargs)
    return RandomCooperativeGenerator(**defaults)


def make_constrained_cooperative(**kwargs):
    defaults = dict(size=(5, 5), agents=2, lasers=1, t_max=12, max_attempts=500, seed=7)
    defaults.update(kwargs)
    return ConstrainedRandomCooperativeGenerator(**defaults)


def make_constructive_cooperative(**kwargs):
    defaults = dict(size=(6, 6), agents=2, lasers=1, t_max=15, max_attempts=200, seed=7)
    defaults.update(kwargs)
    return ConstructiveCooperativeGenerator(**defaults)


# ---------------------------------------------------------------------------
# Profile argument is accepted (no error at construction)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile", [
    "cooperative", "asymmetric", "mutual", "chain", "distributed", "fully_coupled"
])
def test_random_cooperative_accepts_profile_argument(profile):
    gen = make_random_cooperative()
    gen.profile = profile
    assert gen.profile == profile


@pytest.mark.parametrize("profile", [
    "cooperative", "asymmetric", "mutual", "chain", "distributed", "fully_coupled"
])
def test_constrained_random_cooperative_accepts_profile_argument(profile):
    gen = make_constrained_cooperative()
    gen.profile = profile
    assert gen.profile == profile


@pytest.mark.parametrize("profile", ["cooperative", "asymmetric"])
def test_constructive_cooperative_accepts_profile_argument(profile):
    gen = make_constructive_cooperative()
    gen.profile = profile
    assert gen.profile == profile


# ---------------------------------------------------------------------------
# Default profile is "cooperative"
# ---------------------------------------------------------------------------

def test_random_cooperative_default_profile():
    gen = make_random_cooperative()
    assert gen.profile == "cooperative"


def test_constrained_cooperative_default_profile():
    gen = make_constrained_cooperative()
    assert gen.profile == "cooperative"


def test_constructive_cooperative_default_profile():
    gen = make_constructive_cooperative()
    assert gen.profile == "cooperative"


# ---------------------------------------------------------------------------
# Generated levels actually satisfy the requested profile
# ---------------------------------------------------------------------------

def test_random_cooperative_generates_cooperative_level():
    gen = make_random_cooperative()
    gen.profile = "cooperative"
    world = gen.generate()
    result = analyze_profile(world, t_max=12)
    assert result.cooperation_required
    assert result.matches_profile("cooperative")


def test_constrained_cooperative_generates_cooperative_level():
    gen = make_constrained_cooperative()
    gen.profile = "cooperative"
    world = gen.generate()
    result = analyze_profile(world, t_max=12)
    assert result.cooperation_required
    assert result.matches_profile("cooperative")


def test_constructive_cooperative_generates_cooperative_level():
    gen = make_constructive_cooperative()
    gen.profile = "cooperative"
    world = gen.generate()
    result = analyze_profile(world, t_max=15)
    assert result.cooperation_required
    assert result.matches_profile("cooperative")


# ---------------------------------------------------------------------------
# Asymmetric profile targeting
# ---------------------------------------------------------------------------

def test_random_cooperative_asymmetric_profile():
    gen = make_random_cooperative(max_attempts=2000, seed=42)
    gen.profile = "asymmetric"
    world = gen.generate()
    result = analyze_profile(world, t_max=12)
    assert result.matches_profile("asymmetric")


def test_constructive_cooperative_asymmetric_profile():
    gen = make_constructive_cooperative(max_attempts=500, seed=42)
    gen.profile = "asymmetric"
    world = gen.generate()
    result = analyze_profile(world, t_max=15)
    assert result.matches_profile("asymmetric")


# ---------------------------------------------------------------------------
# from_args classmethod wires profile correctly
# ---------------------------------------------------------------------------

class _FakeArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_random_cooperative_from_args_wires_profile():
    args = _FakeArgs(
        size=[5, 5],
        agents=2,
        lasers=1,
        num_walls=None,
        t_max=12,
        t_min=0,
        max_attempts=500,
        seed=7,
        profile="asymmetric",
        debug_rejections=False,
    )
    gen = RandomCooperativeGenerator.from_args(args)
    assert gen.profile == "asymmetric"


def test_constrained_cooperative_from_args_wires_profile():
    args = _FakeArgs(
        size=[5, 5],
        agents=2,
        lasers=1,
        num_walls=None,
        t_max=12,
        t_min=0,
        max_attempts=500,
        seed=7,
        profile="mutual",
        debug_rejections=False,
        min_beam_length=None,
        max_beam_length=None,
        require_exit_clear=False,
    )
    gen = ConstrainedRandomCooperativeGenerator.from_args(args)
    assert gen.profile == "mutual"
