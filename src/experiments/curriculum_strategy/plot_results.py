"""Plot the curriculum-strategy comparison, aggregated over seeds.

Run dirs are named ``{condition}_{algo}_seed{N}``. Scales to any number of
seeds: every figure aggregates over the available seeds with a 95 % confidence
interval (Student-t for small n, falling back to the normal 1.96 for large n).

Figures written to ``--out-dir``:
  - ``final_success.pdf``      train vs held-out test success, grouped bars per
                               condition x algo, CI95 error bars over seeds.
  - ``test_curves_pooled.pdf`` held-out test success vs step, one line per
                               condition pooled over algos+seeds, CI95 band.
                               The headline "curriculum vs direct" figure.
  - ``test_curves_by_algo.pdf`` same, one panel per algorithm (rigorous view).

A mean +- CI95 summary table is printed to stdout for the thesis numbers.

Run with the marl venv::

    PYTHONPATH=src python -m experiments.curriculum_strategy.plot_results
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from experiments.curriculum_strategy.configs import ALGORITHMS, CONDITIONS, TARGET_RUNG

plt.rcParams.update({
    "text.usetex": shutil.which("latex") is not None,
    "text.latex.preamble": r"\usepackage{amsmath}",
    "font.family": "serif",
})

# Conditions get stable colours (the curve plots are keyed by condition).
CONDITION_COLORS: dict[str, str] = {
    "direct": "#888888",   # baseline
    "forward": "#1b9e77",  # the curriculum
    "reverse": "#d95f02",
    "mixed": "#7570b3",
}
ALGO_COLORS: dict[str, str] = {"IQL": "#4C78A8", "VDN": "#F58518", "QMIX": "#54A24B"}

_TARGET = f"{TARGET_RUNG.height}x{TARGET_RUNG.width}/{TARGET_RUNG.n_lasers}L"

_RUN_DIR_RE = re.compile(
    r"^(?P<condition>direct|forward|reverse|mixed)_"
    r"(?P<algo>QMIX|VDN|IQL)_seed(?P<seed>\d+)$"
)

# Two-sided t_{n-1, 0.025} for small samples; >30 falls back to 1.96.
_T = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365,
      9: 2.306, 10: 2.262, 15: 2.145, 20: 2.093, 25: 2.064, 30: 2.045}


def _t(n: int) -> float:
    if n <= 1:
        return 0.0
    if n in _T:
        return _T[n]
    return 1.96 if n > 30 else _T[min(_T, key=lambda k: abs(k - n))]


def _ci95(vals: list[float]) -> tuple[float, float, int]:
    """Return (mean, ci95_halfwidth, n)."""
    a = np.asarray(vals, dtype=float)
    n = len(a)
    if n == 0:
        return 0.0, 0.0, 0
    mean = float(a.mean())
    ci = _t(n) * float(a.std(ddof=1)) / math.sqrt(n) if n > 1 else 0.0
    return mean, ci, n


def parse_run_dir(name: str):
    m = _RUN_DIR_RE.match(name)
    return (m["condition"], m["algo"], int(m["seed"])) if m else None


def _iter_runs(runs_dir: Path):
    if not runs_dir.exists():
        return
    for entry in sorted(runs_dir.iterdir()):
        parsed = parse_run_dir(entry.name) if entry.is_dir() else None
        if parsed is not None:
            yield (*parsed, entry)


# ---------------------------------------------------------------------------
# Final success (bar charts)
# ---------------------------------------------------------------------------

def collect_final(runs_dir: Path) -> dict[tuple[str, str], dict[str, list[float]]]:
    buckets: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: {"train": [], "test": []}
    )
    for cond, algo, _seed, run_dir in _iter_runs(runs_dir):
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
                buckets[(cond, algo)][split].append(float(sr))
    return buckets


def plot_final(runs_dir: Path, out_path: Path) -> None:
    buckets = collect_final(runs_dir)
    if not buckets:
        print("[plot] WARN: no final_results.json, skipping final_success", file=sys.stderr)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)

    conds = [c for c in CONDITIONS if any((c, a) in buckets for a in ALGORITHMS)]
    algos = [a for a in ALGORITHMS if any((c, a) in buckets for c in conds)]
    x = np.arange(len(conds))
    width = 0.8 / max(len(algos), 1)
    n_max = max((len(b["test"]) for b in buckets.values()), default=0)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    ymax = 0.0
    for ax, split in zip(axes, ("train", "test")):
        for i, algo in enumerate(algos):
            means, cis = [], []
            for c in conds:
                m, ci, _ = _ci95(buckets.get((c, algo), {"train": [], "test": []})[split])
                means.append(m)
                cis.append(ci)
            ymax = max(ymax, max((m + ci for m, ci in zip(means, cis)), default=0.0))
            offset = (i - (len(algos) - 1) / 2) * width
            ax.bar(x + offset, means, width, yerr=cis, capsize=3,
                   color=ALGO_COLORS.get(algo, "#999"), edgecolor="#333",
                   linewidth=0.7, label=algo, alpha=0.88)
        ax.set_xticks(x)
        ax.set_xticklabels(conds)
        ax.set_title(f"{split} success")
        ax.margins(x=0.02)
    axes[0].set_ylabel("success rate (greedy exit rate)")
    axes[0].set_ylim(0.0, min(1.0, ymax * 1.25 + 0.02))
    axes[1].legend(loc="upper right", fontsize="small", title="algorithm")
    fig.suptitle(f"Curriculum strategy on the {_TARGET} target (n={n_max} seeds, 95% CI)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Learning curves (test success vs step)
# ---------------------------------------------------------------------------

def _read_curve(run_dir: Path, split: str):
    path = run_dir / f"{split}_eval.csv"
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
    return np.asarray(steps), np.asarray(sr, dtype=float)


def _stack(curves: list[tuple[np.ndarray, np.ndarray]]):
    """Align ragged curves to the shortest length; return (steps, mean, ci95)."""
    curves = [c for c in curves if c is not None and len(c[0]) > 0]
    if not curves:
        return None
    min_len = min(len(s) for s, _ in curves)
    if min_len == 0:
        return None
    steps = curves[0][0][:min_len]
    matrix = np.vstack([sr[:min_len] for _, sr in curves])
    n = matrix.shape[0]
    mean = matrix.mean(axis=0)
    if n > 1:
        ci = _t(n) * matrix.std(axis=0, ddof=1) / math.sqrt(n)
    else:
        ci = np.zeros_like(mean)
    return steps, mean, ci, n


def collect_curves(runs_dir: Path, split: str):
    """(condition, algo) -> list of (steps, sr)."""
    by: dict[tuple[str, str], list] = defaultdict(list)
    for cond, algo, _seed, run_dir in _iter_runs(runs_dir):
        c = _read_curve(run_dir, split)
        if c is not None:
            by[(cond, algo)].append(c)
    return by


def plot_test_curves_pooled(runs_dir: Path, out_path: Path, split: str = "test") -> None:
    by = collect_curves(runs_dir, split)
    if not by:
        print(f"[plot] WARN: no {split}_eval.csv, skipping pooled curves", file=sys.stderr)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    ymax, n_max = 0.0, 0
    for cond in CONDITIONS:
        pooled = [c for a in ALGORITHMS for c in by.get((cond, a), [])]
        stacked = _stack(pooled)
        if stacked is None:
            continue
        steps, mean, ci, n = stacked
        n_max = max(n_max, n)
        color = CONDITION_COLORS[cond]
        ax.plot(steps, mean, label=cond, color=color, linewidth=1.8)
        ax.fill_between(steps, mean - ci, mean + ci, color=color, alpha=0.18)
        ymax = max(ymax, float((mean + ci).max()))
    ax.set_xlabel("environment step")
    ax.set_ylabel(f"held-out {split} success")
    ax.set_ylim(0.0, min(1.0, ymax * 1.25 + 0.02))
    ax.margins(x=0.01)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize="small", title="condition")
    ax.set_title(f"Curriculum strategy on {_TARGET}  (pooled over algorithms, n={n_max}, 95% CI)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_test_curves_by_algo(runs_dir: Path, out_path: Path, split: str = "test") -> None:
    by = collect_curves(runs_dir, split)
    if not by:
        print(f"[plot] WARN: no {split}_eval.csv, skipping by-algo curves", file=sys.stderr)
        return
    algos = [a for a in ALGORITHMS if any((c, a) in by for c in CONDITIONS)]
    if not algos:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, len(algos), figsize=(4.2 * len(algos), 4.2),
                             sharey=True, squeeze=False)
    ymax = 0.0
    for ax, algo in zip(axes[0], algos):
        for cond in CONDITIONS:
            stacked = _stack(by.get((cond, algo), []))
            if stacked is None:
                continue
            steps, mean, ci, _ = stacked
            color = CONDITION_COLORS[cond]
            ax.plot(steps, mean, label=cond, color=color, linewidth=1.6)
            ax.fill_between(steps, mean - ci, mean + ci, color=color, alpha=0.16)
            ymax = max(ymax, float((mean + ci).max()))
        ax.set_title(algo)
        ax.set_xlabel("environment step")
        ax.grid(True, alpha=0.25)
        ax.margins(x=0.01)
    axes[0][0].set_ylabel(f"held-out {split} success")
    axes[0][0].set_ylim(0.0, min(1.0, ymax * 1.25 + 0.02))
    axes[0][-1].legend(loc="upper left", fontsize="small", title="condition")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_summary(runs_dir: Path) -> None:
    buckets = collect_final(runs_dir)
    if not buckets:
        return
    print(f"\nFinal success on {_TARGET} (mean +- CI95):")
    print(f"{'algo':5} {'cond':8} {'train':>16} {'test':>16}")
    for algo in ALGORITHMS:
        for cond in CONDITIONS:
            b = buckets.get((cond, algo))
            if not b:
                continue
            trm, trc, n = _ci95(b["train"])
            tem, tec, _ = _ci95(b["test"])
            print(f"{algo:5} {cond:8} {trm:7.3f}+-{trc:<6.3f} {tem:7.3f}+-{tec:<6.3f}  (n={n})")
    # Pooled over algorithms.
    print(f"\n{'POOLED':5} {'cond':8} {'train':>16} {'test':>16}")
    for cond in CONDITIONS:
        tr = [v for a in ALGORITHMS for v in buckets.get((cond, a), {"train": []})["train"]]
        te = [v for a in ALGORITHMS for v in buckets.get((cond, a), {"test": []})["test"]]
        if not te:
            continue
        trm, trc, n = _ci95(tr)
        tem, tec, _ = _ci95(te)
        print(f"{'':5} {cond:8} {trm:7.3f}+-{trc:<6.3f} {tem:7.3f}+-{tec:<6.3f}  (n={n})")


def generate_all_figures(runs_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_final(runs_dir, out_dir / "final_success.pdf")
    plot_test_curves_pooled(runs_dir, out_dir / "test_curves_pooled.pdf")
    plot_test_curves_by_algo(runs_dir, out_dir / "test_curves_by_algo.pdf")
    print_summary(runs_dir)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plot_results")
    parser.add_argument("--runs-dir", type=Path, default=Path("results/curriculum_strategy/runs"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/curriculum_strategy/figures"))
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    generate_all_figures(args.runs_dir, args.out_dir)
