from pickletools import dis

from core import Agent, CellType, Entity, World
from solver import WorldSolver


def display_world(world: World):
    import matplotlib.pyplot as plt
    from lle import LLE

    env = LLE.from_str(world.to_str()).build()
    plt.imshow(env.get_image())
    plt.axis("off")
    plt.show()


def main():

    world = World(3, 3)
    world.add_entity((0, 0), Agent(0))
    world.add_entity((0, 2), Agent(1))
    world.add_entity((2, 0), Entity(CellType.EXIT))
    world.add_entity((2, 2), Entity(CellType.EXIT))
    solver = WorldSolver(world, T_MAX=1)

    is_solvable, model = solver.solve()
    print("Solvable:", is_solvable)
    # solver.print_model(model)

    display_world(world)


if __name__ == "__main__":
    main()
