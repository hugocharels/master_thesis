"""Tests for the curriculum-strategy schedulers.

Uses a ``_FakeWorld`` stub (no SAT / lle.World) -- the schedulers are pure
combinatorial logic over opaque world tokens. Written generically over the
rung count so it survives ladder changes.
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

EP = 1000  # episode length used in the fake drain


@dataclass(frozen=True)
class _FakeWorld:
    stage_id: int
    idx: int


def _fake_pools() -> dict[int, list[_FakeWorld]]:
    return {r.stage_id: [_FakeWorld(r.stage_id, i) for i in range(5)] for r in RUNGS}


def _drain(strategy, total_steps, episode_len=EP):
    seen = []
    step = 0
    while step < total_steps and not strategy.is_finished():
        world, rung = strategy.next_world()
        assert world.stage_id == rung.stage_id
        seen.append(rung.stage_id)
        strategy.record_steps(episode_len)
        step += episode_len
    return seen, step


def _expected(order_rungs, order_budgets):
    seen = []
    for rung, budget in zip(order_rungs, order_budgets):
        seen.extend([rung.stage_id] * (budget // EP))
    return seen


def _make(cond, total_steps=TOTAL_STEPS):
    return make_strategy(
        cond, RUNGS, _fake_pools(), total_steps, rng_seed=0,
        stage_budgets=list(FORWARD_STAGE_STEPS),
    )


def test_forward_visits_rungs_in_order_with_scaled_budgets():
    seen, step = _drain(_make("forward"), TOTAL_STEPS)
    assert seen == _expected(RUNGS, FORWARD_STAGE_STEPS)
    assert step == TOTAL_STEPS


def test_reverse_same_budgets_reversed_order():
    seen, _ = _drain(_make("reverse"), TOTAL_STEPS)
    assert seen == _expected(list(reversed(RUNGS)), list(reversed(FORWARD_STAGE_STEPS)))


def test_direct_trains_only_on_target():
    seen, step = _drain(_make("direct"), TOTAL_STEPS)
    assert set(seen) == {RUNGS[-1].stage_id}
    assert len(seen) == TOTAL_STEPS // EP
    assert step == TOTAL_STEPS


def test_mixed_covers_all_rungs_and_never_finishes():
    strat = _make("mixed")
    seen, _ = _drain(strat, TOTAL_STEPS)
    assert set(seen) == {r.stage_id for r in RUNGS}
    assert not strat.is_finished()


def test_stage_budgets_scale_to_a_shorter_run():
    # Scaled to a 10k smoke run; budgets shrink proportionally, total conserved.
    total = 10_000
    seen, step = _drain(_make("forward", total_steps=total), total)
    assert step == total
    assert len(seen) == total // EP
    assert seen[0] == RUNGS[0].stage_id          # still starts on the warmup
    assert seen[-1] == RUNGS[-1].stage_id        # still ends on the target


def test_stage_budgets_length_mismatch_raises():
    with pytest.raises(ValueError):
        make_strategy(
            "forward", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0,
            stage_budgets=[1000],  # wrong length
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
    pools = {RUNGS[0].stage_id: [_FakeWorld(RUNGS[0].stage_id, 0)]}
    with pytest.raises(ValueError):
        FixedScheduleScheduler([(RUNGS[-1], 1000)], pools, rng_seed=0)
