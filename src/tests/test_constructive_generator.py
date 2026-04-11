import pytest

from generators.constructive_solvable_generator import ConstructiveSolvableGenerator
from solver import LLEAdapter, WorldSolver


def is_satisfiable(world, t_max):
    world.reset()
    solver = WorldSolver(LLEAdapter(world), T_MAX=t_max)
    result, _ = solver.solve()
    return bool(result)


@pytest.mark.parametrize("seed", list(range(10)))
def test_constructive_generator_produces_satisfiable_worlds(seed):
    generator = ConstructiveSolvableGenerator(
        size=(6, 6),
        agents=2,
        lasers=1,
        num_walls=6,
        t_max=8,
        max_attempts=50,
        seed=seed,
    )

    world = generator.generate()

    assert is_satisfiable(world, generator.t_max)
    assert generator.last_attempts <= generator.max_attempts


@pytest.mark.parametrize(
    "rows,cols,agents,lasers,num_walls,t_max",
    [
        (5, 5, 2, 0, 4, 6),
        (6, 6, 2, 1, 6, 8),
        (7, 6, 3, 1, 8, 10),
        (6, 7, 3, 2, 8, 10),
    ],
)
def test_constructive_generator_supports_multiple_grid_shapes(
    rows, cols, agents, lasers, num_walls, t_max
):
    generator = ConstructiveSolvableGenerator(
        size=(rows, cols),
        agents=agents,
        lasers=lasers,
        num_walls=num_walls,
        t_max=t_max,
        max_attempts=100,
        seed=123,
    )

    world = generator.generate()

    assert is_satisfiable(world, t_max)


def test_constructive_generator_respects_t_min_window():
    generator = ConstructiveSolvableGenerator(
        size=(6, 6),
        agents=2,
        lasers=0,
        num_walls=4,
        t_max=8,
        t_min=5,
        max_attempts=50,
        seed=7,
    )

    world = generator.generate()

    assert is_satisfiable(world, generator.t_max)
    assert not is_satisfiable(world, generator.t_min - 1)


def test_constructive_generator_often_accepts_first_attempt_on_easy_instance():
    generator = ConstructiveSolvableGenerator(
        size=(6, 6),
        agents=2,
        lasers=1,
        num_walls=4,
        t_max=8,
        max_attempts=20,
        seed=1,
    )

    generator.generate()

    assert generator.last_attempts == 1
