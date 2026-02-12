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
    world.add_entity(Agent((0, 0), 0))
    world.add_entity(Entity((9, 9), CellType.EXIT))
    display(LLE.from_str(world.to_str()).build())


if __name__ == "__main__":
    main()
