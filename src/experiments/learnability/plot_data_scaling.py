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

plt.rcParams.update({"font.family": "serif"})

# Two-sided t_{n-1, 0.025} for the small samples we use here.
_T = {5: 2.776, 10: 2.262, 14: 2.145, 15: 2.131, 29: 2.045, 30: 2.042, 44: 2.015}


def _t(n: int) -> float:
    if n <= 1:
        return 0.0
    return _T.get(n - 1, 1.96)


def _collect(pattern: str):
    data = defaultdict(lambda: {"train": [], "test": []})
    for f in glob.glob(f"{pattern}/runs/*/final_results.json"):
        m = re.search(r"_n(\d+)", f)
        if not m:
            continue
        n = int(m.group(1))
        d = json.loads(Path(f).read_text())
        data[n]["train"].append(d["success_rate_train"])
        data[n]["test"].append(d["success_rate_test"])
    return data


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

    data = _collect(args.glob)
    if not data:
        print(f"[plot] no runs matched {args.glob!r}", file=sys.stderr)
        return
    sizes = sorted(data)

    rows = []
    for n in sizes:
        trm, trc, k = _stats(data[n]["train"])
        tem, tec, _ = _stats(data[n]["test"])
        rows.append((n, k, trm, trc, tem, tec))

    # Console table (for the thesis numbers).
    print(f"{'#train':>7} {'runs':>5} {'train(CI95)':>16} {'test(CI95)':>16} {'gap':>6}")
    for n, k, trm, trc, tem, tec in rows:
        print(f"{n:>7} {k:>5} {trm:>7.3f}+-{trc:<6.3f} {tem:>7.3f}+-{tec:<6.3f} {trm - tem:>6.3f}")

    x = [r[0] for r in rows]
    tr = [r[2] for r in rows]; trc = [r[3] for r in rows]
    te = [r[4] for r in rows]; tec = [r[5] for r in rows]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, tr, "o--", color="#4C78A8", label="train pool")
    ax.fill_between(x, np.array(tr) - np.array(trc), np.array(tr) + np.array(trc),
                    color="#4C78A8", alpha=0.18)
    ax.plot(x, te, "o-", color="#F58518", label="held-out test pool")
    ax.fill_between(x, np.array(te) - np.array(tec), np.array(te) + np.array(tec),
                    color="#F58518", alpha=0.18)
    ax.set_xscale("log")
    ax.set_xticks(x); ax.set_xticklabels([str(v) for v in x])
    ax.set_xlabel("number of training levels")
    ax.set_ylabel("success rate (greedy exit rate)")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Training-pool scaling closes the generalisation gap (5×5 / 2a / 1L)")
    ax.legend(loc="upper left")
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(args.out)
    plt.close(fig)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
