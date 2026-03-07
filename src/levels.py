"""
LLE default level definitions.

Single source of truth used by tests, benchmarks, and scripts.
The T_MAX values are the known minimum steps for solvability.
"""

from lle import World

# level number -> (lle.World, T_MAX)
LLE_LEVELS: dict[int, tuple[World, int]] = {}


def _register():
    t_max_per_level = {1: 10, 2: 10, 3: 10, 4: 10, 5: 19, 6: 20}
    for level_num, t_max in t_max_per_level.items():
        world = World.level(level_num)
        world.reset()
        LLE_LEVELS[level_num] = (world, t_max)


_register()
