"""2-laser curriculum-strategy runner: train one (condition, algo, seed) cell.

Training/eval logic is identical to
:mod:`experiments.curriculum_strategy.run_experiment` -- its config-free helpers
(`_build_trainer`, `_set_stage_epsilon`, `_make_padded_env`, `_assess_on_pool`,
`_train_one_episode`) are imported and reused directly, so the two experiments
stay in lock-step. Only the difficulty ladder and the fully_coupled 2-laser
target differ (see ``.configs``). Output layout matches the 1-laser experiment so
``plot_results`` can be reused.

All conditions consume exactly ``--steps`` environment steps; only the allocation
across the ladder differs. Every condition is evaluated on the same held-out
6x6/2-laser fully_coupled target pool.

Usage (inside the docker container):

    GPU_DEVICES=2 bash docker/run.sh -- python -m \
        experiments.curriculum_strategy_2L.run_experiment \
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

from experiments.curriculum.lle_marl_env import ThesisLLEConfig
from experiments.curriculum.pool_generator import load_pool, pool_path
from experiments.curriculum_strategy.run_experiment import (
    _assess_on_pool,
    _build_trainer,
    _make_padded_env,
    _set_stage_epsilon,
    _train_one_episode,
)
from experiments.curriculum_strategy.schedulers import make_strategy
from experiments.curriculum_strategy_2L.configs import (
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

DEFAULT_OUT_DIR = Path("results") / "curriculum_strategy_2L"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_experiment",
        description="Train one (condition, algo, seed) 2-laser curriculum-strategy cell.",
    )
    parser.add_argument("--condition", required=True, choices=CONDITIONS)
    parser.add_argument("--algo", required=True, choices=ALGORITHMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--steps", type=int, default=TOTAL_STEPS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--target-train-subsample",
        type=int,
        default=0,
        help=(
            "If > 0, truncate the 2-laser target TRAIN pool to its first N levels "
            "(the held-out eval pool is untouched). N=1 is a single-level overfit "
            "probe -- the capacity gate for whether the learner can represent a "
            "mutual-coordination solution at all."
        ),
    )
    return parser


def _load_train_pools(out_dir: Path) -> dict[int, list[World]]:
    return {r.stage_id: load_pool(pool_path(out_dir, r, "train")) for r in RUNGS}


def _load_target_eval_pool(out_dir: Path) -> list[World]:
    return load_pool(pool_path(out_dir, TARGET_RUNG, "eval"))


def _target_shapes(sample_target_world: World):
    cfg = ThesisLLEConfig.from_world(sample_target_world, t_max=TARGET_RUNG.t_max)
    obs_shape = cfg.env.observation_shape
    state_shape = cfg.env.state_shape
    return (
        (int(obs_shape[0]), int(obs_shape[1]), int(obs_shape[2])),
        (int(state_shape[0]),),
    )


def main() -> None:
    args = build_parser().parse_args()
    condition, algo, seed = args.condition, args.algo, args.seed
    total_steps, out_dir = args.steps, args.out_dir

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    train_pools = _load_train_pools(out_dir)
    target_eval_pool = _load_target_eval_pool(out_dir)
    if args.target_train_subsample > 0:
        n = min(args.target_train_subsample, len(train_pools[TARGET_RUNG.stage_id]))
        train_pools[TARGET_RUNG.stage_id] = train_pools[TARGET_RUNG.stage_id][:n]
        print(
            f"Subsampled target train pool to {n} level(s) (overfit probe)",
            file=sys.stderr,
        )
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
    stage_eval_csv.writerow(["step", "stage_id", "success_rate", "mean_return"])
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
