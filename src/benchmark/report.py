"""Benchmark reporting: console table and JSON export."""

import json
import os

from levels import LLE_LEVELS

from .runner import METHODS


def print_summary_table(results):
    """Print a summary table to the console."""
    levels = sorted(LLE_LEVELS.keys())

    print("\n" + "=" * 90)
    print(
        f"{'Level':<10} {'Method':<30} {'Clauses':>10} "
        f"{'Gen (s)':>12} {'Solve (s)':>12} {'Total (s)':>12}"
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
    print("  -> benchmark_results.json")
