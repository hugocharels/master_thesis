"""
Cooperation profile distribution benchmark.

For random_cooperative and constructive_cooperative generators:
  - Generates 100 accepted cooperative levels at 5x5 and 8x8
  - Runs CooperationProfileAnalyzer on each
  - Records profile classification distribution

Results saved to results/profile_benchmark/.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.constructive_cooperative_generator import ConstructiveCooperativeGenerator
from generators.random_cooperative_generator import RandomCooperativeGenerator
from solver import LLEAdapter
from solver.cooperation_profile_analyzer import CooperationProfileAnalyzer

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results" / "profile_benchmark"

LEVELS_TO_GENERATE = 100

CONFIGS = [
    # (rows, cols, agents, lasers, label)
    (5, 5, 2, 1, "5x5"),
    (8, 8, 3, 2, "8x8"),
]

ALL_PROFILES = ["asymmetric", "mutual", "chain", "distributed", "fully_coupled", "cooperative"]

GENERATOR_SPECS = {
    "random_cooperative": RandomCooperativeGenerator,
    "constructive_cooperative": ConstructiveCooperativeGenerator,
}


def _make_generator(cls, rows, cols, agents, lasers):
    t_max = max(rows * cols // 2, 8)
    common = dict(
        size=(rows, cols),
        agents=agents,
        lasers=lasers,
        t_max=t_max,
        max_attempts=10_000,
        seed=None,
    )
    try:
        return cls(**common)
    except (ValueError, TypeError):
        return cls(size=(rows, cols), agents=agents, lasers=lasers, t_max=t_max, max_attempts=10_000)


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    for gen_name, gen_cls in GENERATOR_SPECS.items():
        results[gen_name] = {}
        for rows, cols, agents, lasers, size_label in CONFIGS:
            print(f"  [{gen_name}] {size_label} — generating {LEVELS_TO_GENERATE} levels...", flush=True)

            gen = _make_generator(gen_cls, rows, cols, agents, lasers)
            t_max = max(rows * cols // 2, 8)

            profile_counts: dict[str, int] = defaultdict(int)
            accepted = 0
            t_start = time.perf_counter()

            while accepted < LEVELS_TO_GENERATE:
                try:
                    world = gen.generate()
                except RuntimeError:
                    print(f"    -> generator exhausted at {accepted} levels")
                    break

                world.reset()
                adapted = LLEAdapter(world)
                result = CooperationProfileAnalyzer(adapted, T_MAX=t_max).analyze()
                profile_counts[result.profile] += 1
                accepted += 1

                if accepted % 10 == 0:
                    elapsed = time.perf_counter() - t_start
                    print(f"    {accepted}/{LEVELS_TO_GENERATE} ({elapsed:.1f}s)", flush=True)

            elapsed_total = time.perf_counter() - t_start
            print(f"    done: {accepted} levels in {elapsed_total:.1f}s")
            print(f"    profiles: {dict(profile_counts)}")

            results[gen_name][size_label] = {
                "accepted": accepted,
                "elapsed_seconds": elapsed_total,
                "profile_counts": dict(profile_counts),
                "profile_fractions": {
                    p: profile_counts[p] / max(1, accepted)
                    for p in profile_counts
                },
            }

    json_path = OUTPUT_DIR / "benchmark_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {json_path}")

    _make_plots(results)


def _make_plots(results: dict):
    generators = list(results.keys())
    sizes = [cfg[4] for cfg in CONFIGS]

    # Grouped bar chart: x-axis = profile, groups = generator × size
    profiles_present: set[str] = set()
    for gen_data in results.values():
        for size_data in gen_data.values():
            profiles_present.update(size_data.get("profile_counts", {}).keys())
    profiles = sorted(profiles_present)

    n_groups = len(generators) * len(sizes)
    x = np.arange(len(profiles))
    width = 0.8 / n_groups

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.tab10(np.linspace(0, 1, n_groups))

    for idx, (gen_name, size_label) in enumerate(
        (g, s) for g in generators for s in sizes
    ):
        fractions = []
        for profile in profiles:
            data = results[gen_name].get(size_label, {})
            frac = data.get("profile_fractions", {}).get(profile, 0.0)
            fractions.append(frac * 100)
        offset = (idx - n_groups / 2) * width + width / 2
        ax.bar(
            x + offset,
            fractions,
            width,
            label=f"{gen_name} / {size_label}",
            color=colors[idx],
        )

    ax.set_xlabel("Cooperation profile")
    ax.set_ylabel("% of accepted levels")
    ax.set_title("Cooperation Profile Distribution by Generator and Grid Size")
    ax.set_xticks(x)
    ax.set_xticklabels(profiles)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "profile_distribution.png", dpi=150)
    plt.close(fig)
    print("Saved profile_distribution.png")


if __name__ == "__main__":
    print("=== Cooperation Profile Distribution Benchmark ===")
    run()
    print("Done.")
