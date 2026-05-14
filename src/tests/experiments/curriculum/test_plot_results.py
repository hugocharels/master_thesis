"""Fast tests for the curriculum-experiment plotting module (Phase 8.1).

These tests use synthetic CSV / JSON fixtures inside ``tmp_path``: no real
training runs are required. ``matplotlib`` is forced to the ``Agg``
backend in :mod:`experiments.curriculum.plot_results` so the figures
render headlessly on Windows CI / local dev.

Run with the marl venv::

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_plot_results.py -v
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from experiments.curriculum.plot_results import (
    generate_all_figures,
    plot_exp1_learnability,
    plot_final_success_rates,
    plot_learning_curves,
    plot_stage_progression,
)


# ---------------------------------------------------------------------------
# Synthetic-data helpers
# ---------------------------------------------------------------------------


def _write_level6_eval_csv(run_dir: Path, n_rows: int, base_sr: float) -> None:
    """Write a synthetic level6_eval.csv with ``n_rows`` evaluation rows.

    Steps go ``20_000, 40_000, ...``. success_rate climbs linearly from
    ``base_sr`` to roughly ``base_sr + 0.5``. mean_return tracks loosely.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "level6_eval.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "success_rate", "mean_return"])
        for i in range(n_rows):
            step = (i + 1) * 20_000
            sr = min(1.0, base_sr + 0.05 * i)
            mr = sr * 5.0
            writer.writerow([step, f"{sr:.6f}", f"{mr:.6f}"])


def _write_stage_progress_csv(
    run_dir: Path, transitions: list[tuple[int, int]] | None
) -> None:
    """Write a synthetic stage_progress.csv.

    ``transitions`` is ``[(step, stage_id), ...]``. When ``None``,
    write only the header (mimics baselines).
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "stage_progress.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "stage_id"])
        if transitions is not None:
            for step, stage_id in transitions:
                writer.writerow([step, stage_id])


def _write_final_results_json(run_dir: Path, payload: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "final_results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Test 1: plot_learning_curves with 2 conditions x 3 seeds
# ---------------------------------------------------------------------------


def test_plot_learning_curves_with_synthetic_csv_data(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "figures"
    for cond, base in [("B3", 0.0), ("CURR", 0.1)]:
        for seed in range(3):
            run_dir = runs_dir / f"{cond}_QMIX_seed{seed}"
            _write_level6_eval_csv(run_dir, n_rows=10, base_sr=base + 0.01 * seed)

    out_path = out_dir / "learning_curves_level6.pdf"
    plot_learning_curves(runs_dir, out_path)

    assert out_path.exists(), "Learning-curves PDF should be created"
    assert out_path.stat().st_size > 100


# ---------------------------------------------------------------------------
# Test 2: plot_final_success_rates with 4 conditions x 3 seeds
# ---------------------------------------------------------------------------


def test_plot_final_success_rates_with_synthetic_json(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "figures"
    sr_by_condition = {"B3": 0.05, "B1": 0.10, "B2": 0.30, "CURR": 0.55}
    for cond, base_sr in sr_by_condition.items():
        for seed in range(3):
            run_dir = runs_dir / f"{cond}_QMIX_seed{seed}"
            _write_final_results_json(
                run_dir,
                {
                    "algo": "QMIX",
                    "condition": cond,
                    "seed": seed,
                    "total_steps_trained": 1_500_000,
                    "success_rate_level6": base_sr + 0.02 * seed,
                    "success_rate_level6_std": 0.05,
                    "mean_return_level6": (base_sr + 0.02 * seed) * 5.0,
                    "n_eval_episodes": 200,
                },
            )

    out_path = out_dir / "final_success_rates.pdf"
    plot_final_success_rates(runs_dir, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 100


# ---------------------------------------------------------------------------
# Test 3: plot_stage_progression with 3 CURR seeds
# ---------------------------------------------------------------------------


def test_plot_stage_progression_with_synthetic_data(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "figures"
    transitions_by_seed = [
        [(0, 1), (250_000, 2), (600_000, 3), (1_100_000, 4)],
        [(0, 1), (300_000, 2), (700_000, 3), (1_200_000, 4)],
        [(0, 1), (200_000, 2), (550_000, 3), (1_000_000, 4)],
    ]
    for seed, transitions in enumerate(transitions_by_seed):
        run_dir = runs_dir / f"CURR_QMIX_seed{seed}"
        _write_stage_progress_csv(run_dir, transitions)

    out_path = out_dir / "stage_progression.pdf"
    plot_stage_progression(runs_dir, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 100


# ---------------------------------------------------------------------------
# Test 4: plot_exp1_learnability with 3 algos
# ---------------------------------------------------------------------------


def test_plot_exp1_learnability_with_synthetic_json(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "figures"
    sr_by_algo = {"IQL": 0.25, "VDN": 0.40, "QMIX": 0.55}
    for algo, base in sr_by_algo.items():
        for seed in range(3):
            run_dir = runs_dir / f"B1_{algo}_seed{seed}"
            _write_final_results_json(
                run_dir,
                {
                    "algo": algo,
                    "condition": "B1",
                    "seed": seed,
                    "total_steps_trained": 1_500_000,
                    "success_rate_level6": base * 0.5,
                    "success_rate_level6_std": 0.05,
                    "mean_return_level6": 1.0,
                    "n_eval_episodes": 200,
                    "success_rate_held_out_pool": base + 0.02 * seed,
                    "success_rate_held_out_pool_std": 0.04,
                    "mean_return_held_out_pool": (base + 0.02 * seed) * 5.0,
                },
            )

    out_path = out_dir / "exp1_learnability.pdf"
    plot_exp1_learnability(runs_dir, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 100


# ---------------------------------------------------------------------------
# Test 5: generate_all_figures with no data must not crash
# ---------------------------------------------------------------------------


def test_generate_all_figures_with_no_data_does_not_crash(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    out_dir = tmp_path / "figures"

    # Should print warnings but never raise.
    generate_all_figures(runs_dir, out_dir)

    # out_dir should be created even if no figures were produced.
    assert out_dir.exists()


# ---------------------------------------------------------------------------
# Test 6: plot_learning_curves handles uneven seed row counts
# ---------------------------------------------------------------------------


def test_plot_learning_curves_handles_uneven_seed_row_counts(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "figures"
    _write_level6_eval_csv(runs_dir / "B3_QMIX_seed0", n_rows=5, base_sr=0.1)
    _write_level6_eval_csv(runs_dir / "B3_QMIX_seed1", n_rows=3, base_sr=0.2)

    out_path = out_dir / "learning_curves_level6.pdf"
    plot_learning_curves(runs_dir, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 100


# ---------------------------------------------------------------------------
# Test 7: plot_exp1_learnability with only IQL data must not crash
# ---------------------------------------------------------------------------


def test_plot_exp1_learnability_skips_algo_with_no_data(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "figures"
    for seed in range(2):
        run_dir = runs_dir / f"B1_IQL_seed{seed}"
        _write_final_results_json(
            run_dir,
            {
                "algo": "IQL",
                "condition": "B1",
                "seed": seed,
                "total_steps_trained": 1_500_000,
                "success_rate_level6": 0.1,
                "success_rate_level6_std": 0.05,
                "mean_return_level6": 0.5,
                "n_eval_episodes": 200,
                "success_rate_held_out_pool": 0.3 + 0.02 * seed,
                "success_rate_held_out_pool_std": 0.04,
                "mean_return_held_out_pool": 1.5,
            },
        )

    out_path = out_dir / "exp1_learnability.pdf"
    plot_exp1_learnability(runs_dir, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 100
