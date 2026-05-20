"""Tests for the curriculum-strategy schedulers.

Uses a ``_FakeWorld`` stub (no SAT / lle.World) -- the schedulers are
pure combinatorial logic over opaque world tokens, like the existing
curriculum scheduler tests.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from experiments.curriculum_strategy.configs import (
    FORWARD_STAGE_STEPS,
    RUNGS,
    TOTAL_STEPS,
)
from experiments.curriculum_strategy.schedulers import (
    FixedScheduleScheduler,
    make_strategy,
)

# Per-rung budgets in 1000-step episodes (FORWARD_STAGE_STEPS = 50k/150k).
NAV_EPS = FORWARD_STAGE_STEPS[0] // 1000      # 50
COOP_EPS = FORWARD_STAGE_STEPS[1] // 1000     # 150
TOTAL_EPS = TOTAL_STEPS // 1000               # 200


@dataclass(frozen=True)
class _FakeWorld:
    stage_id: int
    idx: int


def _fake_pools() -> dict[int, list[_FakeWorld]]:
    return {r.stage_id: [_FakeWorld(r.stage_id, i) for i in range(5)] for r in RUNGS}


def _drain(strategy, total_steps, episode_len=1000):
    """Run the strategy like the runner does; return rung id per episode."""
    seen = []
    step = 0
    while step < total_steps and not strategy.is_finished():
        world, rung = strategy.next_world()
        assert world.stage_id == rung.stage_id  # sampler bound to right pool
        seen.append(rung.stage_id)
        strategy.record_steps(episode_len)
        step += episode_len
    return seen, step


def _fwd(condition, total_steps=TOTAL_STEPS):
    return make_strategy(
        condition, RUNGS, _fake_pools(), total_steps, rng_seed=0,
        stage_budgets=list(FORWARD_STAGE_STEPS),
    )


def test_forward_navigation_then_cooperation_with_weighted_budget():
    seen, step = _drain(_fwd("forward"), TOTAL_STEPS)
    assert seen[:NAV_EPS] == [1] * NAV_EPS          # navigation warmup (stage 1)
    assert seen[NAV_EPS:TOTAL_EPS] == [2] * COOP_EPS  # cooperation target (stage 2)
    assert step == TOTAL_STEPS


def test_reverse_keeps_per_rung_budget_but_flips_order():
    seen, _ = _drain(_fwd("reverse"), TOTAL_STEPS)
    # Cooperation (stage 2) first, for its 150k; then navigation (stage 1) 50k.
    assert seen[:COOP_EPS] == [2] * COOP_EPS
    assert seen[COOP_EPS:TOTAL_EPS] == [1] * NAV_EPS


def test_direct_trains_only_on_target():
    seen, step = _drain(_fwd("direct"), TOTAL_STEPS)
    assert set(seen) == {2}                # target (cooperation) rung only
    assert len(seen) == TOTAL_EPS
    assert step == TOTAL_STEPS


def test_mixed_covers_both_rungs_and_never_finishes():
    strat = _fwd("mixed")
    seen, step = _drain(strat, TOTAL_STEPS)
    assert set(seen) == {1, 2}
    assert not strat.is_finished()


def test_stage_budgets_scale_to_a_shorter_run():
    # 50k/150k scaled to a 20k smoke run -> 5k/15k -> 5 + 15 episodes.
    seen, step = _drain(_fwd("forward", total_steps=20_000), 20_000)
    assert seen[:5] == [1] * 5
    assert seen[5:20] == [2] * 15
    assert step == 20_000


def test_forward_falls_back_to_equal_split_without_budgets():
    strat = make_strategy("forward", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)
    seen, _ = _drain(strat, TOTAL_STEPS)
    assert seen[:100] == [1] * 100   # equal split: 100k / 100k
    assert seen[100:200] == [2] * 100


def test_stage_budgets_length_mismatch_raises():
    with pytest.raises(ValueError):
        make_strategy(
            "forward", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0,
            stage_budgets=[1000],  # only 1 budget for 2 rungs
        )


def test_unknown_condition_raises():
    with pytest.raises(ValueError):
        make_strategy("bogus", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)


def test_fixed_schedule_rejects_empty_and_nonpositive_budget():
    pools = _fake_pools()
    with pytest.raises(ValueError):
        FixedScheduleScheduler([], pools, rng_seed=0)
    with pytest.raises(ValueError):
        FixedScheduleScheduler([(RUNGS[0], 0)], pools, rng_seed=0)


def test_fixed_schedule_rejects_missing_pool():
    pools = {RUNGS[0].stage_id: [_FakeWorld(RUNGS[0].stage_id, 0)]}  # no target pool
    with pytest.raises(ValueError):
        FixedScheduleScheduler([(RUNGS[-1], 1000)], pools, rng_seed=0)
