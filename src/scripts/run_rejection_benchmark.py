"""
Rejection rate benchmark.

For each generator type and grid size, runs 200 generation attempts and records:
  - number of accepted levels
  - number of rejected levels
  - rejection reason breakdown
  - mean time per accepted level
  - mean time per rejected attempt

Results saved to results/rejection_benchmark/.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Ensure src/ is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.constrained_random_cooperative_generator import ConstrainedRandomCooperativeGenerator
from generators.constrained_random_solvable_generator import ConstrainedRandomSolvableGenerator
from generators.constructive_cooperative_generator import ConstructiveCooperativeGenerator
from generators.constructive_solvable_generator import ConstructiveSolvableGenerator
from generators.random_cooperative_generator import RandomCooperativeGenerator
from generators.random_solvable_generator import RandomSolvableGenerator

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

ATTEMPTS = 200

CONFIGS = [
    # (rows, cols, agents, lasers)
    (3, 3, 2, 1),
    (5, 5, 3, 2),
    (8, 8, 4, 3),
]

GENERATOR_SPECS = {
    "random_solvable": RandomSolvableGenerator,
    "constrained_random_solvable": ConstrainedRandomSolvableGenerator,
    "random_cooperative": RandomCooperativeGenerator,
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "constructive_solvable": ConstructiveSolvableGenerator,
    "constructive_cooperative": ConstructiveCooperativeGenerator,
}

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results" / "rejection_benchmark"


# ---------------------------------------------------------------------------
# Instrumented generator that intercepts accept/reject decisions
# ---------------------------------------------------------------------------

class InstrumentedGenerator:
    """Wraps a generator to record per-attempt outcomes without modifying it."""

    def __init__(self, generator):
        self._gen = generator
        self.attempts: list[dict] = []

    def run_attempts(self, num_attempts: int):
        gen = self._gen

        for attempt_idx in range(num_attempts):
            t_start = time.perf_counter()
            outcome = {"accepted": False, "reason": "", "elapsed": 0.0}

            layout = gen._make_candidate_layout() if hasattr(gen, "_make_candidate_layout") else None
            if layout is not None:
                valid, reason = gen.validate_candidate(layout) if hasattr(gen, "validate_candidate") else (True, "ok")
                if not valid:
                    outcome["reason"] = f"layout:{reason}"
                    outcome["elapsed"] = time.perf_counter() - t_start
                    self.attempts.append(outcome)
                    continue
                try:
                    world = gen._build_world_from_layout(layout) if hasattr(gen, "_build_world_from_layout") else gen.generate()
                except Exception as exc:
                    outcome["reason"] = f"build_error:{type(exc).__name__}"
                    outcome["elapsed"] = time.perf_counter() - t_start
                    self.attempts.append(outcome)
                    continue
            else:
                outcome["reason"] = "layout:none"
                outcome["elapsed"] = time.perf_counter() - t_start
                self.attempts.append(outcome)
                continue

            try:
                accepted, reason = gen._accept_world(world)
            except Exception as exc:
                outcome["reason"] = f"solver_error:{type(exc).__name__}"
                outcome["elapsed"] = time.perf_counter() - t_start
                self.attempts.append(outcome)
                continue

            outcome["elapsed"] = time.perf_counter() - t_start
            if accepted:
                outcome["accepted"] = True
                outcome["reason"] = reason
            else:
                outcome["reason"] = reason

            self.attempts.append(outcome)

    def summarize(self) -> dict:
        accepted = [a for a in self.attempts if a["accepted"]]
        rejected = [a for a in self.attempts if not a["accepted"]]

        reason_counts: dict[str, int] = defaultdict(int)
        for a in rejected:
            # Normalize reason to a top-level bucket
            raw = a["reason"]
            if raw.startswith("layout:"):
                bucket = "layout_invalid"
            elif raw.startswith("build_error:"):
                bucket = "build_error"
            elif raw.startswith("solver_error:"):
                bucket = "solver_error"
            elif "outside_difficulty" in raw:
                bucket = "difficulty_window"
            elif "profile" in raw:
                bucket = "wrong_profile"
            else:
                bucket = raw[:40]
            reason_counts[bucket] += 1

        return {
            "total_attempts": len(self.attempts),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "rejection_rate": len(rejected) / max(1, len(self.attempts)),
            "mean_time_accepted": float(np.mean([a["elapsed"] for a in accepted])) if accepted else None,
            "mean_time_rejected": float(np.mean([a["elapsed"] for a in rejected])) if rejected else None,
            "rejection_reasons": dict(reason_counts),
        }


# ---------------------------------------------------------------------------
# Main benchmark loop
# ---------------------------------------------------------------------------

def _make_generator(cls, rows, cols, agents, lasers):
    common = dict(
        size=(rows, cols),
        agents=agents,
        lasers=lasers,
        t_max=max(rows * cols // 2, 8),
        max_attempts=1,  # We drive the loop ourselves
        seed=42,
    )
    try:
        return cls(**common)
    except (ValueError, TypeError):
        # Some generators may not accept all kwargs
        try:
            return cls(size=(rows, cols), agents=agents, lasers=lasers, t_max=common["t_max"], max_attempts=1)
        except Exception:
            return None


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

            # Enable debug output suppression
            gen.debug_rejections = False if hasattr(gen, "debug_rejections") else None

            instrumented = InstrumentedGenerator(gen)
            instrumented.run_attempts(ATTEMPTS)
            summary = instrumented.summarize()

            print(
                f"    accepted={summary['accepted']}/{summary['total_attempts']} "
                f"({100*(1-summary['rejection_rate']):.1f}% accept rate)"
            )
            results[gen_name][size_key] = summary

    # Save JSON
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
    width = 0.12

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

    # --- Plot 2: Time per accepted level ---
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

    # --- Plot 3: Rejection reason stacked bar ---
    all_reasons: set[str] = set()
    for gen_data in results.values():
        for size_data in gen_data.values():
            if not size_data.get("skipped"):
                all_reasons.update(size_data.get("rejection_reasons", {}).keys())
    all_reasons = sorted(all_reasons)

    labels = [f"{gen}\n{size}" for gen in generators for size in sizes]
    reason_arrays = {r: [] for r in all_reasons}
    for gen in generators:
        for size in sizes:
            data = results[gen].get(size, {})
            reasons = data.get("rejection_reasons", {}) if not data.get("skipped") else {}
            total = max(1, data.get("rejected", 1)) if not data.get("skipped") else 1
            for r in all_reasons:
                reason_arrays[r].append(reasons.get(r, 0) / total * 100)

    fig, ax = plt.subplots(figsize=(16, 6))
    x2 = np.arange(len(labels))
    bottom = np.zeros(len(labels))
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_reasons)))
    for reason, color in zip(all_reasons, colors):
        vals = np.array(reason_arrays[reason])
        ax.bar(x2, vals, bottom=bottom, label=reason, color=color)
        bottom += vals

    ax.set_xlabel("Generator × Grid size")
    ax.set_ylabel("% of rejections")
    ax.set_title("Rejection Reason Breakdown (% of rejected attempts)")
    ax.set_xticks(x2)
    ax.set_xticklabels(labels, fontsize=7)
    ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rejection_reasons.png", dpi=150)
    plt.close(fig)
    print("Saved rejection_reasons.png")


if __name__ == "__main__":
    print("=== Rejection Rate Benchmark ===")
    run()
    print("Done.")
