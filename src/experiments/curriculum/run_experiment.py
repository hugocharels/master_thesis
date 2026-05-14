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
import sys
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
from experiments.curriculum.lle_marl_env import ThesisLLEConfig
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
    """Build a single ``ThesisLLEConfig`` used to size the Q-network.

    The trainer / mixer / replay buffer must be built *once*; for that
    we need an env to feed ``qnetworks.from_env`` and
    ``mixers.QMix.from_env``. We pick a representative world (the first
    of the first pool) and the corresponding ``t_max`` (the level-6
    horizon for B3, the stage-1 horizon for CURR, the stage-4 horizon
    for B1, and 21 for B2 since its union spans heterogeneous t_max
    values - the per-episode env is rebuilt anyway with the correct
    t_max).
    """
    if condition == "B3":
        # Level 6 has the same geometry as stage 4.
        t_max = CURRICULUM_STAGES[3].t_max
        return ThesisLLEConfig.from_world(pools[0][0], t_max=t_max)
    if condition == "B1":
        t_max = CURRICULUM_STAGES[3].t_max
        return ThesisLLEConfig.from_world(pools[0][0], t_max=t_max)
    if condition == "B2":
        # Largest stage's t_max keeps the time-limit wrapper safe for any
        # sample env we build at runtime; the per-episode env will use the
        # actual stage's t_max. Q-network shapes only care about
        # observation_shape / n_actions, not t_max, so this is harmless.
        t_max = CURRICULUM_STAGES[3].t_max
        return ThesisLLEConfig.from_world(pools[0][0], t_max=t_max)
    if condition == "CURR":
        t_max = CURRICULUM_STAGES[0].t_max
        return ThesisLLEConfig.from_world(pools[0][0], t_max=t_max)
    raise ValueError(f"Unknown condition: {condition!r}")


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


def _evaluate(eval_pool: list[World], eval_t_max: int, eval_agent, n_episodes: int, eval_rng: random.Random) -> tuple[float, float, float]:
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
            cfg = ThesisLLEConfig.from_world(world, t_max=eval_t_max)
            env = cfg.env
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
) -> int:
    """Drive the shared trainer through ``total_steps`` env steps.

    Returns the actual number of env steps consumed (which may slightly
    exceed ``total_steps`` because we never cut an episode in flight).
    """
    time_step = 0
    episode_num = 0
    next_eval_at = EVAL_FREQUENCY_STEPS  # do the first eval at 20k, not at 0

    # Initial stage-progress row for CURR.
    if log_stage_transitions:
        csv_writer_stage.writerow([0, sampler.current_stage_id])

    while time_step < total_steps:
        if sampler.is_finished():
            break

        # Sample a world for this episode and build the env.
        world = sampler.sample_world()
        t_max = sampler.current_t_max
        env_cfg = ThesisLLEConfig.from_world(world, t_max=t_max)
        env = env_cfg.env

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
            )
            csv_writer_eval.writerow([next_eval_at, f"{sr:.6f}", f"{mr:.6f}"])
            next_eval_at += EVAL_FREQUENCY_STEPS

    return time_step


# ---------------------------------------------------------------------------
# Orchestration / IO
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

    # Open CSV writers in append-friendly mode and drive the loop.
    eval_csv_path = run_dir / "level6_eval.csv"
    stage_csv_path = run_dir / "stage_progress.csv"
    eval_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with eval_csv_path.open("w", newline="", encoding="utf-8") as eval_f, \
            stage_csv_path.open("w", newline="", encoding="utf-8") as stage_f:
        eval_writer = csv.writer(eval_f)
        eval_writer.writerow(["step", "success_rate", "mean_return"])
        stage_writer = csv.writer(stage_f)
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
        )

    # Final eval on Level 6.
    final_sr, final_sr_std, final_return = _evaluate(
        eval_pool=level6_pool,
        eval_t_max=level6_t_max,
        eval_agent=eval_agent,
        n_episodes=FINAL_EVAL_EPISODES,
        eval_rng=eval_rng,
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
