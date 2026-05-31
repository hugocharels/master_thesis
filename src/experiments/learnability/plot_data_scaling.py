"""Plot held-out success vs training-pool size for the data-scaling experiment.

Reads ``results/datascale_<grid>_<a>a_<l>L_n<N>/runs/*/final_results.json`` and
plots mean train- and test-pool success against the number of training levels
(log x-axis), aggregated over all (algorithm, seed) runs with a 95 % CI band.

Run with the marl venv::

    PYTHONPATH=src python -m experiments.learnability.plot_data_scaling \
        --glob "results/datascale_5x5_2a_1L_n*" \
        --out results/data_scaling/data_scaling_curve.pdf
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

plt.rcParams.update({"font.family": "serif"})

ALGORITHMS = ["IQL", "VDN", "QMIX"]
ALGO_COLORS = {"IQL": "#4C78A8", "VDN": "#F58518", "QMIX": "#54A24B"}

# Two-sided t_{n-1, 0.025} for the small samples we use here.
_T = {5: 2.776, 10: 2.262, 14: 2.145, 15: 2.131, 29: 2.045, 30: 2.042, 44: 2.015}


def _t(n: int) -> float:
    if n <= 1:
        return 0.0
    return _T.get(n - 1, 1.96)


def _collect(pattern: str):
    """Return (per_algo, pooled).

    per_algo[n][algo] = {"train": [...], "test": [...]} over seeds;
    pooled[n]         = {"train": [...], "test": [...]} over all runs.
    """
    per_algo = defaultdict(lambda: defaultdict(lambda: {"train": [], "test": []}))
    pooled = defaultdict(lambda: {"train": [], "test": []})
    for f in glob.glob(f"{pattern}/runs/*/final_results.json"):
        m = re.search(r"_n(\d+)", f)
        if not m:
            continue
        n = int(m.group(1))
        d = json.loads(Path(f).read_text())
        algo = d.get("algo", "?")
        per_algo[n][algo]["train"].append(d["success_rate_train"])
        per_algo[n][algo]["test"].append(d["success_rate_test"])
        pooled[n]["train"].append(d["success_rate_train"])
        pooled[n]["test"].append(d["success_rate_test"])
    return per_algo, pooled


def _stats(vals):
    a = np.asarray(vals, dtype=float)
    n = len(a)
    mean = float(a.mean())
    ci = _t(n) * float(a.std(ddof=1)) / math.sqrt(n) if n > 1 else 0.0
    return mean, ci, n


def main() -> None:
    p = argparse.ArgumentParser(prog="plot_data_scaling")
    p.add_argument("--glob", default="results/datascale_5x5_2a_1L_n*")
    p.add_argument("--out", type=Path, default=Path("results/data_scaling/data_scaling_curve.pdf"))
    args = p.parse_args()

    per_algo, pooled = _collect(args.glob)
    if not pooled:
        print(f"[plot] no runs matched {args.glob!r}", file=sys.stderr)
        return
    sizes = sorted(pooled)

    # Console table (pooled over all algorithms and seeds, for the thesis numbers).
    print(f"{'#train':>7} {'runs':>5} {'train(CI95)':>16} {'test(CI95)':>16} {'gap':>6}")
    pooled_tr, pooled_trc, pooled_te, pooled_tec = [], [], [], []
    for n in sizes:
        trm, trc, k = _stats(pooled[n]["train"])
        tem, tec, _ = _stats(pooled[n]["test"])
        pooled_tr.append(trm); pooled_trc.append(trc)
        pooled_te.append(tem); pooled_tec.append(tec)
        print(f"{n:>7} {k:>5} {trm:>7.3f}+-{trc:<6.3f} {tem:>7.3f}+-{tec:<6.3f} {trm - tem:>6.3f}")

    x = np.asarray(sizes, dtype=float)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))

    # Per-algorithm means at each pool size (rows = algorithms).
    train_stack = np.array(
        [[float(np.mean(per_algo[n][a]["train"])) for n in sizes] for a in ALGORITHMS]
    )
    test_stack = np.array(
        [[float(np.mean(per_algo[n][a]["test"])) for n in sizes] for a in ALGORITHMS]
    )

    # Per-algorithm curves: colour = algorithm, solid = train, dashed = test.
    for i, algo in enumerate(ALGORITHMS):
        color = ALGO_COLORS[algo]
        ax.plot(x, train_stack[i], "-", color=color, lw=1.6, marker="o", ms=4)
        ax.plot(x, test_stack[i], "--", color=color, lw=1.6, marker="o", ms=4)

    ax.set_xscale("log")
    ax.set_xticks(sizes); ax.set_xticklabels([str(v) for v in sizes])
    ax.set_xlabel("Number of training levels")
    ax.set_ylabel("Exit rate")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Training-pool scaling closes the generalisation gap")

    # Two-dimensional legend: colour = algorithm, line style = pool
    # (solid = train, dashed = test).
    algo_handles = [Line2D([0], [0], color=ALGO_COLORS[a], lw=2, label=a) for a in ALGORITHMS]
    split_handles = [
        Line2D([0], [0], color="black", lw=2, linestyle="-", label="Train pool"),
        Line2D([0], [0], color="black", lw=2, linestyle="--", label="Test pool"),
    ]
    leg_algo = ax.legend(handles=algo_handles, loc="upper right", fontsize="small",
                         title="Algorithm", framealpha=0.9)
    ax.add_artist(leg_algo)
    ax.legend(handles=split_handles, loc="lower right", fontsize="small",
              title="Pool", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(args.out)
    plt.close(fig)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
