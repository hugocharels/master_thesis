"""Pre-flight: SAT-generate the rung pools for the curriculum-strategy run.

Generates a train pool for every rung and a held-out eval pool for the
target rung, under ``results/curriculum_strategy/levels/`` using the
canonical ``pool_generator`` layout. R1 (5x5/2a/1L cooperative) matches
the proven-learnable ``learnability_5x5`` regime.

Run (project venv, has lle + pysat):

    python -m experiments.curriculum_strategy._preflight
"""
from __future__ import annotations

from pathlib import Path

from experiments.curriculum.configs import StageConfig
from experiments.curriculum.pool_generator import build_pool, pool_path, save_pool
from experiments.curriculum_strategy.configs import RNG_SEED, RUNGS, TARGET_RUNG

BASE_DIR = Path("results") / "curriculum_strategy"


def pool_jobs() -> list[tuple[StageConfig, str, int, int]]:
    """Return the list of ``(rung, split, seed, n_levels)`` to generate.

    Seeds are derived from ``RNG_SEED`` so the pools are reproducible and
    the target's train/eval draws never coincide (held-out integrity).
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
        print(
            f"[rung {rung.stage_id} {split}] {rung.height}x{rung.width}, "
            f"{rung.n_agents}a, {rung.n_lasers}L, gen={rung.generator_name}, "
            f"seed={seed}, n={n} -> {out}"
        )
        worlds = build_pool(rung, seed=seed, n_levels=n)
        save_pool(worlds, out)
        print("  done")
    print("\nAll rung pools generated.")


if __name__ == "__main__":
    main()
