"""Diagnostic: train a MARL algorithm on a SINGLE fixed level.

If MARL fails to solve a single fixed level even when 100% of the
training budget is spent on it, the issue is algorithmic (model
capacity, exploration, reward sparsity) -- not pool diversity.

If MARL solves a single level reliably but failed on the 20-level
pool in the learnability experiment, the bottleneck is the diversity
of the pool relative to the 200k-step budget (each level effectively
sees ~10k steps).

Usage (from project root, inside the docker container):
    GPU_DEVICES=2 bash docker/run.sh -- python scripts/diagnose_single_level.py

Options:
    --level-file PATH    Path to a .txt world string. Defaults to the
                         first train level of the learnability pool.
    --algo {IQL,VDN,QMIX}  Default QMIX.
    --steps N            Training step budget. Default 50_000.
    --assess-every N     Greedy assessment every N steps. Default 5_000.
    --assess-episodes N  Episodes per assessment (all on the same
                         level). Default 50.
    --print-trajectory   After training, run one greedy episode and
                         print every step (agent positions + actions +
                         reward).
"""

from __future__ import annotations

import argparse
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
from experiments.learnability.configs import GRID


def _build_trainer(algo: str, sample_env: ThesisLLEConfig, total_steps: int):
    eps_decay = max(10_000, int(0.30 * total_steps))
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


def _greedy_assess(env_factory, test_agent, n_episodes: int) -> tuple[float, float]:
    test_agent.set_testing()
    successes: list[int] = []
    returns: list[float] = []
    try:
        for _ in range(n_episodes):
            env = env_factory().env
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
            successes.append(int(_is_solved(last_info, episode)))
            returns.append(float(np.sum(np.array(episode.rewards))))
    finally:
        test_agent.set_training()
    return float(np.mean(successes)), float(np.mean(returns))


def _print_trajectory(env_factory, test_agent) -> None:
    test_agent.set_testing()
    env = env_factory().env
    obs, state = env.reset()
    test_agent.new_episode()
    print("\n--- Greedy trajectory ---")
    step_num = 0
    total_reward = 0.0
    last_info = {}
    while True:
        action = test_agent.choose_action(obs)
        step = env.step(action.action)
        total_reward += float(np.sum(step.reward))
        last_info = step.info
        info_short = {k: v for k, v in step.info.items() if k != "state"}
        print(
            f"  step {step_num:2d}  action={action.action}  "
            f"reward={float(np.sum(step.reward)):+.3f}  "
            f"cum={total_reward:+.3f}  "
            f"done={step.done}  truncated={step.truncated}  "
            f"info={info_short}"
        )
        step_num += 1
        if step.done or step.truncated:
            break
        obs = step.obs
        state = step.state
    success = bool(last_info.get("exit_rate", 0.0) >= 1.0 - 1e-9)
    print(f"--- End ({step_num} steps, success={success}, return={total_reward:+.3f}) ---")
    test_agent.set_training()


def main() -> None:
    parser = argparse.ArgumentParser(prog="diagnose_single_level")
    parser.add_argument("--level-file", type=Path,
                        default=Path("results/learnability/levels/8x8_3a_2L_cooperative/train/level_000.txt"))
    parser.add_argument("--algo", choices=("IQL", "VDN", "QMIX"), default="QMIX")
    parser.add_argument("--steps", type=int, default=50_000)
    parser.add_argument("--assess-every", type=int, default=5_000)
    parser.add_argument("--assess-episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--print-trajectory", action="store_true")
    args = parser.parse_args()

    if not args.level_file.is_file():
        print(f"ERROR: level file not found: {args.level_file}", file=sys.stderr)
        sys.exit(1)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    world_str = args.level_file.read_text(encoding="utf-8")
    print(f"Training {args.algo} on a single level:")
    print(f"  file: {args.level_file}")
    print(f"  steps: {args.steps}, t_max: {GRID.t_max}")
    print(world_str)

    def env_factory() -> ThesisLLEConfig:
        return ThesisLLEConfig.from_world(World(world_str), t_max=GRID.t_max)

    sample_env = env_factory()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    trainer = _build_trainer(args.algo, sample_env, args.steps).to(device)
    trainer.randomize()
    agent = trainer.make_agent().to(device)
    test_agent = trainer.make_agent().to(device)

    time_step = 0
    episode_num = 0
    next_assess_at = args.assess_every

    print(f"\n{'step':>7s}  {'success_rate':>12s}  {'mean_return':>12s}")
    while time_step < args.steps:
        env = env_factory().env
        _, _, time_step = _train_one_episode(
            env, agent, trainer, time_step, episode_num, args.steps,
        )
        episode_num += 1
        while time_step >= next_assess_at:
            sr, mr = _greedy_assess(env_factory, test_agent, args.assess_episodes)
            print(f"{next_assess_at:>7d}  {sr:>12.3f}  {mr:>+12.3f}")
            next_assess_at += args.assess_every

    sr, mr = _greedy_assess(env_factory, test_agent, max(args.assess_episodes, 100))
    print(f"\nFinal: success_rate={sr:.3f}  mean_return={mr:+.3f}  "
          f"(over {max(args.assess_episodes, 100)} greedy episodes)")

    if args.print_trajectory:
        _print_trajectory(env_factory, test_agent)


if __name__ == "__main__":
    main()
