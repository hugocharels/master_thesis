"""Render every 2-laser curriculum-strategy pool level to PNG for the thesis appendix.

Sibling of ``render_curriculum_strategy_pools.py`` but for the fixed-grid
0L -> 1L -> 2L ladder of ``experiments.curriculum_strategy_2L``. For each pool
(rung + split) it writes:

- ``images/level_NNN.png``  LLE-rendered PNG (one per level)
- ``params.json``           generator, effective parameters, profile, seed, count

Run from the project root with the marl venv (bare script, like
``generate_appendix_galleries.py``)::

    C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe \
        src/scripts/render_curriculum_strategy_2L_pools.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Allow running as a bare script (python src/scripts/...) as well as -m.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.curriculum.pool_generator import load_pool, pool_path
from experiments.curriculum_strategy_2L._preflight import BASE_DIR, pool_jobs
from experiments.curriculum_strategy_2L.configs import RUNG_PROFILES


def _effective_num_walls(height: int, width: int) -> int:
    """The generator's default when ``num_walls`` is not passed (area // 10)."""
    return (height * width) // 10


def render_all() -> None:
    for rung, split, seed, n in pool_jobs():
        d = pool_path(BASE_DIR, rung, split)
        worlds = load_pool(d)
        img_dir = d / "images"
        img_dir.mkdir(exist_ok=True)
        for i, world in enumerate(worlds):
            world.reset()
            plt.imsave(img_dir / f"level_{i:03d}.png", world.get_image())
        params = {
            "generator": rung.generator_name,
            "profile": RUNG_PROFILES.get(rung.stage_id),
            "size": [rung.height, rung.width],
            "agents": rung.n_agents,
            "lasers": rung.n_lasers,
            "t_max": rung.t_max,
            "num_walls": _effective_num_walls(rung.height, rung.width),
            "seed": seed,
            "n_levels": len(worlds),
            "split": split,
        }
        (d / "params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
        print(f"  rung {rung.stage_id} {split}: {len(worlds)} PNGs -> {img_dir}")


if __name__ == "__main__":
    render_all()
    print("Done.")
