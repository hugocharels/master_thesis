"""CLI entry point for the curriculum-transfer MARL experiment (Phase 4).

Trains one (condition, algo, seed) configuration and writes per-run
results under ``{out_dir}/runs/{condition}_{algo}_seed{N}/``:

    - ``level6_eval.csv``     periodic greedy evaluations on hand-crafted Level 6
                              (columns: ``step,success_rate,mean_return``)
    - ``stage_progress.csv``  CURR-only stage transition log
                              (columns: ``step,stage_id``)
    - ``final_results.json``  end-of-run summary (success rate, return, ...)

Run with the marl venv (system python3.13 cannot import marl, see
``docs/superpowers/notes/marl-api.md`` section 5)::

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe \\
        -m experiments.curriculum.run_experiment \\
        --condition CURR --algo QMIX --seed 0

Why a custom training loop instead of :func:`marl.simple_run` /
:meth:`Experiment.run`:
``simple_run`` calls ``trainer.randomize()`` on every entry, which would
wipe the Q-net weights between curriculum stages. The CURR condition
needs the trainer / replay buffer / optimiser to *persist* across stage
transitions while only the env (geometry + ``t_max``) changes. The
custom loop in :func:`_train_loop` mirrors marl's
``simple_runner._train_episode`` minus the randomisation step. See
``docs/superpowers/notes/marl-api.md`` section 9.8.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import lle
import numpy as np
import torch
from lle import World
from marlenv import Episode, Transition

import marl
from marl import algos
from marl.nn import mixers
from marl.nn.model_bank import qnetworks
from marl.policy import ArgMax, EpsilonGreedy

from experiments.curriculum.configs import (
    ADVANCEMENT_SUCCESS_THRESHOLD,
    ADVANCEMENT_WINDOW_EPISODES,
    CURRICULUM_STAGES,
    EVAL_EPISODES,
    EVAL_FREQUENCY_STEPS,
    FINAL_EVAL_EPISODES,
    FULL_RUN_TOTAL_STEPS,
    PILOT_RUN_TOTAL_STEPS,
    RNG_SEED,
)
from experiments.curriculum.curriculum_scheduler import StageScheduler
from experiments.curriculum.lle_marl_env import PadObservations3D, ThesisLLEConfig
from experiments.curriculum.pool_generator import load_pool, pool_path

# ---------------------------------------------------------------------------
# Constants and types
# ---------------------------------------------------------------------------

CONDITIONS = ("B1", "B2", "B3", "CURR")
ALGOS = ("QMIX", "VDN", "IQL")

DEFAULT_OUT_DIR = Path("results") / "curriculum_experiment"


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser.

    Exposed at module scope so unit tests can exercise the parser
    without invoking :func:`main`.
    """
    parser = argparse.ArgumentParser(
        prog="run_experiment",
        description=(
            "Train one (condition, algo, seed) cell of the curriculum-transfer "
            "experiment and write CSV / JSON results."
        ),
    )
    parser.add_argument(
        "--condition",
        required=True,
        choices=CONDITIONS,
        help="Experimental condition (B1, B2, B3, CURR).",
    )
    parser.add_argument(
        "--algo",
        required=True,
        choices=ALGOS,
        help="MARL algorithm (QMIX, VDN, IQL).",
    )
    parser.add_argument(
        "--seed",
        required=True,
        type=int,
        help="Integer seed for python/numpy/torch and the scheduler RNG.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=FULL_RUN_TOTAL_STEPS,
        help=(
            "Total environment steps to train. "
            f"Defaults to {FULL_RUN_TOTAL_STEPS}. "
            f"If set to {PILOT_RUN_TOTAL_STEPS}, the CURR scheduler uses the "
            "pilot per-stage step caps; otherwise it uses the full caps."
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=(
            "Top-level output directory. The run directory is "
            "{out_dir}/runs/{condition}_{algo}_seed{N}/."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# Pool loading per condition
# ---------------------------------------------------------------------------


def _load_pools_for_condition(
    condition: str, out_dir: Path
) -> list[list[World]]:
    """Return a list of training pools keyed by curriculum stage.

    For B1/B2/B3 there is exactly one logical pool (returned as a
    one-element list). For CURR there are 4 pools, one per stage in the
    same order as :data:`CURRICULUM_STAGES`.

    B3 returns ``[[World.level(6)]]`` regardless of ``out_dir`` (the
    pool is hand-crafted Level 6, no disk I/O needed). All other
    conditions read pre-flight-generated levels from disk.
    """
    if condition == "B3":
        return [[World.level(6)]]
    if condition == "B1":
        # Stage-4 train pool only.
        return [load_pool(pool_path(out_dir, CURRICULUM_STAGES[3], "train"))]
    if condition == "B2":
        # Union of all 4 stages' train pools, one big bag the runner
        # samples uniformly from.
        union: list[World] = []
        for stage in CURRICULUM_STAGES:
            union.extend(load_pool(pool_path(out_dir, stage, "train")))
        return [union]
    if condition == "CURR":
        return [
            load_pool(pool_path(out_dir, stage, "train"))
            for stage in CURRICULUM_STAGES
        ]
    raise ValueError(f"Unknown condition: {condition!r}")


# ---------------------------------------------------------------------------
# Trainer / agent construction
# ---------------------------------------------------------------------------


def _build_sample_env_config(condition: str, pools: list[list[World]]) -> ThesisLLEConfig:
    """Build the ``ThesisLLEConfig`` used to size the Q-network.

    The trainer / mixer / replay buffer must be built *once*. We size
    them from a stage-4-geometry world (`World.level(6)` has the same
    grid, agent and laser counts as stage 4 in the current design) so
    that the Q-network's expected observation shape is the *maximum*
    across all curriculum stages. Per-episode envs are wrapped with
    :class:`PadObservations3D` to zero-pad smaller-stage observations
    up to the same shape.

    The ``condition`` argument is kept for symmetry with
    :func:`_load_pools_for_condition` but is no longer needed for
    sizing.
    """
    del condition, pools  # unused: sizing is condition-independent
    t_max = CURRICULUM_STAGES[3].t_max
    return ThesisLLEConfig.from_world(World.level(6), t_max=t_max)


def _target_obs_shape() -> tuple[int, int, int]:
    """Return the obs shape that all stages must be padded up to.

    Stage 4 has the largest grid (12x13) and the largest channel count
    (3 lasers), so its layered observation is the elementwise maximum
    across the curriculum stages.
    """
    cfg = ThesisLLEConfig.from_world(World.level(6), t_max=CURRICULUM_STAGES[3].t_max)
    shape = cfg.env.observation_shape
    return (int(shape[0]), int(shape[1]), int(shape[2]))


def _make_padded_env(world: World, t_max: int, target_obs_shape: tuple[int, int, int]):
    """Build a ``ThesisLLEConfig``-backed env padded to ``target_obs_shape``."""
    cfg = ThesisLLEConfig.from_world(world, t_max=t_max)
    return PadObservations3D(cfg.env, target_obs_shape)


def _build_trainer(algo: str, sample_env: ThesisLLEConfig):
    """Build a trainer with the given algorithm using ``sample_env`` for sizing.

    All three algorithms share the same Q-network factory call (per
    ``marl-api.md`` section 2.5, ``independent=True`` is recommended for
    IQL and VDN; for QMix we use the shared default to match the
    canonical example).
    """
    if algo == "QMIX":
        qnet = qnetworks.from_env(sample_env)
        return algos.QMix(
            qnet,
            mixer=mixers.QMix.from_env(sample_env),
            train_policy=EpsilonGreedy.linear(1.0, 0.05, 100_000),
            test_policy=ArgMax(),
            lr=5e-4,
            batch_size=64,
            gamma=0.95,
            train_interval=(5, "step"),
            grad_norm_clipping=10,
        )
    if algo == "VDN":
        qnet = qnetworks.from_env(sample_env, independent=True)
        return algos.VDN(
            qnet,
            train_policy=EpsilonGreedy.linear(1.0, 0.05, 100_000),
            test_policy=ArgMax(),
            lr=5e-4,
            batch_size=64,
            gamma=0.95,
            train_interval=(5, "step"),
            grad_norm_clipping=10,
        )
    if algo == "IQL":
        qnet = qnetworks.from_env(sample_env, independent=True)
        return algos.DQN(
            qnet,
            mixer=None,
            train_policy=EpsilonGreedy.linear(1.0, 0.05, 100_000),
            test_policy=ArgMax(),
            lr=5e-4,
            batch_size=64,
            gamma=0.95,
            train_interval=(5, "step"),
            grad_norm_clipping=10,
        )
    raise ValueError(f"Unknown algo: {algo!r}")


# ---------------------------------------------------------------------------
# Sampler abstraction (uniform vs. curriculum)
# ---------------------------------------------------------------------------


@dataclass
class _UniformSampler:
    """Uniform-with-current-stage sampler used by B1/B2/B3.

    Implements the same minimal interface the training loop uses:
    ``sample_world()``, ``current_t_max``, ``record_episode``,
    ``maybe_advance``, ``current_stage_id``, ``is_finished``. This lets
    the loop in :func:`_train_loop` stay condition-agnostic.
    """

    pool: list[World]
    t_max: int
    rng: random.Random

    def sample_world(self) -> World:
        return self.rng.choice(self.pool)

    @property
    def current_t_max(self) -> int:
        return self.t_max

    @property
    def current_stage_id(self) -> int:
        # Baselines have no stage progression - return 0 to signal this
        # in the (unused for baselines) stage_progress.csv.
        return 0

    def record_episode(self, success: bool, steps: int) -> None:  # noqa: ARG002
        return None

    def maybe_advance(self) -> bool:
        return False

    def is_finished(self) -> bool:
        return False


class _SchedulerSampler:
    """Adapter exposing the same interface around :class:`StageScheduler`."""

    def __init__(self, scheduler: StageScheduler) -> None:
        self._scheduler = scheduler

    def sample_world(self) -> World:
        return self._scheduler.sample_world()

    @property
    def current_t_max(self) -> int:
        return self._scheduler.current_stage.t_max

    @property
    def current_stage_id(self) -> int:
        return self._scheduler.current_stage_id

    def record_episode(self, success: bool, steps: int) -> None:
        self._scheduler.record_episode(success=success, steps=steps)

    def maybe_advance(self) -> bool:
        return self._scheduler.maybe_advance()

    def is_finished(self) -> bool:
        return self._scheduler.is_finished()


# ---------------------------------------------------------------------------
# Episode primitives
# ---------------------------------------------------------------------------


def _episode_success(info: dict, episode: Episode) -> bool:
    """An episode "succeeded" iff every agent reached an exit.

    LLE encodes this in ``info["exit_rate"]`` (== ``n_arrived /
    n_agents``); ``exit_rate >= 1.0`` means all agents exited. We also
    require the env to be ``done`` (not just truncated) so a time-out
    on a near-finished episode does not count as success.
    """
    return bool(episode.is_done) and float(info.get("exit_rate", 0.0)) >= 1.0 - 1e-9


def _train_one_episode(env, agent, trainer, time_step: int, episode_num: int, max_steps: int) -> tuple[Episode, dict, int]:
    """Run a single training episode and return (episode, last_info, end_step).

    Mirrors :func:`marl.runners.simple_runner._train_episode` but:
    - takes the env as a positional (we rebuild it per episode);
    - returns the final ``info`` dict so the caller can extract
      ``exit_rate``;
    - never invokes test logging (the caller decides when to eval).
    """
    obs, state = env.reset()
    agent.new_episode()
    episode = Episode.new(obs, state, metrics={"episode_num": episode_num})
    last_info: dict = {}
    while not episode.is_finished:
        action = agent.choose_action(obs)
        step = env.step(action.action)
        if time_step + 1 >= max_steps:
            step.truncated = True
        transition = Transition.from_step(obs, state, action.action, step, **action.details)
        trainer.update_step(transition, time_step)
        episode.add(transition)
        obs = step.obs
        state = step.state
        last_info = step.info
        time_step += 1
    trainer.update_episode(episode, episode_num, time_step)
    return episode, last_info, time_step


def _greedy_eval_episode(env, eval_agent) -> tuple[bool, float]:
    """Run one greedy episode (epsilon=0). Returns ``(success, return)``.

    The eval agent shares the trainer's Q-network but uses ``ArgMax`` as
    its policy (set via :meth:`Agent.set_testing`). The function fully
    handles env reset and step.
    """
    obs, state = env.reset()
    eval_agent.new_episode()
    episode = Episode.new(obs, state)
    last_info: dict = {}
    while not episode.is_finished:
        action = eval_agent.choose_action(obs)
        step = env.step(action.action)
        transition = Transition.from_step(obs, state, action.action, step, **action.details)
        episode.add(transition)
        obs = step.obs
        state = step.state
        last_info = step.info
    success = _episode_success(last_info, episode)
    total_return = float(np.sum(np.array(episode.rewards)))
    return success, total_return


def _evaluate(
    eval_pool: list[World],
    eval_t_max: int,
    eval_agent,
    n_episodes: int,
    eval_rng: random.Random,
    target_obs_shape: tuple[int, int, int],
) -> tuple[float, float, float]:
    """Run ``n_episodes`` greedy evals over ``eval_pool``.

    Returns (success_rate, success_rate_std, mean_return).
    Uniformly samples one world per episode from ``eval_pool``.
    """
    eval_agent.set_testing()
    successes: list[int] = []
    returns: list[float] = []
    try:
        for _ in range(n_episodes):
            world = eval_rng.choice(eval_pool)
            env = _make_padded_env(world, t_max=eval_t_max, target_obs_shape=target_obs_shape)
            success, total_return = _greedy_eval_episode(env, eval_agent)
            successes.append(int(success))
            returns.append(total_return)
    finally:
        eval_agent.set_training()
    if len(successes) == 0:
        return 0.0, 0.0, 0.0
    succ_arr = np.asarray(successes, dtype=np.float64)
    ret_arr = np.asarray(returns, dtype=np.float64)
    return float(succ_arr.mean()), float(succ_arr.std()), float(ret_arr.mean())


# ---------------------------------------------------------------------------
# Top-level training loop
# ---------------------------------------------------------------------------


def _train_loop(
    *,
    sampler,
    trainer,
    agent,
    eval_agent,
    eval_pool: list[World],
    eval_t_max: int,
    total_steps: int,
    csv_writer_eval,
    csv_writer_stage,
    eval_rng: random.Random,
    log_stage_transitions: bool,
    target_obs_shape: tuple[int, int, int],
    start_step: int = 0,
    start_episode: int = 0,
    start_wall_clock_seconds: float = 0.0,
    run_dir: Path | None = None,
    scheduler_for_checkpoint: StageScheduler | None = None,
) -> int:
    """Drive the shared trainer through ``total_steps`` env steps.

    Returns the actual number of env steps consumed (which may slightly
    exceed ``total_steps`` because we never cut an episode in flight).

    Parameters
    ----------
    start_step, start_episode
        Cursor from which to resume; both ``0`` for a fresh start.
    start_wall_clock_seconds
        Wall-clock seconds already spent in previous (pre-resume) runs;
        added back into the per-checkpoint sidecar so the running
        total reflects cumulative time across restarts.
    run_dir
        If provided (and ``CHECKPOINT_INTERVAL_STEPS`` > 0), the loop
        writes a checkpoint every :data:`CHECKPOINT_INTERVAL_STEPS`
        env steps under ``<run_dir>/checkpoints/``. ``None`` disables
        checkpointing (used by a few tests).
    scheduler_for_checkpoint
        If non-None, the scheduler whose state should be persisted
        alongside the trainer (CURR only). Baselines pass ``None``.
    """
    time_step = start_step
    episode_num = start_episode
    # Skip eval steps that already lie at or before the resume cursor:
    # they were already written out before the prior run was killed (and
    # the truncate helper has clipped any post-checkpoint stragglers).
    next_eval_at = ((time_step // EVAL_FREQUENCY_STEPS) + 1) * EVAL_FREQUENCY_STEPS
    # Same logic for checkpoints: the next save is the first multiple
    # of CHECKPOINT_INTERVAL_STEPS strictly past the resume cursor.
    next_checkpoint_at = (
        ((time_step // CHECKPOINT_INTERVAL_STEPS) + 1) * CHECKPOINT_INTERVAL_STEPS
        if CHECKPOINT_INTERVAL_STEPS > 0
        else None
    )

    # Initial stage-progress row for CURR (only on a fresh start; on
    # resume the stage history is already in ``stage_progress.csv``).
    if log_stage_transitions and time_step == 0:
        csv_writer_stage.writerow([0, sampler.current_stage_id])

    loop_started_at = time.monotonic()

    while time_step < total_steps:
        if sampler.is_finished():
            break

        # Sample a world for this episode and build the env.
        world = sampler.sample_world()
        t_max = sampler.current_t_max
        env = _make_padded_env(world, t_max=t_max, target_obs_shape=target_obs_shape)

        episode, last_info, time_step = _train_one_episode(
            env=env,
            agent=agent,
            trainer=trainer,
            time_step=time_step,
            episode_num=episode_num,
            max_steps=total_steps,
        )
        episode_num += 1

        # Record into the scheduler / no-op for baselines.
        success = _episode_success(last_info, episode)
        sampler.record_episode(success=success, steps=len(episode))
        advanced = sampler.maybe_advance()
        if advanced and log_stage_transitions:
            csv_writer_stage.writerow([time_step, sampler.current_stage_id])

        # Periodic greedy eval. Multiple cadences may pile up if a single
        # episode covered more than 20k steps (impossible in practice but
        # defensive).
        while time_step >= next_eval_at:
            sr, _sr_std, mr = _evaluate(
                eval_pool=eval_pool,
                eval_t_max=eval_t_max,
                eval_agent=eval_agent,
                n_episodes=EVAL_EPISODES,
                eval_rng=eval_rng,
                target_obs_shape=target_obs_shape,
            )
            csv_writer_eval.writerow([next_eval_at, f"{sr:.6f}", f"{mr:.6f}"])
            next_eval_at += EVAL_FREQUENCY_STEPS

        # Periodic checkpoint. We allow multiple cadences in one
        # iteration only defensively; in practice a single episode
        # never spans 100k env steps.
        if (
            run_dir is not None
            and next_checkpoint_at is not None
            and time_step >= next_checkpoint_at
        ):
            elapsed = time.monotonic() - loop_started_at
            wall_clock_total = start_wall_clock_seconds + elapsed
            _save_checkpoint(
                run_dir=run_dir,
                step=next_checkpoint_at,
                episode=episode_num,
                wall_clock_seconds=wall_clock_total,
                trainer=trainer,
                scheduler=scheduler_for_checkpoint,
            )
            # Advance the cursor past whatever interval boundaries were
            # crossed by this episode (defensive in case of >100k-step
            # episodes).
            while time_step >= next_checkpoint_at:
                next_checkpoint_at += CHECKPOINT_INTERVAL_STEPS

    return time_step


# ---------------------------------------------------------------------------
# Orchestration / IO
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

CHECKPOINT_INTERVAL_STEPS = 100_000
"""How often (in env steps) to dump a checkpoint to disk."""

KEEP_LATEST_CHECKPOINTS = 2
"""Bound on disk usage: only keep the N most-recent checkpoints."""

_STEP_DIR_PREFIX = "step_"
_STEP_DIR_DIGITS = 10
"""10-digit zero-padded step in folder name so lexicographic sort = step order."""


def _checkpoints_root(run_dir: Path) -> Path:
    """The ``checkpoints/`` subdirectory of a per-run output directory."""
    return run_dir / "checkpoints"


def _step_dir_name(step: int) -> str:
    """Format a step count as ``step_0000123456`` (10-digit, zero-padded)."""
    return f"{_STEP_DIR_PREFIX}{step:0{_STEP_DIR_DIGITS}d}"


def _parse_step_dir(name: str) -> int | None:
    """Inverse of :func:`_step_dir_name`. Returns None on malformed input.

    Accepts shorter-than-10-digit suffixes too in case an older run
    produced a non-padded folder name.
    """
    if not name.startswith(_STEP_DIR_PREFIX):
        return None
    suffix = name[len(_STEP_DIR_PREFIX):]
    if not suffix.isdigit():
        return None
    return int(suffix)


def find_latest_checkpoint(run_dir: Path) -> Path | None:
    """Return the highest-step ``step_*`` subdir under ``run_dir/checkpoints``.

    Returns ``None`` if the checkpoints root is missing, empty, or
    contains no parseable ``step_*`` directories. The selection is by
    parsed step count (not lexicographic) so it stays correct even if
    a non-padded folder slips in.
    """
    root = _checkpoints_root(run_dir)
    if not root.is_dir():
        return None
    best: tuple[int, Path] | None = None
    for child in root.iterdir():
        if not child.is_dir():
            continue
        step = _parse_step_dir(child.name)
        if step is None:
            continue
        if best is None or step > best[0]:
            best = (step, child)
    return None if best is None else best[1]


def _prune_old_checkpoints(run_dir: Path, keep: int = KEEP_LATEST_CHECKPOINTS) -> None:
    """Delete all but the ``keep`` newest ``step_*`` checkpoints.

    Sort by parsed step (descending), keep the first ``keep`` entries,
    ``shutil.rmtree`` the rest. Silently no-ops if the checkpoints root
    does not exist or contains <= ``keep`` entries.
    """
    root = _checkpoints_root(run_dir)
    if not root.is_dir():
        return
    entries: list[tuple[int, Path]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        step = _parse_step_dir(child.name)
        if step is None:
            continue
        entries.append((step, child))
    entries.sort(key=lambda t: t[0], reverse=True)
    for _step, path in entries[keep:]:
        shutil.rmtree(path, ignore_errors=True)


def _save_checkpoint(
    *,
    run_dir: Path,
    step: int,
    episode: int,
    wall_clock_seconds: float,
    trainer,
    scheduler: StageScheduler | None,
) -> Path:
    """Persist trainer + scheduler + progress sidecar at ``step``.

    Layout (single checkpoint)::

        checkpoints/step_0000100000/
            trainer/         <- trainer.save() output
            scheduler.json   <- scheduler.state_dict() (CURR only)
            progress.json    <- {step, episode, wall_clock_seconds}

    Old checkpoints are pruned so only :data:`KEEP_LATEST_CHECKPOINTS`
    remain. Returns the path to the newly written checkpoint dir.
    """
    ckpt_dir = _checkpoints_root(run_dir) / _step_dir_name(step)
    trainer_dir = ckpt_dir / "trainer"
    trainer_dir.mkdir(parents=True, exist_ok=True)
    trainer.save(trainer_dir)

    if scheduler is not None:
        (ckpt_dir / "scheduler.json").write_text(
            json.dumps(scheduler.state_dict(), indent=2),
            encoding="utf-8",
        )

    progress = {
        "step": int(step),
        "episode": int(episode),
        "wall_clock_seconds": int(wall_clock_seconds),
    }
    (ckpt_dir / "progress.json").write_text(
        json.dumps(progress, indent=2, sort_keys=True), encoding="utf-8"
    )

    _prune_old_checkpoints(run_dir, keep=KEEP_LATEST_CHECKPOINTS)
    return ckpt_dir


def _truncate_csv_to_step(csv_path: Path, max_step: int) -> None:
    """Drop rows whose first column (``step``) is strictly greater than ``max_step``.

    Used on resume to bring CSVs back in sync with the checkpoint:

    * ``level6_eval.csv`` may contain rows past the checkpoint because
      eval cadence (20k steps) is finer than checkpoint cadence (100k
      steps).
    * ``stage_progress.csv`` may have post-checkpoint stage transitions.

    A missing file is a no-op (fresh start). A header-only file is also
    preserved as-is. The first column is parsed as ``int``; any
    unparseable value (e.g. the literal ``"step"`` header) is treated
    as a header and kept.
    """
    if not csv_path.is_file():
        return
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    kept: list[list[str]] = []
    for row in rows:
        if not row:
            kept.append(row)
            continue
        try:
            step_val = int(row[0])
        except ValueError:
            # Header row (or any non-int first col): always keep.
            kept.append(row)
            continue
        if step_val <= max_step:
            kept.append(row)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(kept)


def _load_checkpoint(
    *,
    ckpt_dir: Path,
    trainer,
    scheduler: StageScheduler | None,
) -> tuple[int, int, float]:
    """Restore trainer + scheduler from ``ckpt_dir``; return (step, episode, wall).

    Reads ``trainer/`` via ``trainer.load(...)``, optionally reads
    ``scheduler.json`` via :meth:`StageScheduler.load_state_dict`,
    then reads ``progress.json`` for the resume cursor. Raises if any
    expected file is missing - the caller has already verified the dir
    exists by calling :func:`find_latest_checkpoint`.
    """
    trainer_dir = ckpt_dir / "trainer"
    trainer.load(trainer_dir)

    if scheduler is not None:
        sched_path = ckpt_dir / "scheduler.json"
        if sched_path.is_file():
            sched_state = json.loads(sched_path.read_text(encoding="utf-8"))
            scheduler.load_state_dict(sched_state)

    progress_path = ckpt_dir / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    return (
        int(progress["step"]),
        int(progress["episode"]),
        float(progress.get("wall_clock_seconds", 0)),
    )


# ---------------------------------------------------------------------------


def _per_stage_step_cap(total_steps: int) -> int:
    """Pilot vs. full per-stage cap selection (CURR only).

    The plan says: if ``total_steps == PILOT_RUN_TOTAL_STEPS`` use
    pilot caps, otherwise full caps. We take the cap from stage 1 (all
    stages share the same cap value in :data:`CURRICULUM_STAGES`).
    """
    stage = CURRICULUM_STAGES[0]
    if total_steps == PILOT_RUN_TOTAL_STEPS:
        return stage.per_stage_step_cap_pilot
    return stage.per_stage_step_cap_full


def _make_run_dir(out_dir: Path, condition: str, algo: str, seed: int) -> Path:
    """Resolve and create the per-run output directory."""
    run_dir = out_dir / "runs" / f"{condition}_{algo}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _seed_everything(seed: int) -> None:
    """Seed Python, numpy and torch via marl's helper.

    The scheduler keeps its own :class:`random.Random` instance derived
    from a separate seed so the pool-sampling stream stays independent
    of the trainer/torch streams (see Phase 4 spec).
    """
    marl.seed(seed)


def main(argv: list[str] | None = None) -> int:
    """Argparse + orchestrate one training run. Returns process exit code."""
    args = build_parser().parse_args(argv)
    _seed_everything(args.seed)

    out_dir: Path = args.out_dir
    run_dir = _make_run_dir(out_dir, args.condition, args.algo, args.seed)

    # Eval pool / horizon = always Level 6.
    level6_pool: list[World] = [World.level(6)]
    level6_t_max = CURRICULUM_STAGES[3].t_max

    # Load training pools and build sampler.
    pools = _load_pools_for_condition(args.condition, out_dir)
    # Q-network is sized once on stage 4's max obs shape; per-episode envs
    # are zero-padded up to it (see ``PadObservations3D``).
    target_obs_shape = _target_obs_shape()
    scheduler: StageScheduler | None
    if args.condition == "CURR":
        scheduler = StageScheduler(
            stages=CURRICULUM_STAGES,
            pools=pools,
            rng_seed=args.seed + RNG_SEED,
            per_stage_step_cap=_per_stage_step_cap(args.steps),
            success_threshold=ADVANCEMENT_SUCCESS_THRESHOLD,
            success_window=ADVANCEMENT_WINDOW_EPISODES,
        )
        sampler = _SchedulerSampler(scheduler)
        # Baselines have a single pool; CURR's first stage starts at index 0.
        sample_env = _build_sample_env_config("CURR", pools)
    else:
        scheduler = None
        # Disentangle the pool-sampling RNG from torch/numpy by deriving
        # it from a separate stream (seed + RNG_SEED) just like the
        # scheduler does.
        baseline_rng = random.Random(args.seed + RNG_SEED)
        # Use stage 4's t_max for B1/B2/B3 (level-6-sized levels).
        # Stage 4 t_max == level 6 t_max == 21 in the current design.
        baseline_t_max = CURRICULUM_STAGES[3].t_max
        sampler = _UniformSampler(pool=pools[0], t_max=baseline_t_max, rng=baseline_rng)
        sample_env = _build_sample_env_config(args.condition, pools)

    # Build trainer + agents (ONCE, reused across all episodes/stages).
    trainer = _build_trainer(args.algo, sample_env)
    device = torch.device("cpu")
    trainer = trainer.to(device)
    trainer.randomize()  # one-time, replaces simple_run's call
    train_agent = trainer.make_agent().to(device)

    # The eval agent shares the same Q-network but uses ArgMax. We
    # construct it from the trainer too (so weight updates propagate
    # automatically) and toggle policy via set_testing().
    eval_agent = trainer.make_agent().to(device)

    # Eval RNG is yet another disentangled stream so the periodic
    # 50-episode eval over Level 6 is reproducible without coupling to
    # the training RNG. (Level 6 is a singleton pool but the rng is
    # threaded for forward-compatibility with held-out evals.)
    eval_rng = random.Random(args.seed * 1_000_003 + 17)

    # ---- Resume from checkpoint (if any) -----------------------------------
    eval_csv_path = run_dir / "level6_eval.csv"
    stage_csv_path = run_dir / "stage_progress.csv"
    eval_csv_path.parent.mkdir(parents=True, exist_ok=True)

    scheduler_for_ckpt: StageScheduler | None = scheduler

    latest_ckpt = find_latest_checkpoint(run_dir)
    start_step = 0
    start_episode = 0
    start_wall_clock = 0.0
    resumed = False
    if latest_ckpt is not None:
        try:
            start_step, start_episode, start_wall_clock = _load_checkpoint(
                ckpt_dir=latest_ckpt,
                trainer=trainer,
                scheduler=scheduler_for_ckpt,
            )
            resumed = True
        except Exception as exc:
            # Corrupt / partial checkpoint: fall back to a fresh start
            # rather than crashing - the user can always wipe the dir
            # manually if they prefer.
            print(
                f"warning: failed to load checkpoint {latest_ckpt}: {exc!r}; "
                "starting from scratch.",
                file=sys.stderr,
            )
            resumed = False

    if resumed:
        # Truncate CSVs to the checkpoint cursor so we don't double-write
        # rows that survived past the last successful save.
        _truncate_csv_to_step(eval_csv_path, start_step)
        _truncate_csv_to_step(stage_csv_path, start_step)
        stage_id_msg = (
            scheduler.current_stage_id if scheduler is not None else "n/a"
        )
        print(
            f"Resuming from step {start_step}, episode {start_episode}, "
            f"stage {stage_id_msg}",
            file=sys.stderr,
        )

    # Open CSV writers. Append mode on resume preserves prior rows; on a
    # fresh start we (re)write the header at the top.
    csv_mode = "a" if resumed else "w"
    with eval_csv_path.open(csv_mode, newline="", encoding="utf-8") as eval_f, \
            stage_csv_path.open(csv_mode, newline="", encoding="utf-8") as stage_f:
        eval_writer = csv.writer(eval_f)
        stage_writer = csv.writer(stage_f)
        if not resumed:
            eval_writer.writerow(["step", "success_rate", "mean_return"])
            stage_writer.writerow(["step", "stage_id"])

        steps_consumed = _train_loop(
            sampler=sampler,
            trainer=trainer,
            agent=train_agent,
            eval_agent=eval_agent,
            eval_pool=level6_pool,
            eval_t_max=level6_t_max,
            total_steps=args.steps,
            csv_writer_eval=eval_writer,
            csv_writer_stage=stage_writer,
            eval_rng=eval_rng,
            log_stage_transitions=(args.condition == "CURR"),
            target_obs_shape=target_obs_shape,
            start_step=start_step,
            start_episode=start_episode,
            start_wall_clock_seconds=start_wall_clock,
            run_dir=run_dir,
            scheduler_for_checkpoint=scheduler_for_ckpt,
        )

    # Final eval on Level 6.
    final_sr, final_sr_std, final_return = _evaluate(
        eval_pool=level6_pool,
        eval_t_max=level6_t_max,
        eval_agent=eval_agent,
        n_episodes=FINAL_EVAL_EPISODES,
        eval_rng=eval_rng,
        target_obs_shape=target_obs_shape,
    )

    final_payload: dict = {
        "condition": args.condition,
        "algo": args.algo,
        "seed": args.seed,
        "total_steps_trained": steps_consumed,
        "success_rate_level6": final_sr,
        "success_rate_level6_std": final_sr_std,
        "mean_return_level6": final_return,
        "n_eval_episodes": FINAL_EVAL_EPISODES,
    }

    # B1 only: also evaluate on the held-out generated stage-4 pool.
    if args.condition == "B1":
        try:
            held_out_pool = load_pool(pool_path(out_dir, CURRICULUM_STAGES[3], "eval"))
        except FileNotFoundError:
            held_out_pool = []
        if held_out_pool:
            held_sr, held_sr_std, held_ret = _evaluate(
                eval_pool=held_out_pool,
                eval_t_max=CURRICULUM_STAGES[3].t_max,
                eval_agent=eval_agent,
                n_episodes=FINAL_EVAL_EPISODES,
                eval_rng=eval_rng,
                target_obs_shape=target_obs_shape,
            )
            final_payload["success_rate_held_out_pool"] = held_sr
            final_payload["success_rate_held_out_pool_std"] = held_sr_std
            final_payload["mean_return_held_out_pool"] = held_ret
        else:
            final_payload["success_rate_held_out_pool"] = None
            final_payload["mean_return_held_out_pool"] = None

    (run_dir / "final_results.json").write_text(
        json.dumps(final_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
