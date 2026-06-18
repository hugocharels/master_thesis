"""Generate step-by-step construction images for generator slides.

Renders intermediate states of level construction:
  - Constructive: empty → agents+exits → +walls → +lasers (full)
  - Level6Style:   empty → agents+exits → +lasers → +walls (full)

Every intermediate world is a valid LLE world.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lle import World
from lle.tiles import Direction

# Add project src to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from generators.world_builder import WorldBuilder

OUTDIR = Path(__file__).parent
OUTDIR.mkdir(parents=True, exist_ok=True)


def save_world(builder: WorldBuilder, path: Path):
    """Build an LLE world and render to a PNG file."""
    world = builder.build()
    plt.imsave(path, world.get_image())
    print(f"  {path}")


# ─── Constructive generator: 7×7, 2 agents ────────────────────────────────────


def demo_constructive(rows=7, cols=7):
    print("\nConstructive generator steps:")
    prefix = "constructive"

    # Parameters
    agents = [(1, 0), (4, 0)]
    exits = [(1, cols - 1), (4, cols - 1)]
    walls = [(2, 2), (2, 3), (5, 3), (5, 4)]

    # Step 1: empty grid rendered as white with lines
    white_grid(prefix, rows, cols, "01_empty")

    # Step 2: agents + exits (minimal valid world)
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    save_world(b, OUTDIR / f"{prefix}_02_agents_exits.png")

    # Step 3: + walls
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    for pos in walls:
        b.add_wall(pos)
    save_world(b, OUTDIR / f"{prefix}_03_walls.png")

    # Step 4: full (+ lasers)
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    for pos in walls:
        b.add_wall(pos)
    b.add_laser(0, (6, 1), Direction.EAST)  # bottom row, shoots right
    b.add_laser(1, (0, 5), Direction.SOUTH)  # top row, shoots down
    save_world(b, OUTDIR / f"{prefix}_04_full.png")


# ─── Level6Style generator: 9×9, 2 agents, 2 lasers ─────────────────────────


def demo_level6(rows=9, cols=9):
    print("\nLevel6Style generator steps:")
    prefix = "level6style"

    # Parameters
    agents = [(0, 3), (0, 4)]
    exits = [(rows - 1, 3), (rows - 1, 4)]
    walls = [(3, 1), (3, 2), (3, 3), (6, 5), (6, 6), (6, 7)]

    # Step 1: empty
    white_grid(prefix, rows, cols, "01_empty")

    # Step 2: agents + exits
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    save_world(b, OUTDIR / f"{prefix}_02_agents_exits.png")

    # Step 3: + lasers in corridor
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    b.add_laser(0, (2, 0), Direction.EAST)
    b.add_laser(1, (5, cols - 1), Direction.WEST)
    save_world(b, OUTDIR / f"{prefix}_03_lasers.png")

    # Step 4: full (+ walls)
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    b.add_laser(0, (2, 0), Direction.EAST)
    b.add_laser(1, (5, cols - 1), Direction.WEST)
    for pos in walls:
        b.add_wall(pos)
    save_world(b, OUTDIR / f"{prefix}_04_full.png")


# ─── Random generator quick example ────────────────────────────────────────


def demo_random(rows=6, cols=6):
    print("\nRandom generator example:")
    w = [(1, 2), (1, 3), (2, 2), (3, 4), (4, 3)]

    b = WorldBuilder(cols, rows)
    b.add_agent(0, (0, 0))
    b.add_agent(1, (rows - 1, cols - 1))
    b.add_exit((0, cols - 1))
    b.add_exit((rows - 1, 0))
    for pos in w:
        b.add_wall(pos)
    b.add_laser(0, (1, 1), Direction.EAST)
    b.add_laser(1, (3, 3), Direction.SOUTH)
    save_world(b, OUTDIR / "random_example.png")


# ─── Helper: white grid with LLE tile dimensions ────────────────────────────


def white_grid(prefix, rows, cols, suffix):
    """Render a white grid with tile borders using LLE tile dimensions."""
    # Need at least 1 agent + 1 exit to get tile size from LLE
    b = WorldBuilder(cols, rows)
    b.add_agent(0, (0, 0))
    b.add_exit((rows - 1, cols - 1))
    world = b.build()
    img = world.get_image().copy()
    h, w = img.shape[:2]
    tile_h, tile_w = h // rows, w // cols
    # White background
    img[:, :] = (1.0, 1.0, 1.0)
    # Grid lines
    for ry in range(rows + 1):
        y = ry * tile_h
        if y < h:
            img[y, :] = (0.6, 0.6, 0.6)
    for cx in range(cols + 1):
        x = cx * tile_w
        if x < w:
            img[:, x] = (0.6, 0.6, 0.6)
    out_path = OUTDIR / f"{prefix}_{suffix}.png"
    plt.imsave(out_path, img)
    print(f"  {out_path}")


# ─── Bad vs Constrained random examples ──────────────────────────────────────


def demo_random_bad():
    """A badly placed random laser (points outside the grid)."""
    print("\nBad random example (laser points off-grid):")
    b = WorldBuilder(6, 6)
    b.add_agent(0, (0, 0))
    b.add_agent(1, (5, 5))
    b.add_exit((0, 5))
    b.add_exit((5, 0))
    for pos in [(1, 2), (1, 3), (2, 2), (3, 4), (4, 3)]:
        b.add_wall(pos)
    # Laser on the left edge pointing WEST = immediately leaves the grid
    b.add_laser(0, (2, 0), Direction.WEST)
    b.add_laser(1, (3, 3), Direction.SOUTH)
    save_world(b, OUTDIR / "random_bad.png")


def demo_random_constrained():
    """Same layout but with fixed laser direction + additional wall."""
    print("\nConstrained random example (geometric filters applied):")
    b = WorldBuilder(6, 6)
    b.add_agent(0, (0, 0))
    b.add_agent(1, (5, 5))
    b.add_exit((0, 5))
    b.add_exit((5, 0))
    for pos in [(1, 2), (1, 3), (2, 2), (3, 4)]:
        b.add_wall(pos)
    # Fixed: laser now points EAST (stays inside the grid)
    b.add_laser(0, (2, 0), Direction.EAST)
    b.add_laser(1, (3, 3), Direction.SOUTH)
    save_world(b, OUTDIR / "random_constrained.png")


if __name__ == "__main__":
    demo_constructive()
    demo_level6()
    demo_random()
    demo_random_bad()
    demo_random_constrained()
    print(f"\nDone. Images saved to {OUTDIR}")
