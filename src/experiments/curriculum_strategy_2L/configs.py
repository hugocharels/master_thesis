"""Static configuration for the 2-laser curriculum-strategy experiment.

Sibling of :mod:`experiments.curriculum_strategy`, moved to the regime where a
curriculum is *expected* to help. The Phase-0 frontier probe
(``results/learnability_6x6_2L``) showed that direct-from-scratch training on the
6x6 / 2-agent / 2-laser **fully_coupled** (mutual) target reaches a nonzero
*train* success but ~0 held-out -- a learnable task on which ``direct`` fails to
generalise, i.e. exactly the room a curriculum needs.

The grid is held fixed at 6x6 and only the cooperation dimension is ramped
(0 -> 1 -> 2 lasers). This isolates the curriculum effect from grid-size growth,
the confound that sank the earlier 8x8/2L pilot (where ``forward`` also scored
0.00 because grid size and laser count grew together).

Ladder (2 agents throughout; all rungs 6x6, so no observation padding is needed):

    S1: 6x6 / 2a / 0L (random)                     -- navigation warmup
    S2: 6x6 / 2a / 1L (cooperative, asymmetric)    -- single-laser cooperation
    S3: 6x6 / 2a / 2L (cooperative, fully_coupled) -- target (mutual)

``direct`` spends the whole budget on S3; ``forward`` walks S1->S3; ``reverse``
visits the same per-rung budgets in reverse order; ``mixed`` samples rungs
uniformly. All conditions share TOTAL_STEPS, so the comparison is budget-matched.
Only the 2-laser target pool is constrained to the fully_coupled profile.
"""
from __future__ import annotations

from experiments.curriculum.configs import StageConfig

RNG_SEED: int = 20260523

# Per-rung level budget (matches the 1-laser curriculum_strategy experiment).
POOL_SIZE: int = 100

# Cooperation-profile filter applied to the 2-laser target pool. At 2 agents the
# mutually-blocking structure is classified ``fully_coupled`` (largest SCC spans
# both agents); see solver/profile and the 2laser design note.
TARGET_PROFILE: str = "fully_coupled"

RUNGS: tuple[StageConfig, ...] = (
    StageConfig(
        stage_id=1, height=6, width=6, n_agents=2, n_lasers=0, t_max=12,
        generator_name="random", pool_size=POOL_SIZE, eval_pool_size=0,
        per_stage_step_cap_full=50_000, per_stage_step_cap_pilot=25_000,
    ),
    StageConfig(
        stage_id=2, height=6, width=6, n_agents=2, n_lasers=1, t_max=14,
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=0,
        per_stage_step_cap_full=150_000, per_stage_step_cap_pilot=75_000,
    ),
    StageConfig(
        stage_id=3, height=6, width=6, n_agents=2, n_lasers=2, t_max=18,
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=50,
        per_stage_step_cap_full=400_000, per_stage_step_cap_pilot=200_000,
    ),
)

# The rung every condition is evaluated on (held-out eval pool lives here).
TARGET_RUNG: StageConfig = RUNGS[-1]

# Per-rung cooperation-profile filter for the pre-flight (``None`` = the
# generator's own default). Only the 2-laser target is constrained.
RUNG_PROFILES: dict[int, str | None] = {
    rung.stage_id: (TARGET_PROFILE if rung is TARGET_RUNG else None) for rung in RUNGS
}

# Total environment-step budget, identical for every condition.
TOTAL_STEPS: int = 600_000

# Forward/reverse per-stage budgets (aligned to RUNGS order), summing to
# TOTAL_STEPS. Navigation gets the small slice; the 2-laser target gets the bulk.
FORWARD_STAGE_STEPS: tuple[int, ...] = (50_000, 150_000, 400_000)

CONDITIONS: tuple[str, ...] = ("direct", "forward", "reverse", "mixed")
ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")

EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200
