import matplotlib.pyplot as plt
from lle import LLE
from typing_extensions import Dict

from core import Agent, CellType, Direction, Entity, Laser, World
from solver import WorldSolver


def display_world(world: World):
    env = LLE.from_str(world.to_str()).build()
    plt.imshow(env.get_image())
    plt.axis("off")
    plt.show()


def display_lle(level):
    env = LLE.level(level).build()
    plt.imshow(env.get_image())
    plt.axis("off")
    plt.show()


def make_world(width, height, agents=(), exits=(), walls=(), lasers=()):
    world = World(width, height)
    for c, pos in enumerate(agents):
        world.add_entity(pos, Agent(c))
    for pos in exits:
        world.add_entity(pos, Entity(CellType.EXIT))
    for pos in walls:
        world.add_entity(pos, Entity(CellType.WALL))
    for c, pos, direction in lasers:
        world.add_entity(pos, Laser(c, direction=direction))
    return world


def display_sequence_interactive(world, solver, model):
    env = LLE.from_str(world.to_str()).build()

    # Collect all images first
    images = [env.get_image()]
    for actions in solver.extract_plan(model):
        try:
            env.world.step(actions)
            images.append(env.get_image())
        except Exception as e:
            plt.imshow(env.get_image())
            plt.axis("off")
            plt.show()

    # Interactive display
    current_idx = 0

    fig, ax = plt.subplots()
    im = ax.imshow(images[current_idx])
    ax.axis("off")
    ax.set_title(
        f"Step {current_idx}/{len(images) - 1} - Use arrow keys to navigate, 'q' to quit"
    )

    def on_key(event):
        nonlocal current_idx
        if event.key == "right" and current_idx < len(images) - 1:
            current_idx += 1
        elif event.key == "left" and current_idx > 0:
            current_idx -= 1
        elif event.key == "q":
            plt.close()
            return

        im.set_array(images[current_idx])
        ax.set_title(
            f"Step {current_idx}/{len(images) - 1} - Use arrow keys to navigate, 'q' to quit"
        )
        fig.canvas.draw()

    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()


def main():

    # world = make_world(
    #     13,
    #     12,
    #     [(0, 4), (0, 5), (0, 6), (0, 7)],
    #     [(10, 9), (10, 10), (11, 9), (11, 10)],
    #     [
    #         (3, 0),
    #         (3, 1),
    #         (4, 12),
    #         (4, 11),
    #         (4, 10),
    #         (4, 9),
    #         (4, 8),
    #         (4, 7),
    #         (7, 7),
    #         (8, 7),
    #         (8, 8),
    #         (8, 9),
    #         (8, 10),
    #         (8, 11),
    #         (8, 12),
    #     ],
    #     [
    #         (1, (6, 12), Direction.WEST),
    #         (2, (0, 2), Direction.SOUTH),
    #         (0, (4, 0), Direction.EAST),
    #     ],
    # )
    T_MAX = 5
    world = make_world(3, 3, [(0, 0)], [(2, 0)], [(1, 0)], [])

    solver = WorldSolver(world, T_MAX)

    # world = make_world(3, 3, [(0, 0), (0, 2)], [(2, 0), (2, 2)], [(1, 0), (1, 2)], [])
    # solver = WorldSolver(world, T_MAX=6)

    is_solvable, model = solver.solve()
    print("Solvable:", is_solvable)

    if is_solvable:
        # solver.print_model(model)
        print(solver.extract_plan(model))

    display_sequence_interactive(world, solver, model)


if __name__ == "__main__":
    main()
