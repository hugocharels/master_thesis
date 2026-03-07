"""Benchmark runner: timing and clause counting across levels and methods."""

import numpy as np
from lle import World

from levels import LLE_LEVELS
from solver import LLEAdapter, WorldSolver
from solver.constraints.movements import METHOD_GLOBAL, METHOD_LOCAL

METHODS = {
    METHOD_LOCAL: "Local (neighbor exclusion)",
    METHOD_GLOBAL: "Global (all-pairs exclusion)",
}


def run_single(world: World, t_max: int, method: str) -> dict:
    """Run solver once with profiling. Returns profiling dict."""
    adapted = LLEAdapter(world)
    solver = WorldSolver(
        adapted,
        T_MAX=t_max,
        enable_profiling=True,
        movement_method=method,
    )
    result, _model = solver.solve()
    data = solver.get_profiling_data()
    data["satisfiable"] = result
    return data


def run_benchmark(num_runs=100):
    """
    Run the benchmark for all levels and methods.
    Returns a nested dict: results[method][level] = { ... }
    """
    results = {}

    for method_key, method_label in METHODS.items():
        results[method_key] = {}

        for level_num, (world, t_max) in LLE_LEVELS.items():
            print(f"  [{method_label}] Level {level_num}: ", end="", flush=True)

            first_run = run_single(world, t_max, method_key)
            total_clauses = first_run["total_clauses"]
            constraint_clauses = {}
            constraint_method_clauses = {}
            for cname, cdata in first_run["constraints"].items():
                constraint_clauses[cname] = cdata["num_clauses"]
                constraint_method_clauses[cname] = {
                    mname: mdata["clauses"]
                    for mname, mdata in cdata["method_profiles"].items()
                }

            gen_times = []
            solve_times = []
            for i in range(num_runs):
                data = run_single(world, t_max, method_key)
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
