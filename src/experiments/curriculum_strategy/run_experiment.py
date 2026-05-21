"""Curriculum-strategy runner: train one (condition, algo, seed) cell.

All conditions consume exactly ``--steps`` environment steps; only the
allocation across the difficulty ladder differs (see
experiments.curriculum_strategy.configs / .schedulers). Every condition
is evaluated on the same held-out 7x7 target pool.

Output (mirrors learnability for plot reuse)::

    {out_dir}/runs/{condition}_{algo}_seed{N}/
        train_eval.csv        step,success_rate,mean_return  (target train pool)
        test_eval.csv         step,success_rate,mean_return  (target eval pool)
        schedule_progress.csv step,stage_id
        final_results.json    end-of-run summary

Usage (inside the docker container):

    GPU_DEVICES=2 bash docker/run.sh -- python -m \
        experiments.curriculum_strategy.run_experiment \
        --condition forward --algo VDN --seed 0
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

from experiments.curriculum.lle_marl_env import PadObservations3D, ThesisLLEConfig
from experiments.curriculum.pool_generator import load_pool, pool_path
from experiments.curriculum_strategy.configs import (
    ALGORITHMS,
    CONDITIONS,
    EVAL_EPISODES,
    EVAL_FREQUENCY_STEPS,
    FINAL_EVAL_EPISODES,
    FORWARD_STAGE_STEPS,
    RUNGS,
    TARGET_RUNG,
    TOTAL_STEPS,
)
from experiments.curriculum_strategy.schedulers import make_strategy

DEFAULT_OUT_DIR = Path("results") / "curriculum_strategy"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_experiment",
        description="Train one (condition, algo, seed) curriculum-strategy cell.",
    )
    parser.add_argument("--condition", required=True, choices=CONDITIONS)
    parser.add_argument("--algo", required=True, choices=ALGORITHMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--steps", type=int, default=TOTAL_STEPS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser


def _load_train_pools(out_dir: Path) -> dict[int, list[World]]:
    return {r.stage_id: load_pool(pool_path(out_dir, r, "train")) for r in RUNGS}


def _load_target_eval_pool(out_dir: Path) -> list[World]:
    return load_pool(pool_path(out_dir, TARGET_RUNG, "eval"))


def _epsilon_decay_steps(total_steps: int) -> int:
    return max(100_000, int(0.30 * total_steps))


EPS_DECAY_FRACTION: float = 0.30


def _set_stage_epsilon(
    trainer, global_start: int, stage_budget: int,
    start: float = 1.0, end: float = 0.05,
) -> int:
    """Reconfigure the epsilon schedule for a fresh explore->exploit cycle on
    the current stage; returns the decay length used.

    marl's ``LinearSchedule`` is a pure function of the global step the algo
    feeds it (``algos/dqn.py``: ``self.policy.update(time_step)``), so a single
    ramp would span the whole run -- early curriculum rungs would only explore
    and the final (hardest) rung would never explore. We re-express the ramp in
    global-step coordinates at each stage boundary: epsilon falls ``start`` ->
    ``end`` over ``EPS_DECAY_FRACTION`` of this stage's budget, then holds.
    """
    decay = max(1, int(EPS_DECAY_FRACTION * stage_budget))
    sched = trainer.train_policy.epsilon
    sched.start_value = start
    sched.end_value = end
    sched.n_steps = global_start + decay  # clamp to ``end`` once the ramp ends
    sched.a = (end - start) / decay
    sched.b = start - sched.a * global_start
    sched._t = global_start
    sched._current_value = start
    return decay


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


def _target_shapes(sample_target_world: World):
    cfg = ThesisLLEConfig.from_world(sample_target_world, t_max=TARGET_RUNG.t_max)
    obs_shape = cfg.env.observation_shape
    state_shape = cfg.env.state_shape
    return (
        (int(obs_shape[0]), int(obs_shape[1]), int(obs_shape[2])),
        (int(state_shape[0]),),
    )


def _make_padded_env(world, t_max, target_obs_shape, target_state_shape):
    cfg = ThesisLLEConfig.from_world(world, t_max=t_max)
    return PadObservations3D(cfg.env, target_obs_shape, target_state_shape)


def _is_solved(info: dict, episode: Episode) -> bool:
    return bool(episode.is_done) and float(info.get("exit_rate", 0.0)) >= 1.0 - 1e-9


def _train_one_episode(env, agent, trainer, time_step, episode_num, max_steps):
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


def _greedy_one_episode(env, test_agent):
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


def _assess_on_pool(pool, t_max, test_agent, n_episodes, rng, target_obs_shape, target_state_shape):
    test_agent.set_testing()
    successes, returns = [], []
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


def main() -> None:
    args = build_parser().parse_args()
    condition, algo, seed = args.condition, args.algo, args.seed
    total_steps, out_dir = args.steps, args.out_dir

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    train_pools = _load_train_pools(out_dir)
    target_eval_pool = _load_target_eval_pool(out_dir)
    target_train_pool = train_pools[TARGET_RUNG.stage_id]
    print(
        f"Loaded train pools {[len(train_pools[r.stage_id]) for r in RUNGS]} + "
        f"{len(target_eval_pool)} target eval levels",
        file=sys.stderr,
    )

    sample_world = target_train_pool[0]
    target_obs_shape, target_state_shape = _target_shapes(sample_world)
    sample_env = ThesisLLEConfig.from_world(sample_world, t_max=TARGET_RUNG.t_max)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)
    trainer = _build_trainer(algo, sample_env, total_steps).to(device)
    trainer.randomize()
    agent = trainer.make_agent().to(device)
    test_agent = trainer.make_agent().to(device)

    strategy = make_strategy(
        condition, RUNGS, train_pools, total_steps, rng_seed=seed,
        stage_budgets=list(FORWARD_STAGE_STEPS),
    )
    eval_rng = random.Random(seed + 1000)

    run_dir = out_dir / "runs" / f"{condition}_{algo}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_csv_f = open(run_dir / "train_eval.csv", "w", newline="", encoding="utf-8")
    test_csv_f = open(run_dir / "test_eval.csv", "w", newline="", encoding="utf-8")
    stage_csv_f = open(run_dir / "schedule_progress.csv", "w", newline="", encoding="utf-8")
    stage_eval_csv_f = open(run_dir / "stage_eval.csv", "w", newline="", encoding="utf-8")
    train_csv = csv.writer(train_csv_f)
    test_csv = csv.writer(test_csv_f)
    stage_csv = csv.writer(stage_csv_f)
    stage_eval_csv = csv.writer(stage_eval_csv_f)
    train_csv.writerow(["step", "success_rate", "mean_return"])
    test_csv.writerow(["step", "success_rate", "mean_return"])
    stage_csv.writerow(["step", "stage_id"])
    stage_csv.writerow([0, strategy.current_rung.stage_id])
    # success on the rung currently being trained (vs. the always-on-target
    # train_eval/test_eval), so a per-stage stall is visible during the run.
    stage_eval_csv.writerow(["step", "stage_id", "success_rate", "mean_return"])
    # Flush after every write below so the CSVs are readable live (for
    # monitoring) and survive a killed run -- the default block buffering
    # otherwise holds all ~30 small rows until the file is closed at the end.
    train_csv_f.flush()
    test_csv_f.flush()
    stage_csv_f.flush()
    stage_eval_csv_f.flush()

    time_step = 0
    episode_num = 0
    next_eval_at = EVAL_FREQUENCY_STEPS
    prev_stage = strategy.current_rung.stage_id
    _set_stage_epsilon(trainer, 0, strategy.current_budget)

    try:
        while time_step < total_steps and not strategy.is_finished():
            world, rung = strategy.next_world()
            env = _make_padded_env(world, rung.t_max, target_obs_shape, target_state_shape)
            episode, last_info, time_step = _train_one_episode(
                env=env, agent=agent, trainer=trainer,
                time_step=time_step, episode_num=episode_num, max_steps=total_steps,
            )
            episode_num += 1
            strategy.record_steps(len(episode.rewards))

            cur_stage = strategy.current_rung.stage_id
            if cur_stage != prev_stage:
                stage_csv.writerow([time_step, cur_stage])
                stage_csv_f.flush()
                prev_stage = cur_stage
                # fresh explore->exploit cycle for the rung we just entered
                _set_stage_epsilon(trainer, time_step, strategy.current_budget)

            while time_step >= next_eval_at:
                cur_rung = strategy.current_rung
                sr_stage, mr_stage = _assess_on_pool(
                    train_pools[cur_rung.stage_id], cur_rung.t_max, test_agent,
                    EVAL_EPISODES, eval_rng, target_obs_shape, target_state_shape,
                )
                sr_train, mr_train = _assess_on_pool(
                    target_train_pool, TARGET_RUNG.t_max, test_agent,
                    EVAL_EPISODES, eval_rng, target_obs_shape, target_state_shape,
                )
                sr_test, mr_test = _assess_on_pool(
                    target_eval_pool, TARGET_RUNG.t_max, test_agent,
                    EVAL_EPISODES, eval_rng, target_obs_shape, target_state_shape,
                )
                train_csv.writerow([next_eval_at, f"{sr_train:.6f}", f"{mr_train:.6f}"])
                test_csv.writerow([next_eval_at, f"{sr_test:.6f}", f"{mr_test:.6f}"])
                stage_eval_csv.writerow(
                    [next_eval_at, cur_rung.stage_id, f"{sr_stage:.6f}", f"{mr_stage:.6f}"]
                )
                train_csv_f.flush()
                test_csv_f.flush()
                stage_eval_csv_f.flush()
                print(
                    f"step={next_eval_at:>7d} cond={condition} stage={cur_stage} "
                    f"eps={float(trainer.train_policy.epsilon.value):.2f} "
                    f"stage_sr={sr_stage:.3f} tgt_train_sr={sr_train:.3f} tgt_test_sr={sr_test:.3f} "
                    f"stage_ret={mr_stage:.2f} tgt_test_ret={mr_test:.2f}",
                    file=sys.stderr,
                )
                next_eval_at += EVAL_FREQUENCY_STEPS
    finally:
        train_csv_f.close()
        test_csv_f.close()
        stage_csv_f.close()
        stage_eval_csv_f.close()

    sr_train, mr_train = _assess_on_pool(
        target_train_pool, TARGET_RUNG.t_max, test_agent,
        FINAL_EVAL_EPISODES, eval_rng, target_obs_shape, target_state_shape,
    )
    sr_test, mr_test = _assess_on_pool(
        target_eval_pool, TARGET_RUNG.t_max, test_agent,
        FINAL_EVAL_EPISODES, eval_rng, target_obs_shape, target_state_shape,
    )
    results = {
        "condition": condition,
        "algo": algo,
        "seed": seed,
        "total_steps_trained": time_step,
        "success_rate_train": sr_train,
        "mean_return_train": mr_train,
        "success_rate_test": sr_test,
        "mean_return_test": mr_test,
    }
    (run_dir / "final_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(
        f"\nDone: {run_dir / 'final_results.json'}\n"
        f"  cond={condition} train_sr={sr_train:.3f} test_sr={sr_test:.3f}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
