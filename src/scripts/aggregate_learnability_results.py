"""Aggregate every ``results/learnability_5x5/runs/<algo>_seed<N>/final_results.json``
into a single ``results/learnability_5x5/aggregated.json`` that the thesis
appendix can load via Typst's ``json()`` to build the per-seed table.

Run from the project root::

    python3.13 src/scripts/aggregate_learnability_results.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "results" / "learnability_5x5" / "runs"
OUTPUT_PATH = PROJECT_ROOT / "results" / "learnability_5x5" / "aggregated.json"

RUN_PATTERN = re.compile(r"^(?P<algo>[A-Z]+)_seed(?P<seed>\d+)$")


def main() -> None:
    rows = []
    for run_dir in sorted(RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        match = RUN_PATTERN.match(run_dir.name)
        if match is None:
            continue
        final = run_dir / "final_results.json"
        if not final.exists():
            print(f"  {run_dir.name}: no final_results.json, skipping")
            continue
        data = json.loads(final.read_text())
        rows.append({
            "algorithm": match.group("algo"),
            "seed": int(match.group("seed")),
            "train_success": data["success_rate_train"],
            "train_success_std": data["success_rate_train_std"],
            "test_success": data["success_rate_test"],
            "test_success_std": data["success_rate_test_std"],
            "train_return": data["mean_return_train"],
            "test_return": data["mean_return_test"],
        })

    rows.sort(key=lambda r: (r["algorithm"], r["seed"]))
    OUTPUT_PATH.write_text(json.dumps(rows, indent=2))
    print(f"wrote {OUTPUT_PATH} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
