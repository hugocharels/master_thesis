"""Scheduling primitives for the curriculum-strategy comparison.

Two strategy types, both reusing the existing
:class:`experiments.curriculum.curriculum_scheduler.PoolSampler`:

* :class:`FixedScheduleScheduler` -- walks an ordered list of
  ``(rung, step_budget)`` pairs, advancing purely on consumed steps (no
  mastery early-exit), so every condition is exactly budget-matched.
  Drives ``direct`` (single entry), ``forward`` and ``reverse``.
* :class:`MixedSampler` -- draws a rung uniformly at random each episode
  (domain randomization); the runner's global step total bounds it.

Both satisfy the same minimal contract the runner needs:
``next_world() -> (world, rung)``, ``record_steps(n)``, ``is_finished()``.
"""
from __future__ import annotations

import random
from collections.abc import Sequence

from experiments.curriculum.configs import StageConfig
from experiments.curriculum.curriculum_scheduler import PoolSampler


class FixedScheduleScheduler:
    """Budget-driven walk over an ordered ``(rung, step_budget)`` schedule.

    Advances to the next entry once the consumed steps reach the current
    entry's budget; any overshoot from the final episode carries into the
    next entry so the cumulative budget is preserved. On the last entry
    the same trigger flips ``_finished`` instead of advancing.
    """

    def __init__(
        self,
        schedule: Sequence[tuple[StageConfig, int]],
        pools: dict[int, list],
        rng_seed: int,
    ) -> None:
        if len(schedule) == 0:
            raise ValueError("schedule must have at least one entry")
        for rung, budget in schedule:
            if budget <= 0:
                raise ValueError(f"budget must be positive, got {budget}")
            if rung.stage_id not in pools:
                raise ValueError(f"no pool for rung stage_id={rung.stage_id}")
        self._schedule = list(schedule)
        self._pools = pools
        self._rng = random.Random(rng_seed)
        self._idx = 0
        self._steps_in_current = 0
        self._finished = False
        self._sampler = PoolSampler(pools[self._schedule[0][0].stage_id], self._rng)

    @property
    def current_rung(self) -> StageConfig:
        return self._schedule[self._idx][0]

    def next_world(self) -> tuple[object, StageConfig]:
        return self._sampler.next(), self.current_rung

    def record_steps(self, n: int) -> None:
        if self._finished:
            return
        if n < 0:
            raise ValueError(f"steps must be non-negative, got {n}")
        self._steps_in_current += n
        while (
            not self._finished
            and self._steps_in_current >= self._schedule[self._idx][1]
        ):
            carry = self._steps_in_current - self._schedule[self._idx][1]
            if self._idx == len(self._schedule) - 1:
                self._finished = True
            else:
                self._idx += 1
                self._steps_in_current = carry
                self._sampler = PoolSampler(
                    self._pools[self._schedule[self._idx][0].stage_id], self._rng
                )

    def is_finished(self) -> bool:
        return self._finished


class MixedSampler:
    """Uniform-random rung each episode (domain randomization).

    Never reports finished -- the runner's global step budget is the only
    stopping condition.
    """

    def __init__(
        self,
        rungs: Sequence[StageConfig],
        pools: dict[int, list],
        rng_seed: int,
    ) -> None:
        if len(rungs) == 0:
            raise ValueError("rungs must be non-empty")
        self._rungs = list(rungs)
        self._rng = random.Random(rng_seed)
        self._samplers = {
            r.stage_id: PoolSampler(pools[r.stage_id], self._rng) for r in rungs
        }

    @property
    def current_rung(self) -> StageConfig:
        # No single "current" rung; report the hardest for logging.
        return self._rungs[-1]

    def next_world(self) -> tuple[object, StageConfig]:
        rung = self._rng.choice(self._rungs)
        return self._samplers[rung.stage_id].next(), rung

    def record_steps(self, n: int) -> None:
        return None

    def is_finished(self) -> bool:
        return False


def make_strategy(
    condition: str,
    rungs: Sequence[StageConfig],
    pools: dict[int, list],
    total_steps: int,
    rng_seed: int,
):
    """Build the strategy object for ``condition``.

    ``forward``/``reverse`` split ``total_steps`` into equal per-rung
    budgets; ``direct`` puts the whole budget on the last (target) rung;
    ``mixed`` samples rungs uniformly for the whole budget.
    """
    from experiments.curriculum_strategy.configs import equal_split

    rungs = list(rungs)
    target = rungs[-1]
    if condition == "direct":
        return FixedScheduleScheduler([(target, total_steps)], pools, rng_seed)
    if condition == "forward":
        budgets = equal_split(total_steps, len(rungs))
        return FixedScheduleScheduler(list(zip(rungs, budgets)), pools, rng_seed)
    if condition == "reverse":
        budgets = equal_split(total_steps, len(rungs))
        return FixedScheduleScheduler(
            list(zip(list(reversed(rungs)), budgets)), pools, rng_seed
        )
    if condition == "mixed":
        return MixedSampler(rungs, pools, rng_seed)
    raise ValueError(
        f"Unknown condition {condition!r}; expected one of "
        f"direct/forward/reverse/mixed"
    )
