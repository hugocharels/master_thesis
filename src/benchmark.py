"""
Benchmark script to compare movement constraint methods across LLE levels 1-6.

Generates plots comparing:
  1. Number of clauses per level (by constraint type)
  2. Generation time per level (mean over N runs)
  3. Solve time per level (mean over N runs)
  4. Total time (generation + solve) per level
  5. Clause count breakdown by constraint method

Usage:
    python benchmark.py [--runs 100] [--output-dir plots]
"""

import argparse
import json
import os

import matplotlib.pyplot as plt
import numpy as np

from core import Agent, CellType, Direction, Entity, Laser, World
from solver.constraints.movements import METHOD_GLOBAL, METHOD_LOCAL
from solver.world_solver import WorldSolver

# ============================================================
# LLE Default Levels 1-6 definitions
# Each entry: (width, height, agents, exits, walls, lasers, T_MAX)
# ============================================================
LLE_LEVELS = {
    1: {
        "name": "Level 1 (1 agent, no lasers)",
        "width": 13,
        "height": 12,
        "agents": [(0, 7)],
        "exits": [(10, 7)],
        "walls": [],
        "lasers": [],
        "T_MAX": 10,
    },
    2: {
        "name": "Level 2 (2 agents, no lasers)",
        "width": 13,
        "height": 12,
        "agents": [(0, 6), (0, 7)],
        "exits": [(10, 6), (10, 7)],
        "walls": [],
        "lasers": [],
        "T_MAX": 10,
    },
    3: {
        "name": "Level 3 (2 agents, 1 laser)",
        "width": 13,
        "height": 12,
        "agents": [(0, 7), (0, 8)],
        "exits": [(10, 7), (10, 8)],
        "walls": [],
        "lasers": [(0, (4, 0), Direction.EAST)],
        "T_MAX": 10,
    },
    4: {
        "name": "Level 4 (2 agents, 2 lasers)",
        "width": 13,
        "height": 12,
        "agents": [(0, 7), (0, 8)],
        "exits": [(10, 7), (10, 8)],
        "walls": [],
        "lasers": [(0, (4, 0), Direction.EAST), (1, (6, 12), Direction.WEST)],
        "T_MAX": 10,
    },
    5: {
        "name": "Level 5 (4 agents, walls, 2 lasers)",
        "width": 13,
        "height": 12,
        "agents": [(0, 4), (0, 5), (0, 6), (0, 7)],
        "exits": [(10, 9), (10, 10), (11, 9), (11, 10)],
        "walls": [
            (3, 0),
            (3, 1),
            (4, 12),
            (4, 11),
            (4, 10),
            (4, 9),
            (4, 8),
            (4, 7),
            (7, 7),
            (8, 7),
            (8, 8),
            (8, 9),
            (8, 10),
            (8, 11),
            (8, 12),
        ],
        "lasers": [(1, (6, 12), Direction.WEST), (2, (0, 2), Direction.SOUTH)],
        "T_MAX": 19,
    },
    6: {
        "name": "Level 6 (4 agents, walls, 3 lasers)",
        "width": 13,
        "height": 12,
        "agents": [(0, 4), (0, 5), (0, 6), (0, 7)],
        "exits": [(10, 9), (10, 10), (11, 9), (11, 10)],
        "walls": [
            (3, 0),
            (3, 1),
            (4, 12),
            (4, 11),
            (4, 10),
            (4, 9),
            (4, 8),
            (4, 7),
            (7, 7),
            (8, 7),
            (8, 8),
            (8, 9),
            (8, 10),
            (8, 11),
            (8, 12),
        ],
        "lasers": [
            (1, (6, 12), Direction.WEST),
            (2, (0, 2), Direction.SOUTH),
            (0, (4, 0), Direction.EAST),
        ],
        "T_MAX": 20,
    },
}

METHODS = {
    METHOD_LOCAL: "Local (neighbor exclusion)",
    METHOD_GLOBAL: "Global (all-pairs exclusion)",
}


def make_world(level_def):
    """Build a World from a level definition dict."""
    world = World(level_def["width"], level_def["height"])
    for c, pos in enumerate(level_def["agents"]):
        world.add_entity(pos, Agent(c))
    for pos in level_def["exits"]:
        world.add_entity(pos, Entity(CellType.EXIT))
    for pos in level_def["walls"]:
        world.add_entity(pos, Entity(CellType.WALL))
    for c, pos, direction in level_def["lasers"]:
        world.add_entity(pos, Laser(c, direction=direction))
    return world


def run_single(level_def, method):
    """Run solver once with profiling. Returns profiling dict."""
    world = make_world(level_def)
    solver = WorldSolver(
        world,
        T_MAX=level_def["T_MAX"],
        enable_profiling=True,
        movement_method=method,
    )
    result, model = solver.solve()
    data = solver.get_profiling_data()
    data["satisfiable"] = result
    return data


def run_benchmark(num_runs=100):
    """
    Run the benchmark for all levels and methods.
    Returns a nested dict: results[method][level] = {clauses, gen_times, solve_times, ...}
    """
    results = {}

    for method_key, method_label in METHODS.items():
        results[method_key] = {}

        for level_num, level_def in LLE_LEVELS.items():
            print(f"  [{method_label}] Level {level_num}: ", end="", flush=True)

            # First run: get clause counts (deterministic, only need once)
            first_run = run_single(level_def, method_key)
            total_clauses = first_run["total_clauses"]
            constraint_clauses = {}
            constraint_method_clauses = {}
            for cname, cdata in first_run["constraints"].items():
                constraint_clauses[cname] = cdata["num_clauses"]
                constraint_method_clauses[cname] = {
                    mname: mdata["clauses"]
                    for mname, mdata in cdata["method_profiles"].items()
                }

            # Timing runs
            gen_times = []
            solve_times = []

            for i in range(num_runs):
                data = run_single(level_def, method_key)
                gen_times.append(data["total_generation_time"])
                solve_times.append(data["solve_time"])

                if (i + 1) % 10 == 0:
                    print(".", end="", flush=True)

            print(f" done ({num_runs} runs)")

            results[method_key][level_num] = {
                "total_clauses": total_clauses,
                "constraint_clauses": constraint_clauses,
                "constraint_method_clauses": constraint_method_clauses,
                "gen_times": gen_times,
                "solve_times": solve_times,
                "mean_gen_time": np.mean(gen_times),
                "std_gen_time": np.std(gen_times),
                "mean_solve_time": np.mean(solve_times),
                "std_solve_time": np.std(solve_times),
                "mean_total_time": np.mean(gen_times) + np.mean(solve_times),
                "satisfiable": first_run["satisfiable"],
            }

    return results


# ============================================================
# Plotting functions
# ============================================================


def plot_clauses_per_level(results, output_dir):
    """Bar chart: total number of clauses per level, grouped by method."""
    levels = sorted(LLE_LEVELS.keys())
    x = np.arange(len(levels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, (method_key, method_label) in enumerate(METHODS.items()):
        clauses = [results[method_key][lvl]["total_clauses"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        bars = ax.bar(x + offset, clauses, width, label=method_label)
        # Add value labels on bars
        for bar, val in zip(bars, clauses):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_xlabel("LLE Level")
    ax.set_ylabel("Number of Clauses")
    ax.set_title("Total Number of Clauses per Level")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Level {lvl}" for lvl in levels])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "clauses_per_level.png"), dpi=150)
    plt.close(fig)
    print("  -> clauses_per_level.png")


def plot_clauses_breakdown(results, output_dir):
    """Stacked bar chart: clause breakdown by constraint type, per level & method."""
    levels = sorted(LLE_LEVELS.keys())

    # Collect all constraint names (union across all runs)
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

        ax.set_xlabel("LLE Level")
        ax.set_ylabel("Number of Clauses")
        ax.set_title(f"Clause Breakdown — {method_label}")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Lvl {lvl}" for lvl in levels])
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "clauses_breakdown.png"), dpi=150)
    plt.close(fig)
    print("  -> clauses_breakdown.png")


def plot_method_clauses_breakdown(results, output_dir):
    """Stacked bar: clause breakdown by sub-method inside MovementConstraints."""
    levels = sorted(LLE_LEVELS.keys())

    # Collect all sub-method names from MovementConstraints
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

        ax.set_xlabel("LLE Level")
        ax.set_ylabel("Number of Clauses")
        ax.set_title(f"Movement Sub-Methods — {method_label}")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Lvl {lvl}" for lvl in levels])
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "movement_methods_breakdown.png"), dpi=150)
    plt.close(fig)
    print("  -> movement_methods_breakdown.png")


def plot_times_per_level(results, output_dir):
    """Bar chart: mean generation time and solve time, grouped by method."""
    levels = sorted(LLE_LEVELS.keys())
    x = np.arange(len(levels))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Generation time
    for i, (method_key, method_label) in enumerate(METHODS.items()):
        means = [results[method_key][lvl]["mean_gen_time"] for lvl in levels]
        stds = [results[method_key][lvl]["std_gen_time"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        ax1.bar(x + offset, means, width, yerr=stds, label=method_label, capsize=3)

    ax1.set_xlabel("LLE Level")
    ax1.set_ylabel("Time (seconds)")
    ax1.set_title("Mean Generation Time per Level")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Level {lvl}" for lvl in levels])
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    # Solve time
    for i, (method_key, method_label) in enumerate(METHODS.items()):
        means = [results[method_key][lvl]["mean_solve_time"] for lvl in levels]
        stds = [results[method_key][lvl]["std_solve_time"] for lvl in levels]
        offset = (i - 0.5) * width + width / 2
        ax2.bar(x + offset, means, width, yerr=stds, label=method_label, capsize=3)

    ax2.set_xlabel("LLE Level")
    ax2.set_ylabel("Time (seconds)")
    ax2.set_title("Mean Solve Time per Level")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"Level {lvl}" for lvl in levels])
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "times_per_level.png"), dpi=150)
    plt.close(fig)
    print("  -> times_per_level.png")


def plot_total_time(results, output_dir):
    """Bar chart: mean total time (gen + solve), grouped by method."""
    levels = sorted(LLE_LEVELS.keys())
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

    ax.set_xlabel("LLE Level")
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Mean Total Time (Generation + Solve) per Level")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Level {lvl}" for lvl in levels])
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "total_time_per_level.png"), dpi=150)
    plt.close(fig)
    print("  -> total_time_per_level.png")


def plot_clause_vs_time_scatter(results, output_dir):
    """Scatter plot: clauses vs solve time for each level, colored by method."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for method_key, method_label in METHODS.items():
        clauses = []
        solve_times = []
        labels = []
        for lvl in sorted(LLE_LEVELS.keys()):
            data = results[method_key][lvl]
            clauses.append(data["total_clauses"])
            solve_times.append(data["mean_solve_time"])
            labels.append(f"L{lvl}")

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


def print_summary_table(results):
    """Print a nice summary table to the console."""
    levels = sorted(LLE_LEVELS.keys())

    print("\n" + "=" * 90)
    print(
        f"{'Level':<10} {'Method':<30} {'Clauses':>10} {'Gen (s)':>12} {'Solve (s)':>12} {'Total (s)':>12}"
    )
    print("=" * 90)

    for lvl in levels:
        for method_key, method_label in METHODS.items():
            data = results[method_key][lvl]
            print(
                f"{'Lvl ' + str(lvl):<10} "
                f"{method_label:<30} "
                f"{data['total_clauses']:>10,} "
                f"{data['mean_gen_time']:>12.4f} "
                f"{data['mean_solve_time']:>12.4f} "
                f"{data['mean_total_time']:>12.4f}"
            )
        print("-" * 90)


def save_results_json(results, output_dir):
    """Save raw benchmark results as JSON for later use."""
    # Convert numpy types to native Python for JSON serialization
    serializable = {}
    for method_key, method_data in results.items():
        serializable[method_key] = {}
        for lvl, data in method_data.items():
            serializable[method_key][str(lvl)] = {
                "total_clauses": data["total_clauses"],
                "constraint_clauses": data["constraint_clauses"],
                "constraint_method_clauses": data["constraint_method_clauses"],
                "mean_gen_time": float(data["mean_gen_time"]),
                "std_gen_time": float(data["std_gen_time"]),
                "mean_solve_time": float(data["mean_solve_time"]),
                "std_solve_time": float(data["std_solve_time"]),
                "mean_total_time": float(data["mean_total_time"]),
                "satisfiable": data["satisfiable"],
            }

    filepath = os.path.join(output_dir, "benchmark_results.json")
    with open(filepath, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"  -> benchmark_results.json")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark movement constraint methods"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=100,
        help="Number of timing runs per level/method (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_plots",
        help="Directory to save plots (default: benchmark_plots)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running benchmark: {args.runs} timing runs per level/method")
    print(f"Output directory: {output_dir}\n")

    results = run_benchmark(num_runs=args.runs)

    print_summary_table(results)

    print("\nGenerating plots...")
    plot_clauses_per_level(results, output_dir)
    plot_clauses_breakdown(results, output_dir)
    plot_method_clauses_breakdown(results, output_dir)
    plot_times_per_level(results, output_dir)
    plot_total_time(results, output_dir)
    plot_clause_vs_time_scatter(results, output_dir)
    save_results_json(results, output_dir)

    print(f"\nAll plots saved to {output_dir}/")


if __name__ == "__main__":
    main()
