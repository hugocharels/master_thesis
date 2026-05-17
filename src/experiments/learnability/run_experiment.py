"""CLI entry point for the learnability experiment.

Trains one (algo, seed) configuration on the generated train pool and
evaluates periodically on both train and test pools.

Run with the marl venv::

    PYTHONPATH=src python -m experiments.learnability.run_experiment \
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

from experiments.curriculum.lle_marl_env import ThesisLLEConfig
from experiments.learnability.configs import (
    ALGORITHMS,
    EVAL_EPISODES,
    EVAL_FREQUENCY_STEPS,
    FINAL_EVAL_EPISODES,
    GRID,
    TOTAL_STEPS,
)
from experiments.learnability.pool_generator import load_pool, pool_dir

DEFAULT_OUT_DIR = Path("results") / "learnability"


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_experiment",
        description="Train one (algo, seed) cell of the learnability experiment.",
    )
    parser.add_argument("--algo", required=True, choices=ALGORITHMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--steps", type=int, default=TOTAL_STEPS)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


# ---------------------------------------------------------------------------
# Trainer construction
# ---------------------------------------------------------------------------


def _epsilon_decay_steps(total_steps: int) -> int:
    """Scale the epsilon-greedy anneal length with the total budget.

    Returns ``max(100_000, int(0.3 * total_steps))`` so short runs
    keep their legacy 100 k anneal and longer runs get a proportional
    exploration phase instead of going greedy after 7 % of training.
    """
    return max(100_000, int(0.30 * total_steps))


def _build_trainer(algo: str, sample_env: ThesisLLEConfig, total_steps: int):
    if algo == "QMIX":
        qnet = qnetworks.from_env(sample_env)
        return algos.QMix(
            qnet,
            mixer=mixers.QMix.from_env(sample_env),
            train_policy=EpsilonGreedy.linear(1.0, 0.05, _epsilon_decay_steps(total_steps)),
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
            train_policy=EpsilonGreedy.linear(1.0, 0.05, _epsilon_decay_steps(total_steps)),
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
            train_policy=EpsilonGreedy.linear(1.0, 0.05, _epsilon_decay_steps(total_steps)),
            test_policy=ArgMax(),
            lr=5e-4,
            batch_size=64,
            gamma=0.95,
            train_interval=(5, "step"),
            grad_norm_clipping=10,
        )
    raise ValueError(f"Unknown algo: {algo!r}")


# ---------------------------------------------------------------------------
# Episode primitives
# ---------------------------------------------------------------------------


def _episode_success(info: dict, episode: Episode) -> bool:
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


def _greedy_eval_episode(env, eval_agent):
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


def _evaluate(pool: list[World], t_max: int, eval_agent, n_episodes: int, rng: random.Random):
    """Run greedy eval over pool. Returns (success_rate, std, mean_return)."""
    eval_agent.set_testing()
    successes: list[int] = []
    returns: list[float] = []
    try:
        for _ in range(n_episodes):
            world = rng.choice(pool)
            cfg = ThesisLLEConfig.from_world(world, t_max=t_max)
            success, ret = _greedy_eval_episode(cfg.env, eval_agent)
            successes.append(int(success))
            returns.append(ret)
    finally:
        eval_agent.set_training()
    s = np.asarray(successes, dtype=np.float64)
    r = np.asarray(returns, dtype=np.float64)
    return float(s.mean()), float(s.std()), float(r.mean())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = build_parser().parse_args()
    algo: str = args.algo
    seed: int = args.seed
    total_steps: int = args.steps
    config = GRID
    out_dir: Path = args.out_dir or DEFAULT_OUT_DIR

    # Seed everything
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # Load pools
    train_pool = load_pool(pool_dir(out_dir, config, "train"))
    test_pool = load_pool(pool_dir(out_dir, config, "test"))
    print(f"Loaded {len(train_pool)} train + {len(test_pool)} test levels", file=sys.stderr)

    # Build trainer
    sample_env = ThesisLLEConfig.from_world(train_pool[0], t_max=config.t_max)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)
    trainer = _build_trainer(algo, sample_env, total_steps)
    trainer = trainer.to(device)
    trainer.randomize()
    agent = trainer.make_agent().to(device)
    eval_agent = trainer.make_agent().to(device)

    # RNGs
    train_rng = random.Random(seed)
    eval_rng = random.Random(seed + 1000)

    # Output directory
    run_dir = out_dir / "runs" / f"{algo}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Open CSV files
    train_csv_path = run_dir / "train_eval.csv"
    test_csv_path = run_dir / "test_eval.csv"
    train_csv_f = open(train_csv_path, "w", newline="", encoding="utf-8")
    test_csv_f = open(test_csv_path, "w", newline="", encoding="utf-8")
    train_csv = csv.writer(train_csv_f)
    test_csv = csv.writer(test_csv_f)
    train_csv.writerow(["step", "success_rate", "mean_return"])
    test_csv.writerow(["step", "success_rate", "mean_return"])

    # Training loop
    time_step = 0
    episode_num = 0
    next_eval_at = EVAL_FREQUENCY_STEPS

    try:
        while time_step < total_steps:
            world = train_rng.choice(train_pool)
            env_cfg = ThesisLLEConfig.from_world(world, t_max=config.t_max)

            episode, last_info, time_step = _train_one_episode(
                env=env_cfg.env,
                agent=agent,
                trainer=trainer,
                time_step=time_step,
                episode_num=episode_num,
                max_steps=total_steps,
            )
            episode_num += 1

            # Periodic eval on both pools
            while time_step >= next_eval_at:
                sr_train, _, mr_train = _evaluate(
                    train_pool, config.t_max, eval_agent, EVAL_EPISODES, eval_rng,
                )
                sr_test, _, mr_test = _evaluate(
                    test_pool, config.t_max, eval_agent, EVAL_EPISODES, eval_rng,
                )
                train_csv.writerow([next_eval_at, f"{sr_train:.6f}", f"{mr_train:.6f}"])
                test_csv.writerow([next_eval_at, f"{sr_test:.6f}", f"{mr_test:.6f}"])
                print(
                    f"step={next_eval_at:>7d}  "
                    f"train_sr={sr_train:.3f}  test_sr={sr_test:.3f}",
                    file=sys.stderr,
                )
                next_eval_at += EVAL_FREQUENCY_STEPS
    finally:
        train_csv_f.close()
        test_csv_f.close()

    # Final eval
    sr_train, sr_train_std, mr_train = _evaluate(
        train_pool, config.t_max, eval_agent, FINAL_EVAL_EPISODES, eval_rng,
    )
    sr_test, sr_test_std, mr_test = _evaluate(
        test_pool, config.t_max, eval_agent, FINAL_EVAL_EPISODES, eval_rng,
    )

    results = {
        "algo": algo,
        "seed": seed,
        "total_steps_trained": time_step,
        "success_rate_train": sr_train,
        "success_rate_train_std": sr_train_std,
        "mean_return_train": mr_train,
        "success_rate_test": sr_test,
        "success_rate_test_std": sr_test_std,
        "mean_return_test": mr_test,
    }
    results_path = run_dir / "final_results.json"
    results_path.write_text(
        json.dumps(results, indent=2), encoding="utf-8",
    )
    print(f"\nDone: {results_path}", file=sys.stderr)
    print(f"  train_sr={sr_train:.3f} test_sr={sr_test:.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
