"""Generate step-by-step construction images for generator slides.

Builds a complete cooperative level FIRST, verifies it, then derives
intermediate states backward (remove lasers, then walls) for the slides.

Step order for the slides (animation plays forward; script builds backward):
  1. Empty grid (white)
  2. Agents + exits
  3. + walls
  4. + lasers (full cooperative level)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lle import World
from lle.tiles import Direction

# Add project src to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lle.tiles import Direction

from generators.cooperative import CooperativeGenerator
from generators.level6_style import Level6StyleGenerator
from generators.world_builder import WorldBuilder
from solver.world_solver import LaserMode, WorldSolver

OUTDIR = Path(__file__).parent
OUTDIR.mkdir(parents=True, exist_ok=True)


def build_world(
    rows: int,
    cols: int,
    agents: list[tuple[int, int]],
    exits: list[tuple[int, int]],
    walls: list[tuple[int, int]],
    lasers: list[tuple[int, tuple[int, int], Direction]],
) -> World:
    b = WorldBuilder(cols, rows)
    for i, pos in enumerate(agents):
        b.add_agent(i, pos)
    for pos in exits:
        b.add_exit(pos)
    for pos in walls:
        b.add_wall(pos)
    for laser in lasers:
        b.add_laser(laser[0], laser[1], laser[2])
    return b.build()


def save_world(world: World, path: Path) -> None:
    """Render an LLE world to a PNG file."""
    plt.imsave(path, world.get_image())
    print(f"  {path}")


def is_cooperative(world: World, t_max: int = 20) -> bool:
    """True iff standard SAT and strict UNSAT."""
    standard = WorldSolver(world, laser_mode=LaserMode.STANDARD, T_MAX=t_max)
    strict = WorldSolver(world, laser_mode=LaserMode.STRICT, T_MAX=t_max)
    return standard.solve()[0] and not strict.solve()[0]


def white_grid(prefix: str, rows: int, cols: int, suffix: str) -> None:
    """Render a white grid with tile borders (LLE tile dimensions)."""
    # Need at least 1 agent + 1 exit to get tile size from LLE
    b = WorldBuilder(cols, rows)
    b.add_agent(0, (0, 0))
    b.add_exit((rows - 1, cols - 1))
    world = b.build()
    img = world.get_image().copy()
    h, w = img.shape[:2]
    tile_h = h // rows
    tile_w = w // cols
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


def derive_steps(
    prefix: str,
    rows: int,
    cols: int,
    agents: list[tuple[int, int]],
    exits: list[tuple[int, int]],
    walls: list[tuple[int, int]],
    lasers: list[tuple[int, tuple[int, int], Direction]],
    t_max: int = 20,
) -> None:
    """Build full cooperative level, verify, then save intermediates backwards."""
    # 1) Build full level first
    world = build_world(rows, cols, agents, exits, walls, lasers)

    # 2) Verify it's cooperative
    assert is_cooperative(world, t_max=t_max), (
        f"Full level ({prefix}) is NOT cooperative!"
    )
    print(f"  -> Verified cooperative (t_max={t_max})")

    # 3) Save steps BACKWARD (full → no lasers → no walls → white grid)
    # Step 4: full
    save_world(world, OUTDIR / f"{prefix}_04_full.png")

    # Step 3: remove lasers
    world_no_lasers = build_world(rows, cols, agents, exits, walls, lasers=[])
    save_world(world_no_lasers, OUTDIR / f"{prefix}_03_walls.png")

    # Step 3: remove walls
    world_no_walls = build_world(rows, cols, agents, exits, [], lasers)
    save_world(world_no_walls, OUTDIR / f"{prefix}_03_lasers.png")

    # Step 2: also remove walls
    world_agents_only = build_world(rows, cols, agents, exits, walls=[], lasers=[])
    save_world(world_agents_only, OUTDIR / f"{prefix}_02_agents_exits.png")

    # Step 1: white grid
    white_grid(prefix, rows, cols, "01_empty")


def extract_world(world):
    """
    Extract objects from generated world.
    Adjust tile access depending on your LLE version.
    """
    agents = []
    exits = []
    walls = []
    lasers = []

    for r in range(world.height):
        for c in range(world.width):
            tile = world.get_tile((r, c))

            if tile.is_agent():
                agents.append((r, c))

            if tile.is_exit():
                exits.append((r, c))

            if tile.is_wall():
                walls.append((r, c))

            if tile.is_laser():
                lasers.append((tile.laser.owner, (r, c), tile.laser.direction))

    return agents, exits, walls, lasers


# ─── Demo: Constructive generator (lane-based, 2 agents, 7x7) ──────────────────


def demo_constructive(rows: int = 7, cols: int = 7) -> None:
    print("\nConstructive generator steps:")
    prefix = "constructive"

    agents = [(1, 0), (4, 0)]
    exits = [(1, cols - 1), (4, cols - 1)]
    walls = [(2, 2), (2, 3), (5, 3), (5, 4)]
    lasers = [
        LaserSpec(0, (6, 1), Direction.EAST),
        LaserSpec(1, (0, 5), Direction.SOUTH),
    ]

    derive_steps(prefix, rows, cols, agents, exits, walls, lasers, t_max=15)


def demo_constructive_generator():

    print("\nReal constructive generator:")

    gen = CooperativeGenerator(
        size=(7, 7),
        agents=2,
        lasers=2,
        num_walls=4,
        max_attempts=10000,
        seed=0,
    )

    world = gen.generate()

    print("Constructive generated after", gen.last_attempts, "attempts")

    agents, exits, walls, lasers = world

    derive_steps(
        "constructive_generated",
        7,
        7,
        agents,
        exits,
        walls,
        lasers,
        t_max=20,
    )


# ─── Demo: Level-6-Style generator (clustered, 9x9, 2 agents) ─────────────────


def demo_level6(rows: int = 9, cols: int = 9) -> None:
    print("\nLevel6Style generator steps:")
    prefix = "level6style"

    agents = [(0, 3), (0, 4)]
    exits = [(rows - 1, 3), (rows - 1, 4)]
    walls = [(3, 1), (3, 2), (3, 3), (6, 5), (6, 6), (6, 7)]
    lasers = [
        LaserSpec(0, (2, 0), Direction.EAST),
        LaserSpec(1, (5, cols - 1), Direction.WEST),
    ]

    derive_steps(prefix, rows, cols, agents, exits, walls, lasers, t_max=20)


def demo_level6_generator():

    print("\nReal level6 generator:")

    gen = Level6StyleGenerator(
        size=(10, 10),
        agents=4,
        lasers=3,
        num_walls=8,
        max_attempts=100000,
        seed=1,
    )

    world = gen.generate()

    print("Level6 generated after", gen.last_attempts, "attempts")

    agents, exits, walls, lasers = world

    derive_steps(
        "level6_generated",
        10,
        10,
        agents,
        exits,
        walls,
        lasers,
        t_max=25,
    )


# ─── Demo: Random (static bad vs constrained examples) ────────────────────────


def demo_random(rows: int = 6, cols: int = 6) -> None:
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
    save_world(b.build(), OUTDIR / "random_example.png")


def demo_random_bad() -> None:
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
    save_world(b.build(), OUTDIR / "random_bad.png")


def demo_random_constrained() -> None:
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
    save_world(b.build(), OUTDIR / "random_constrained.png")


if __name__ == "__main__":
    demo_constructive_generator()
    demo_level6_generator()
    demo_random()
    demo_random_bad()
    demo_random_constrained()
    print(f"\nDone. Images saved to {OUTDIR}")
