"""Benchmark runner: timing and clause counting across levels and methods."""

from collections.abc import Iterable
from copy import deepcopy

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
    world.reset()
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


def _normalize_levels(levels):
    """
    Normalize different level inputs into iterable of (level_key, world, t_max).

    Supported inputs:
    - None -> uses LLE_LEVELS (dict-like level -> (world, t_max))
    - dict[level_key, (world, t_max)]
    - iterable of tuples:
        - (level_key, world, t_max)
        - (level_key, (world, t_max))
    """
    if levels is None:
        for level_key, (world, t_max) in LLE_LEVELS.items():
            yield level_key, world, t_max
        return

    if isinstance(levels, dict):
        for level_key, value in levels.items():
            if (
                isinstance(value, tuple)
                and len(value) == 2
                and isinstance(value[1], int)
            ):
                world, t_max = value
                yield level_key, world, t_max
            else:
                raise ValueError(
                    "Invalid dict value in levels. Expected (world, t_max)."
                )
        return

    if isinstance(levels, Iterable):
        for item in levels:
            if not isinstance(item, tuple):
                raise ValueError(
                    "Invalid iterable item in levels. Expected tuple entries."
                )

            if len(item) == 3:
                level_key, world, t_max = item
                if not isinstance(t_max, int):
                    raise ValueError("Invalid t_max in levels iterable entry.")
                yield level_key, world, t_max
            elif len(item) == 2:
                level_key, value = item
                if (
                    isinstance(value, tuple)
                    and len(value) == 2
                    and isinstance(value[1], int)
                ):
                    world, t_max = value
                    yield level_key, world, t_max
                else:
                    raise ValueError(
                        "Invalid 2-tuple levels entry. Expected "
                        "(level_key, (world, t_max))."
                    )
            else:
                raise ValueError(
                    "Invalid levels tuple length. Expected 2 or 3 elements."
                )
        return

    raise ValueError(
        "Unsupported levels format. Use None, dict, or iterable of tuples."
    )


def _fresh_world(world: World) -> World:
    """Return a fresh world instance for each benchmark run when possible."""
    # World.level(...) worlds are typically mutable during solve/reset;
    # deepcopy gives each run independent state for custom-built worlds too.
    return deepcopy(world)


def run_benchmark(num_runs=100, levels=None):
    """
    Run benchmark for all movement methods and provided levels.

    Parameters
    ----------
    num_runs : int
        Number of repeated timing runs per method/level.
    levels : None | dict | iterable
        If None, use LLE_LEVELS.
        Otherwise one of:
          - dict[level_key] = (world, t_max)
          - iterable of (level_key, world, t_max)
          - iterable of (level_key, (world, t_max))

    Returns
    -------
    dict
        Nested dict: results[method][level_key] = { ... }
    """
    level_entries = list(_normalize_levels(levels))
    results = {}

    for method_key, method_label in METHODS.items():
        results[method_key] = {}

        for level_key, world_template, t_max in level_entries:
            print(f"  [{method_label}] Level {level_key}: ", end="", flush=True)

            first_run = run_single(_fresh_world(world_template), t_max, method_key)
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
                data = run_single(_fresh_world(world_template), t_max, method_key)
                gen_times.append(data["total_generation_time"])
                solve_times.append(data["solve_time"])
                if (i + 1) % 10 == 0:
                    print(".", end="", flush=True)

            print(f" done ({num_runs} runs)")

            results[method_key][level_key] = {
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
