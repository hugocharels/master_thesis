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
        (
            5,
            5,
            [(2, 2)],
            [(4, 4)],
            [(1, 1), (1, 2), (1, 4), (2, 1), (2, 4), (3, 1), (3, 2), (3, 3), (3, 4)],
            [],
            13,
            False,
        ),
        (
            5,
            5,
            [(2, 2)],
            [(4, 4)],
            [(1, 1), (1, 2), (1, 4), (2, 1), (2, 4), (3, 1), (3, 2), (3, 3), (3, 4)],
            [],
            14,
            True,
        ),
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
        # 1 agent, 1 exit, no walls, 1 laser
        # own laser
        (3, 3, [(0, 2)], [(2, 2)], [], [(0, (1, 0), Direction.EAST)], 2, True),
        # 2 agents, 2 exits, no walls, 2 lasers
        # lasers block the path to the exits
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [],
            [(0, (1, 0), Direction.EAST)],
            3,
            False,
        ),
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [],
            [(0, (1, 0), Direction.EAST)],
            4,
            True,
        ),
        # LLE default levels
        # Level 1: 1 agent, 1 exit, no walls, no lasers
        (
            13,
            12,
            [(0, 7)],
            [(10, 7)],
            [],
            [],
            10,
            True,
        ),
        (
            13,
            12,
            [(0, 7)],
            [(10, 7)],
            [],
            [],
            9,
            False,
        ),
        # Level 2: 2 agents, 2 exits, no walls, no lasers
        (
            13,
            12,
            [(0, 6), (0, 7)],
            [(10, 6), (10, 7)],
            [],
            [],
            10,
            True,
        ),
        (
            13,
            12,
            [(0, 6), (0, 7)],
            [(10, 6), (10, 7)],
            [],
            [],
            9,
            False,
        ),
        # Level 3: 2 agents, 2 exits, no walls, 1 laser
        (
            13,
            12,
            [(0, 7), (0, 8)],
            [(10, 7), (10, 8)],
            [],
            [(0, (4, 0), Direction.EAST)],
            10,
            True,
        ),
        (
            13,
            12,
            [(0, 7), (0, 8)],
            [(10, 7), (10, 8)],
            [],
            [(0, (4, 0), Direction.EAST)],
            9,
            False,
        ),
        # Level 4: 2 agents, 2 exits, 2 lasers
        (
            13,
            12,
            [(0, 7), (0, 8)],
            [(10, 7), (10, 8)],
            [],
            [(0, (4, 0), Direction.EAST), (1, (6, 12), Direction.WEST)],
            10,
            True,
        ),
        (
            13,
            12,
            [(0, 7), (0, 8)],
            [(10, 7), (10, 8)],
            [],
            [(0, (4, 0), Direction.EAST), (1, (6, 12), Direction.WEST)],
            9,
            False,
        ),
        # Level 5: 4 agents, 2 exits, walls, 2 lasers
        (
            13,
            12,
            [(0, 4), (0, 5), (0, 6), (0, 7)],
            [(10, 9), (10, 10), (11, 9), (11, 10)],
            [
                (3, 0),
                (3, 1),
                (4, 12),
                (4, 11),
                (4, 10),
                (4, 9),
                (4, 8),
                (4, 7),
                (7, 7),
                (8, 7),
                (8, 8),
                (8, 9),
                (8, 10),
                (8, 11),
                (8, 12),
            ],
            [(1, (6, 12), Direction.WEST), (2, (0, 2), Direction.SOUTH)],
            17,
            True,
        ),
        (
            13,
            12,
            [(0, 4), (0, 5), (0, 6), (0, 7)],
            [(10, 9), (10, 10), (11, 9), (11, 10)],
            [
                (3, 0),
                (3, 1),
                (4, 12),
                (4, 11),
                (4, 10),
                (4, 9),
                (4, 8),
                (4, 7),
                (7, 7),
                (8, 7),
                (8, 8),
                (8, 9),
                (8, 10),
                (8, 11),
                (8, 12),
            ],
            [(1, (6, 12), Direction.WEST), (2, (0, 2), Direction.SOUTH)],
            16,
            False,
        ),
        # Level 6: 4 agents, 2 exits, walls, 3 lasers
        (
            13,
            12,
            [(0, 4), (0, 5), (0, 6), (0, 7)],
            [(10, 9), (10, 10), (11, 9), (11, 10)],
            [
                (3, 0),
                (3, 1),
                (4, 12),
                (4, 11),
                (4, 10),
                (4, 9),
                (4, 8),
                (4, 7),
                (7, 7),
                (8, 7),
                (8, 8),
                (8, 9),
                (8, 10),
                (8, 11),
                (8, 12),
            ],
            [
                (1, (6, 12), Direction.WEST),
                (2, (0, 2), Direction.SOUTH),
                (0, (4, 0), Direction.EAST),
            ],
            17,
            True,
        ),
        (
            13,
            12,
            [(0, 4), (0, 5), (0, 6), (0, 7)],
            [(10, 9), (10, 10), (11, 9), (11, 10)],
            [
                (3, 0),
                (3, 1),
                (4, 12),
                (4, 11),
                (4, 10),
                (4, 9),
                (4, 8),
                (4, 7),
                (7, 7),
                (8, 7),
                (8, 8),
                (8, 9),
                (8, 10),
                (8, 11),
                (8, 12),
            ],
            [
                (1, (6, 12), Direction.WEST),
                (2, (0, 2), Direction.SOUTH),
                (0, (4, 0), Direction.EAST),
            ],
            16,
            False,
        ),
    ],
)
def test_solver(width, height, agents, exits, walls, lasers, t, expected):
    world = make_world(width, height, agents, exits, walls, lasers)
    assert solve(world, t) == expected
