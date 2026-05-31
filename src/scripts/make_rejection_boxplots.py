"""Render the boxplot-style rejection figures embedded in the thesis.

Produces, with plain-number log axes, directly into
``results/rejection_benchmark/``:
  - mean_attempts_per_level_boxplot.{pdf,png}
  - time_per_accepted_level_boxplot.{pdf,png}

These are the boxplot counterparts of the bar charts emitted by
``run_rejection_benchmark.py`` and are the versions referenced from the
experiments chapter. Reads the per-trial arrays from
``results/rejection_benchmark/benchmark_results.json``.
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, LogLocator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from benchmark._plot_style import apply_thesis_style
from scripts.run_rejection_benchmark import GENERATOR_LABELS, _grouped_boxplot

apply_thesis_style()

OUT = ROOT / "results" / "rejection_benchmark"

REJ = json.load(open(OUT / "benchmark_results.json"))

sizes = ["3x3", "5x5", "8x8"]
x = np.arange(len(sizes))
generators = list(REJ.keys())
legend_labels = [GENERATOR_LABELS.get(g, g.replace("_", " ")) for g in generators]

_PLAIN = FuncFormatter(lambda v, _: f"{v:g}")


def plain_log_yaxis(ax):
    ax.yaxis.set_major_formatter(_PLAIN)
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=(2, 5), numticks=15))
    ax.yaxis.set_minor_formatter(_PLAIN)
    ax.tick_params(axis="y", which="minor", labelsize=6)


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)
    print("saved", name)


def rej_boxplot(raw_key, ylabel, title, name, legend_loc="upper right"):
    fig, ax = plt.subplots(figsize=(12, 7))
    handles = _grouped_boxplot(
        ax, REJ, generators, legend_labels, sizes, x,
        value_fn=lambda v: v, raw_key=raw_key,
    )
    ax.set_xlabel("Grid size")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(top=ax.get_ylim()[1] * 4)
    plain_log_yaxis(ax)
    ax.legend(handles=handles, loc=legend_loc)
    ax.grid(axis="y", which="major")
    save(fig, name)


if __name__ == "__main__":
    rej_boxplot("attempts_per_level_raw", "Attempts per accepted level",
                "Attempts per accepted level by generator and grid size",
                "mean_attempts_per_level_boxplot")
    rej_boxplot("times_per_level_raw", "Time to find one accepted level (s)",
                "Time to find one accepted level by generator and grid size",
                "time_per_accepted_level_boxplot", legend_loc="upper left")
    print("\nWrote boxplot variants to:", OUT)
