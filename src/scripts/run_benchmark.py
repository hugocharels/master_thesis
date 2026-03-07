"""CLI entry point for running benchmarks."""

import argparse
import os

from benchmark import (
    generate_all_plots,
    print_summary_table,
    run_benchmark,
    save_results_json,
)


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
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running benchmark: {args.runs} timing runs per level/method")
    print(f"Output directory: {output_dir}\n")

    results = run_benchmark(num_runs=args.runs)

    print_summary_table(results)

    print("\nGenerating plots...")
    generate_all_plots(results, output_dir)
    save_results_json(results, output_dir)
    print(f"\nAll plots saved to {output_dir}/")


if __name__ == "__main__":
    main()
