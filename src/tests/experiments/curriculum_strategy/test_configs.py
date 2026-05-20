"""Tests for the curriculum-strategy static configuration."""
from __future__ import annotations

from experiments.curriculum_strategy.configs import (
    ALGORITHMS,
    CONDITIONS,
    RUNGS,
    TARGET_RUNG,
    TOTAL_STEPS,
    equal_split,
)


def test_three_rungs_anchored_on_proven_regime():
    assert len(RUNGS) == 3
    r1, r2, r3 = RUNGS
    # R1 == proven-learnable learnability_5x5 regime
    assert (r1.height, r1.width, r1.n_agents, r1.n_lasers) == (5, 5, 2, 1)
    assert (r2.height, r2.width, r2.n_agents, r2.n_lasers) == (6, 6, 2, 1)
    assert (r3.height, r3.width, r3.n_agents, r3.n_lasers) == (7, 7, 2, 2)
    # All rungs cooperative, fixed agent count, ascending stage ids
    assert [r.stage_id for r in RUNGS] == [1, 2, 3]
    assert all(r.generator_name == "cooperative" for r in RUNGS)
    assert all(r.n_agents == 2 for r in RUNGS)


def test_target_is_last_rung_with_eval_pool():
    assert TARGET_RUNG is RUNGS[-1]
    assert TARGET_RUNG.eval_pool_size > 0
    # Non-target rungs need no held-out eval pool
    assert all(r.eval_pool_size == 0 for r in RUNGS[:-1])


def test_conditions_and_algorithms():
    assert CONDITIONS == ("direct", "forward", "reverse", "mixed")
    assert ALGORITHMS == ("IQL", "VDN", "QMIX")


def test_total_steps_and_equal_split_invariants():
    assert TOTAL_STEPS == 600_000
    split = equal_split(TOTAL_STEPS, len(RUNGS))
    assert len(split) == len(RUNGS)
    assert sum(split) == TOTAL_STEPS          # budget conserved exactly
    assert split == [200_000, 200_000, 200_000]


def test_equal_split_remainder_goes_to_last():
    assert equal_split(10, 3) == [3, 3, 4]
    assert sum(equal_split(10, 3)) == 10
