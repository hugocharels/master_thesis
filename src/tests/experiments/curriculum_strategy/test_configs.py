"""Tests for the curriculum-vs-direct learnability configuration."""
from __future__ import annotations

from experiments.curriculum_strategy.configs import (
    ALGORITHMS,
    CONDITIONS,
    FORWARD_STAGE_STEPS,
    RUNGS,
    TARGET_RUNG,
    TOTAL_STEPS,
    equal_split,
)


def test_two_rung_laser_ramp_ends_at_learnability_task():
    assert len(RUNGS) == 2
    nav, coop = RUNGS
    # Stage 1: pure-navigation warmup (no laser), random generator.
    assert (nav.height, nav.width, nav.n_agents, nav.n_lasers) == (5, 5, 2, 0)
    assert nav.generator_name == "random"
    # Stage 2 (target): the exact learnability task, 5x5/2a/1L cooperative.
    assert (coop.height, coop.width, coop.n_agents, coop.n_lasers) == (5, 5, 2, 1)
    assert coop.generator_name == "cooperative"
    assert coop.t_max == 10  # matches learnability_5x5
    assert [r.stage_id for r in RUNGS] == [1, 2]
    assert all(r.n_agents == 2 for r in RUNGS)


def test_target_is_last_rung_with_eval_pool():
    assert TARGET_RUNG is RUNGS[-1]
    assert TARGET_RUNG.eval_pool_size == 20  # matches learnability test pool size
    assert RUNGS[0].eval_pool_size == 0      # warmup needs no held-out pool


def test_conditions_and_algorithms():
    assert CONDITIONS == ("direct", "forward", "reverse", "mixed")
    assert ALGORITHMS == ("IQL", "VDN", "QMIX")


def test_total_budget_matches_learnability_and_split_conserves_it():
    assert TOTAL_STEPS == 200_000
    assert len(FORWARD_STAGE_STEPS) == len(RUNGS)
    assert sum(FORWARD_STAGE_STEPS) == TOTAL_STEPS  # same total as direct
    # Navigation gets the small slice, cooperation target the bulk.
    assert FORWARD_STAGE_STEPS[0] < FORWARD_STAGE_STEPS[-1]


def test_equal_split_fallback_conserves_total():
    assert equal_split(TOTAL_STEPS, 2) == [100_000, 100_000]
    assert equal_split(10, 3) == [3, 3, 4]
    assert sum(equal_split(10, 3)) == 10
