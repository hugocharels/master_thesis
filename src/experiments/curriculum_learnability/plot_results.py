"""Plot results of the curriculum-learnability experiment.

The output CSV format matches the learnability experiment, so we
reuse its plotting helpers verbatim and point them at the
curriculum_learnability run dir.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.learnability.plot_results import generate_all_figures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plot_results",
        description="Aggregate curriculum-learnability runs into figures.",
    )
    parser.add_argument(
        "--runs-dir", type=Path,
        default=Path("results/curriculum_learnability/runs"),
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path("results/curriculum_learnability/figures"),
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    generate_all_figures(args.runs_dir, args.out_dir)
