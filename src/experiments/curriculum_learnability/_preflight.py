"""Pre-flight: generate the stage-1 and stage-2 training pools.

Stage 3 reuses the learnability experiment's pools
(``results/learnability/levels/8x8_3a_2L_cooperative/``), so this
preflight only needs to produce stages 1 and 2.

Run with the marl venv (inside docker):

    python -m experiments.curriculum_learnability._preflight
"""

from __future__ import annotations

from pathlib import Path

from experiments.curriculum_learnability.configs import (
    LEARNABILITY_TARGET_STAGES,
    RNG_SEED,
)
from experiments.curriculum.pool_generator import build_pool, pool_path, save_pool


BASE_DIR = Path("results") / "curriculum_learnability"


def main() -> None:
    # Stages 1 and 2 only -- stage 3 reuses the learnability pool.
    for stage in LEARNABILITY_TARGET_STAGES[:2]:
        train_seed = RNG_SEED + stage.stage_id * 100
        train_dir = pool_path(BASE_DIR, stage, "train")
        print(
            f"[stage {stage.stage_id}] {stage.height}x{stage.width}, "
            f"{stage.n_agents} agents, {stage.n_lasers} lasers, "
            f"generator={stage.generator_name}, "
            f"seed={train_seed}, n={stage.pool_size} -> {train_dir}"
        )
        worlds = build_pool(stage, seed=train_seed, n_levels=stage.pool_size)
        save_pool(worlds, train_dir)
        print(f"  done")

    print(
        f"\nStage 3 reuses results/learnability/levels/"
        f"8x8_3a_2L_cooperative/{{train,test}} (no preflight needed).\n"
        f"Done."
    )


if __name__ == "__main__":
    main()
