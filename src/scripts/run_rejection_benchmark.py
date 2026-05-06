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
from generators.constructive_solvable_generator import ConstructiveSolvableGenerator

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

MAX_TRIALS = 50               # number of accepted levels to find per (generator, size)
MAX_ATTEMPTS_PER_TRIAL = 500  # give up on a single trial after this many attempts

CONFIGS = [
    # (rows, cols, agents, lasers)
    (3, 3, 2, 1),
    (5, 5, 3, 2),
    (8, 8, 4, 3),
]

GENERATOR_SPECS = {
    "constrained_random_solvable": ConstrainedRandomSolvableGenerator,
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "constructive_solvable": ConstructiveSolvableGenerator,
    "constructive_cooperative": ConstructiveCooperativeGenerator,
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
        seed=42,
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
    results: dict = {}

    for gen_name, gen_cls in GENERATOR_SPECS.items():
        results[gen_name] = {}
        for rows, cols, agents, lasers in CONFIGS:
            size_key = f"{rows}x{cols}"
            print(f"  [{gen_name}] {size_key} ({agents} agents, {lasers} lasers) ...", flush=True)

            gen = _make_generator(gen_cls, rows, cols, agents, lasers)
            if gen is None:
                print("    -> skipped (generator init failed)")
                results[gen_name][size_key] = {"skipped": True}
                continue

            attempts_per_level: list[int] = []
            times_per_level: list[float] = []
            failed_trials = 0

            t_run_start = time.perf_counter()
            for trial in range(MAX_TRIALS):
                attempts = 0
                t_start = time.perf_counter()
                found = False

                while attempts < MAX_ATTEMPTS_PER_TRIAL:
                    attempts += 1
                    try:
                        gen.generate()
                        found = True
                        break
                    except RuntimeError:
                        if attempts % 100 == 0:
                            print(f"    trial {trial+1}/{MAX_TRIALS}: {attempts} attempts so far...", flush=True)

                t_elapsed = time.perf_counter() - t_start

                if found:
                    attempts_per_level.append(attempts)
                    times_per_level.append(t_elapsed)
                    if (trial + 1) % 10 == 0:
                        elapsed = time.perf_counter() - t_run_start
                        mean_so_far = float(np.mean(attempts_per_level))
                        print(
                            f"    {trial+1}/{MAX_TRIALS} trials done ({elapsed:.1f}s), "
                            f"mean attempts so far: {mean_so_far:.1f}",
                            flush=True,
                        )
                else:
                    failed_trials += 1
                    print(f"    trial {trial+1}/{MAX_TRIALS}: FAILED (>{MAX_ATTEMPTS_PER_TRIAL} attempts)", flush=True)

            successful = len(attempts_per_level)
            mean_attempts = float(np.mean(attempts_per_level)) if attempts_per_level else None
            rejection_rate = ((mean_attempts - 1) / mean_attempts) if mean_attempts else None

            print(
                f"    done: {successful}/{MAX_TRIALS} trials, "
                f"mean attempts={mean_attempts:.1f}" if mean_attempts else f"    done: {successful}/{MAX_TRIALS} trials"
            )

            results[gen_name][size_key] = {
                "successful_trials": successful,
                "failed_trials": failed_trials,
                "mean_attempts_per_level": mean_attempts,
                "std_attempts_per_level": float(np.std(attempts_per_level)) if attempts_per_level else None,
                "mean_time_per_level": float(np.mean(times_per_level)) if times_per_level else None,
                "rejection_rate": rejection_rate,
            }

    json_path = OUTPUT_DIR / "benchmark_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {json_path}")

    _make_plots(results)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _make_plots(results: dict):
    generators = list(results.keys())
    sizes = ["3x3", "5x5", "8x8"]
    x = np.arange(len(sizes))
    width = 0.18

    # --- Plot 1: Rejection rate by generator (derived from mean attempts) ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, gen in enumerate(generators):
        rates = []
        for size in sizes:
            data = results[gen].get(size, {})
            if data.get("skipped") or not data:
                rates.append(0.0)
            else:
                r = data.get("rejection_rate")
                rates.append((r * 100) if r is not None else 0.0)
        offset = (i - len(generators) / 2) * width + width / 2
        ax.bar(x + offset, rates, width, label=gen)

    ax.set_xlabel("Grid size")
    ax.set_ylabel("Rejection rate (%)")
    ax.set_title("Rejection Rate by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rejection_rate_by_generator.png", dpi=150)
    plt.close(fig)
    print("Saved rejection_rate_by_generator.png")

    # --- Plot 2: Mean time to find one accepted level ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, gen in enumerate(generators):
        times = []
        for size in sizes:
            data = results[gen].get(size, {})
            if data.get("skipped") or not data:
                times.append(0.0)
            else:
                t = data.get("mean_time_per_level")
                times.append(t if t is not None else 0.0)
        offset = (i - len(generators) / 2) * width + width / 2
        ax.bar(x + offset, times, width, label=gen)

    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean time to find one accepted level (s)")
    ax.set_title("Mean Time per Accepted Level by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "time_per_accepted_level.png", dpi=150)
    plt.close(fig)
    print("Saved time_per_accepted_level.png")

    # --- Plot 3: Mean attempts to find one accepted level ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, gen in enumerate(generators):
        attempts = []
        for size in sizes:
            data = results[gen].get(size, {})
            if data.get("skipped") or not data:
                attempts.append(0.0)
            else:
                a = data.get("mean_attempts_per_level")
                attempts.append(a if a is not None else 0.0)
        offset = (i - len(generators) / 2) * width + width / 2
        ax.bar(x + offset, attempts, width, label=gen)

    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean attempts to find one accepted level")
    ax.set_title("Mean Attempts per Accepted Level by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "mean_attempts_per_level.png", dpi=150)
    plt.close(fig)
    print("Saved mean_attempts_per_level.png")


if __name__ == "__main__":
    print("=== Rejection Rate Benchmark ===")
    run()
    print("Done.")
