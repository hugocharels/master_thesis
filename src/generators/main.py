import matplotlib.pyplot as plt
from core.types import Agent, CellType, Entity
from core.world import World
from lle import LLE


def display(env: LLE):
    plt.imshow(env.get_image())
    plt.axis("off")
    plt.show()


def main():
    world = World(10, 10)
    world.add_entity((0, 0), Agent(0))
    world.add_entity((0, 9), Agent(1))
    world.add_entity((9, 9), Entity(CellType.EXIT))
    world.add_entity((9, 0), Entity(CellType.EXIT))
    display(LLE.from_str(world.to_str()).build())


if __name__ == "__main__":
    main()
