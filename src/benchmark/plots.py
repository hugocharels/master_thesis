"""Benchmark plotting functions."""

import os

import matplotlib.pyplot as plt
import numpy as np

from .runner import METHODS


def _sort_level_keys(level_keys):
    """Sort numeric keys numerically, otherwise sort by string representation."""
    return sorted(
        level_keys,
        key=lambda k: (
            not isinstance(k, (int, float)),
            float(k) if isinstance(k, (int, float)) else str(k),
        ),
    )


def _get_levels_from_results(results):
    """Extract ordered level keys from results."""
    first_method_key = next(iter(METHODS))
    return _sort_level_keys(results[first_method_key].keys())


def _level_label(level_key):
    """Human-readable level label."""
    if isinstance(level_key, (int, float)):
        return f"Level {level_key}"
    return str(level_key)


def _short_level_label(level_key):
    """Short label for dense axes/annotations."""
    if isinstance(level_key, (int, float)):
        return f"L{level_key}"
    return str(level_key)


def generate_all_plots(results, output_dir):
    """Generate all benchmark plots."""
    plot_clauses_per_level(results, output_dir)
    plot_clauses_breakdown(results, output_dir)
    plot_method_clauses_breakdown(results, output_dir)
    plot_times_per_level(results, output_dir)
    plot_total_time(results, output_dir)
    plot_clause_vs_time_scatter(results, output_dir)


def plot_clauses_per_level(results, output_dir):
    """Bar chart: total number of clauses per level, grouped by method."""
    levels = _get_levels_from_results(results)
    x = np.arange(len(levels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, (method_key, method_label) in enumerate(METHODS.items()):
        clauses = [results[method_key][lvl]["total_clauses"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        bars = ax.bar(x + offset, clauses, width, label=method_label)
        for bar, val in zip(bars, clauses):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_xlabel("Level")
    ax.set_ylabel("Number of Clauses")
    ax.set_title("Total Number of Clauses per Level")
    ax.set_xticks(x)
    ax.set_xticklabels([_level_label(lvl) for lvl in levels], rotation=20, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "clauses_per_level.png"), dpi=150)
    plt.close(fig)
    print("  -> clauses_per_level.png")


def plot_clauses_breakdown(results, output_dir):
    """Stacked bar chart: clause breakdown by constraint type, per level & method."""
    levels = _get_levels_from_results(results)
    all_constraint_names = set()
    for method_key in METHODS:
        for lvl in levels:
            all_constraint_names.update(
                results[method_key][lvl]["constraint_clauses"].keys()
            )
    constraint_names = sorted(all_constraint_names)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    for ax, (method_key, method_label) in zip(axes, METHODS.items()):
        x = np.arange(len(levels))
        bottom = np.zeros(len(levels))
        for cname in constraint_names:
            values = [
                results[method_key][lvl]["constraint_clauses"].get(cname, 0)
                for lvl in levels
            ]
            ax.bar(x, values, 0.6, label=cname, bottom=bottom)
            bottom += np.array(values)
        ax.set_xlabel("Level")
        ax.set_ylabel("Number of Clauses")
        ax.set_title(f"Clause Breakdown — {method_label}")
        ax.set_xticks(x)
        ax.set_xticklabels(
            [_short_level_label(lvl) for lvl in levels], rotation=20, ha="right"
        )
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "clauses_breakdown.png"), dpi=150)
    plt.close(fig)
    print("  -> clauses_breakdown.png")


def plot_method_clauses_breakdown(results, output_dir):
    """Stacked bar: clause breakdown by sub-method inside MovementConstraints."""
    levels = _get_levels_from_results(results)
    all_method_names = set()
    for method_key in METHODS:
        for lvl in levels:
            mc = results[method_key][lvl]["constraint_method_clauses"].get(
                "MovementConstraints", {}
            )
            all_method_names.update(mc.keys())
    method_names = sorted(all_method_names)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    for ax, (method_key, method_label) in zip(axes, METHODS.items()):
        x = np.arange(len(levels))
        bottom = np.zeros(len(levels))
        for mname in method_names:
            values = [
                results[method_key][lvl]["constraint_method_clauses"]
                .get("MovementConstraints", {})
                .get(mname, 0)
                for lvl in levels
            ]
            ax.bar(x, values, 0.6, label=mname, bottom=bottom)
            bottom += np.array(values)
        ax.set_xlabel("Level")
        ax.set_ylabel("Number of Clauses")
        ax.set_title(f"Movement Sub-Methods — {method_label}")
        ax.set_xticks(x)
        ax.set_xticklabels(
            [_short_level_label(lvl) for lvl in levels], rotation=20, ha="right"
        )
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "movement_methods_breakdown.png"), dpi=150)
    plt.close(fig)
    print("  -> movement_methods_breakdown.png")


def plot_times_per_level(results, output_dir):
    """Bar chart: mean generation time and solve time, grouped by method."""
    levels = _get_levels_from_results(results)
    x = np.arange(len(levels))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    for i, (method_key, method_label) in enumerate(METHODS.items()):
        means = [results[method_key][lvl]["mean_gen_time"] for lvl in levels]
        stds = [results[method_key][lvl]["std_gen_time"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        ax1.bar(x + offset, means, width, yerr=stds, label=method_label, capsize=3)
    ax1.set_xlabel("Level")
    ax1.set_ylabel("Time (seconds)")
    ax1.set_title("Mean Generation Time per Level")
    ax1.set_xticks(x)
    ax1.set_xticklabels([_level_label(lvl) for lvl in levels], rotation=20, ha="right")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    for i, (method_key, method_label) in enumerate(METHODS.items()):
        means = [results[method_key][lvl]["mean_solve_time"] for lvl in levels]
        stds = [results[method_key][lvl]["std_solve_time"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        ax2.bar(x + offset, means, width, yerr=stds, label=method_label, capsize=3)
    ax2.set_xlabel("Level")
    ax2.set_ylabel("Time (seconds)")
    ax2.set_title("Mean Solve Time per Level")
    ax2.set_xticks(x)
    ax2.set_xticklabels([_level_label(lvl) for lvl in levels], rotation=20, ha="right")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "times_per_level.png"), dpi=150)
    plt.close(fig)
    print("  -> times_per_level.png")


def plot_total_time(results, output_dir):
    """Bar chart: mean total time (gen + solve), grouped by method."""
    levels = _get_levels_from_results(results)
    x = np.arange(len(levels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, (method_key, method_label) in enumerate(METHODS.items()):
        gen_means = [results[method_key][lvl]["mean_gen_time"] for lvl in levels]
        solve_means = [results[method_key][lvl]["mean_solve_time"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        ax.bar(x + offset, gen_means, width, label=f"{method_label} — generation")
        ax.bar(
            x + offset,
            solve_means,
            width,
            bottom=gen_means,
            label=f"{method_label} — solve",
            alpha=0.7,
        )

    ax.set_xlabel("Level")
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Mean Total Time (Generation + Solve) per Level")
    ax.set_xticks(x)
    ax.set_xticklabels([_level_label(lvl) for lvl in levels], rotation=20, ha="right")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "total_time_per_level.png"), dpi=150)
    plt.close(fig)
    print("  -> total_time_per_level.png")


def plot_clause_vs_time_scatter(results, output_dir):
    """Scatter plot: clauses vs solve time for each level, colored by method."""
    levels = _get_levels_from_results(results)

    fig, ax = plt.subplots(figsize=(10, 6))
    for method_key, method_label in METHODS.items():
        clauses, solve_times, labels = [], [], []
        for lvl in levels:
            data = results[method_key][lvl]
            clauses.append(data["total_clauses"])
            solve_times.append(data["mean_solve_time"])
            labels.append(_short_level_label(lvl))
        ax.scatter(clauses, solve_times, s=100, label=method_label, zorder=5)
        for c, t, lbl in zip(clauses, solve_times, labels):
            ax.annotate(
                lbl, (c, t), textcoords="offset points", xytext=(5, 5), fontsize=9
            )

    ax.set_xlabel("Number of Clauses")
    ax.set_ylabel("Mean Solve Time (seconds)")
    ax.set_title("Clauses vs Solve Time")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "clause_vs_time_scatter.png"), dpi=150)
    plt.close(fig)
    print("  -> clause_vs_time_scatter.png")
