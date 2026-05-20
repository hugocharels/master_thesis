"""Static configuration for the curriculum-strategy comparison.

Compares four budget-matched strategies (direct / forward / reverse /
mixed) over a 3-rung difficulty ladder anchored on the proven-learnable
5x5 / 2 agents / 1 laser cooperative regime (see
``results/learnability_5x5/``: ~0.63 train / ~0.20 test). All rungs keep
``n_agents = 2`` so the Q-network input shape is fixed (observations are
padded up to the 7x7 target by ``PadObservations3D``).

Design doc: docs/superpowers/specs/2026-05-20-curriculum-strategy-comparison-design.md
"""
from __future__ import annotations

from experiments.curriculum.configs import StageConfig

# Master seed for pool generation (distinct from the learnability seeds
# so the pools are independent draws from the same regime).
RNG_SEED: int = 20260520

# 3-rung ladder. ``per_stage_step_cap_*`` are documentation only here --
# the curriculum-strategy schedulers take an explicit per-rung budget --
# but StageConfig requires them, so we set them to the forward per-rung
# budget for readability.
RUNGS: tuple[StageConfig, ...] = (
    StageConfig(
        stage_id=1,
        height=5,
        width=5,
        n_agents=2,
        n_lasers=1,
        t_max=10,
        generator_name="cooperative",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=200_000,
        per_stage_step_cap_pilot=100_000,
    ),
    StageConfig(
        stage_id=2,
        height=6,
        width=6,
        n_agents=2,
        n_lasers=1,
        t_max=12,
        generator_name="cooperative",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=200_000,
        per_stage_step_cap_pilot=100_000,
    ),
    StageConfig(
        stage_id=3,
        height=7,
        width=7,
        n_agents=2,
        n_lasers=2,
        t_max=14,
        generator_name="cooperative",
        pool_size=50,
        eval_pool_size=50,
        per_stage_step_cap_full=200_000,
        per_stage_step_cap_pilot=100_000,
    ),
)

# The rung every condition is evaluated on (held-out eval pool lives here).
TARGET_RUNG: StageConfig = RUNGS[-1]

# Total environment-step budget, identical for every condition. This is
# the controlled variable (NOT wall-clock: small grids step faster, so
# equal wall-clock would hand the curriculum more env steps).
TOTAL_STEPS: int = 600_000

CONDITIONS: tuple[str, ...] = ("direct", "forward", "reverse", "mixed")
ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")

# Periodic + final evaluation cadence (greedy, on the target pools).
EVAL_FREQUENCY_STEPS: int = 20_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200


def equal_split(total: int, n: int) -> list[int]:
    """Split ``total`` into ``n`` budgets that sum to exactly ``total``.

    Each gets ``total // n``; any remainder is added to the last entry so
    the per-rung budgets always conserve the total (the comparison is
    only fair if every condition spends the same number of steps).
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    base = total // n
    out = [base] * n
    out[-1] += total - base * n
    return out
