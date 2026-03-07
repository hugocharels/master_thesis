import os

import matplotlib.pyplot as plt
from lle import LLE
from matplotlib.animation import FuncAnimation, PillowWriter

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
            print(e)
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


def create_gif(world, solver, model, filename="agent_movement.gif", duration=500):
    """
    Create a GIF showing the agent moving from start to end.

    Args:
        world: The world object
        solver: The WorldSolver instance
        model: The solved model
        filename: Name of the output GIF file (default: "agent_movement.gif")
        duration: Duration between frames in milliseconds (default: 500ms)
    """
    env = LLE.from_str(world.to_str()).build()

    # Collect all images first
    images = [env.get_image()]
    step_count = 0

    print(f"Creating GIF with initial state...")

    for actions in solver.extract_plan(model):
        try:
            env.world.step(actions)
            images.append(env.get_image())
            step_count += 1
            print(f"Added step {step_count}")
        except Exception as e:
            print(f"Error at step {step_count}: {e}")
            break

    print(f"Total frames: {len(images)}")

    # Create the animation
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.axis("off")

    # Display first image
    im = ax.imshow(images[0])
    title = ax.set_title(f"Step 0/{len(images) - 1}")

    def animate(frame):
        im.set_array(images[frame])
        title.set_text(f"Step {frame}/{len(images) - 1}")
        return [im, title]

    # Create animation
    anim = FuncAnimation(
        fig, animate, frames=len(images), interval=duration, blit=True, repeat=True
    )

    # Save as GIF
    print(f"Saving GIF as '{filename}'...")
    writer = PillowWriter(fps=int(1000 / duration))  # Convert duration to fps
    anim.save(filename, writer=writer)

    plt.close()
    print(f"GIF saved successfully as '{filename}'")

    # Return the absolute path
    return os.path.abspath(filename)


WORLD = (
    13,
    12,
    [(0, 4), (0, 5), (0, 6), (0, 7)],
    [(10, 9), (10, 10), (11, 9), (11, 10)],
    [
        (3, 0),
        (3, 1),
        (4, 12),
        (4, 11),
        (4, 10),
        (4, 9),
        (4, 8),
        (4, 7),
        (7, 7),
        (8, 7),
        (8, 8),
        (8, 9),
        (8, 10),
        (8, 11),
        (8, 12),
    ],
    [
        (1, (6, 12), Direction.WEST),
        (2, (0, 2), Direction.SOUTH),
        (0, (4, 0), Direction.EAST),
    ],
)
T_MAX = 20


def main():
    world = make_world(*WORLD)
    solver = WorldSolver(world, T_MAX)

    is_solvable, model = solver.solve()
    print("Solvable:", is_solvable)

    if is_solvable:
        solver.print_model(model)
        print(solver.extract_plan(model))

        # Create GIF
        gif_path = create_gif(
            world, solver, model, "agent_solution_level6.gif", duration=500
        )
        print(f"GIF created at: {gif_path}")

        # Still show interactive display
        display_sequence_interactive(world, solver, model)
    else:
        print("No solution found, cannot create GIF")


def main2():

    # Create solver with profiling enabled
    solver = WorldSolver(make_world(*WORLD), T_MAX=T_MAX, enable_profiling=True)

    # Solve the problem
    result, model = solver.solve()

    # Get profiling data as dictionary
    profiling_data = solver.get_profiling_data()
    if profiling_data is None:
        print("No profiling data available")
        return

    print("Total clauses generated:", profiling_data["total_clauses"])
    print("Total generation time:", profiling_data["total_generation_time"])
    print("Solve time:", profiling_data["solve_time"])

    # Export to JSON
    solver.export_profiling_json("profiling_results_level6.json")

    # Export to CSV
    solver.export_profiling_csv("profiling_results_level6.csv")

    # Print constraint breakdown
    for constraint_name, constraint_data in profiling_data["constraints"].items():
        print(f"\n{constraint_name}:")
        print(f"  Total clauses: {constraint_data['num_clauses']}")
        print(f"  Generation time: {constraint_data['generation_time']:.4f}s")
        print("  Methods:")
        for method_name, method_data in constraint_data["method_profiles"].items():
            print(
                f"    {method_name}: {method_data['clauses']} clauses, {method_data['time']:.4f}s"
            )


if __name__ == "__main__":
    # main()
    main2()
