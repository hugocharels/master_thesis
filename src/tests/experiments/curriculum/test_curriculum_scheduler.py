"""Tests for the curriculum scheduler (Phase 3).

The scheduler is the policy-agnostic glue between the per-stage
:class:`StageConfig` budget/threshold and the training loop. It owns:

1. :class:`PoolSampler` - uniform-random world sampler over a pool
   (a thin wrapper around ``random.Random.choice`` plus an
   empty-pool guard).
2. :class:`StageScheduler` - 4-stage hybrid-advance state machine
   (advance on success-rate threshold OR per-stage step cap), with
   reproducibility-friendly seeded RNG.

These tests deliberately use a ``_FakeWorld`` stub so that no level
generator (and therefore no SAT solver / ``lle.World``) needs to run -
the scheduler is purely combinatorial logic. ``CURRICULUM_STAGES`` is
imported from :mod:`experiments.curriculum.configs` to keep the
scheduler tests in lockstep with the thesis design.

Run with the marl venv (preferred):

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_curriculum_scheduler.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from experiments.curriculum.configs import CURRICULUM_STAGES
from experiments.curriculum.curriculum_scheduler import (
    PoolSampler,
    StageScheduler,
)


# ---- Stub world ------------------------------------------------------------


@dataclass(frozen=True)
class _FakeWorld:
    """Minimal stand-in for :class:`lle.World` in scheduler tests.

    The scheduler never calls any ``lle.World`` API - it only ever
    *returns* the world objects to the caller - so a tiny dataclass
    with a single ``idx`` field is enough to assert identity / origin.
    """

    idx: int


def _make_pool(n: int) -> list[_FakeWorld]:
    return [_FakeWorld(i) for i in range(n)]


def _make_pools_for_curriculum() -> list[list[_FakeWorld]]:
    """One distinct pool per curriculum stage.

    Each pool's ``_FakeWorld.idx`` values are offset by ``stage_idx*100``
    so the test ``test_sample_world_uses_current_stage_pool_after_advance``
    can tell which pool a sampled world came from without having to
    track object identity.
    """
    return [
        [_FakeWorld(stage_idx * 100 + i) for i in range(5)]
        for stage_idx in range(len(CURRICULUM_STAGES))
    ]


# ---- PoolSampler tests -----------------------------------------------------


def test_pool_sampler_visits_each_level_at_least_once_in_2x_episodes():
    """High-probability coverage check.

    Coupon-collector with N=10 has expected E[T]=10*H_10 ~ 29.3 draws
    to see every level once. ``2*pool_size=20`` is below E[T] so we
    use ``10*pool_size=100`` draws, where Pr[all seen] is effectively
    1. The seed is pinned so the assertion is deterministic.
    """
    pool = _make_pool(10)
    rng = random.Random(20260514)
    sampler = PoolSampler(pool, rng)
    seen: set[int] = set()
    for _ in range(100):
        world = sampler.next()
        seen.add(world.idx)
    assert seen == set(range(10))


def test_pool_sampler_is_seed_reproducible():
    pool = _make_pool(7)
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    sampler_a = PoolSampler(pool, rng_a)
    sampler_b = PoolSampler(pool, rng_b)
    seq_a = [sampler_a.next().idx for _ in range(30)]
    seq_b = [sampler_b.next().idx for _ in range(30)]
    assert seq_a == seq_b


def test_pool_sampler_raises_on_empty_pool():
    with pytest.raises(ValueError):
        PoolSampler([], random.Random(0))


# ---- StageScheduler tests --------------------------------------------------


# A deliberately small per-stage cap so the cap-trigger tests stay fast.
_TINY_STEP_CAP = 1_000
# A small success window so we don't need 100 episodes per test.
_TINY_WINDOW = 10


def _make_scheduler(
    *,
    per_stage_step_cap: int = _TINY_STEP_CAP,
    success_threshold: float = 0.80,
    success_window: int = _TINY_WINDOW,
    rng_seed: int = 20260514,
) -> StageScheduler:
    return StageScheduler(
        stages=CURRICULUM_STAGES,
        pools=_make_pools_for_curriculum(),
        rng_seed=rng_seed,
        per_stage_step_cap=per_stage_step_cap,
        success_threshold=success_threshold,
        success_window=success_window,
    )


def test_advances_when_success_threshold_hit():
    """Success-rate trigger advances stage 1 -> stage 2."""
    scheduler = _make_scheduler()
    assert scheduler.current_stage_id == 1

    for _ in range(_TINY_WINDOW):
        scheduler.record_episode(success=True, steps=1)

    advanced = scheduler.maybe_advance()
    assert advanced is True
    assert scheduler.current_stage_id == 2
    assert not scheduler.is_finished()


def test_advances_on_step_cap_even_without_success():
    """Cap trigger advances even with all-failure episodes.

    Each episode contributes ``steps``; the scheduler must integrate
    those and trigger as soon as the running total >= cap.
    """
    scheduler = _make_scheduler()
    # Many small failed episodes -> total steps grows past the cap.
    n_episodes = (_TINY_STEP_CAP // 10) + 1  # 10 steps each, > cap total
    for _ in range(n_episodes):
        scheduler.record_episode(success=False, steps=10)

    advanced = scheduler.maybe_advance()
    assert advanced is True
    assert scheduler.current_stage_id == 2


def test_no_advance_below_window_size():
    """Success-only path must not fire before the window is full.

    A short streak of perfect successes is not enough evidence: the
    scheduler must wait until ``success_window`` episodes have been
    recorded, mirroring the thesis spec's "rolling window" criterion.
    """
    scheduler = _make_scheduler()
    # Fewer than _TINY_WINDOW episodes, all successes.
    for _ in range(_TINY_WINDOW - 1):
        scheduler.record_episode(success=True, steps=1)

    advanced = scheduler.maybe_advance()
    assert advanced is False
    assert scheduler.current_stage_id == 1


def test_terminates_after_last_stage_cap():
    """Looping cap-triggered advances eventually flips ``is_finished``.

    Walk through all four stages by saturating the step cap each time.
    After the fourth cap-trigger, ``maybe_advance`` must return False
    (no further stage to move to) and ``is_finished()`` must be True.
    """
    scheduler = _make_scheduler()
    n_stages = len(CURRICULUM_STAGES)

    for stage_idx in range(n_stages):
        # Saturate this stage's step budget.
        n_episodes = (_TINY_STEP_CAP // 10) + 1
        for _ in range(n_episodes):
            scheduler.record_episode(success=False, steps=10)
        advanced = scheduler.maybe_advance()
        if stage_idx < n_stages - 1:
            assert advanced is True, f"should advance after stage {stage_idx + 1}"
            assert scheduler.current_stage_id == stage_idx + 2
            assert not scheduler.is_finished()
        else:
            # Final stage: cap fires but there's no stage k+1.
            assert advanced is False, "no advance possible after final stage"
            assert scheduler.is_finished()
            # current_stage_id must remain the final stage.
            assert scheduler.current_stage_id == CURRICULUM_STAGES[-1].stage_id


def test_sample_world_uses_current_stage_pool_after_advance():
    """The sampler must follow the active stage after every advance.

    Stage 1's pool has indices [0..4]; stage 2's has [100..104]. After
    one success-trigger advance, every sampled world must come from
    the stage-2 pool.
    """
    scheduler = _make_scheduler()
    # Pre-advance: world must come from stage 1's pool.
    pre_world = scheduler.sample_world()
    assert pre_world.idx in {0, 1, 2, 3, 4}

    for _ in range(_TINY_WINDOW):
        scheduler.record_episode(success=True, steps=1)
    assert scheduler.maybe_advance() is True
    assert scheduler.current_stage_id == 2

    stage2_indices = {100, 101, 102, 103, 104}
    # Many draws to make the assertion robust against any single
    # accidental in-bounds collision (here the index ranges are
    # disjoint, so even one draw is sufficient, but we draw many for
    # belt-and-braces).
    for _ in range(50):
        world = scheduler.sample_world()
        assert world.idx in stage2_indices


# ---- Extra correctness checks (bonus) --------------------------------------


def test_sample_world_works_after_finished():
    """After ``is_finished``, sampling still returns from the last stage.

    Consumers (eval loops, late-running training threads) might still
    need a world after the scheduler declares itself done; the spec
    says "still works after _finished=True (returns from the last
    stage's pool)".
    """
    scheduler = _make_scheduler()
    # Drive through every stage via cap.
    for _ in range(len(CURRICULUM_STAGES)):
        for _ in range((_TINY_STEP_CAP // 10) + 1):
            scheduler.record_episode(success=False, steps=10)
        scheduler.maybe_advance()

    assert scheduler.is_finished()
    last_pool_indices = {(len(CURRICULUM_STAGES) - 1) * 100 + i for i in range(5)}
    world = scheduler.sample_world()
    assert world.idx in last_pool_indices


def test_window_resets_between_stages():
    """A fresh stage must judge advancement on its own episodes only.

    If the scheduler kept the success deque across stages, a perfectly
    aced stage 1 would auto-advance stage 2 on its very first
    episode, defeating the per-stage budget.
    """
    scheduler = _make_scheduler()
    for _ in range(_TINY_WINDOW):
        scheduler.record_episode(success=True, steps=1)
    assert scheduler.maybe_advance() is True
    assert scheduler.current_stage_id == 2

    # One episode in stage 2, even successful, must not trigger an advance.
    scheduler.record_episode(success=True, steps=1)
    assert scheduler.maybe_advance() is False
    assert scheduler.current_stage_id == 2
