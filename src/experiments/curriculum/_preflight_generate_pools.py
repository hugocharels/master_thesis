"""One-shot pre-flight script to materialise every curriculum level pool.

Run this **once** (manually) before launching the curriculum-transfer
experiment, so that subsequent training runs reload pre-built pools
instead of regenerating levels on every seed and condition.

Usage::

    python3.13 src/experiments/curriculum/_preflight_generate_pools.py

Output layout (under ``results/curriculum_experiment/``)::

    levels/
      stage_1_6x6_4a_1L_random/
        train/level_000.json ... level_049.json
      stage_2_8x8_4a_2L_cooperative/
        train/level_000.json ... level_049.json
      stage_3_10x10_4a_3L_cooperative/
        train/level_000.json ... level_049.json
      stage_4_12x13_4a_3L_level6_style/
        train/level_000.json ... level_049.json
        eval/level_000.json ... level_049.json

Per-stage seeds are derived deterministically from
:data:`experiments.curriculum.configs.RNG_SEED`:

* train pool: ``RNG_SEED + stage_id * 100``
* held-out pool: ``RNG_SEED + stage_id * 100 + 1``

Only stage 4 currently produces a held-out pool; the other stages have
``eval_pool_size == 0`` and therefore skip the second invocation.

The leading underscore in the filename intentionally marks this as a
private one-shot tool, not part of the package public API.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from experiments.curriculum.configs import (
    CURRICULUM_STAGES,
    RNG_SEED,
    StageConfig,
)
from experiments.curriculum.pool_generator import (
    build_pool,
    pool_path,
    save_pool,
)


# ---- Output directory ------------------------------------------------------
#
# CLAUDE.md / project memory restricts ``results/`` to read-only except
# for the curriculum_experiment subdirectory. We always write under that.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_BASE = PROJECT_ROOT / "results" / "curriculum_experiment"


# ---- Per-stage seed derivation --------------------------------------------


def train_seed(stage: StageConfig) -> int:
    """Return the deterministic train-pool seed for a given stage."""
    return RNG_SEED + stage.stage_id * 100


def heldout_seed(stage: StageConfig) -> int:
    """Return the deterministic held-out-pool seed for a given stage."""
    return RNG_SEED + stage.stage_id * 100 + 1


# ---- Main ------------------------------------------------------------------


def _generate_one(
    stage: StageConfig,
    seed: int,
    n_levels: int,
    out_dir: Path,
    label: str,
) -> None:
    """Build and save one pool, with a progress / timing line on stdout."""
    t0 = time.monotonic()
    print(
        f"  [{label}] seed={seed} n={n_levels} -> {out_dir}",
        flush=True,
    )
    worlds = build_pool(stage, seed=seed, n_levels=n_levels)
    save_pool(worlds, out_dir)
    dt = time.monotonic() - t0
    print(f"  [{label}] done in {dt:.2f}s", flush=True)


def main() -> int:
    print(f"Pre-flight: writing pools under {OUTPUT_BASE}", flush=True)
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    for stage in CURRICULUM_STAGES:
        print(
            f"\n=== Stage {stage.stage_id}: "
            f"{stage.height}x{stage.width}, "
            f"{stage.n_agents} agents, {stage.n_lasers} lasers, "
            f"t_max={stage.t_max}, generator={stage.generator_name} ===",
            flush=True,
        )
        train_dir = pool_path(OUTPUT_BASE, stage, "train")
        _generate_one(
            stage=stage,
            seed=train_seed(stage),
            n_levels=stage.pool_size,
            out_dir=train_dir,
            label="train",
        )
        if stage.eval_pool_size > 0:
            held_dir = pool_path(OUTPUT_BASE, stage, "eval")
            _generate_one(
                stage=stage,
                seed=heldout_seed(stage),
                n_levels=stage.eval_pool_size,
                out_dir=held_dir,
                label="held-out",
            )
        else:
            print(
                f"  [held-out] eval_pool_size=0 -> skipped (stage reuses "
                f"its training pool for in-stage success metrics)",
                flush=True,
            )
    print("\nAll pools written.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
