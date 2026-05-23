"""Plot the 2-laser curriculum-strategy comparison.

Reuses the 1-laser plotting routines verbatim
(:mod:`experiments.curriculum_strategy.plot_results`); those functions read the
condition/algorithm/target names as module-level globals at call time, so we
re-point them at the 2-laser config before delegating. This keeps a single
implementation of the figures and summary table.

Run with the marl venv::

    PYTHONPATH=src python -m experiments.curriculum_strategy_2L.plot_results
"""
from __future__ import annotations

import argparse
from pathlib import Path

import experiments.curriculum_strategy.plot_results as base
from experiments.curriculum_strategy_2L.configs import (
    ALGORITHMS,
    CONDITIONS,
    TARGET_RUNG,
)

# Re-point the shared plotting routines at the 2-laser config.
base.CONDITIONS = CONDITIONS
base.ALGORITHMS = ALGORITHMS
base.TARGET_RUNG = TARGET_RUNG
base._TARGET = f"{TARGET_RUNG.height}x{TARGET_RUNG.width}/{TARGET_RUNG.n_lasers}L"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plot_results")
    parser.add_argument("--runs-dir", type=Path, default=Path("results/curriculum_strategy_2L/runs"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/curriculum_strategy_2L/figures"))
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    base.generate_all_figures(args.runs_dir, args.out_dir)
