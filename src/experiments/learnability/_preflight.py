"""One-shot script to generate the train + test level pools.

Usage:
    python -m experiments.learnability._preflight
"""

from __future__ import annotations

from pathlib import Path

from experiments.learnability.configs import (
    GRID,
    RNG_SEED,
    TEST_POOL_SIZE,
    TRAIN_POOL_SIZE,
)
from experiments.learnability.pool_generator import build_pool, pool_dir, save_pool


def main() -> None:
    base_dir = Path("results/learnability")

    print(
        f"=== {GRID.height}x{GRID.width}, {GRID.n_agents} agents, "
        f"{GRID.n_lasers} lasers, generator={GRID.generator_name} ==="
    )

    train_seed = RNG_SEED
    test_seed = RNG_SEED + 1

    train_d = pool_dir(base_dir, GRID, "train")
    print(f"  [train] seed={train_seed} n={TRAIN_POOL_SIZE} -> {train_d}")
    train_worlds = build_pool(GRID, seed=train_seed, n_levels=TRAIN_POOL_SIZE)
    save_pool(train_worlds, train_d)
    print(f"  [train] done")

    test_d = pool_dir(base_dir, GRID, "test")
    print(f"  [test]  seed={test_seed} n={TEST_POOL_SIZE} -> {test_d}")
    test_worlds = build_pool(GRID, seed=test_seed, n_levels=TEST_POOL_SIZE)
    save_pool(test_worlds, test_d)
    print(f"  [test]  done")

    print("\nDone!")


if __name__ == "__main__":
    main()
