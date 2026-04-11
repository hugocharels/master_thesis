import pytest

from generators.constructive_cooperative_generator import (
    ConstructiveCooperativeGenerator,
)
from solver import CooperationProfileAnalyzer, LLEAdapter, WorldSolver


def analyze(world, t_max):
    world.reset()
    return CooperationProfileAnalyzer(LLEAdapter(world), T_MAX=t_max).analyze()


def is_satisfiable(world, t_max):
    world.reset()
    result, _ = WorldSolver(LLEAdapter(world), T_MAX=t_max).solve()
    return bool(result)


@pytest.mark.parametrize("seed", list(range(5)))
def test_constructive_cooperative_generator_produces_cooperative_worlds(seed):
    generator = ConstructiveCooperativeGenerator(
        size=(5, 6),
        agents=2,
        lasers=1,
        num_walls=0,
        t_max=8,
        max_attempts=10,
        seed=seed,
    )

    world = generator.generate()
    result = analyze(world, generator.t_max)

    assert is_satisfiable(world, generator.t_max)
    assert result.cooperation_required is True
    assert result.matches_profile("cooperative")
    assert result.matches_profile("asymmetric")


def test_constructive_cooperative_generator_supports_three_agents():
    generator = ConstructiveCooperativeGenerator(
        size=(6, 7),
        agents=3,
        lasers=1,
        num_walls=0,
        t_max=10,
        max_attempts=10,
        seed=3,
    )

    world = generator.generate()
    result = analyze(world, generator.t_max)

    assert is_satisfiable(world, generator.t_max)
    assert result.cooperation_required is True
    assert result.matches_profile("cooperative")


def test_constructive_cooperative_generator_accepts_asymmetric_profile():
    generator = ConstructiveCooperativeGenerator(
        size=(5, 6),
        agents=2,
        lasers=1,
        num_walls=0,
        t_max=8,
        max_attempts=10,
        seed=1,
    )
    generator.profile = "asymmetric"

    world = generator.generate()
    result = analyze(world, generator.t_max)

    assert result.matches_profile("asymmetric")


def test_constructive_cooperative_generator_often_accepts_first_attempt():
    generator = ConstructiveCooperativeGenerator(
        size=(5, 6),
        agents=2,
        lasers=1,
        num_walls=0,
        t_max=8,
        max_attempts=10,
        seed=0,
    )

    generator.generate()

    assert generator.last_attempts == 1
