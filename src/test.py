from core import Agent, CellType, Direction, Entity, Laser, World
from solver import WorldSolver


def display_world(world: World):
    import matplotlib.pyplot as plt
    from lle import LLE

    env = LLE.from_str(world.to_str()).build()
    plt.imshow(env.get_image())
    plt.axis("off")
    plt.show()


def main():

    world = World(5, 5)
    world.add_entity((2, 2), Agent(0))
    world.add_entity((4, 4), Entity(CellType.EXIT))

    for pos in [(1, 1), (1, 2), (1, 4), (2, 1), (2, 4), (3, 1), (3, 2), (3, 3), (3, 4)]:
        world.add_entity(pos, Entity(CellType.WALL))
    # world.add_entity((1, 0), Laser(0, Direction.EAST))
    solver = WorldSolver(world, T_MAX=14)

    is_solvable, model = solver.solve()
    print("Solvable:", is_solvable)
    # solver.print_model(model)

    display_world(world)


if __name__ == "__main__":
    main()
