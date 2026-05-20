"""Static configuration for the curriculum-vs-direct learnability experiment.

Goal: take the EXACT learnability task that worked (5x5 / 2 agents / 1 laser
cooperative, 200k steps -- see ``results/learnability_5x5/``: ~0.63 train /
~0.20 test) and test whether a curriculum trained on the SAME total budget
learns it *better* than direct training.

Ladder (laser ramp, fixed 5x5 grid, n_agents = 2 throughout):

    Stage 1: 5x5 / 2a / 0 lasers (random)       -- pure navigation warmup
    Stage 2: 5x5 / 2a / 1 laser  (cooperative)  -- the target == learnability task

The ``direct`` condition spends the whole budget on stage 2, so it *is* the
learnability baseline (and should reproduce ~0.63 train / ~0.20 test). The
``forward`` condition spends a small navigation warmup first, then the rest on
the target -- same 200k total, so the only difference is how the budget is
spent. ``reverse`` / ``mixed`` are ablations (does ordering matter, or just
exposure?).

Design doc: docs/superpowers/specs/2026-05-20-curriculum-strategy-comparison-design.md
"""
from __future__ import annotations

from experiments.curriculum.configs import StageConfig

# Master seed for pool generation.
RNG_SEED: int = 20260520

# 2-rung ladder. ``per_stage_step_cap_full`` doubles as the forward/reverse
# per-stage training budget (see FORWARD_STAGE_STEPS, kept in sync).
RUNGS: tuple[StageConfig, ...] = (
    StageConfig(
        stage_id=1,
        height=5,
        width=5,
        n_agents=2,
        n_lasers=0,
        t_max=10,
        # No laser -> the cooperative generator does not apply; use the random
        # solvable generator for a pure-navigation warmup pool.
        generator_name="random",
        pool_size=20,
        eval_pool_size=0,
        per_stage_step_cap_full=50_000,
        per_stage_step_cap_pilot=25_000,
    ),
    StageConfig(
        stage_id=2,
        height=5,
        width=5,
        n_agents=2,
        n_lasers=1,
        t_max=10,
        # The learnability task exactly: 5x5 / 2a / 1L cooperative.
        generator_name="cooperative",
        pool_size=20,
        eval_pool_size=20,
        per_stage_step_cap_full=150_000,
        per_stage_step_cap_pilot=75_000,
    ),
)

# The rung every condition is evaluated on (held-out eval pool lives here).
TARGET_RUNG: StageConfig = RUNGS[-1]

# Total environment-step budget, identical for every condition -- matches the
# learnability experiment's TOTAL_STEPS so the comparison is apples-to-apples.
TOTAL_STEPS: int = 200_000

# Forward/reverse per-stage training budgets, aligned to RUNGS order. Navigation
# is easy, so it gets a small slice; the cooperation target keeps the bulk. Sums
# to TOTAL_STEPS. The scheduler scales these proportionally if a run uses a
# different --steps (e.g. a short smoke test), so they always conserve the total.
FORWARD_STAGE_STEPS: tuple[int, ...] = (50_000, 150_000)

CONDITIONS: tuple[str, ...] = ("direct", "forward", "reverse", "mixed")
ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")

# Periodic + final evaluation cadence (greedy, on the target pools). Matches the
# learnability experiment.
EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200


def equal_split(total: int, n: int) -> list[int]:
    """Split ``total`` into ``n`` budgets that sum to exactly ``total``.

    Each gets ``total // n``; any remainder is added to the last entry so the
    per-stage budgets always conserve the total. Used as the fallback when no
    explicit per-stage budget is supplied.
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    base = total // n
    out = [base] * n
    out[-1] += total - base * n
    return out
