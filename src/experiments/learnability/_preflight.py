"""One-shot script to generate the train + test level pools.

Usage:
    python -m experiments.learnability._preflight          # phase 1 (default)
    python -m experiments.learnability._preflight --phase 2 # phase 2
    python -m experiments.learnability._preflight --all     # both phases
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.learnability.configs import (
    PHASES,
    RNG_SEED,
    TEST_POOL_SIZE,
    TRAIN_POOL_SIZE,
)
from experiments.learnability.pool_generator import build_pool, pool_dir, save_pool


def generate_phase(phase: int) -> None:
    config = PHASES[phase]
    base_dir = Path(f"results/learnability_phase{phase}")

    print(f"\n=== Phase {phase}: {config.height}x{config.width}, "
          f"{config.n_agents} agents, {config.n_lasers} lasers, "
          f"generator={config.generator_name} ===")

    train_seed = RNG_SEED + (phase - 1) * 100
    test_seed = train_seed + 1

    # Train pool
    train_d = pool_dir(base_dir, config, "train")
    print(f"  [train] seed={train_seed} n={TRAIN_POOL_SIZE} -> {train_d}")
    train_worlds = build_pool(config, seed=train_seed, n_levels=TRAIN_POOL_SIZE)
    save_pool(train_worlds, train_d)
    print(f"  [train] done")

    # Test pool
    test_d = pool_dir(base_dir, config, "test")
    print(f"  [test]  seed={test_seed} n={TEST_POOL_SIZE} -> {test_d}")
    test_worlds = build_pool(config, seed=test_seed, n_levels=TEST_POOL_SIZE)
    save_pool(test_worlds, test_d)
    print(f"  [test]  done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, default=None, choices=list(PHASES.keys()))
    parser.add_argument("--all", action="store_true", help="Generate pools for all phases")
    args = parser.parse_args()

    if args.all:
        for p in PHASES:
            generate_phase(p)
    else:
        generate_phase(args.phase or 1)

    print("\nDone!")


if __name__ == "__main__":
    main()
