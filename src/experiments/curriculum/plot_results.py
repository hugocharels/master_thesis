"""Plotting helpers for the curriculum-transfer MARL experiment (Phase 8.1).

Reads per-run artefacts written by :mod:`experiments.curriculum.run_experiment`
under ``{out_dir}/runs/{condition}_{algo}_seed{N}/`` and produces four PDF
figures for the thesis:

    - ``learning_curves_level6.pdf``  success rate on Level 6 vs. training step,
      one line per condition (mean +/- seed std band).
    - ``stage_progression.pdf``       step plot of curriculum stage id over
      time, one line per CURR seed.
    - ``final_success_rates.pdf``     bar chart of final Level-6 success rate,
      one bar per condition (error bar = seed std).
    - ``exp1_learnability.pdf``       bar chart of held-out-pool success rate
      for the B1 condition, one bar per algorithm (IQL, VDN, QMIX).

All helpers are robust to missing / partial run data: a missing CSV / JSON
prints a warning to stderr and skips the affected element rather than
raising. When called with an empty or non-existent ``runs_dir`` they
gracefully no-op (after still ``mkdir``-ing the output directory).

The Agg backend is forced *before* :mod:`matplotlib.pyplot` is imported so
the module renders headlessly on Windows / CI without a DISPLAY.

Strategy for uneven seed row counts in :func:`plot_learning_curves`:
    we truncate to the minimum row count across seeds. This keeps the mean
    and the std band well-defined at every step we plot. (The alternative
    of NaN-padding + ``np.nanmean`` is a one-liner change if a future
    figure ever needs the longer tail.)
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # noqa: E402 -- must run before pyplot import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


CONDITIONS: tuple[str, ...] = ("B3", "B1", "B2", "CURR")
"""Plot order for conditions (matches the thesis colour ordering)."""

ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")

CONDITION_COLORS: dict[str, str] = {
    "B3": "#888888",  # grey
    "B1": "#1f77b4",  # blue
    "B2": "#ff7f0e",  # orange
    "CURR": "#2ca02c",  # green
}

CONDITION_LABELS: dict[str, str] = {
    "B3": "B3 (Level 6 only)",
    "B1": "B1 (target only)",
    "B2": "B2 (mixed bag)",
    "CURR": "CURR (curriculum)",
}

ALGO_COLORS: dict[str, str] = {
    "IQL": "#4C78A8",
    "VDN": "#F58518",
    "QMIX": "#54A24B",
}

# Match {condition}_{algo}_seed{N}: condition is one of CONDITIONS,
# algo is one of ALGORITHMS, seed is a non-negative integer.
_RUN_DIR_RE = re.compile(
    r"^(?P<condition>B1|B2|B3|CURR)_(?P<algo>QMIX|VDN|IQL)_seed(?P<seed>\d+)$"
)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _iter_run_dirs(runs_dir: Path):
    """Yield ``(condition, algo, seed, path)`` for every well-formed run dir."""
    if not runs_dir.exists() or not runs_dir.is_dir():
        return
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        m = _RUN_DIR_RE.match(entry.name)
        if not m:
            continue
        yield m["condition"], m["algo"], int(m["seed"]), entry


def _read_level6_eval_csv(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Return ``(steps, success_rates)`` or ``None`` on missing / empty file."""
    if not path.exists():
        return None
    steps: list[int] = []
    sr: list[float] = []
    try:
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    steps.append(int(row["step"]))
                    sr.append(float(row["success_rate"]))
                except (KeyError, ValueError):
                    continue
    except OSError as e:
        print(f"[plot_results] WARN: failed to read {path}: {e}", file=sys.stderr)
        return None
    if not steps:
        return None
    return np.asarray(steps, dtype=np.int64), np.asarray(sr, dtype=np.float64)


def _read_stage_progress_csv(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Return ``(steps, stage_ids)`` or ``None`` if the file has no data rows."""
    if not path.exists():
        return None
    steps: list[int] = []
    stage_ids: list[int] = []
    try:
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    steps.append(int(row["step"]))
                    stage_ids.append(int(row["stage_id"]))
                except (KeyError, ValueError):
                    continue
    except OSError as e:
        print(f"[plot_results] WARN: failed to read {path}: {e}", file=sys.stderr)
        return None
    if not steps:
        return None
    return np.asarray(steps, dtype=np.int64), np.asarray(stage_ids, dtype=np.int64)


def _read_final_results_json(path: Path) -> dict | None:
    """Return the parsed JSON or ``None`` if missing / unreadable."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[plot_results] WARN: failed to read {path}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Plot 1 -- learning curves on Level 6
# ---------------------------------------------------------------------------


def plot_learning_curves(runs_dir: Path, out_path: Path) -> None:
    """Aggregate ``level6_eval.csv`` per condition (QMIX only) and plot.

    Each line shows the per-step mean success rate across seeds with a
    shaded band of +/- 1 std. Seeds with shorter histories are truncated
    to the shared minimum length (see module docstring).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Group seeds per condition (QMIX only for the main learning-curves
    # figure; the per-algo comparison lives in exp1_learnability).
    per_condition: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
        c: [] for c in CONDITIONS
    }
    for condition, algo, _seed, run_dir in _iter_run_dirs(runs_dir):
        if algo != "QMIX":
            continue
        data = _read_level6_eval_csv(run_dir / "level6_eval.csv")
        if data is None:
            print(
                f"[plot_results] WARN: no level6_eval.csv data in {run_dir.name}",
                file=sys.stderr,
            )
            continue
        per_condition[condition].append(data)

    if not any(per_condition.values()):
        print(
            "[plot_results] WARN: no level6_eval.csv data found, "
            "skipping learning_curves_level6.pdf",
            file=sys.stderr,
        )
        return

    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    plotted_any = False
    for condition in CONDITIONS:
        seed_data = per_condition[condition]
        if not seed_data:
            continue
        # Truncate every seed to the shortest history so element-wise
        # mean / std are well-defined at every plotted step.
        min_len = min(len(steps) for steps, _ in seed_data)
        if min_len == 0:
            continue
        steps_ref = seed_data[0][0][:min_len]
        sr_matrix = np.vstack([sr[:min_len] for _, sr in seed_data])
        mean = sr_matrix.mean(axis=0)
        std = sr_matrix.std(axis=0)
        color = CONDITION_COLORS[condition]
        label = f"{CONDITION_LABELS[condition]} (n={sr_matrix.shape[0]})"
        ax.plot(steps_ref, mean, label=label, color=color, linewidth=1.8)
        ax.fill_between(steps_ref, mean - std, mean + std, color=color, alpha=0.18)
        plotted_any = True

    if not plotted_any:
        plt.close(fig)
        print(
            "[plot_results] WARN: no plottable learning-curve data; "
            "skipping learning_curves_level6.pdf",
            file=sys.stderr,
        )
        return

    ax.set_xlabel("Training steps")
    ax.set_ylabel("Success rate on Level 6")
    ax.set_title("Learning curves on hand-crafted Level 6 (QMIX)")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Plot 2 -- curriculum stage progression
# ---------------------------------------------------------------------------


def plot_stage_progression(runs_dir: Path, out_path: Path) -> None:
    """Plot the curriculum stage id over training step, one line per CURR seed.

    Skipped (no figure written) when there is no CURR run with non-empty
    ``stage_progress.csv``.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    series: list[tuple[int, np.ndarray, np.ndarray]] = []  # (seed, steps, ids)
    for condition, algo, seed, run_dir in _iter_run_dirs(runs_dir):
        if condition != "CURR" or algo != "QMIX":
            continue
        data = _read_stage_progress_csv(run_dir / "stage_progress.csv")
        if data is None:
            continue
        series.append((seed, data[0], data[1]))

    if not series:
        print(
            "[plot_results] WARN: no CURR_QMIX stage_progress.csv data; "
            "skipping stage_progression.pdf",
            file=sys.stderr,
        )
        return

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    cmap = plt.get_cmap("viridis")
    n = len(series)
    for i, (seed, steps, ids) in enumerate(series):
        color = cmap(0.15 + 0.7 * (i / max(1, n - 1))) if n > 1 else cmap(0.5)
        ax.step(steps, ids, where="post", label=f"seed {seed}", color=color, linewidth=1.6)

    ax.set_xlabel("Training steps")
    ax.set_ylabel("Curriculum stage id")
    ax.set_title("Curriculum stage progression (CURR, QMIX)")
    ax.set_yticks([1, 2, 3, 4])
    ax.set_ylim(0.5, 4.5)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Plot 3 -- final success rates per condition
# ---------------------------------------------------------------------------


def plot_final_success_rates(runs_dir: Path, out_path: Path) -> None:
    """Bar chart of final Level-6 success rate (QMIX), one bar per condition.

    Bars are ordered ``B3, B1, B2, CURR``. Error bars are the std of
    ``success_rate_level6`` across seeds. Conditions with no data are
    omitted.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    per_condition: dict[str, list[float]] = {c: [] for c in CONDITIONS}
    for condition, algo, _seed, run_dir in _iter_run_dirs(runs_dir):
        if algo != "QMIX":
            continue
        payload = _read_final_results_json(run_dir / "final_results.json")
        if payload is None:
            continue
        sr = payload.get("success_rate_level6")
        if sr is None:
            continue
        try:
            per_condition[condition].append(float(sr))
        except (TypeError, ValueError):
            continue

    present = [c for c in CONDITIONS if per_condition[c]]
    if not present:
        print(
            "[plot_results] WARN: no final_results.json data; "
            "skipping final_success_rates.pdf",
            file=sys.stderr,
        )
        return

    means = [float(np.mean(per_condition[c])) for c in present]
    stds = [
        float(np.std(per_condition[c])) if len(per_condition[c]) > 1 else 0.0
        for c in present
    ]
    colors = [CONDITION_COLORS[c] for c in present]
    counts = [len(per_condition[c]) for c in present]

    fig, ax = plt.subplots(figsize=(6.0, 4.5))
    x = np.arange(len(present))
    ax.bar(
        x,
        means,
        yerr=stds,
        color=colors,
        edgecolor="#444444",
        linewidth=0.8,
        capsize=4,
        alpha=0.85,
    )
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c}\n(n={n})" for c, n in zip(present, counts)])
    ax.set_ylabel("Final success rate on Level 6")
    ax.set_title("Final Level-6 success rate by condition (QMIX)")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Plot 4 -- experiment 1 learnability (B1, all 3 algorithms)
# ---------------------------------------------------------------------------


def plot_exp1_learnability(runs_dir: Path, out_path: Path) -> None:
    """Bar chart of B1 ``success_rate_held_out_pool`` per algorithm.

    Algorithms with no B1 run, or B1 runs whose
    ``success_rate_held_out_pool`` is missing or null, are omitted.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    per_algo: dict[str, list[float]] = {a: [] for a in ALGORITHMS}
    for condition, algo, _seed, run_dir in _iter_run_dirs(runs_dir):
        if condition != "B1":
            continue
        payload = _read_final_results_json(run_dir / "final_results.json")
        if payload is None:
            continue
        sr = payload.get("success_rate_held_out_pool")
        if sr is None:
            continue
        try:
            per_algo[algo].append(float(sr))
        except (TypeError, ValueError):
            continue

    present = [a for a in ALGORITHMS if per_algo[a]]
    if not present:
        print(
            "[plot_results] WARN: no B1 success_rate_held_out_pool data; "
            "skipping exp1_learnability.pdf",
            file=sys.stderr,
        )
        return

    means = [float(np.mean(per_algo[a])) for a in present]
    stds = [
        float(np.std(per_algo[a])) if len(per_algo[a]) > 1 else 0.0 for a in present
    ]
    colors = [ALGO_COLORS[a] for a in present]
    counts = [len(per_algo[a]) for a in present]

    fig, ax = plt.subplots(figsize=(6.0, 4.5))
    x = np.arange(len(present))
    ax.bar(
        x,
        means,
        yerr=stds,
        color=colors,
        edgecolor="#444444",
        linewidth=0.8,
        capsize=4,
        alpha=0.85,
    )
    ax.set_xticks(x)
    ax.set_xticklabels([f"{a}\n(n={n})" for a, n in zip(present, counts)])
    ax.set_ylabel("Success rate on held-out generated pool")
    ax.set_title("Experiment 1: B1 learnability on the held-out pool")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_all_figures(runs_dir: Path, out_dir: Path) -> None:
    """Generate all 4 PDFs into ``out_dir`` (created if needed).

    Each helper is robust to missing data: partial pilots produce
    partial figures; an empty ``runs_dir`` yields warnings on stderr but
    does not raise.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_learning_curves(runs_dir, out_dir / "learning_curves_level6.pdf")
    plot_stage_progression(runs_dir, out_dir / "stage_progression.pdf")
    plot_final_success_rates(runs_dir, out_dir / "final_success_rates.pdf")
    plot_exp1_learnability(runs_dir, out_dir / "exp1_learnability.pdf")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    generate_all_figures(
        Path("results/curriculum_experiment/runs"),
        Path("results/curriculum_experiment/figures"),
    )
