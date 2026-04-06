import pytest
from lle import World

from generators.world_builder import Direction, WorldBuilder
from levels import LLE_LEVELS
from solver import LLEAdapter
from solver.cooperation_solver import CooperationSolver


def cooperation_needed(world: World, t: int) -> bool:
    """Adapt an lle.World and run cooperation analysis."""
    world.reset()
    adapted = LLEAdapter(world)
    solver = CooperationSolver(adapted, T_MAX=t)
    return solver.analyze().cooperation_needed


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
# Cooperation tests on custom grids
# NOTE: these assume the level is solvable at T_MAX.
# ==========================================================


@pytest.mark.parametrize(
    "width,height,agents,exits,walls,lasers,t,expected",
    [
        # 1 agent
        (2, 2, [(0, 0)], [(0, 1)], [], [], 1, False),
        # 1 agent, 1 laser
        (3, 3, [(0, 2)], [(2, 2)], [], [(0, (1, 0), E)], 2, False),
        # 2 agents, no lasers
        (2, 2, [(0, 0), (0, 1)], [(1, 0), (1, 1)], [], [], 1, False),
        # better one
        (3, 3, [(0, 0), (0, 2)], [(2, 2), (2, 0)], [], [(0, (1, 0), E)], 4, True),
        (
            5,
            5,
            [(0, 0), (0, 2), (0, 4)],
            [(4, 1), (4, 2), (4, 3)],
            [],
            [(0, (2, 0), E), (2, (3, 4), W)],
            5,
            True,
        ),
        (
            8,
            8,
            [(0, 1), (1, 1), (0, 2), (1, 2)],
            [(6, 6), (6, 5), (7, 6), (7, 5)],
            [],
            [(0, (3, 0), E), (1, (4, 7), W), (2, (7, 3), N)],
            15,
            True,
        ),
    ],
)
def test_cooperation_solver(width, height, agents, exits, walls, lasers, t, expected):
    world = _world(width, height, agents, exits, walls, lasers)
    assert cooperation_needed(world, t) == expected


# ==========================================================
# LLE default levels
# ==========================================================


@pytest.mark.parametrize(
    "level,expected",
    [
        (1, False),
        (2, False),
        (3, True),
        (4, True),
        (5, True),
        (6, True),
    ],
)
def test_cooperation_lle_levels(level, expected):
    world, t = LLE_LEVELS[level]
    result = cooperation_needed(world, t)
    assert result == expected
