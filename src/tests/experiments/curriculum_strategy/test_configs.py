"""Tests for the curriculum-vs-direct (hard-target) configuration."""
from __future__ import annotations

from experiments.curriculum_strategy.configs import (
    ALGORITHMS,
    CONDITIONS,
    FORWARD_STAGE_STEPS,
    POOL_SIZE,
    RUNGS,
    TARGET_RUNG,
    TOTAL_STEPS,
    equal_split,
)


def test_five_rung_ladder_to_8x8():
    assert len(RUNGS) == 5
    geo = [(r.height, r.width, r.n_agents, r.n_lasers) for r in RUNGS]
    assert geo == [
        (4, 4, 2, 0),   # navigation warmup
        (5, 5, 2, 1),   # intro cooperation (proven-learnable rung)
        (6, 6, 2, 1),
        (7, 7, 2, 2),   # mutual cooperation
        (8, 8, 2, 2),   # target
    ]
    assert [r.stage_id for r in RUNGS] == [1, 2, 3, 4, 5]
    assert all(r.n_agents == 2 for r in RUNGS)
    assert RUNGS[0].generator_name == "random"               # 0-laser warmup
    assert all(r.generator_name == "cooperative" for r in RUNGS[1:])


def test_target_is_8x8_with_held_out_pool():
    assert TARGET_RUNG is RUNGS[-1]
    assert (TARGET_RUNG.height, TARGET_RUNG.width, TARGET_RUNG.n_lasers) == (8, 8, 2)
    assert TARGET_RUNG.eval_pool_size > 0
    assert all(r.eval_pool_size == 0 for r in RUNGS[:-1])


def test_more_data_per_rung_than_the_overfitting_pool():
    # The learnability pool of 20 overfits; every rung here gets many more.
    assert POOL_SIZE >= 50
    assert all(r.pool_size == POOL_SIZE for r in RUNGS)


def test_conditions_and_algorithms():
    assert CONDITIONS == ("direct", "forward", "reverse", "mixed")
    assert ALGORITHMS == ("IQL", "VDN", "QMIX")


def test_forward_budget_aligns_and_conserves_total():
    assert len(FORWARD_STAGE_STEPS) == len(RUNGS)
    assert sum(FORWARD_STAGE_STEPS) == TOTAL_STEPS  # same total as direct
    # Difficulty-scaled: navigation smallest, target (8x8) largest.
    assert FORWARD_STAGE_STEPS[0] == min(FORWARD_STAGE_STEPS)
    assert FORWARD_STAGE_STEPS[-1] == max(FORWARD_STAGE_STEPS)


def test_equal_split_fallback_conserves_total():
    assert equal_split(10, 3) == [3, 3, 4]
    assert sum(equal_split(TOTAL_STEPS, len(RUNGS))) == TOTAL_STEPS
