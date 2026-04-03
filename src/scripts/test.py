from solver import CooperationSolver, LLEAdapter, WorldSolver

from .custom_levels import CUSTOM_BENCHMARK_LEVELS


def main():
    level = "3x3_agents=2_lasers=1"

    world = CUSTOM_BENCHMARK_LEVELS[level][0]
    adapted = LLEAdapter(world)

    solvability_solver = WorldSolver(adapted)
    solvable = solvability_solver.solve()[0]
    print(f"Level {level} solvable: {solvable}")

    solver = CooperationSolver(adapted, T_MAX=CUSTOM_BENCHMARK_LEVELS[level][1])

    result = solver.analyze().cooperation_needed
    print(f"Cooperation needed for {level}: {result}")


if __name__ == "__main__":
    main()
