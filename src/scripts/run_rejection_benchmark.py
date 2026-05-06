"""
Rejection rate benchmark.

For each generator type and grid size, runs up to ATTEMPTS generation attempts
(each with max_attempts=1) and records:
  - number of accepted levels
  - number of rejected levels
  - rejection rate
  - mean time per accepted level
  - mean time per rejected attempt

Each call to gen.generate() with max_attempts=1 is one attempt: it either
returns an accepted world or raises RuntimeError. This directly measures the
natural rejection rate of the generator without hiding retries inside it.

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

ATTEMPTS = 200       # total attempts per (generator, size)
MAX_ACCEPTED = 50    # stop early once this many levels are accepted

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
    t_max = max(rows * cols // 2, 8)
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

            times_accepted: list[float] = []
            times_rejected: list[float] = []
            accepted = 0

            for _ in range(ATTEMPTS):
                if accepted >= MAX_ACCEPTED:
                    break
                t_start = time.perf_counter()
                try:
                    gen.generate()
                    elapsed = time.perf_counter() - t_start
                    times_accepted.append(elapsed)
                    accepted += 1
                except RuntimeError:
                    elapsed = time.perf_counter() - t_start
                    times_rejected.append(elapsed)

            total = len(times_accepted) + len(times_rejected)
            rejection_rate = len(times_rejected) / max(1, total)

            print(
                f"    accepted={accepted}/{total} "
                f"({100 * (1 - rejection_rate):.1f}% accept rate)"
            )

            results[gen_name][size_key] = {
                "total_attempts": total,
                "accepted": len(times_accepted),
                "rejected": len(times_rejected),
                "rejection_rate": rejection_rate,
                "mean_time_accepted": float(np.mean(times_accepted)) if times_accepted else None,
                "mean_time_rejected": float(np.mean(times_rejected)) if times_rejected else None,
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

    # --- Plot 1: Rejection rate by generator ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, gen in enumerate(generators):
        rejection_rates = []
        for size in sizes:
            data = results[gen].get(size, {})
            if data.get("skipped") or not data:
                rejection_rates.append(0.0)
            else:
                rejection_rates.append(data.get("rejection_rate", 0.0) * 100)
        offset = (i - len(generators) / 2) * width + width / 2
        ax.bar(x + offset, rejection_rates, width, label=gen)

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

    # --- Plot 2: Mean time per accepted level ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, gen in enumerate(generators):
        times = []
        for size in sizes:
            data = results[gen].get(size, {})
            if data.get("skipped") or not data:
                times.append(0.0)
            else:
                t = data.get("mean_time_accepted")
                times.append(t if t is not None else 0.0)
        offset = (i - len(generators) / 2) * width + width / 2
        ax.bar(x + offset, times, width, label=gen)

    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean time per accepted level (s)")
    ax.set_title("Mean Time per Accepted Level by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "time_per_accepted_level.png", dpi=150)
    plt.close(fig)
    print("Saved time_per_accepted_level.png")


if __name__ == "__main__":
    print("=== Rejection Rate Benchmark ===")
    run()
    print("Done.")
