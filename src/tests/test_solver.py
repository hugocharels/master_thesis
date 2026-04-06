import pytest
from lle import World

from generators.world_builder import Direction, WorldBuilder
from solver import LLEAdapter, WorldSolver


def solve(world: World, t: int) -> bool:
    """Adapt an lle.World and solve it."""
    world.reset()
    adapted = LLEAdapter(world)
    solver = WorldSolver(adapted, T_MAX=t)
    return bool(solver.solve()[0])


N, S, E, W = Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST


def _world(width, height, agents=(), exits=(), walls=(), lasers=()):
    """Build an lle.World from components using WorldBuilder."""
    b = WorldBuilder(width, height)
    for idx, pos in enumerate(agents):
        b.add_agent(idx, pos)
    for pos in exits:
        b.add_exit(pos)
    for pos in walls:
        b.add_wall(pos)
    for color, pos, direction in lasers:
        b.add_laser(color, pos, direction)
    return b.build()


# ==========================================================
# Custom grid tests
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
        # 1 agent, 1 exit, walls
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
        # 2 agents, 2 exits, no walls
        (2, 2, [(0, 0), (0, 1)], [(1, 0), (1, 1)], [], [], 1, True),
        (3, 3, [(0, 0), (0, 2)], [(2, 0), (2, 2)], [], [], 1, False),
        (3, 3, [(0, 0), (0, 2)], [(2, 0), (2, 2)], [], [], 2, True),
        # 2 agents, walls blocking entirely
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
        # Narrow corridor
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [(1, 0), (1, 2)],
            [],
            5,
            False,
        ),
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [(1, 0), (1, 2)],
            [],
            6,
            True,
        ),
        # One laser (agent 0 can walk through laser 0)
        (3, 3, [(0, 2)], [(2, 2)], [], [(0, (1, 0), E)], 2, True),
        # Laser blocks path
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [],
            [(0, (1, 0), E)],
            3,
            False,
        ),
        (
            3,
            3,
            [(0, 0), (0, 2)],
            [(2, 0), (2, 2)],
            [],
            [(0, (1, 0), E)],
            4,
            True,
        ),
        # Laser pointing out of bounds must not create a backward beam.
        (3, 3, [(1, 1)], [(1, 2)], [], [(0, (2, 0), W)], 1, True),
    ],
)
def test_solver(width, height, agents, exits, walls, lasers, t, expected):
    world = _world(width, height, agents, exits, walls, lasers)
    assert solve(world, t) == expected


# ==========================================================
# LLE default levels (no manual coordinates needed)
# ==========================================================


@pytest.mark.parametrize(
    "level,t,expected",
    [
        (1, 10, True),
        (1, 9, False),
        (2, 10, True),
        (2, 9, False),
        (3, 10, True),
        (3, 9, False),
        (4, 10, True),
        (4, 9, False),
        (5, 19, True),
        (5, 18, False),
        (6, 21, True),
        (6, 20, False),
    ],
)
def test_lle_levels(level, t, expected):
    world = World.level(level)
    assert solve(world, t) == expected
