"""Pre-flight: SAT-generate the rung pools for the 2-laser curriculum-strategy run.

Mirrors :mod:`experiments.curriculum_strategy._preflight` but for the fixed-grid
0L -> 1L -> 2L ladder, and constrains the 2-laser target pool to the
``fully_coupled`` cooperation profile (see ``configs.RUNG_PROFILES``). Pools land
under ``results/curriculum_strategy_2L/levels/`` using the shared
``experiments.curriculum.pool_generator`` layout.

Run (marl venv, has lle + pysat):

    PYTHONPATH=src python -m experiments.curriculum_strategy_2L._preflight
"""
from __future__ import annotations

from pathlib import Path

from experiments.curriculum.configs import StageConfig
from experiments.curriculum.pool_generator import build_pool, pool_path, save_pool
from experiments.curriculum_strategy_2L.configs import (
    RNG_SEED,
    RUNG_PROFILES,
    RUNGS,
    TARGET_RUNG,
)

BASE_DIR = Path("results") / "curriculum_strategy_2L"


def pool_jobs() -> list[tuple[StageConfig, str, int, int]]:
    """Return ``(rung, split, seed, n_levels)`` jobs.

    Seeds are derived from ``RNG_SEED`` so the pools are reproducible and the
    target's train/eval draws never coincide (held-out integrity).
    """
    jobs: list[tuple[StageConfig, str, int, int]] = []
    for rung in RUNGS:
        jobs.append((rung, "train", RNG_SEED + rung.stage_id * 100, rung.pool_size))
    jobs.append(
        (TARGET_RUNG, "eval", RNG_SEED + TARGET_RUNG.stage_id * 100 + 1, TARGET_RUNG.eval_pool_size)
    )
    return jobs


def main() -> None:
    for rung, split, seed, n in pool_jobs():
        out = pool_path(BASE_DIR, rung, split)
        profile = RUNG_PROFILES.get(rung.stage_id)
        print(
            f"[rung {rung.stage_id} {split}] {rung.height}x{rung.width}, "
            f"{rung.n_agents}a, {rung.n_lasers}L, gen={rung.generator_name}, "
            f"profile={profile}, seed={seed}, n={n} -> {out}"
        )
        worlds = build_pool(rung, seed=seed, n_levels=n, profile=profile)
        save_pool(worlds, out)
        print("  done")
    print("\nAll rung pools generated.")


if __name__ == "__main__":
    main()
