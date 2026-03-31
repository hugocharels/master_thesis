"""Example custom benchmark levels built with WorldBuilder."""

from lle.lle import World

from generators.world_builder import Direction, WorldBuilder


def _world(width, height, agents=(), exits=(), walls=(), lasers=()):
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


N, S, E, W = Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST


# dict[label] = (world, t_max)
CUSTOM_BENCHMARK_LEVELS: dict[str, tuple[World, int]] = {
    "3x3_agents=2_lasers=1": (
        _world(
            width=3,
            height=3,
            agents=[(0, 0), (0, 2)],
            exits=[(2, 2), (2, 0)],
            lasers=[(0, (1, 0), E)],
        ),
        4,
    ),
    "5x5_agents=3_lasers=2": (
        _world(
            width=5,
            height=5,
            agents=[(0, 0), (0, 2), (0, 4)],
            exits=[(4, 1), (4, 2), (4, 3)],
            lasers=[(0, (2, 0), E), (2, (3, 4), W)],
        ),
        5,
    ),
    "8x8_agents=4_lasers=3": (
        _world(
            width=8,
            height=8,
            agents=[(0, 1), (1, 1), (0, 2), (1, 2)],
            exits=[(6, 6), (6, 5), (7, 6), (7, 5)],
            lasers=[(0, (3, 0), E), (1, (4, 7), W), (2, (7, 3), N)],
        ),
        15,
    ),
    "lle_level6": (
        World.level(6),
        21,
    ),
}
