"""Static configuration for the curriculum-vs-direct experiment (hard target).

Tests whether curriculum learning lets value-decomposition MARL reach a
cooperative target that direct training cannot, when each rung is given enough
data to not be starved (the lesson from the data-scaling sweep: 20 levels
overfits; the SAT generator can supply many more).

Ladder (laser + size ramp, 2 agents throughout so the Q-net input shape is
fixed; observations padded up to the 8x8 target by ``PadObservations3D``):

    S1: 4x4 / 2a / 0L (random)       -- navigation warmup, no cooperation
    S2: 5x5 / 2a / 1L (cooperative)  -- intro cooperation (the proven-learnable rung)
    S3: 6x6 / 2a / 1L (cooperative)
    S4: 7x7 / 2a / 2L (cooperative)  -- mutual cooperation
    S5: 8x8 / 2a / 2L (cooperative)  -- target

``direct`` spends the whole budget on S5 (8x8) -- the learnability/sweep
baseline (train ~0.12, test 0). ``forward`` walks S1->S5; ``reverse`` /
``mixed`` are ablations. All conditions get the same TOTAL_STEPS. Each rung
gets ``pool_size`` distinct levels (>> the 20 that overfit), and the target
keeps a held-out ``eval_pool_size`` for the generalization metric.

Design doc: docs/superpowers/specs/2026-05-20-curriculum-strategy-comparison-design.md
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
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=0,
        per_stage_step_cap_full=200_000, per_stage_step_cap_pilot=100_000,
    ),
    StageConfig(
        stage_id=4, height=7, width=7, n_agents=2, n_lasers=2, t_max=14,
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=0,
        per_stage_step_cap_full=250_000, per_stage_step_cap_pilot=125_000,
    ),
    StageConfig(
        stage_id=5, height=8, width=8, n_agents=2, n_lasers=2, t_max=16,
        generator_name="cooperative", pool_size=POOL_SIZE, eval_pool_size=50,
        per_stage_step_cap_full=350_000, per_stage_step_cap_pilot=175_000,
    ),
)

# The rung every condition is evaluated on (held-out eval pool lives here).
TARGET_RUNG: StageConfig = RUNGS[-1]

# Total environment-step budget, identical for every condition.
TOTAL_STEPS: int = 1_000_000

# Forward/reverse per-stage training budgets (aligned to RUNGS order), scaled by
# difficulty, summing to TOTAL_STEPS. Navigation gets the small slice; the hard
# rungs (incl. the 8x8 target) get the bulk.
FORWARD_STAGE_STEPS: tuple[int, ...] = (50_000, 150_000, 200_000, 250_000, 350_000)

CONDITIONS: tuple[str, ...] = ("direct", "forward", "reverse", "mixed")
ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")

EVAL_FREQUENCY_STEPS: int = 25_000
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
