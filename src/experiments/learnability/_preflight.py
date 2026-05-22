"""One-shot script to generate the train + test level pools.

Default usage reproduces the 5x5 baseline pools::

    python -m experiments.learnability._preflight

Grid parameters can be overridden from the CLI to produce additional
learnability-probe pools (7x7, 9x9, etc.) without editing ``configs.py``::

    python -m experiments.learnability._preflight \
        --height 7 --width 7 --agents 3 --lasers 1 --t-max 14 \
        --out-dir results/learnability_7x7
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.learnability.configs import (
    GRID,
    GridConfig,
    RNG_SEED,
    TEST_POOL_SIZE,
    TRAIN_POOL_SIZE,
)
from experiments.learnability.pool_generator import build_pool, pool_dir, save_pool
from generators.profile_choices import COOP_PROFILE_CHOICES


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="learnability._preflight")
    parser.add_argument("--height", type=int, default=GRID.height)
    parser.add_argument("--width", type=int, default=GRID.width)
    parser.add_argument("--agents", type=int, default=GRID.n_agents)
    parser.add_argument("--lasers", type=int, default=GRID.n_lasers)
    parser.add_argument("--t-max", type=int, default=GRID.t_max)
    parser.add_argument("--generator", default=GRID.generator_name)
    parser.add_argument(
        "--profile",
        choices=list(COOP_PROFILE_CHOICES),
        default=None,
        help="Cooperation-profile filter for profile-aware generators "
        "(e.g. fully_coupled). Default: the generator's own default.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("results/learnability_5x5"))
    parser.add_argument("--train-pool-size", type=int, default=TRAIN_POOL_SIZE)
    parser.add_argument("--test-pool-size", type=int, default=TEST_POOL_SIZE)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    config = GridConfig(
        height=args.height,
        width=args.width,
        n_agents=args.agents,
        n_lasers=args.lasers,
        t_max=args.t_max,
        generator_name=args.generator,
    )
    base_dir: Path = args.out_dir

    print(
        f"=== {config.height}x{config.width}, {config.n_agents} agents, "
        f"{config.n_lasers} lasers, generator={config.generator_name} ==="
    )

    train_seed = RNG_SEED
    test_seed = RNG_SEED + 1

    train_d = pool_dir(base_dir, config, "train")
    print(f"  [train] seed={train_seed} n={args.train_pool_size} profile={args.profile} -> {train_d}")
    train_worlds = build_pool(
        config, seed=train_seed, n_levels=args.train_pool_size, profile=args.profile,
    )
    save_pool(train_worlds, train_d)
    print(f"  [train] done")

    test_d = pool_dir(base_dir, config, "test")
    print(f"  [test]  seed={test_seed} n={args.test_pool_size} profile={args.profile} -> {test_d}")
    test_worlds = build_pool(
        config, seed=test_seed, n_levels=args.test_pool_size, profile=args.profile,
    )
    save_pool(test_worlds, test_d)
    print(f"  [test]  done")

    print("\nDone!")


if __name__ == "__main__":
    main()
