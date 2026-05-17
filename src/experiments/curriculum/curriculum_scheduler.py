"""Curriculum scheduler for the four-stage transfer experiment.

Two cooperating pieces of state:

* :class:`PoolSampler` is a stateless (modulo its caller-owned
  :class:`random.Random`) uniform sampler over a sequence of worlds.
* :class:`StageScheduler` is the four-stage state machine that owns
  the *current* :class:`PoolSampler`, tracks per-stage progress (step
  budget consumed, rolling success-rate window), and advances stages
  on a hybrid criterion: rolling success rate ``>= success_threshold``
  over the last ``success_window`` episodes, OR per-stage step cap
  reached, whichever fires first.

References
----------
- Thesis, RQ4 (curriculum transfer protocol): the four
  :class:`StageConfig` instances live in
  :mod:`experiments.curriculum.configs` and are the single source of
  truth for stage geometry.
- ``docs/superpowers/notes/marl-api.md`` section 9.8: motivates why
  Phase 4 cannot just call :func:`Experiment.run` for every stage -
  ``simple_run`` triggers ``trainer.randomize()`` and would wipe the
  weights between stages. The scheduler here is policy-agnostic; it
  only tells the runner *which world to sample next* and *whether to
  move on*. The custom Phase-4 runner is responsible for keeping the
  trainer alive across stage transitions.
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Sequence
from typing import Generic, TypeVar

from experiments.curriculum.configs import StageConfig


# Generic over the world type so the scheduler can be exercised with a
# stub ``_FakeWorld`` in tests and with real ``lle.World`` in
# production - both satisfy the same "opaque token returned by sample"
# contract.
W = TypeVar("W")


# ---------------------------------------------------------------------------
# PoolSampler
# ---------------------------------------------------------------------------


class PoolSampler(Generic[W]):
    """Uniform-random sampler over a fixed sequence of worlds.

    Construction validates that the pool is non-empty (an empty pool
    would silently yield ``IndexError`` on the first ``next()``, which
    is harder to debug than a fail-fast ``ValueError`` at construction
    time).

    The :class:`random.Random` instance is *owned by the caller*. The
    :class:`StageScheduler` deliberately keeps a single
    :class:`random.Random` across stage transitions so the global
    sequence of pseudo-random draws stays continuous and reproducible
    (handing back the same seed on a re-run reproduces every world
    pick across all four stages).
    """

    def __init__(self, pool: Sequence[W], rng: random.Random) -> None:
        if len(pool) == 0:
            raise ValueError("PoolSampler requires a non-empty pool")
        # Hold a reference, not a copy: pools are large and immutable
        # for the lifetime of a stage.
        self._pool: Sequence[W] = pool
        self._rng = rng

    def next(self) -> W:
        """Return one world drawn uniformly at random from the pool."""
        return self._rng.choice(self._pool)


# ---------------------------------------------------------------------------
# StageScheduler
# ---------------------------------------------------------------------------


class StageScheduler(Generic[W]):
    """Four-stage curriculum advancement state machine.

    Hybrid trigger: a stage advances as soon as **either** criterion
    fires:

    * ``mean(recent_successes) >= success_threshold`` once the rolling
      window has at least ``success_window`` entries (success path);
    * ``stage_steps >= per_stage_step_cap`` (cap path - guarantees
      termination even on a stage the agent cannot solve).

    On the final stage, the same trigger flips an internal
    ``_finished`` flag instead of incrementing the stage index, so
    consumers (training loop, eval loop) can keep calling
    :meth:`sample_world` after the scheduler is done - the last
    stage's pool is the one that remains active.

    Reproducibility: a single :class:`random.Random(rng_seed)` instance
    is kept for the entire run and threaded into every per-stage
    :class:`PoolSampler`. This preserves continuity of the global RNG
    sequence across stage transitions; resetting the RNG at each
    advance would be surprising and would make stage-N world picks
    independent of stage-(N-1) progress, which is *not* what the
    thesis asks for.
    """

    def __init__(
        self,
        stages: Sequence[StageConfig],
        pools: list[list[W]],
        rng_seed: int,
        per_stage_step_cap: int | Sequence[int],
        success_threshold: float = 0.80,
        success_window: int = 100,
    ) -> None:
        if len(stages) == 0:
            raise ValueError("StageScheduler requires at least one stage")
        if len(pools) != len(stages):
            raise ValueError(
                f"len(pools)={len(pools)} must match len(stages)={len(stages)}"
            )
        # Normalise per_stage_step_cap to a per-stage list. An int means
        # "same cap for every stage" (legacy behaviour); a sequence must
        # match len(stages) (one cap per stage, supporting asymmetric
        # budgets).
        if isinstance(per_stage_step_cap, int):
            caps = [per_stage_step_cap] * len(stages)
        else:
            caps = list(per_stage_step_cap)
            if len(caps) != len(stages):
                raise ValueError(
                    f"per_stage_step_cap sequence length {len(caps)} "
                    f"must match len(stages)={len(stages)}"
                )
        for i, c in enumerate(caps):
            if c <= 0:
                raise ValueError(
                    f"per_stage_step_cap[{i}] must be positive, got {c}"
                )
        if success_window <= 0:
            raise ValueError(
                f"success_window must be positive, got {success_window}"
            )
        if not 0.0 <= success_threshold <= 1.0:
            raise ValueError(
                f"success_threshold must be in [0, 1], got {success_threshold}"
            )

        self._stages: tuple[StageConfig, ...] = tuple(stages)
        self._pools: tuple[tuple[W, ...], ...] = tuple(tuple(p) for p in pools)
        self._per_stage_step_caps: tuple[int, ...] = tuple(caps)
        self._success_threshold = success_threshold
        self._success_window = success_window

        # One RNG kept for the whole run - see class docstring.
        self._rng = random.Random(rng_seed)

        self._stage_idx: int = 0
        self._stage_steps: int = 0
        self._recent_successes: deque[bool] = deque(maxlen=success_window)
        self._finished: bool = False

        # Build the first sampler eagerly so ``sample_world`` works
        # before any episode has been recorded.
        self._sampler: PoolSampler[W] = PoolSampler(
            self._pools[self._stage_idx], self._rng
        )

    # -- Read-only views -----------------------------------------------------

    @property
    def current_stage(self) -> StageConfig:
        """The :class:`StageConfig` for the active stage.

        After ``is_finished()`` becomes True, this still returns the
        last (final) stage, mirroring :meth:`sample_world` semantics.
        """
        return self._stages[self._stage_idx]

    @property
    def current_stage_id(self) -> int:
        """1-based stage id of the active stage (matches the thesis labels)."""
        return self.current_stage.stage_id

    def is_finished(self) -> bool:
        """``True`` once the final stage's trigger has fired."""
        return self._finished

    # -- Sampling ------------------------------------------------------------

    def sample_world(self) -> W:
        """Return a world from the active stage's pool."""
        return self._sampler.next()

    # -- Episode bookkeeping -------------------------------------------------

    def record_episode(self, success: bool, steps: int) -> None:
        """Record a finished episode against the active stage's budget.

        Once :meth:`is_finished` is True the scheduler stops
        accumulating steps / successes - any further episodes belong
        to the eval phase, not curriculum bookkeeping.
        """
        if self._finished:
            return
        if steps < 0:
            raise ValueError(f"steps must be non-negative, got {steps}")
        self._stage_steps += steps
        self._recent_successes.append(bool(success))

    def maybe_advance(self) -> bool:
        """Advance to the next stage if either trigger fires.

        Returns
        -------
        bool
            ``True`` iff the scheduler just advanced to a new stage in
            this call. Returns ``False`` when no trigger fires *and*
            when the final-stage trigger fires (the latter case flips
            ``is_finished`` instead of advancing).
        """
        if self._finished:
            return False

        success_trigger = (
            len(self._recent_successes) >= self._success_window
            and self._mean_recent() >= self._success_threshold
        )
        cap_trigger = self._stage_steps >= self._per_stage_step_caps[self._stage_idx]

        if not (success_trigger or cap_trigger):
            return False

        # Trigger fired. Either advance or terminate.
        is_last_stage = self._stage_idx == len(self._stages) - 1
        if is_last_stage:
            self._finished = True
            return False

        self._stage_idx += 1
        self._stage_steps = 0
        # New per-stage window: previous successes belonged to the
        # previous stage and would otherwise let stage N+1 auto-advance
        # off stage N's evidence.
        self._recent_successes.clear()
        # Re-bind the sampler to the new stage's pool. Reuse the same
        # RNG to keep the global pseudo-random sequence continuous.
        self._sampler = PoolSampler(self._pools[self._stage_idx], self._rng)
        return True

    # -- Internals -----------------------------------------------------------

    def _mean_recent(self) -> float:
        """Mean of the rolling success deque (caller checks non-emptiness)."""
        # ``sum`` of bools is fine and avoids the float overhead of
        # ``statistics.mean`` on a tiny deque.
        return sum(self._recent_successes) / len(self._recent_successes)

    # -- Checkpointing -------------------------------------------------------

    def state_dict(self) -> dict:
        """Return a JSON-serialisable snapshot of the scheduler's state.

        Captures the bookkeeping needed to resume mid-run from a
        checkpoint:

        * ``stage_idx`` and the per-stage cumulative ``stage_steps``;
        * the rolling ``recent_successes`` window (as a plain list);
        * the ``finished`` terminal flag;
        * the underlying ``random.Random`` state so the next pool draw
          continues the exact same pseudo-random sequence (key for
          reproducibility across restarts).

        The static configuration (``stages``, ``pools``,
        ``per_stage_step_cap``, ``success_threshold``,
        ``success_window``) is *not* serialised: the caller is expected
        to rebuild the scheduler with the same constructor arguments
        and only restore the dynamic state via
        :meth:`load_state_dict`.
        """
        return {
            "stage_idx": self._stage_idx,
            "stage_steps": self._stage_steps,
            "recent_successes": list(self._recent_successes),
            "finished": self._finished,
            # ``random.Random.getstate`` returns a tuple of (version, tuple,
            # gauss_next). It is not JSON-friendly as-is (nested tuples,
            # potential ``None``); convert to a list-of-lists round-trip
            # safe form. ``load_state_dict`` reverses this.
            "rng_state": _rng_state_to_jsonable(self._rng.getstate()),
        }

    def load_state_dict(self, state: dict) -> None:
        """Restore scheduler state previously produced by :meth:`state_dict`.

        After this call:

        * the active stage index, per-stage step counter, success
          deque and ``_finished`` flag match the snapshot;
        * the internal RNG resumes from the exact recorded state, so
          the next ``sample_world()`` call returns the same world the
          original (uninterrupted) run would have returned;
        * the active :class:`PoolSampler` is rebound to the correct
          stage's pool.
        """
        stage_idx = int(state["stage_idx"])
        if not 0 <= stage_idx < len(self._stages):
            raise ValueError(
                f"stage_idx={stage_idx} out of range [0, {len(self._stages)})"
            )
        stage_steps = int(state["stage_steps"])
        if stage_steps < 0:
            raise ValueError(f"stage_steps must be non-negative, got {stage_steps}")

        self._stage_idx = stage_idx
        self._stage_steps = stage_steps
        # Rebuild the deque with the configured maxlen so the rolling
        # window keeps its size invariant after the restore.
        recent = [bool(x) for x in state.get("recent_successes", [])]
        self._recent_successes = deque(recent, maxlen=self._success_window)
        self._finished = bool(state.get("finished", False))

        rng_state = state.get("rng_state")
        if rng_state is not None:
            self._rng.setstate(_rng_state_from_jsonable(rng_state))

        # Re-bind the sampler to the (now possibly different) active
        # stage's pool. Reuse the same RNG to preserve the global PRNG
        # sequence (matches advance-time semantics in
        # :meth:`maybe_advance`).
        self._sampler = PoolSampler(self._pools[self._stage_idx], self._rng)


# ---------------------------------------------------------------------------
# RNG state JSON helpers
# ---------------------------------------------------------------------------


def _rng_state_to_jsonable(state: tuple) -> list:
    """Convert ``random.Random.getstate()`` output to a JSON-safe list.

    ``state`` is a ``(version, internalstate_tuple, gauss_next_or_None)``
    triple. We return a 3-element list ``[version, list(internal),
    gauss_next]`` so it survives a JSON round-trip.
    """
    version, internal, gauss_next = state
    return [int(version), [int(x) for x in internal], gauss_next]


def _rng_state_from_jsonable(serialised: list) -> tuple:
    """Inverse of :func:`_rng_state_to_jsonable`."""
    version, internal, gauss_next = serialised
    return (int(version), tuple(int(x) for x in internal), gauss_next)
