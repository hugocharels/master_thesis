"""Plotting for the learnability experiment.

Produces two figures:
  - learning_curves.pdf: train/test success rate vs step, per algo
  - final_bar_chart.pdf: grouped bars per algo (train vs test)

Style matches the marl framework's plot_results.py conventions:
serif font, CI95 bands at alpha=0.2, tight margins, "Time step" x-axis.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from experiments.learnability.configs import ALGORITHMS

# Match marl UI style
plt.rcParams.update({
    "text.usetex": shutil.which("latex") is not None,
    "text.latex.preamble": r"\usepackage{amsmath}",
    "font.family": "serif",
})

ALGO_COLORS: dict[str, str] = {
    "IQL": "#4C78A8",
    "VDN": "#F58518",
    "QMIX": "#54A24B",
}

_RUN_DIR_RE = re.compile(r"^(?P<algo>QMIX|VDN|IQL)_seed(?P<seed>\d+)$")


def _iter_run_dirs(runs_dir: Path):
    if not runs_dir.exists():
        return
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        m = _RUN_DIR_RE.match(entry.name)
        if m:
            yield m["algo"], int(m["seed"]), entry


def _read_eval_csv(path: Path):
    if not path.exists():
        return None
    steps, sr = [], []
    try:
        with path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    steps.append(int(row["step"]))
                    sr.append(float(row["success_rate"]))
                except (KeyError, ValueError):
                    continue
    except OSError:
        return None
    if not steps:
        return None
    return np.asarray(steps, dtype=np.int64), np.asarray(sr, dtype=np.float64)


def plot_learning_curves(runs_dir: Path, out_path: Path) -> None:
    """Single axes overlaying train and test success rate per algo.

    Colour encodes the algorithm; line style encodes the pool (solid =
    train, dashed = test). CI95 bands (like marl UI default) when n > 1,
    falls back to raw line when n = 1.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, dict[str, list[tuple[np.ndarray, np.ndarray]]]] = {
        a: {"train": [], "test": []} for a in ALGORITHMS
    }
    for algo, _seed, run_dir in _iter_run_dirs(runs_dir):
        for split in ("train", "test"):
            result = _read_eval_csv(run_dir / f"{split}_eval.csv")
            if result is not None:
                data[algo][split].append(result)

    if not any(data[a][s] for a in ALGORITHMS for s in ("train", "test")):
        print("[plot] WARN: no eval CSV data, skipping learning_curves", file=sys.stderr)
        return

    split_style = {"train": "-", "test": "--"}

    fig, ax = plt.subplots(figsize=(8, 5))
    for algo in ALGORITHMS:
        color = ALGO_COLORS[algo]
        for split in ("train", "test"):
            seed_data = data[algo][split]
            if not seed_data:
                continue
            min_len = min(len(s) for s, _ in seed_data)
            if min_len == 0:
                continue
            steps_ref = seed_data[0][0][:min_len]
            matrix = np.vstack([sr[:min_len] for _, sr in seed_data])
            n = matrix.shape[0]
            mean = matrix.mean(axis=0)
            std = matrix.std(axis=0)

            ax.plot(steps_ref, mean, color=color, linestyle=split_style[split])

            if n > 1:
                # CI95 band clipped to [min, max], matching marl style
                ci95 = std * 1.96 / np.sqrt(n)
                low = np.maximum(mean - ci95, matrix.min(axis=0))
                high = np.minimum(mean + ci95, matrix.max(axis=0))
                ax.fill_between(steps_ref, low, high, color=color, alpha=0.15)

    ax.set_xlabel("Time step")
    ax.set_ylabel("Exit rate")
    ax.set_ylim(-0.05, 1.05)
    ax.margins(x=0.01, y=0.01)

    # Two-dimensional legend: colour = algorithm, line style = pool. Two
    # separate legends, both kept inside the axes frame.
    algo_handles = [
        Line2D([0], [0], color=ALGO_COLORS[a], lw=2, label=a) for a in ALGORITHMS
    ]
    split_handles = [
        Line2D([0], [0], color="black", lw=2, linestyle="-", label="Train set"),
        Line2D([0], [0], color="black", lw=2, linestyle="--", label="Test set"),
    ]
    leg_algo = ax.legend(handles=algo_handles, loc="upper left", fontsize="small",
                         title="Algorithm", framealpha=0.9)
    ax.add_artist(leg_algo)
    ax.legend(handles=split_handles, loc="lower right", fontsize="small",
              title="Pool", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_final_bar_chart(runs_dir: Path, out_path: Path) -> None:
    """Grouped bars: per algo, train vs test final success rate."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    per_algo: dict[str, dict[str, list[float]]] = {
        a: {"train": [], "test": []} for a in ALGORITHMS
    }
    for algo, _seed, run_dir in _iter_run_dirs(runs_dir):
        path = run_dir / "final_results.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for split in ("train", "test"):
            sr = payload.get(f"success_rate_{split}")
            if sr is not None:
                per_algo[algo][split].append(float(sr))

    present = [a for a in ALGORITHMS if per_algo[a]["train"] or per_algo[a]["test"]]
    if not present:
        print("[plot] WARN: no final_results.json data, skipping bar chart", file=sys.stderr)
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(present))
    width = 0.35

    for split, offset, hatch in [("train", -width / 2, None), ("test", width / 2, "//")]:
        means, stds = [], []
        for a in present:
            vals = per_algo[a][split]
            means.append(float(np.mean(vals)) if vals else 0.0)
            if len(vals) > 1:
                stds.append(float(np.std(vals) * 1.96 / np.sqrt(len(vals))))
            else:
                stds.append(0.0)
        colors = [ALGO_COLORS[a] for a in present]
        ax.bar(x + offset, means, width, yerr=stds,
               color=colors, edgecolor="#444", linewidth=0.8,
               capsize=4, alpha=0.7 if hatch else 0.85,
               hatch=hatch, label=f"{split} set")

    ax.set_xticks(x)
    ax.set_xticklabels(present)
    ax.set_ylabel("Exit rate")
    ax.set_title("Final success rate by algorithm")
    ax.set_ylim(0.0, 1.05)
    ax.margins(x=0.01, y=0.01)
    ax.legend(loc="upper right", fontsize="small", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_all_figures(runs_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_learning_curves(runs_dir, out_dir / "learning_curves.pdf")
    plot_final_bar_chart(runs_dir, out_dir / "final_bar_chart.pdf")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plot_results",
        description="Aggregate learnability runs into figures.",
    )
    parser.add_argument(
        "--runs-dir", type=Path, default=Path("results/learnability_5x5/runs"),
        help="Run directory. Default: results/learnability_5x5/runs.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("results/learnability_5x5/figures"),
        help="Figure directory. Default: results/learnability_5x5/figures.",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    generate_all_figures(args.runs_dir, args.out_dir)
