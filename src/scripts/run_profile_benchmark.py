"""
Cooperation profile distribution benchmark.

For each cooperative generator and grid size, generates LEVELS_TO_GENERATE accepted
cooperative levels and records their cooperation profile distribution. Each call to
gen.generate() uses max_attempts=1, so each call is one attempt: success or
RuntimeError. Rejected attempts are counted to report the rejection rate alongside
the profile distribution.

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

from generators.constrained_random_cooperative_generator import ConstrainedRandomCooperativeGenerator
from generators.constructive_cooperative_generator import ConstructiveCooperativeGenerator
from solver import LLEAdapter
from solver.cooperation_profile_analyzer import CooperationProfileAnalyzer

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results" / "profile_benchmark"

LEVELS_TO_GENERATE = 100
LEVELS_TO_GENERATE_LARGE = 20  # reduced target for large grids

CONFIGS = [
    # (rows, cols, agents, lasers, label, is_large)
    (5, 5, 2, 1, "5x5", False),
    (8, 8, 3, 2, "8x8", True),
]

ALL_PROFILES = ["asymmetric", "mutual", "chain", "distributed", "fully_coupled", "cooperative"]

GENERATOR_SPECS = {
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "constructive_cooperative": ConstructiveCooperativeGenerator,
}


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
        return cls(size=(rows, cols), agents=agents, lasers=lasers, t_max=t_max, max_attempts=1)


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    for gen_name, gen_cls in GENERATOR_SPECS.items():
        results[gen_name] = {}
        for rows, cols, agents, lasers, size_label, is_large in CONFIGS:
            target = LEVELS_TO_GENERATE_LARGE if is_large else LEVELS_TO_GENERATE
            print(f"\n[{gen_name}] {size_label} — target: {target} levels", flush=True)

            gen = _make_generator(gen_cls, rows, cols, agents, lasers)
            t_max = min(max(rows * cols // 2, 8), 20)

            profile_counts: dict[str, int] = defaultdict(int)
            accepted = 0
            rejected = 0
            max_total_attempts = target * 200
            t_start = time.perf_counter()

            t_gen_total = 0.0
            t_analyze_total = 0.0

            while accepted < target and (accepted + rejected) < max_total_attempts:
                total_so_far = accepted + rejected

                # --- generation attempt ---
                t_gen = time.perf_counter()
                try:
                    world = gen.generate()
                    t_gen_total += time.perf_counter() - t_gen
                except RuntimeError:
                    t_gen_total += time.perf_counter() - t_gen
                    rejected += 1
                    if rejected % 50 == 0:
                        elapsed = time.perf_counter() - t_start
                        print(
                            f"  attempt {accepted+rejected}: {rejected} rejected, {accepted} accepted "
                            f"({elapsed:.1f}s | gen_avg={1000*t_gen_total/max(1,accepted+rejected):.1f}ms)",
                            flush=True,
                        )
                    continue

                # --- profile analysis ---
                t_analyze = time.perf_counter()
                world.reset()
                adapted = LLEAdapter(world)
                result = CooperationProfileAnalyzer(adapted, T_MAX=t_max).analyze()
                t_analyze_total += time.perf_counter() - t_analyze

                profile_counts[result.profile] += 1
                accepted += 1
                elapsed = time.perf_counter() - t_start
                n_attempts = accepted + rejected
                print(
                    f"  [{accepted:>3}/{target}] profile={result.profile:<14} "
                    f"attempts={n_attempts:>5} ({rejected} rejected)  "
                    f"{elapsed:.1f}s | gen={1000*t_gen_total/max(1,n_attempts):.0f}ms "
                    f"| analyze={1000*t_analyze_total/max(1,accepted):.0f}ms",
                    flush=True,
                )

            total_attempts = accepted + rejected
            elapsed_total = time.perf_counter() - t_start
            rejection_rate = rejected / max(1, total_attempts)
            print(
                f"  done: {accepted} levels, {rejected} rejected "
                f"({100*rejection_rate:.1f}% rejection) in {elapsed_total:.1f}s",
                flush=True,
            )
            print(f"  profiles: {dict(profile_counts)}", flush=True)
            print(
                f"  timing: gen_avg={1000*t_gen_total/max(1,total_attempts):.1f}ms/attempt, "
                f"analyze_avg={1000*t_analyze_total/max(1,accepted):.1f}ms/level",
                flush=True,
            )

            results[gen_name][size_label] = {
                "accepted": accepted,
                "rejected": rejected,
                "total_attempts": total_attempts,
                "rejection_rate": rejection_rate,
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
