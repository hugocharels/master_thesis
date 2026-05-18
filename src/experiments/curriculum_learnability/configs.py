"""Curriculum-learnability experiment config.

Apples-to-apples follow-up to the learnability experiment: same
target task (8x8 / 3 agents / 2 lasers, cooperative generator), same
test pool, same overall step budget -- the only difference is that
training is scaffolded through a 3-stage curriculum instead of being
direct.

The learnability experiment finished with 0 % test success across
60 cells: a single 8 x 8 cooperative level provides no reward signal
during random exploration within T_max=16, so vanilla MARL never
gets a learning gradient. This experiment tests whether stepping
through easier stages (no laser -> 1 laser -> 2 lasers) gives the
agent a foothold that transfers to the target.

Stages:
    1. 6x6, 3 agents, 0 lasers, random       -> 50_000 steps  (warmup)
    2. 7x7, 3 agents, 1 laser,  cooperative  -> 50_000 steps  (intro)
    3. 8x8, 3 agents, 2 lasers, cooperative  -> 100_000 steps (target)

Total: 200_000 steps == TOTAL_STEPS in
``experiments.learnability.configs`` so the two experiments are
directly comparable on a per-cell basis.
"""

from __future__ import annotations

from experiments.curriculum.configs import StageConfig

# Pool seeds for the stage-1/2 train pools (stage-3 reuses
# learnability's pool, so its seed is shared with that experiment).
RNG_SEED: int = 20260518

# All stages have 3 agents -> no per-stage padding needed at all.
LEARNABILITY_TARGET_STAGES: tuple[StageConfig, ...] = (
    StageConfig(
        stage_id=1,
        height=6,
        width=6,
        n_agents=3,
        n_lasers=0,
        t_max=12,
        generator_name="random",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=50_000,
        per_stage_step_cap_pilot=25_000,
    ),
    StageConfig(
        stage_id=2,
        height=7,
        width=7,
        n_agents=3,
        n_lasers=1,
        t_max=14,
        generator_name="cooperative",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=50_000,
        per_stage_step_cap_pilot=25_000,
    ),
    StageConfig(
        stage_id=3,
        height=8,
        width=8,
        n_agents=3,
        n_lasers=2,
        t_max=16,
        generator_name="cooperative",
        # Stage 3 reuses the learnability train (20 levels) and test
        # (20 levels) pools, so pool_size / eval_pool_size are
        # documentation only -- the runner loads from the
        # learnability/levels/ directory directly.
        pool_size=20,
        eval_pool_size=20,
        per_stage_step_cap_full=100_000,
        per_stage_step_cap_pilot=50_000,
    ),
)

# Mirrors learnability's TOTAL_STEPS for a fair budget comparison.
FULL_RUN_TOTAL_STEPS: int = 200_000
PILOT_RUN_TOTAL_STEPS: int = 100_000

ADVANCEMENT_SUCCESS_THRESHOLD: float = 0.80
ADVANCEMENT_WINDOW_EPISODES: int = 100

EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200

ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")
