"""CLI entry point for running benchmarks."""

import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt

from benchmark import (
    generate_all_plots,
    print_summary_table,
    run_benchmark,
    save_results_json,
)
from benchmark.runner import _normalize_levels


def _safe_name(name):
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(name))


def save_level_pngs(levels, output_dir):
    """
    Save one PNG snapshot per level using world.get_image().
    Images are written to: <output_dir>/levels/
    """
    levels_dir = os.path.join(output_dir, "levels")
    os.makedirs(levels_dir, exist_ok=True)

    for level_key, world, _t_max in _normalize_levels(levels):
        world.reset()
        img = world.get_image()

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(img)
        ax.axis("off")
        # ax.set_title(f"Level {level_key}")

        filename = f"level_{_safe_name(level_key)}.png"
        path = os.path.join(levels_dir, filename)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)

        print(f"  -> levels/{filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark movement constraint methods"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=100,
        help="Number of timing runs (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_plots",
        help="Output directory (default: benchmark_plots)",
    )
    parser.add_argument(
        "--custom-levels",
        action="store_true",
        help=(
            "Use levels from scripts.custom_levels:CUSTOM_BENCHMARK_LEVELS "
            "instead of default LLE levels."
        ),
    )
    parser.add_argument(
        "--save-level-pngs",
        action="store_true",
        help="Save one PNG snapshot per benchmark level in <output-dir>/levels/",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    levels = None
    if args.custom_levels:
        if __package__ in (None, ""):
            from scripts.custom_levels import CUSTOM_BENCHMARK_LEVELS
        else:
            from .custom_levels import CUSTOM_BENCHMARK_LEVELS

        levels = CUSTOM_BENCHMARK_LEVELS
        print("Using custom levels from scripts.custom_levels:CUSTOM_BENCHMARK_LEVELS")
    else:
        print("Using default LLE levels")

    if args.save_level_pngs:
        print("Saving level PNG snapshots...")
        save_level_pngs(levels, output_dir)

    print(f"Running benchmark: {args.runs} timing runs per level/method")
    print(f"Output directory: {output_dir}\n")

    results = run_benchmark(num_runs=args.runs, levels=levels)

    print_summary_table(results)

    print("\nGenerating plots...")
    generate_all_plots(results, output_dir)
    save_results_json(results, output_dir)
    print(f"\nAll plots saved to {output_dir}/")


if __name__ == "__main__":
    main()
