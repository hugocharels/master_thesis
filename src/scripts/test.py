from lle.lle import World

import runpy
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if __name__ == "__main__":
        runpy.run_module("scripts.test", run_name="__main__")
        raise SystemExit(0)

from solver import CooperationSolver, LLEAdapter, WorldSolver

from .custom_levels import CUSTOM_BENCHMARK_LEVELS


def main():
    # level = "3x3_agents=2_lasers=1"

    # world = CUSTOM_BENCHMARK_LEVELS[level][0]
    # adapted = LLEAdapter(world)

    # solvability_solver = WorldSolver(adapted)
    # solvable = solvability_solver.solve()[0]
    # print(f"Level {level} solvable: {solvable}")

    # solver = CooperationSolver(adapted, T_MAX=CUSTOM_BENCHMARK_LEVELS[level][1])

    # result = solver.analyze().cooperation_needed
    # print(f"Cooperation needed for {level}: {result}")

    from generators.world_builder import Direction, WorldBuilder

    builder = WorldBuilder(3, 3)
    builder.add_agent(0, (1, 1))
    builder.add_exit((1, 2))
    builder.add_laser(0, (2, 0), Direction.WEST)

    world = builder.build()

    from matplotlib import pyplot as plt

    plt.imshow(world.get_image())
    plt.axis("off")
    plt.show()

    print(WorldSolver(LLEAdapter(world), T_MAX=2).solve()[0])


if __name__ == "__main__":
    main()
