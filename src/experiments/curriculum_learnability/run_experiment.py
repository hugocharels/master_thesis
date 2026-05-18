"""Curriculum-learnability runner: 3-stage curriculum ending at
8x8/3a/2L, evaluated on the same test pool as the learnability
experiment.

Output layout (mirrors learnability for easy plot reuse)::

    {out_dir}/runs/{algo}_seed{N}/
        train_eval.csv       step,success_rate,mean_return  (on train pool)
        test_eval.csv        step,success_rate,mean_return  (on test pool)
        stage_progress.csv   step,stage_id
        final_results.json   end-of-run summary

Usage (inside the docker container):

    GPU_DEVICES=2 bash docker/run.sh -- python -m \
        experiments.curriculum_learnability.run_experiment \
        --algo QMIX --seed 0
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from lle import World
from marlenv import Episode, Transition

from marl import algos
from marl.nn import mixers
from marl.nn.model_bank import qnetworks
from marl.policy import ArgMax, EpsilonGreedy

from experiments.curriculum.curriculum_scheduler import StageScheduler
from experiments.curriculum.lle_marl_env import PadObservations3D, ThesisLLEConfig
from experiments.curriculum.pool_generator import load_pool as load_pool_json
from experiments.curriculum.pool_generator import pool_path as curr_pool_path
from experiments.curriculum_learnability.configs import (
    ADVANCEMENT_SUCCESS_THRESHOLD,
    ADVANCEMENT_WINDOW_EPISODES,
    ALGORITHMS,
    EVAL_EPISODES,
    EVAL_FREQUENCY_STEPS,
    FINAL_EVAL_EPISODES,
    FULL_RUN_TOTAL_STEPS,
    LEARNABILITY_TARGET_STAGES,
    PILOT_RUN_TOTAL_STEPS,
    RNG_SEED,
)
from experiments.learnability.configs import GRID as LEARN_GRID
from experiments.learnability.pool_generator import (
    load_pool as load_pool_txt,
    pool_dir as learn_pool_dir,
)

DEFAULT_OUT_DIR = Path("results") / "curriculum_learnability"
LEARNABILITY_BASE = Path("results") / "learnability"


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_experiment",
        description=(
            "Train one (algo, seed) cell of the curriculum-learnability "
            "experiment (3-stage curriculum ending at 8x8/3a/2L)."
        ),
    )
    parser.add_argument("--algo", required=True, choices=ALGORITHMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--steps", type=int, default=FULL_RUN_TOTAL_STEPS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser


# ---------------------------------------------------------------------------
# Pool loading
# ---------------------------------------------------------------------------


def _load_stage_pools(out_dir: Path) -> list[list[World]]:
    """Return one training pool per stage (in order).

    - Stages 1 and 2 are loaded from ``out_dir/levels/`` (json, written
      by curriculum_learnability._preflight).
    - Stage 3 reuses the learnability train pool (txt files) so this
      experiment shares the same target task as the direct-training
      learnability experiment.
    """
    pools: list[list[World]] = []
    for stage in LEARNABILITY_TARGET_STAGES[:2]:
        pools.append(load_pool_json(curr_pool_path(out_dir, stage, "train")))
    learn_train_dir = learn_pool_dir(LEARNABILITY_BASE, LEARN_GRID, "train")
    pools.append(load_pool_txt(learn_train_dir))
    return pools


def _load_test_pool() -> list[World]:
    """Held-out test pool == learnability's test pool (apples-to-apples)."""
    learn_test_dir = learn_pool_dir(LEARNABILITY_BASE, LEARN_GRID, "test")
    return load_pool_txt(learn_test_dir)


# ---------------------------------------------------------------------------
# Trainer construction
# ---------------------------------------------------------------------------


def _epsilon_decay_steps(total_steps: int) -> int:
    return max(100_000, int(0.30 * total_steps))


def _build_trainer(algo: str, sample_env: ThesisLLEConfig, total_steps: int):
    eps_decay = _epsilon_decay_steps(total_steps)
    common = dict(
        train_policy=EpsilonGreedy.linear(1.0, 0.05, eps_decay),
        test_policy=ArgMax(),
        lr=5e-4,
        batch_size=64,
        gamma=0.95,
        train_interval=(5, "step"),
        grad_norm_clipping=10,
    )
    if algo == "QMIX":
        qnet = qnetworks.from_env(sample_env)
        return algos.QMix(qnet, mixer=mixers.QMix.from_env(sample_env), **common)
    if algo == "VDN":
        qnet = qnetworks.from_env(sample_env, independent=True)
        return algos.VDN(qnet, **common)
    if algo == "IQL":
        qnet = qnetworks.from_env(sample_env, independent=True)
        return algos.DQN(qnet, mixer=None, **common)
    raise ValueError(f"Unknown algo: {algo!r}")


def _target_shapes(sample_target_world: World) -> tuple[tuple[int, int, int], tuple[int, ...]]:
    """Observation / state shapes of the stage-3 (target) environment.

    All earlier stages are padded up to these so the Q-network sees a
    fixed input size across the curriculum.
    """
    target_stage = LEARNABILITY_TARGET_STAGES[-1]
    cfg = ThesisLLEConfig.from_world(sample_target_world, t_max=target_stage.t_max)
    obs_shape = cfg.env.observation_shape
    state_shape = cfg.env.state_shape
    return (
        (int(obs_shape[0]), int(obs_shape[1]), int(obs_shape[2])),
        (int(state_shape[0]),),
    )


def _make_padded_env(
    world: World,
    t_max: int,
    target_obs_shape: tuple[int, int, int],
    target_state_shape: tuple[int, ...],
):
    cfg = ThesisLLEConfig.from_world(world, t_max=t_max)
    return PadObservations3D(cfg.env, target_obs_shape, target_state_shape)


# ---------------------------------------------------------------------------
# Episode primitives
# ---------------------------------------------------------------------------


def _is_solved(info: dict, episode: Episode) -> bool:
    return bool(episode.is_done) and float(info.get("exit_rate", 0.0)) >= 1.0 - 1e-9


def _train_one_episode(env, agent, trainer, time_step: int, episode_num: int, max_steps: int):
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


def _greedy_one_episode(env, test_agent) -> tuple[bool, float]:
    obs, state = env.reset()
    test_agent.new_episode()
    episode = Episode.new(obs, state)
    last_info: dict = {}
    while not episode.is_finished:
        action = test_agent.choose_action(obs)
        step = env.step(action.action)
        transition = Transition.from_step(obs, state, action.action, step, **action.details)
        episode.add(transition)
        obs = step.obs
        state = step.state
        last_info = step.info
    return _is_solved(last_info, episode), float(np.sum(np.array(episode.rewards)))


def _assess_on_pool(
    pool: list[World],
    t_max: int,
    test_agent,
    n_episodes: int,
    rng: random.Random,
    target_obs_shape: tuple[int, int, int],
    target_state_shape: tuple[int, ...],
) -> tuple[float, float]:
    test_agent.set_testing()
    successes: list[int] = []
    returns: list[float] = []
    try:
        for _ in range(n_episodes):
            world = rng.choice(pool)
            env = _make_padded_env(world, t_max, target_obs_shape, target_state_shape)
            ok, ret = _greedy_one_episode(env, test_agent)
            successes.append(int(ok))
            returns.append(ret)
    finally:
        test_agent.set_training()
    return float(np.mean(successes)), float(np.mean(returns))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = build_parser().parse_args()
    algo: str = args.algo
    seed: int = args.seed
    total_steps: int = args.steps
    out_dir: Path = args.out_dir

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # Load pools
    stage_pools = _load_stage_pools(out_dir)
    test_pool = _load_test_pool()
    train_pool_for_eval = stage_pools[-1]  # stage 3 train pool (== learnability train)
    print(
        f"Loaded {[len(p) for p in stage_pools]} stage pools + "
        f"{len(test_pool)} test levels",
        file=sys.stderr,
    )

    # Pick per-stage step caps. PILOT_RUN_TOTAL_STEPS triggers the
    # pilot caps; anything else uses the full caps.
    use_pilot_caps = (total_steps == PILOT_RUN_TOTAL_STEPS)
    per_stage_caps = [
        s.per_stage_step_cap_pilot if use_pilot_caps else s.per_stage_step_cap_full
        for s in LEARNABILITY_TARGET_STAGES
    ]

    # Trainer sized for the stage-3 (target) env. Earlier stages are
    # padded up to this shape.
    target_stage = LEARNABILITY_TARGET_STAGES[-1]
    sample_world = stage_pools[-1][0]
    target_obs_shape, target_state_shape = _target_shapes(sample_world)
    sample_env = ThesisLLEConfig.from_world(sample_world, t_max=target_stage.t_max)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)
    trainer = _build_trainer(algo, sample_env, total_steps).to(device)
    trainer.randomize()
    agent = trainer.make_agent().to(device)
    test_agent = trainer.make_agent().to(device)

    # Curriculum scheduler
    scheduler = StageScheduler(
        stages=LEARNABILITY_TARGET_STAGES,
        pools=stage_pools,
        rng_seed=seed,
        per_stage_step_cap=per_stage_caps,
        success_threshold=ADVANCEMENT_SUCCESS_THRESHOLD,
        success_window=ADVANCEMENT_WINDOW_EPISODES,
    )

    eval_rng = random.Random(seed + 1000)

    # Output directory
    run_dir = out_dir / "runs" / f"{algo}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_csv_f = open(run_dir / "train_eval.csv", "w", newline="", encoding="utf-8")
    test_csv_f = open(run_dir / "test_eval.csv", "w", newline="", encoding="utf-8")
    stage_csv_f = open(run_dir / "stage_progress.csv", "w", newline="", encoding="utf-8")
    train_csv = csv.writer(train_csv_f)
    test_csv = csv.writer(test_csv_f)
    stage_csv = csv.writer(stage_csv_f)
    train_csv.writerow(["step", "success_rate", "mean_return"])
    test_csv.writerow(["step", "success_rate", "mean_return"])
    stage_csv.writerow(["step", "stage_id"])

    # Log starting stage
    stage_csv.writerow([0, scheduler.current_stage_id])

    time_step = 0
    episode_num = 0
    next_eval_at = EVAL_FREQUENCY_STEPS

    try:
        while time_step < total_steps and not scheduler.is_finished():
            current_stage = scheduler.current_stage
            world = scheduler.sample_world()
            env = _make_padded_env(
                world,
                t_max=current_stage.t_max,
                target_obs_shape=target_obs_shape,
                target_state_shape=target_state_shape,
            )
            episode, last_info, time_step = _train_one_episode(
                env=env,
                agent=agent,
                trainer=trainer,
                time_step=time_step,
                episode_num=episode_num,
                max_steps=total_steps,
            )
            episode_num += 1

            scheduler.record_episode(
                success=_is_solved(last_info, episode),
                steps=len(episode.rewards),
            )
            prev_stage = scheduler.current_stage_id
            scheduler.maybe_advance()
            if scheduler.current_stage_id != prev_stage:
                stage_csv.writerow([time_step, scheduler.current_stage_id])

            # Periodic eval on the target task (stage-3 train + test pools)
            while time_step >= next_eval_at:
                sr_train, mr_train = _assess_on_pool(
                    train_pool_for_eval, target_stage.t_max, test_agent,
                    EVAL_EPISODES, eval_rng,
                    target_obs_shape, target_state_shape,
                )
                sr_test, mr_test = _assess_on_pool(
                    test_pool, target_stage.t_max, test_agent,
                    EVAL_EPISODES, eval_rng,
                    target_obs_shape, target_state_shape,
                )
                train_csv.writerow([next_eval_at, f"{sr_train:.6f}", f"{mr_train:.6f}"])
                test_csv.writerow([next_eval_at, f"{sr_test:.6f}", f"{mr_test:.6f}"])
                print(
                    f"step={next_eval_at:>7d}  stage={scheduler.current_stage_id}  "
                    f"train_sr={sr_train:.3f}  test_sr={sr_test:.3f}",
                    file=sys.stderr,
                )
                next_eval_at += EVAL_FREQUENCY_STEPS
    finally:
        train_csv_f.close()
        test_csv_f.close()
        stage_csv_f.close()

    # Final eval
    sr_train, mr_train = _assess_on_pool(
        train_pool_for_eval, target_stage.t_max, test_agent,
        FINAL_EVAL_EPISODES, eval_rng,
        target_obs_shape, target_state_shape,
    )
    sr_test, mr_test = _assess_on_pool(
        test_pool, target_stage.t_max, test_agent,
        FINAL_EVAL_EPISODES, eval_rng,
        target_obs_shape, target_state_shape,
    )

    results = {
        "algo": algo,
        "seed": seed,
        "total_steps_trained": time_step,
        "final_stage_id": scheduler.current_stage_id,
        "scheduler_finished": scheduler.is_finished(),
        "success_rate_train": sr_train,
        "mean_return_train": mr_train,
        "success_rate_test": sr_test,
        "mean_return_test": mr_test,
    }
    (run_dir / "final_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8",
    )
    print(
        f"\nDone: {run_dir / 'final_results.json'}\n"
        f"  train_sr={sr_train:.3f} test_sr={sr_test:.3f} "
        f"final_stage={scheduler.current_stage_id}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
