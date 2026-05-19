"""Generate the appendix generator-gallery pools.

For each row in ``GALLERY`` below, instantiate the named generator with the
listed parameters and a deterministic seed, draw ``n_samples`` levels, and
write them under ``results/appendix_galleries/<label>/``:

- ``levels/level_NNN.txt``    world strings (so the pool is re-renderable)
- ``images/level_NNN.png``    LLE-rendered PNG (used by the thesis appendix)
- ``params.json``             generator name, parameters, seed, sample count

The appendix Typst sections include the ``images/`` grid for each pool plus
a small parameter table read from ``params.json``.

Run from the project root::

    python3.13 src/scripts/generate_appendix_galleries.py

The script is idempotent at the *pool* level: a pool whose ``params.json``
already records ``n_samples_generated == n_samples_requested`` is skipped.
Delete the pool directory to force regeneration.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from generators import GENERATOR_REGISTRY

OUTPUT_ROOT = PROJECT_ROOT / "results" / "appendix_galleries"

# Each row: (label, generator_name, params_dict, n_samples, seed, optional profile)
# profile is honored only for the "cooperative" generator family.
GALLERY: list[tuple] = [
    # ---- Constrained Random generator (with geometric validation) ----
    ("04_constrained_random_3x3_2a_1L",
     "random",
     {"size": (3, 3), "agents": 2, "lasers": 1, "t_max": 6,
      "num_walls": 1, "validate_geometry": True, "max_attempts": 2000},
     16, 20260611, None),
    ("05_constrained_random_5x5_3a_2L",
     "random",
     {"size": (5, 5), "agents": 3, "lasers": 2, "t_max": 10,
      "num_walls": 2, "validate_geometry": True, "max_attempts": 2000},
     16, 20260612, None),
    ("06_constrained_random_7x7_4a_2L",
     "random",
     {"size": (7, 7), "agents": 4, "lasers": 2, "t_max": 14,
      "num_walls": 4, "validate_geometry": True, "max_attempts": 5000},
     16, 20260613, None),
    # ---- Constructive (solvable) ----
    ("07_constructive_5x5_3a_1L",
     "constructive",
     {"size": (5, 5), "agents": 3, "lasers": 1, "t_max": 10,
      "num_walls": 3, "max_attempts": 1000},
     16, 20260621, None),
    ("08_constructive_7x7_4a_2L",
     "constructive",
     {"size": (7, 7), "agents": 4, "lasers": 2, "t_max": 14,
      "num_walls": 5, "max_attempts": 1000},
     16, 20260622, None),
    ("09_constructive_9x9_4a_3L",
     "constructive",
     {"size": (9, 9), "agents": 4, "lasers": 3, "t_max": 18,
      "num_walls": 8, "max_attempts": 1000},
     16, 20260623, None),
    # ---- Constructive (cooperative, any profile accepted) ----
    ("10_cooperative_5x5_2a_1L",
     "cooperative",
     {"size": (5, 5), "agents": 2, "lasers": 1, "t_max": 10,
      "num_walls": 2, "max_attempts": 1000},
     16, 20260631, "cooperative"),
    ("11_cooperative_7x7_3a_2L",
     "cooperative",
     {"size": (7, 7), "agents": 3, "lasers": 2, "t_max": 14,
      "num_walls": 4, "max_attempts": 1000},
     16, 20260632, "cooperative"),
    ("12_cooperative_9x9_4a_3L",
     "cooperative",
     {"size": (9, 9), "agents": 4, "lasers": 3, "t_max": 18,
      "num_walls": 8, "max_attempts": 1000},
     16, 20260633, "cooperative"),
    # ---- Constructive cooperative with profile filter ----
    ("13_cooperative_mutual_8x8_3a_2L",
     "cooperative",
     {"size": (8, 8), "agents": 3, "lasers": 2, "t_max": 16,
      "num_walls": 5, "max_attempts": 2000},
     16, 20260641, "mutual"),
    ("14_cooperative_distributed_10x10_4a_3L",
     "cooperative",
     {"size": (10, 10), "agents": 4, "lasers": 3, "t_max": 20,
      "num_walls": 8, "max_attempts": 5000},
     16, 20260642, "distributed"),
    # ---- Level-6-Style ----
    ("15_level6_style_8x8_4a_2L",
     "level6_style",
     {"size": (8, 8), "agents": 4, "lasers": 2, "t_max": 16,
      "num_walls": 6, "max_attempts": 2000},
     16, 20260651, None),
    ("16_level6_style_10x10_4a_3L",
     "level6_style",
     {"size": (10, 10), "agents": 4, "lasers": 3, "t_max": 18,
      "num_walls": 8, "max_attempts": 2000},
     16, 20260652, None),
    ("17_level6_style_12x13_4a_3L",
     "level6_style",
     {"size": (12, 13), "agents": 4, "lasers": 3, "t_max": 21,
      "num_walls": 10, "max_attempts": 2000},
     16, 20260653, None),
]


def _save_image(world, out_png: Path) -> None:
    image = world.get_image()
    plt.imsave(out_png, image)


def _pool_complete(pool_dir: Path, n_samples: int) -> bool:
    params_path = pool_dir / "params.json"
    if not params_path.exists():
        return False
    try:
        data = json.loads(params_path.read_text())
    except Exception:
        return False
    return data.get("n_samples_generated") == n_samples


def generate_pool(
    label: str,
    generator_name: str,
    params: dict,
    n_samples: int,
    seed: int,
    profile: str | None,
) -> None:
    pool_dir = OUTPUT_ROOT / label
    if _pool_complete(pool_dir, n_samples):
        print(f"  {label}: already complete, skipping")
        return

    pool_dir.mkdir(parents=True, exist_ok=True)
    (pool_dir / "levels").mkdir(exist_ok=True)
    (pool_dir / "images").mkdir(exist_ok=True)

    cls = GENERATOR_REGISTRY[generator_name]
    generator = cls(**params, seed=seed)
    if profile is not None and hasattr(generator, "profile"):
        generator.profile = profile

    started = time.time()
    n_generated = 0
    for i in range(n_samples):
        try:
            world = generator.generate()
        except Exception as exc:
            print(f"  {label}: generate() failed at sample {i}: {exc}")
            break
        level_id = f"level_{i:03d}"
        (pool_dir / "levels" / f"{level_id}.txt").write_text(world.world_string)
        _save_image(world, pool_dir / "images" / f"{level_id}.png")
        n_generated += 1

    elapsed = time.time() - started
    params_dump = {
        "generator": generator_name,
        "profile": profile,
        "params": {k: list(v) if isinstance(v, tuple) else v for k, v in params.items()},
        "seed": seed,
        "n_samples_requested": n_samples,
        "n_samples_generated": n_generated,
        "elapsed_seconds": elapsed,
    }
    (pool_dir / "params.json").write_text(json.dumps(params_dump, indent=2))
    print(f"  {label}: {n_generated}/{n_samples} levels in {elapsed:.1f}s")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for row in GALLERY:
        label, gen_name, params, n_samples, seed, profile = row
        print(f"Generating {label}...")
        try:
            generate_pool(label, gen_name, params, n_samples, seed, profile)
        except Exception as exc:
            print(f"  {label}: aborted with {exc!r}")


if __name__ == "__main__":
    main()
