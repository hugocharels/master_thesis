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

from benchmark._plot_style import DEFAULT_BAR_ALPHA, apply_thesis_style
from generators.cooperative import CooperativeGenerator
from generators.level6_style import Level6StyleGenerator
from generators.random import ConstrainedRandomCooperativeGenerator
from solver import CooperationProfileAnalyzer

apply_thesis_style()

GENERATOR_LABELS = {
    "constrained_random_cooperative": "Random (geom-validated) + cooperation",
    "cooperative": "Constructive (cooperative)",
    "level6_style": "Constructive (Level-6 style)",
}

PROFILE_LABELS = {
    "asymmetric": "Asymmetric",
    "mutual": "Mutual",
    "chain": "Chain",
    "distributed": "Distributed",
    "fully_coupled": "Fully coupled",
}

SHORT_GEN_LABELS = {
    "constrained_random_cooperative": "Random",
    "cooperative": "Constructive",
    "level6_style": "Level-6 Style",
}

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results" / "profile_benchmark"

LEVELS_TO_GENERATE = 100
LEVELS_TO_GENERATE_LARGE = 50  # reduced target for large grids

CONFIGS = [
    # (rows, cols, agents, lasers, label, is_large)
    (5, 5, 2, 1, "5x5", False),
    (8, 8, 3, 2, "8x8", True),
]

ALL_PROFILES = ["asymmetric", "mutual", "chain", "distributed", "fully_coupled"]

GENERATOR_SPECS = {
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "cooperative": CooperativeGenerator,
    "level6_style": Level6StyleGenerator,
}


def _make_generator(cls, rows, cols, agents, lasers, is_large=False):
    """Create generator with max_attempts=1 so each generate() call = one attempt."""
    t_max = min(max(rows * cols // 2, 8), 14 if is_large else 20)
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
        return cls(
            size=(rows, cols), agents=agents, lasers=lasers, t_max=t_max, max_attempts=1
        )


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
            print(
                f"  Resumed from {json_path}: {n_saved} configs already saved",
                flush=True,
            )
        except Exception as e:
            print(
                f"  Warning: could not load existing JSON ({e}); starting fresh",
                flush=True,
            )
            results = {}

    for gen_name, gen_cls in GENERATOR_SPECS.items():
        if gen_name not in results:
            results[gen_name] = {}
        for rows, cols, agents, lasers, size_label, is_large in CONFIGS:
            if size_label in results[gen_name]:
                print(
                    f"  [{gen_name}] {size_label}: SKIP (already in JSON)", flush=True
                )
                continue
            target = LEVELS_TO_GENERATE_LARGE if is_large else LEVELS_TO_GENERATE
            print(f"\n[{gen_name}] {size_label} — target: {target} levels", flush=True)

            gen = _make_generator(gen_cls, rows, cols, agents, lasers, is_large)
            t_max = min(max(rows * cols // 2, 8), 14 if is_large else 20)

            profile_counts: dict[str, int] = defaultdict(int)
            accepted = 0
            rejected = 0
            max_total_attempts = target * 200
            t_start = time.perf_counter()

            t_gen_total = 0.0
            t_analyze_total = 0.0

            while accepted < target and (accepted + rejected) < max_total_attempts:
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
                            f"  attempt {accepted + rejected}: {rejected} rejected, {accepted} accepted "
                            f"({elapsed:.1f}s | gen_avg={1000 * t_gen_total / max(1, accepted + rejected):.1f}ms)",
                            flush=True,
                        )
                    continue

                # --- profile analysis ---
                t_analyze = time.perf_counter()
                world.reset()
                result = CooperationProfileAnalyzer(world, T_MAX=t_max).analyze()
                t_analyze_total += time.perf_counter() - t_analyze

                profile_counts[result.profile] += 1
                accepted += 1
                elapsed = time.perf_counter() - t_start
                n_attempts = accepted + rejected
                print(
                    f"  [{accepted:>3}/{target}] profile={result.profile:<14} "
                    f"attempts={n_attempts:>5} ({rejected} rejected)  "
                    f"{elapsed:.1f}s | gen={1000 * t_gen_total / max(1, n_attempts):.0f}ms "
                    f"| analyze={1000 * t_analyze_total / max(1, accepted):.0f}ms",
                    flush=True,
                )

            total_attempts = accepted + rejected
            elapsed_total = time.perf_counter() - t_start
            rejection_rate = rejected / max(1, total_attempts)
            print(
                f"  done: {accepted} levels, {rejected} rejected "
                f"({100 * rejection_rate:.1f}% rejection) in {elapsed_total:.1f}s",
                flush=True,
            )
            print(f"  profiles: {dict(profile_counts)}", flush=True)
            print(
                f"  timing: gen_avg={1000 * t_gen_total / max(1, total_attempts):.1f}ms/attempt, "
                f"analyze_avg={1000 * t_analyze_total / max(1, accepted):.1f}ms/level",
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
                    p: profile_counts[p] / max(1, accepted) for p in profile_counts
                },
            }

            # Incremental save so a crash doesn't lose completed configs.
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"  -> saved partial results to {json_path}", flush=True)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {json_path}")

    _make_plots(results)


def _make_plots(results: dict):
    generators = list(results.keys())
    sizes = [cfg[4] for cfg in CONFIGS]

    # All five families are listed so the legend is complete; fully_coupled
    # is never observed in this benchmark and so renders at 0 % (no visible bar).
    profiles = ["asymmetric", "mutual", "chain", "distributed", "fully_coupled"]
    profile_labels = [
        PROFILE_LABELS.get(p, p.replace("_", " ").capitalize()) for p in profiles
    ]
    LABEL_MIN = 8  # percent; segments below this are too thin for an inline label

    bar_width = 1.0
    within_gap = 0.18  # small gap inside a generator's pair -> reads as one group
    group_gap = 1.4  # larger gap between generators -> visual separation

    positions = []
    group_centers = []
    bar_labels = []
    pos = 0.0

    for gen_name in generators:
        group_positions = []
        for size_label in sizes:
            positions.append(pos)
            group_positions.append(pos)
            n = results[gen_name].get(size_label, {}).get("accepted", 0)
            bar_labels.append(f"{size_label}\n(n={n})")
            pos += bar_width + within_gap
        # Replace the trailing within-gap with the larger group gap.
        pos += group_gap - within_gap
        # Bars are center-aligned on their positions, so the true visual
        # centre of the group is the midpoint of the first and last bar.
        group_centers.append((group_positions[0] + group_positions[-1]) / 2)

    positions = np.array(positions)

    bar_data = {p: [] for p in profiles}
    for gen_name in generators:
        for size_label in sizes:
            data = results[gen_name].get(size_label, {})
            for profile in profiles:
                frac = data.get("profile_fractions", {}).get(profile, 0.0)
                bar_data[profile].append(frac * 100)

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    fig, ax = plt.subplots(figsize=(13, 6))
    bottom = np.zeros(len(positions))

    for i, (profile, plabel) in enumerate(zip(profiles, profile_labels)):
        values = np.array(bar_data[profile])
        ax.bar(
            positions,
            values,
            width=bar_width,
            bottom=bottom,
            label=plabel,
            color=colors[i % len(colors)],
            alpha=DEFAULT_BAR_ALPHA,
            edgecolor="black",
            linewidth=0.8,
        )
        for j, (val, bot) in enumerate(zip(values, bottom)):
            if val >= LABEL_MIN:
                ax.text(
                    positions[j],
                    bot + val / 2,
                    f"{val:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )
        bottom += values

    # Thin segments cannot hold an inline label, so annotate them with a
    # leader line pointing into the whitespace to the right of the bar.
    for j in range(len(positions)):
        cum = 0.0
        thin = []  # (value, segment_midpoint_y, colour)
        for i, profile in enumerate(profiles):
            val = bar_data[profile][j]
            if 0 < val < LABEL_MIN:
                thin.append((val, cum + val / 2, colors[i % len(colors)]))
            cum += val
        if not thin:
            continue
        # Spread the callout text vertically so adjacent thin slices don't collide.
        thin.sort(key=lambda t: t[1])
        min_sep = 7.0
        prev_y = -1e9
        x_edge = positions[j] + bar_width / 2
        for val, seg_mid, color in thin:
            y_text = max(seg_mid, prev_y + min_sep)
            prev_y = y_text
            ax.annotate(
                f"{val:.0f}%",
                xy=(x_edge, seg_mid),
                xytext=(x_edge + 0.35, y_text),
                ha="left",
                va="center",
                fontsize=8,
                color=color,
                fontweight="bold",
                annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color=color, linewidth=0.8),
            )

    for gen_name, center in zip(generators, group_centers):
        ax.text(
            center,
            103,
            SHORT_GEN_LABELS.get(gen_name, gen_name),
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_ylabel("% of accepted cooperative levels")
    ax.set_title("Cooperation profile distribution by generator and grid size")
    ax.set_xticks(positions)
    ax.set_xticklabels(bar_labels, ha="center")
    ax.set_ylim(0, 112)
    # Headroom on the right so leader-line callouts on the last group fit.
    ax.set_xlim(positions[0] - bar_width, positions[-1] + bar_width + 0.6)
    # Horizontal legend below the plot so it never overlaps the bars or labels.
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=len(profiles),
        frameon=True,
    )
    ax.grid(axis="y", alpha=0.5)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", length=0)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "profile_distribution.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "profile_distribution.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Saved profile_distribution.{png,pdf}")


if __name__ == "__main__":
    print("=== Cooperation Profile Distribution Benchmark ===")
    run()
    print("Done.")
