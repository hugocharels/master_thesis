import pytest

from core import Agent, CellType, Direction, Entity, Laser, World
from solver import WorldSolver


def solve(world, t):
    solver = WorldSolver(world, T_MAX=t)
    return solver.solve()[0]


def make_world(width, height, agents=(), exits=(), walls=(), lasers=()):
    world = World(width, height)

    for c, pos in enumerate(agents):
        world.add_entity(pos, Agent(c))

    for pos in exits:
        world.add_entity(pos, Entity(CellType.EXIT))

    for pos in walls:
        world.add_entity(pos, Entity(CellType.WALL))

    for c, pos, direction in lasers:
        world.add_entity(pos, Laser(c, direction=direction))

    return world


# ==========================================================
# Parametrized Tests
# ==========================================================


@pytest.mark.parametrize(
    "width,height,agents,exits,walls,lasers,t,expected",
    [
        # 1 agent, 1 exit, no walls, no lasers
        (2, 2, [(0, 0)], [(0, 1)], [], [], 1, True),
        (2, 2, [(0, 0)], [(1, 1)], [], [], 1, False),
        (2, 2, [(0, 0)], [(1, 1)], [], [], 2, True),
        (2, 2, [(0, 0)], [(1, 1)], [], [], 3, True),
        (3, 3, [(0, 0)], [(2, 0)], [(1, 0)], [], 2, False),
        (3, 3, [(0, 0)], [(2, 0)], [(1, 0)], [], 3, False),
        (3, 3, [(0, 0)], [(2, 0)], [(1, 0)], [], 4, True),
        # 1 agent, 1 exit, walls, no lasers
        (2, 2, [(0, 0)], [(1, 1)], [(0, 1), (1, 0)], [], 2, False),
        (2, 2, [(0, 0)], [(1, 1)], [(0, 1)], [], 2, True),
        (2, 2, [(0, 0)], [(1, 1)], [(1, 0)], [], 2, True),
        # 2 agent, 2 exit, no walls, no lasers
        (2, 2, [(0, 0), (0, 1)], [(1, 0), (1, 1)], [], [], 1, True),
        (3, 3, [(0, 0), (0, 2)], [(2, 0), (2, 2)], [], [], 1, False),
        (3, 3, [(0, 0), (0, 2)], [(2, 0), (2, 2)], [], [], 2, True),
        # 2 agent, 2 exit, walls, no lasers
        # agents can't reach exits
        (
            4,
            4,
            [(0, 0), (0, 3)],
            [(3, 0), (3, 3)],
            [(2, 0), (2, 1), (2, 2), (2, 3)],
            [],
            3,
            False,
        ),
        (
            4,
            4,
            [(0, 0), (0, 3)],
            [(3, 0), (3, 3)],
            [(2, 0), (2, 1), (2, 2), (2, 3)],
            [],
            10,
            False,
        ),
        # 2 agent, 2 exit, walls, no lasers, only one entrance to exits
        # agents have to wait for each other to pass through the narrow corridor
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [(1, 0), (1, 2)],
            [],
            4,
            False,
        ),
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [(1, 0), (1, 2)],
            [],
            5,
            True,
        ),
    ],
)
def test_solver(width, height, agents, exits, walls, lasers, t, expected):
    world = make_world(width, height, agents, exits, walls, lasers)
    assert solve(world, t) == expected
