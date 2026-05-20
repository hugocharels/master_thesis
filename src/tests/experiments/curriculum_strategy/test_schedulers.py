"""Tests for the curriculum-strategy schedulers.

Uses a ``_FakeWorld`` stub (no SAT / lle.World) -- the schedulers are
pure combinatorial logic over opaque world tokens, like the existing
curriculum scheduler tests.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from experiments.curriculum_strategy.configs import RUNGS, TOTAL_STEPS
from experiments.curriculum_strategy.schedulers import (
    FixedScheduleScheduler,
    MixedSampler,
    make_strategy,
)


@dataclass(frozen=True)
class _FakeWorld:
    stage_id: int
    idx: int


def _fake_pools() -> dict[int, list[_FakeWorld]]:
    # One pool per rung, tagged with the rung's stage_id so a sampled
    # world reveals which rung it came from.
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


def test_forward_traverses_easy_to_hard_at_budget_boundaries():
    strat = make_strategy("forward", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)
    seen, step = _drain(strat, TOTAL_STEPS)
    # 600k / 3 = 200k per rung; 200k / 1000-step episodes = 200 episodes each
    assert seen[:200] == [1] * 200
    assert seen[200:400] == [2] * 200
    assert seen[400:600] == [3] * 200
    assert strat.is_finished()
    assert step == TOTAL_STEPS


def test_reverse_traverses_hard_to_easy():
    strat = make_strategy("reverse", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)
    seen, _ = _drain(strat, TOTAL_STEPS)
    assert seen[:200] == [3] * 200
    assert seen[200:400] == [2] * 200
    assert seen[400:600] == [1] * 200


def test_direct_stays_on_target_and_finishes_at_total():
    strat = make_strategy("direct", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)
    seen, step = _drain(strat, TOTAL_STEPS)
    assert set(seen) == {3}            # target rung only
    assert len(seen) == 600            # 600k / 1000
    assert strat.is_finished()
    assert step == TOTAL_STEPS


def test_mixed_covers_all_rungs_and_never_finishes():
    strat = make_strategy("mixed", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)
    seen, step = _drain(strat, TOTAL_STEPS)
    assert set(seen) == {1, 2, 3}      # all difficulties seen
    assert not strat.is_finished()     # bounded only by the runner's total
    assert step == TOTAL_STEPS


def test_mixed_is_reproducible_under_seed():
    a, _ = _drain(make_strategy("mixed", RUNGS, _fake_pools(), 50_000, 0), 50_000)
    b, _ = _drain(make_strategy("mixed", RUNGS, _fake_pools(), 50_000, 0), 50_000)
    assert a == b


def test_unknown_condition_raises():
    with pytest.raises(ValueError):
        make_strategy("bogus", RUNGS, _fake_pools(), TOTAL_STEPS, rng_seed=0)


def test_fixed_schedule_rejects_empty_and_nonpositive_budget():
    pools = _fake_pools()
    with pytest.raises(ValueError):
        FixedScheduleScheduler([], pools, rng_seed=0)
    with pytest.raises(ValueError):
        FixedScheduleScheduler([(RUNGS[0], 0)], pools, rng_seed=0)
