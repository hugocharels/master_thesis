"""Static configuration for the curriculum-vs-direct experiment.

A first, deliberately reachable demonstration that curriculum learning improves
learning on cooperative LLE levels. The earlier 5-rung 8x8/2L pilot showed that
two-laser (*mutual*) cooperation is a hard wall for value-decomposition MARL --
every condition scored 0 on the 7x7/2L and 8x8/2L rungs -- while the single-laser
rungs were learnable and the warm start compounded (``forward`` reached ~0.52 on
6x6/1L where ``reverse``, arriving cold, got 0). We therefore target the largest
rung that demonstrably works: 6x6 / 2 agents / 1 laser, cooperative.

Ladder (2 agents throughout so the Q-net input shape is fixed; observations
padded up to the 6x6 target by ``PadObservations3D``):

    S1: 4x4 / 2a / 0L (random)       -- navigation warmup, no cooperation
    S2: 5x5 / 2a / 1L (cooperative)  -- intro cooperation
    S3: 6x6 / 2a / 1L (cooperative)  -- target

``direct`` spends the whole budget on S3 (6x6); ``forward`` walks S1->S3;
``reverse`` / ``mixed`` are ablations. All conditions share TOTAL_STEPS, so the
comparison is budget-matched. Each rung gets ``pool_size`` distinct levels and
the target keeps a held-out ``eval_pool_size`` for the generalization metric.
"""
from __future__ import annotations

from experiments.curriculum.configs import StageConfig

RNG_SEED: int = 20260521

# Per-rung level budget. >> the 20-level pool that overfits in the learnability
# experiment; the SAT generator supplies these for free.
POOL_SIZE: int = 100

RUNGS: tuple[StageConfig, ...] = (
    StageConfig(
        stage_id=1, height=4, width=4, n_agents=2, n_lasers=0, t_max=8,
        generator_name="random", pool_size=POOL_SIZE, eval_pool_size=0,
        per_stage_step_cap_full=50_000, per_stage_step_cap_pilot=25_000,
    ),
    StageConfig(
        stage_id=2, height=5, width=5, n_agents=2, n_lasers=1, t_max=10,
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=0,
        per_stage_step_cap_full=150_000, per_stage_step_cap_pilot=75_000,
    ),
    StageConfig(
        stage_id=3, height=6, width=6, n_agents=2, n_lasers=1, t_max=12,
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=50,
        per_stage_step_cap_full=200_000, per_stage_step_cap_pilot=100_000,
    ),
)

# The rung every condition is evaluated on (held-out eval pool lives here).
TARGET_RUNG: StageConfig = RUNGS[-1]

# Total environment-step budget, identical for every condition.
TOTAL_STEPS: int = 400_000

# Forward/reverse per-stage training budgets (aligned to RUNGS order), summing
# to TOTAL_STEPS. Navigation gets the small slice; the 6x6 target gets the bulk.
# This split reproduced forward's ~0.52 on 6x6 in the pilot.
FORWARD_STAGE_STEPS: tuple[int, ...] = (50_000, 150_000, 200_000)

CONDITIONS: tuple[str, ...] = ("direct", "forward", "reverse", "mixed")
ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")

EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200


def equal_split(total: int, n: int) -> list[int]:
    """Split ``total`` into ``n`` budgets that sum to exactly ``total``.

    Fallback when no explicit per-stage budget is supplied.
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    base = total // n
    out = [base] * n
    out[-1] += total - base * n
    return out
