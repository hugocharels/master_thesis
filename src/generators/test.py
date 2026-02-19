from core import Agent, CellType, Entity, World
from solver import WorldSolver


def main():

    world = World(2, 2)
    world.add_entity((0, 0), Agent(0))
    world.add_entity((1, 1), Entity(CellType.EXIT))

    solver = WorldSolver(world, T_MAX=2)
    is_solvable, model = solver.generate()
    print("Solvable:", is_solvable)
    print(model)


if __name__ == "__main__":
    main()
