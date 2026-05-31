"""Render filmstrips of the default LLE levels (1-6) being solved.

For each default level we solve it with the bounded-horizon SAT solver, replay
the resulting joint plan through ``lle.World``, capture the rendered frame at
each timestep, and assemble an evenly-sampled selection into a single filmstrip
figure (one row of frames, each labelled with its timestep).

A static PDF cannot embed an animation, so the filmstrip is the portable
substitute for "watch the level being solved".

Run with the solver venv::

    PYTHONPATH=src python -m scripts.make_solved_filmstrips
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import lle

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solver.world_solver import WorldSolver

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "solved_levels"

# Known minimum solvable horizons for the default levels (see src/levels.py).
T_MAX = {1: 10, 2: 10, 3: 10, 4: 10, 5: 19, 6: 21}
MAX_FRAMES = 7  # frames shown per filmstrip (evenly sampled, including first/last)


def _select(n: int, k: int) -> list[int]:
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def _solve_frames(level: int):
    world = lle.World.level(level)
    solver = WorldSolver(world, T_MAX=T_MAX[level])
    result, model = solver.solve()
    if not result:
        raise RuntimeError(f"level {level} UNSAT at T_MAX={T_MAX[level]}")
    plan = solver.extract_plan(model)

    world.reset()
    frames = [world.get_image()]
    for joint in plan:
        world.step([a for a in joint])
        frames.append(world.get_image())
    return frames


def make_filmstrip(level: int) -> None:
    frames = _solve_frames(level)
    idx = _select(len(frames), MAX_FRAMES)
    sel = [(t, frames[t]) for t in idx]

    fig, axes = plt.subplots(1, len(sel), figsize=(1.9 * len(sel), 2.2))
    if len(sel) == 1:
        axes = [axes]
    for ax, (t, frame) in zip(axes, sel):
        ax.imshow(frame)
        ax.set_title(f"$t = {t}$", fontsize=9)
        ax.axis("off")
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"level_{level}_filmstrip.png", dpi=150, bbox_inches="tight")
    fig.savefig(OUT / f"level_{level}_filmstrip.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  level {level}: {len(frames)} frames -> {idx}")


if __name__ == "__main__":
    for lvl in range(1, 7):
        make_filmstrip(lvl)
    print("wrote filmstrips to", OUT)
