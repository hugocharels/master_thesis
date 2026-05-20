"""Tests for curriculum-strategy plotting helpers (parsing + aggregation)."""
from __future__ import annotations

import json

from experiments.curriculum_strategy.plot_results import (
    aggregate_final,
    parse_run_dir,
)


def test_parse_run_dir_extracts_condition_algo_seed():
    assert parse_run_dir("forward_VDN_seed0") == ("forward", "VDN", 0)
    assert parse_run_dir("direct_QMIX_seed12") == ("direct", "QMIX", 12)
    assert parse_run_dir("mixed_IQL_seed3") == ("mixed", "IQL", 3)


def test_parse_run_dir_rejects_foreign_names():
    assert parse_run_dir("QMIX_seed0") is None       # learnability-style
    assert parse_run_dir("bogus_dir") is None


def test_aggregate_final_groups_by_condition_and_algo(tmp_path):
    runs = tmp_path / "runs"
    for cond in ("direct", "forward"):
        for seed in (0, 1):
            d = runs / f"{cond}_VDN_seed{seed}"
            d.mkdir(parents=True)
            (d / "final_results.json").write_text(json.dumps({
                "condition": cond, "algo": "VDN", "seed": seed,
                "success_rate_train": 0.5 + 0.1 * seed,
                "success_rate_test": 0.2 + 0.1 * seed,
            }))
    agg = aggregate_final(runs)
    assert set(agg.keys()) == {("direct", "VDN"), ("forward", "VDN")}
    # mean test success for forward over seeds 0,1 == mean(0.2, 0.3) == 0.25
    assert abs(agg[("forward", "VDN")]["test"] - 0.25) < 1e-9
    assert agg[("forward", "VDN")]["n"] == 2
