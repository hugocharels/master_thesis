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

    @property
    def current_budget(self) -> int:
        """Step budget of the entry currently being trained."""
        return self._schedule[self._idx][1]

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
        total_steps: int,
    ) -> None:
        if len(rungs) == 0:
            raise ValueError("rungs must be non-empty")
        self._rungs = list(rungs)
        self._total_steps = total_steps
        self._rng = random.Random(rng_seed)
        self._samplers = {
            r.stage_id: PoolSampler(pools[r.stage_id], self._rng) for r in rungs
        }

    @property
    def current_rung(self) -> StageConfig:
        # No single "current" rung; report the hardest for logging.
        return self._rungs[-1]

    @property
    def current_budget(self) -> int:
        """No staging -- the whole run is one budget for epsilon scheduling."""
        return self._total_steps

    def next_world(self) -> tuple[object, StageConfig]:
        rung = self._rng.choice(self._rungs)
        return self._samplers[rung.stage_id].next(), rung

    def record_steps(self, n: int) -> None:
        return None

    def is_finished(self) -> bool:
        return False


def _scaled_budgets(stage_budgets: Sequence[int], total_steps: int) -> list[int]:
    """Scale ``stage_budgets`` proportionally so they sum to ``total_steps``.

    Lets the per-stage split (e.g. 50k/150k summing to the full 200k) be reused
    verbatim for a shorter ``--steps`` run (e.g. a smoke test) while always
    conserving the total exactly -- the rounding remainder goes to the last
    stage.
    """
    s = sum(stage_budgets)
    if s <= 0:
        raise ValueError(f"stage_budgets must sum to a positive value, got {s}")
    out = [int(b / s * total_steps) for b in stage_budgets]
    out[-1] += total_steps - sum(out)
    return out


def make_strategy(
    condition: str,
    rungs: Sequence[StageConfig],
    pools: dict[int, list],
    total_steps: int,
    rng_seed: int,
    stage_budgets: Sequence[int] | None = None,
):
    """Build the strategy object for ``condition``.

    ``forward``/``reverse`` allocate ``total_steps`` across the rungs using
    ``stage_budgets`` (aligned to ``rungs`` order, scaled to sum to
    ``total_steps``); when ``stage_budgets`` is ``None`` they fall back to an
    equal split. ``reverse`` keeps each rung's budget but visits the rungs in
    reverse order, so the only difference from ``forward`` is the ordering.
    ``direct`` puts the whole budget on the last (target) rung; ``mixed``
    samples rungs uniformly for the whole budget.
    """
    from experiments.curriculum_strategy.configs import equal_split

    rungs = list(rungs)
    target = rungs[-1]
    if condition == "direct":
        return FixedScheduleScheduler([(target, total_steps)], pools, rng_seed)
    if condition in ("forward", "reverse"):
        if stage_budgets is None:
            budgets = equal_split(total_steps, len(rungs))
        else:
            if len(stage_budgets) != len(rungs):
                raise ValueError(
                    f"stage_budgets length {len(stage_budgets)} must match "
                    f"len(rungs)={len(rungs)}"
                )
            budgets = _scaled_budgets(stage_budgets, total_steps)
        pairs = list(zip(rungs, budgets))
        if condition == "reverse":
            pairs = list(reversed(pairs))  # same per-rung budget, reversed order
        return FixedScheduleScheduler(pairs, pools, rng_seed)
    if condition == "mixed":
        return MixedSampler(rungs, pools, rng_seed, total_steps)
    raise ValueError(
        f"Unknown condition {condition!r}; expected one of "
        f"direct/forward/reverse/mixed"
    )
