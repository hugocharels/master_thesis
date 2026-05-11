"""
Rejection rate benchmark.

For each generator type and grid size, runs MAX_TRIALS "find one level" trials.
Each trial calls gen.generate() (max_attempts=1) in a loop until one level is
accepted or MAX_ATTEMPTS_PER_TRIAL is exceeded.

This directly measures:
  - mean number of attempts needed to find one accepted level
  - mean time to find one accepted level

The rejection rate is derived as (mean_attempts - 1) / mean_attempts.

Results saved to results/rejection_benchmark/.
"""

import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.constrained_random_cooperative_generator import ConstrainedRandomCooperativeGenerator
from generators.constrained_random_solvable_generator import ConstrainedRandomSolvableGenerator
from generators.constructive_cooperative_generator import ConstructiveCooperativeGenerator
from generators.constructive_level6_style_generator import ConstructiveLevel6StyleGenerator
from generators.constructive_solvable_generator import ConstructiveSolvableGenerator

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

MAX_TRIALS = 200                    # number of accepted levels to find per (generator, size)
MAX_TRIALS_LARGE = 20               # reduced target for large grids (memory-leak-bound)
MAX_ATTEMPTS_PER_TRIAL = 500        # give up on a single trial after this many attempts
MAX_ATTEMPTS_PER_TRIAL_LARGE = 100  # faster give-up for large grids
TRIAL_TIMEOUT_LARGE = 30.0          # seconds: abort a large-grid trial if it exceeds this

CONFIGS = [
    # (rows, cols, agents, lasers, is_large)
    (3, 3, 2, 1, False),
    (5, 5, 3, 2, False),
    (8, 8, 4, 3, True),
]

GENERATOR_SPECS = {
    "constrained_random_solvable": ConstrainedRandomSolvableGenerator,
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "constructive_solvable": ConstructiveSolvableGenerator,
    "constructive_cooperative": ConstructiveCooperativeGenerator,
    "constructive_level6_style": ConstructiveLevel6StyleGenerator,
}

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results" / "rejection_benchmark"


# ---------------------------------------------------------------------------
# Generator factory
# ---------------------------------------------------------------------------

def _make_generator(cls, rows, cols, agents, lasers):
    """Create generator with max_attempts=1 so each generate() call = one attempt."""
    t_max = min(max(rows * cols // 2, 8), 20)
    common = dict(
        size=(rows, cols),
        agents=agents,
        lasers=lasers,
        t_max=t_max,
        max_attempts=1,
        seed=None,
    )
    try:
        return cls(**common)
    except (ValueError, TypeError):
        try:
            return cls(size=(rows, cols), agents=agents, lasers=lasers, t_max=t_max, max_attempts=1)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Main benchmark loop
# ---------------------------------------------------------------------------

def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "benchmark_results.json"

    # Resume: load any previously-saved configs.
    results: dict = {}
    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as f:
                results = json.load(f)
            n_saved = sum(len(v) for v in results.values())
            print(f"  Resumed from {json_path}: {n_saved} configs already saved", flush=True)
        except Exception as e:
            print(f"  Warning: could not load existing JSON ({e}); starting fresh", flush=True)
            results = {}

    for gen_name, gen_cls in GENERATOR_SPECS.items():
        if gen_name not in results:
            results[gen_name] = {}
        for rows, cols, agents, lasers, is_large in CONFIGS:
            size_key = f"{rows}x{cols}"
            if size_key in results[gen_name]:
                print(f"  [{gen_name}] {size_key}: SKIP (already in JSON)", flush=True)
                continue
            trials = MAX_TRIALS_LARGE if is_large else MAX_TRIALS
            print(f"  [{gen_name}] {size_key} ({agents} agents, {lasers} lasers, {trials} trials) ...", flush=True)

            gen = _make_generator(gen_cls, rows, cols, agents, lasers)
            if gen is None:
                print("    -> skipped (generator init failed)")
                results[gen_name][size_key] = {"skipped": True}
                continue

            attempts_per_level: list[int] = []
            times_per_level: list[float] = []
            failed_trials = 0

            max_att = MAX_ATTEMPTS_PER_TRIAL_LARGE if is_large else MAX_ATTEMPTS_PER_TRIAL
            timeout = TRIAL_TIMEOUT_LARGE if is_large else None

            t_run_start = time.perf_counter()
            for trial in range(trials):
                attempts = 0
                t_start = time.perf_counter()
                found = False
                timed_out = False

                while attempts < max_att:
                    if timeout and (time.perf_counter() - t_start) > timeout:
                        timed_out = True
                        break
                    attempts += 1
                    try:
                        gen.generate()
                        found = True
                        break
                    except RuntimeError:
                        if attempts % 50 == 0:
                            elapsed_so_far = time.perf_counter() - t_start
                            print(f"    trial {trial+1}/{trials}: {attempts} attempts ({elapsed_so_far:.1f}s)...", flush=True)

                t_elapsed = time.perf_counter() - t_start
                elapsed_total = time.perf_counter() - t_run_start

                if found:
                    attempts_per_level.append(attempts)
                    times_per_level.append(t_elapsed)
                    mean_so_far = float(np.mean(attempts_per_level))
                    print(
                        f"    [{trial+1:>2}/{trials}] OK  attempts={attempts:>4}  "
                        f"time={t_elapsed:.2f}s  mean_attempts={mean_so_far:.1f}  "
                        f"total_elapsed={elapsed_total:.1f}s",
                        flush=True,
                    )
                else:
                    failed_trials += 1
                    reason = f"timeout>{timeout:.0f}s" if timed_out else f">{max_att} attempts"
                    print(
                        f"    [{trial+1:>2}/{trials}] FAIL ({reason})  "
                        f"total_elapsed={elapsed_total:.1f}s",
                        flush=True,
                    )

            successful = len(attempts_per_level)
            mean_attempts = float(np.mean(attempts_per_level)) if attempts_per_level else None
            rejection_rate = ((mean_attempts - 1) / mean_attempts) if mean_attempts is not None else None

            if mean_attempts is not None:
                print(
                    f"    done: {successful}/{trials} trials ({failed_trials} failed), "
                    f"mean attempts={mean_attempts:.1f}, rejection rate={100*rejection_rate:.1f}%"
                )
            else:
                print(f"    done: {successful}/{trials} trials ({failed_trials} failed) — no data")

            results[gen_name][size_key] = {
                "successful_trials": successful,
                "failed_trials": failed_trials,
                "mean_attempts_per_level": mean_attempts,
                "std_attempts_per_level": float(np.std(attempts_per_level)) if attempts_per_level else None,
                "mean_time_per_level": float(np.mean(times_per_level)) if times_per_level else None,
                "rejection_rate": rejection_rate,
                "note": f"{failed_trials} trials exhausted budget and are excluded from mean_attempts" if failed_trials else None,
            }

            # Incremental save so a crash doesn't lose completed configs.
            json_path = OUTPUT_DIR / "benchmark_results.json"
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"    -> saved partial results to {json_path}", flush=True)

    json_path = OUTPUT_DIR / "benchmark_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {json_path}")

    try:
        _make_plots(results)
    except Exception as e:
        print(f"Warning: plot generation failed: {e}")


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

SOLVABLE_GENS = ["constrained_random_solvable", "constructive_solvable"]
COOPERATIVE_GENS = ["constrained_random_cooperative", "constructive_cooperative"]


def _failure_note(data: dict) -> str:
    failed = data.get("failed_trials") or 0
    successful = data.get("successful_trials") or 0
    total = failed + successful
    if failed and total:
        return f"{failed}/{total} failed"
    return ""


def _bar_with_failure_annotations(ax, x, values, errs, gens, sizes, results, width):
    for i, gen in enumerate(gens):
        offset = (i - len(gens) / 2) * width + width / 2
        bars = ax.bar(x + offset, values[i], width, yerr=errs[i], capsize=3, label=gen)
        for bar, size in zip(bars, sizes):
            note = _failure_note(results[gen].get(size, {}))
            if note:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    note,
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color="firebrick",
                )


def _make_plots(results: dict):
    sizes = ["3x3", "5x5", "8x8"]
    x = np.arange(len(sizes))
    width = 0.35

    # --- Plot 1: Rejection rate, single panel with value labels ---
    generators = list(results.keys())
    width1 = 0.18
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, gen in enumerate(generators):
        rates = [
            ((results[gen].get(s, {}).get("rejection_rate") or 0) * 100)
            for s in sizes
        ]
        offset = (i - len(generators) / 2) * width1 + width1 / 2
        bars = ax.bar(x + offset, rates, width1, label=gen)
        for bar, val in zip(bars, rates):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax.set_xlabel("Grid size")
    ax.set_ylabel("Rejection rate (%)")
    ax.set_title("Rejection Rate by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.set_ylim(0, 110)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rejection_rate_by_generator.png", dpi=150)
    plt.close(fig)
    print("Saved rejection_rate_by_generator.png")

    # --- Plot 2: Mean time to find one accepted level (log scale) ---
    fig, ax = plt.subplots(figsize=(12, 6))
    width2 = 0.18
    for i, gen in enumerate(generators):
        times = [
            (results[gen].get(s, {}).get("mean_time_per_level") or 1e-6)
            for s in sizes
        ]
        offset = (i - len(generators) / 2) * width2 + width2 / 2
        ax.bar(x + offset, times, width2, label=gen)
    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean time to find one accepted level, s (log scale)")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-3)
    ax.set_title("Mean Time per Accepted Level by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "time_per_accepted_level.png", dpi=150)
    plt.close(fig)
    print("Saved time_per_accepted_level.png")

    # --- Plot 3: Mean attempts (log scale, with std error bars and failure notes) ---
    fig, ax = plt.subplots(figsize=(12, 6))
    values, errs = [], []
    for gen in generators:
        means, stds = [], []
        for s in sizes:
            d = results[gen].get(s, {})
            means.append(d.get("mean_attempts_per_level") or 1)
            stds.append(d.get("std_attempts_per_level") or 0)
        values.append(means)
        errs.append(stds)
    _bar_with_failure_annotations(
        ax, x, values, errs, generators, sizes, results, width2
    )
    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean attempts (log scale)")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1)
    ax.set_title("Mean Attempts per Accepted Level by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "mean_attempts_per_level.png", dpi=150)
    plt.close(fig)
    print("Saved mean_attempts_per_level.png")


if __name__ == "__main__":
    print("=== Rejection Rate Benchmark ===")
    run()
    print("Done.")
