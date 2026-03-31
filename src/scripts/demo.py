"""Demo script: solve a level and visualize the solution."""

import os

import matplotlib.pyplot as plt
from lle import World
from matplotlib.animation import FuncAnimation, PillowWriter

from solver import LLEAdapter, WorldSolver

from .custom_levels import CUSTOM_BENCHMARK_LEVELS


def display_sequence_interactive(world: World, solver, model):
    """Step through the solution with arrow keys."""
    world.reset()
    images = [world.get_image()]
    for actions in solver.extract_plan(model):
        try:
            world.step(list(actions))
            images.append(world.get_image())
        except Exception as e:
            print(e)
            break

    current_idx = 0
    fig, ax = plt.subplots()
    im = ax.imshow(images[current_idx])
    ax.axis("off")
    ax.set_title(
        f"Step {current_idx}/{len(images) - 1} — arrows to navigate, 'q' to quit"
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
            f"Step {current_idx}/{len(images) - 1} — arrows to navigate, 'q' to quit"
        )
        fig.canvas.draw()

    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()


def create_gif(
    world: World, solver, model, filename="agent_movement.gif", duration=500
):
    """Create a GIF of the solution."""
    world.reset()
    images = [world.get_image()]
    step_count = 0
    for actions in solver.extract_plan(model):
        try:
            world.step(list(actions))
            images.append(world.get_image())
            step_count += 1
        except Exception as e:
            print(f"Error at step {step_count}: {e}")
            break

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.axis("off")
    im = ax.imshow(images[0])
    title = ax.set_title(f"Step 0/{len(images) - 1}")

    def animate(frame):
        im.set_array(images[frame])
        title.set_text(f"Step {frame}/{len(images) - 1}")
        return [im, title]

    anim = FuncAnimation(
        fig, animate, frames=len(images), interval=duration, blit=True, repeat=True
    )
    writer = PillowWriter(fps=int(1000 / duration))
    anim.save(filename, writer=writer)
    plt.close()
    print(f"GIF saved: {os.path.abspath(filename)}")


def main():
    world = World.level(6)
    world.reset()

    level = "5x5_agents=3_lasers=2"

    world = CUSTOM_BENCHMARK_LEVELS[level][0]
    adapted = LLEAdapter(world)

    solver = WorldSolver(adapted, T_MAX=CUSTOM_BENCHMARK_LEVELS[level][1])
    # solver = WorldSolver(adapted, T_MAX=15)

    is_solvable, model = solver.solve()
    print("Solvable:", is_solvable)

    if is_solvable:
        print(solver.extract_plan(model))
        create_gif(world, solver, model, f"{level}.gif", duration=500)
        display_sequence_interactive(world, solver, model)
    else:
        print("No solution found")


if __name__ == "__main__":
    main()
