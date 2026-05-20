"""Plot the curriculum-strategy comparison.

Run dirs are named ``{condition}_{algo}_seed{N}``. Produces:
  - final_bar_chart.pdf: grouped bars, x = condition, hue = algo, test success
  - learning_curves.pdf : test success vs step, one panel per condition

Style matches experiments.learnability.plot_results.
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

from experiments.curriculum_strategy.configs import ALGORITHMS, CONDITIONS

plt.rcParams.update({
    "text.usetex": shutil.which("latex") is not None,
    "text.latex.preamble": r"\usepackage{amsmath}",
    "font.family": "serif",
})

ALGO_COLORS: dict[str, str] = {"IQL": "#4C78A8", "VDN": "#F58518", "QMIX": "#54A24B"}

_RUN_DIR_RE = re.compile(
    r"^(?P<condition>direct|forward|reverse|mixed)_"
    r"(?P<algo>QMIX|VDN|IQL)_seed(?P<seed>\d+)$"
)


def parse_run_dir(name: str):
    m = _RUN_DIR_RE.match(name)
    if not m:
        return None
    return m["condition"], m["algo"], int(m["seed"])


def aggregate_final(runs_dir: Path):
    """Map ``(condition, algo)`` -> {'train','test','n'} mean success."""
    buckets: dict[tuple[str, str], dict[str, list[float]]] = {}
    if runs_dir.exists():
        for entry in sorted(runs_dir.iterdir()):
            if not entry.is_dir():
                continue
            parsed = parse_run_dir(entry.name)
            if parsed is None:
                continue
            cond, algo, _seed = parsed
            path = entry / "final_results.json"
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            b = buckets.setdefault((cond, algo), {"train": [], "test": []})
            for split in ("train", "test"):
                sr = payload.get(f"success_rate_{split}")
                if sr is not None:
                    b[split].append(float(sr))
    out: dict[tuple[str, str], dict[str, float]] = {}
    for key, b in buckets.items():
        out[key] = {
            "train": float(np.mean(b["train"])) if b["train"] else 0.0,
            "test": float(np.mean(b["test"])) if b["test"] else 0.0,
            "n": len(b["test"]),
        }
    return out


def plot_final_bar_chart(runs_dir: Path, out_path: Path) -> None:
    agg = aggregate_final(runs_dir)
    if not agg:
        print("[plot] WARN: no final_results.json data, skipping bar chart", file=sys.stderr)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)

    conditions = [c for c in CONDITIONS if any((c, a) in agg for a in ALGORITHMS)]
    algos = [a for a in ALGORITHMS if any((c, a) in agg for c in conditions)]
    x = np.arange(len(conditions))
    width = 0.8 / max(len(algos), 1)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, algo in enumerate(algos):
        means = [agg.get((c, algo), {}).get("test", 0.0) for c in conditions]
        offset = (i - (len(algos) - 1) / 2) * width
        ax.bar(x + offset, means, width, color=ALGO_COLORS[algo],
               edgecolor="#444", linewidth=0.8, label=algo, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(conditions)
    ax.set_ylabel("held-out test success")
    ax.set_title("Curriculum strategy vs held-out 7x7 test success")
    ax.set_ylim(0.0, 1.05)
    ax.legend(loc="upper left", fontsize="small")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def _read_test_curve(run_dir: Path):
    path = run_dir / "test_eval.csv"
    if not path.exists():
        return None
    steps, sr = [], []
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                steps.append(int(row["step"]))
                sr.append(float(row["success_rate"]))
            except (KeyError, ValueError):
                continue
    if not steps:
        return None
    return np.asarray(steps), np.asarray(sr)


def plot_learning_curves(runs_dir: Path, out_path: Path) -> None:
    by_cond: dict[str, dict[str, list]] = {c: {a: [] for a in ALGORITHMS} for c in CONDITIONS}
    if runs_dir.exists():
        for entry in sorted(runs_dir.iterdir()):
            parsed = parse_run_dir(entry.name) if entry.is_dir() else None
            if parsed is None:
                continue
            cond, algo, _seed = parsed
            curve = _read_test_curve(entry)
            if curve is not None:
                by_cond[cond][algo].append(curve)
    present = [c for c in CONDITIONS if any(by_cond[c][a] for a in ALGORITHMS)]
    if not present:
        print("[plot] WARN: no test_eval.csv data, skipping curves", file=sys.stderr)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, len(present), figsize=(4 * len(present), 4.0),
                             sharey=True, squeeze=False)
    for ax, cond in zip(axes[0], present):
        for algo in ALGORITHMS:
            seed_curves = by_cond[cond][algo]
            if not seed_curves:
                continue
            min_len = min(len(s) for s, _ in seed_curves)
            if min_len == 0:
                continue
            steps_ref = seed_curves[0][0][:min_len]
            matrix = np.vstack([sr[:min_len] for _, sr in seed_curves])
            ax.plot(steps_ref, matrix.mean(axis=0), label=algo, color=ALGO_COLORS[algo])
        ax.set_title(cond)
        ax.set_xlabel("Time step")
        ax.set_ylim(-0.05, 1.05)
    axes[0][0].set_ylabel("held-out test success")
    axes[0][0].legend(loc="upper left", fontsize="small")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_all_figures(runs_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_final_bar_chart(runs_dir, out_dir / "final_bar_chart.pdf")
    plot_learning_curves(runs_dir, out_dir / "learning_curves.pdf")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plot_results")
    parser.add_argument("--runs-dir", type=Path, default=Path("results/curriculum_strategy/runs"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/curriculum_strategy/figures"))
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    generate_all_figures(args.runs_dir, args.out_dir)
