"""Tests for the curriculum-strategy preflight plan.

We test the *plan* (which rung/split/seed/count to generate) without
running the SAT solver, so the test is fast and deterministic.
"""
from __future__ import annotations

from experiments.curriculum_strategy._preflight import pool_jobs
from experiments.curriculum_strategy.configs import RUNGS, TARGET_RUNG


def test_every_rung_gets_a_train_pool():
    jobs = pool_jobs()
    train = [(rung.stage_id, split, n) for rung, split, _seed, n in jobs if split == "train"]
    assert sorted(train) == sorted((r.stage_id, "train", r.pool_size) for r in RUNGS)


def test_only_target_gets_an_eval_pool():
    jobs = pool_jobs()
    evals = [(rung.stage_id, n) for rung, split, _seed, n in jobs if split == "eval"]
    assert evals == [(TARGET_RUNG.stage_id, TARGET_RUNG.eval_pool_size)]


def test_train_and_eval_seeds_differ_for_target():
    jobs = {(rung.stage_id, split): seed for rung, split, seed, _n in pool_jobs()}
    # Held-out eval pool must not be the same draw as the train pool.
    assert jobs[(TARGET_RUNG.stage_id, "train")] != jobs[(TARGET_RUNG.stage_id, "eval")]


def test_seeds_are_deterministic():
    assert [j[2] for j in pool_jobs()] == [j[2] for j in pool_jobs()]
