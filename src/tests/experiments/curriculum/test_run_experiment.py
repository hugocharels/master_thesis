"""Tests for the curriculum-transfer experiment CLI (Phase 4).

The slow ``test_smoke_run_b3_iql_5k`` test is intentionally NOT run by
default: it takes minutes, depends on torch / cuda availability and on
the marl venv being on PATH. Run it explicitly with::

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_run_experiment.py -m slow

The fast tests below cover the argparse layer and the
``_load_pools_for_condition`` helper without doing any training.

Run with the marl venv (preferred):

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_run_experiment.py -m "not slow"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from lle import World

from experiments.curriculum.configs import (
    CURRICULUM_STAGES,
    FULL_RUN_TOTAL_STEPS,
    PILOT_RUN_TOTAL_STEPS,
)
from experiments.curriculum.pool_generator import pool_path
from experiments.curriculum.run_experiment import (
    ALGOS,
    CONDITIONS,
    _load_pools_for_condition,
    _per_stage_step_cap,
    build_parser,
)


# ---------------------------------------------------------------------------
# Argparse coverage
# ---------------------------------------------------------------------------


def test_parser_accepts_all_conditions(tmp_path):
    parser = build_parser()
    for condition in CONDITIONS:
        args = parser.parse_args(
            [
                "--condition",
                condition,
                "--algo",
                "QMIX",
                "--seed",
                "0",
                "--out-dir",
                str(tmp_path),
            ]
        )
        assert args.condition == condition


def test_parser_accepts_all_algos(tmp_path):
    parser = build_parser()
    for algo in ALGOS:
        args = parser.parse_args(
            [
                "--condition",
                "B3",
                "--algo",
                algo,
                "--seed",
                "0",
                "--out-dir",
                str(tmp_path),
            ]
        )
        assert args.algo == algo


def test_parser_defaults_steps_to_full_run_total_steps(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--condition",
            "B3",
            "--algo",
            "IQL",
            "--seed",
            "0",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert args.steps == FULL_RUN_TOTAL_STEPS


def test_parser_steps_can_be_overridden(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--condition",
            "CURR",
            "--algo",
            "VDN",
            "--seed",
            "1",
            "--steps",
            str(PILOT_RUN_TOTAL_STEPS),
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert args.steps == PILOT_RUN_TOTAL_STEPS


def test_parser_rejects_unknown_condition(tmp_path):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--condition",
                "NOPE",
                "--algo",
                "IQL",
                "--seed",
                "0",
                "--out-dir",
                str(tmp_path),
            ]
        )


def test_parser_rejects_unknown_algo(tmp_path):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--condition",
                "B3",
                "--algo",
                "PPO",
                "--seed",
                "0",
                "--out-dir",
                str(tmp_path),
            ]
        )


def test_parser_seed_is_required(tmp_path):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--condition",
                "B3",
                "--algo",
                "IQL",
                "--out-dir",
                str(tmp_path),
            ]
        )


# ---------------------------------------------------------------------------
# _per_stage_step_cap
# ---------------------------------------------------------------------------


def test_per_stage_cap_full_for_default_steps():
    """Full per-stage cap when the user keeps the default (full) budget."""
    cap = _per_stage_step_cap(FULL_RUN_TOTAL_STEPS)
    assert cap == CURRICULUM_STAGES[0].per_stage_step_cap_full


def test_per_stage_cap_pilot_when_steps_match_pilot_budget():
    cap = _per_stage_step_cap(PILOT_RUN_TOTAL_STEPS)
    assert cap == CURRICULUM_STAGES[0].per_stage_step_cap_pilot


def test_per_stage_cap_full_for_unrelated_step_count():
    """Any value other than PILOT defaults to the full cap."""
    cap = _per_stage_step_cap(123_456)
    assert cap == CURRICULUM_STAGES[0].per_stage_step_cap_full


# ---------------------------------------------------------------------------
# _load_pools_for_condition
# ---------------------------------------------------------------------------


def test_load_pools_b3_returns_singleton_level_6_regardless_of_outdir(tmp_path):
    """B3's pool is hand-crafted Level 6 - no disk read needed."""
    pools = _load_pools_for_condition("B3", tmp_path)
    assert len(pools) == 1
    assert len(pools[0]) == 1
    # Sanity: it is a usable lle.World with the expected number of agents.
    world = pools[0][0]
    assert isinstance(world, World)
    assert world.n_agents == 4


def test_load_pools_b3_does_not_touch_filesystem(tmp_path):
    """B3 must not require any pre-flight pools on disk."""
    # tmp_path is empty - the call should still succeed.
    assert not any(tmp_path.iterdir())
    pools = _load_pools_for_condition("B3", tmp_path)
    assert pools[0][0] is not None


def test_load_pools_unknown_condition_raises(tmp_path):
    with pytest.raises(ValueError):
        _load_pools_for_condition("UNKNOWN", tmp_path)


def _stage4_train_pool_exists(out_dir: Path) -> bool:
    """Helper: True iff the stage-4 train pool has been pre-generated."""
    p = pool_path(out_dir, CURRICULUM_STAGES[3], "train")
    return p.is_dir() and any(p.glob("level_*.json"))


_DEFAULT_OUT_DIR = Path("results") / "curriculum_experiment"


def test_load_pools_b1_returns_stage4_train_pool_if_present():
    if not _stage4_train_pool_exists(_DEFAULT_OUT_DIR):
        pytest.skip(
            "Stage-4 train pool missing; run "
            "_preflight_generate_pools.py to populate "
            f"{pool_path(_DEFAULT_OUT_DIR, CURRICULUM_STAGES[3], 'train')}."
        )
    pools = _load_pools_for_condition("B1", _DEFAULT_OUT_DIR)
    assert len(pools) == 1
    # Stage-4 pool size is 50 (per CURRICULUM_STAGES[3].pool_size).
    assert len(pools[0]) == CURRICULUM_STAGES[3].pool_size


def test_load_pools_b2_returns_union_of_all_stages_if_present():
    for stage in CURRICULUM_STAGES:
        if not (pool_path(_DEFAULT_OUT_DIR, stage, "train").is_dir()
                and any(pool_path(_DEFAULT_OUT_DIR, stage, "train").glob("level_*.json"))):
            pytest.skip(
                f"Stage-{stage.stage_id} train pool missing; run pre-flight."
            )
    pools = _load_pools_for_condition("B2", _DEFAULT_OUT_DIR)
    assert len(pools) == 1
    expected = sum(stage.pool_size for stage in CURRICULUM_STAGES)
    assert len(pools[0]) == expected


def test_load_pools_curr_returns_one_pool_per_stage_if_present():
    for stage in CURRICULUM_STAGES:
        if not (pool_path(_DEFAULT_OUT_DIR, stage, "train").is_dir()
                and any(pool_path(_DEFAULT_OUT_DIR, stage, "train").glob("level_*.json"))):
            pytest.skip(
                f"Stage-{stage.stage_id} train pool missing; run pre-flight."
            )
    pools = _load_pools_for_condition("CURR", _DEFAULT_OUT_DIR)
    assert len(pools) == len(CURRICULUM_STAGES)
    for pool, stage in zip(pools, CURRICULUM_STAGES):
        assert len(pool) == stage.pool_size


# ---------------------------------------------------------------------------
# Slow smoke test (DO NOT RUN here - the user runs it manually)
# ---------------------------------------------------------------------------


PYTHON = sys.executable  # the test runner picks the interpreter; in the
# marl venv that means marl is importable.


@pytest.mark.slow
def test_smoke_run_b3_iql_5k(tmp_path):
    """Tiny 5000-step B3 IQL run completes and writes expected files."""
    out_dir = tmp_path / "results"
    cmd = [
        PYTHON,
        "-m",
        "experiments.curriculum.run_experiment",
        "--condition",
        "B3",
        "--algo",
        "IQL",
        "--seed",
        "0",
        "--steps",
        "5000",
        "--out-dir",
        str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stderr
    run_dir = out_dir / "runs" / "B3_IQL_seed0"
    assert (run_dir / "final_results.json").exists()
    assert (run_dir / "level6_eval.csv").exists()
