"""Structural tests for the curriculum stage configuration table.

These tests exist to lock the experimental design (4 stages, fixed
geometry per stage, fixed generator-name mapping, fixed RNG seed) so
that an accidental edit to ``experiments.curriculum.configs`` cannot
silently change the thesis design surface.

Run with the marl venv:

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_configs.py
"""

from __future__ import annotations

from experiments.curriculum.configs import (
    ADVANCEMENT_SUCCESS_THRESHOLD,
    ADVANCEMENT_WINDOW_EPISODES,
    ALGORITHMS,
    CONDITIONS,
    CURRICULUM_STAGES,
    EVAL_EPISODES,
    EVAL_FREQUENCY_STEPS,
    FINAL_EVAL_EPISODES,
    FULL_RUN_TOTAL_STEPS,
    PILOT_RUN_TOTAL_STEPS,
    RNG_SEED,
    StageConfig,
    THESIS_GENERATOR_NAMES,
)
from generators.registry import GENERATOR_REGISTRY


def test_rng_seed_is_the_thesis_seed():
    assert RNG_SEED == 20260514


def test_curriculum_has_exactly_four_stages():
    assert len(CURRICULUM_STAGES) == 4


def test_stage_ids_are_one_through_four_in_order():
    assert tuple(s.stage_id for s in CURRICULUM_STAGES) == (1, 2, 3, 4)


def test_all_stages_use_four_agents():
    # The Q-network architecture is shared across stages, so n_agents
    # must be constant.
    assert all(s.n_agents == 4 for s in CURRICULUM_STAGES)


def test_grid_dimensions_match_thesis_design():
    expected = ((6, 6), (8, 8), (10, 10), (12, 13))
    actual = tuple((s.height, s.width) for s in CURRICULUM_STAGES)
    assert actual == expected


def test_laser_counts_grow_then_plateau():
    # Stage 1 is a pure-navigation warmup (no laser, no cooperation
    # pressure); stages 2 and 3 ramp the laser count up; stage 4
    # matches the LLE Level 6 target geometry.
    assert tuple(s.n_lasers for s in CURRICULUM_STAGES) == (0, 1, 2, 3)


def test_t_max_per_stage_matches_thesis_design():
    assert tuple(s.t_max for s in CURRICULUM_STAGES) == (12, 16, 18, 21)


def test_generator_names_match_design():
    # Registry keys, not thesis-text names.
    expected = ("random", "cooperative", "cooperative", "level6_style")
    actual = tuple(s.generator_name for s in CURRICULUM_STAGES)
    assert actual == expected


def test_all_generator_names_are_actually_registered():
    for stage in CURRICULUM_STAGES:
        assert stage.generator_name in GENERATOR_REGISTRY, (
            f"stage {stage.stage_id} uses unregistered generator "
            f"{stage.generator_name!r}; registry has {list(GENERATOR_REGISTRY)}"
        )


def test_pool_sizes_are_fifty_for_train_pools():
    assert all(s.pool_size == 50 for s in CURRICULUM_STAGES)


def test_only_stage_four_has_a_held_out_eval_pool():
    eval_sizes = tuple(s.eval_pool_size for s in CURRICULUM_STAGES)
    assert eval_sizes == (0, 0, 0, 50)


def test_step_caps_match_thesis_design():
    # Asymmetric per-stage caps: stage 1 (warmup, no laser) is mastered
    # quickly so its budget is small; stages 2-4 (cooperation under
    # laser pressure) get the bulk of the budget. Pilot caps are
    # exactly half of the full caps.
    expected_full = (100_000, 600_000, 600_000, 700_000)
    expected_pilot = (50_000, 300_000, 300_000, 350_000)
    actual_full = tuple(s.per_stage_step_cap_full for s in CURRICULUM_STAGES)
    actual_pilot = tuple(s.per_stage_step_cap_pilot for s in CURRICULUM_STAGES)
    assert actual_full == expected_full
    assert actual_pilot == expected_pilot


def test_full_pilot_caps_sum_to_total_budget():
    # 100k + 600k + 600k + 700k = 2_000_000 == FULL_RUN_TOTAL_STEPS,
    # halved for the pilot.
    assert sum(s.per_stage_step_cap_full for s in CURRICULUM_STAGES) == FULL_RUN_TOTAL_STEPS
    assert sum(s.per_stage_step_cap_pilot for s in CURRICULUM_STAGES) == PILOT_RUN_TOTAL_STEPS


def test_advancement_constants_are_thesis_values():
    assert ADVANCEMENT_SUCCESS_THRESHOLD == 0.60
    assert ADVANCEMENT_WINDOW_EPISODES == 100


def test_eval_constants_are_thesis_values():
    assert EVAL_FREQUENCY_STEPS == 20_000
    assert EVAL_EPISODES == 50
    assert FINAL_EVAL_EPISODES == 200


def test_conditions_match_design():
    assert CONDITIONS == ("B1", "B2", "B3", "CURR")


def test_algorithms_match_design():
    assert ALGORITHMS == ("QMIX", "VDN", "IQL")


def test_stage_config_is_frozen():
    """StageConfig instances must be immutable (frozen=True)."""
    import dataclasses

    stage = CURRICULUM_STAGES[0]
    assert dataclasses.is_dataclass(stage)
    fields = {f.name for f in dataclasses.fields(StageConfig)}
    expected_fields = {
        "stage_id",
        "height",
        "width",
        "n_agents",
        "n_lasers",
        "t_max",
        "generator_name",
        "pool_size",
        "eval_pool_size",
        "per_stage_step_cap_full",
        "per_stage_step_cap_pilot",
    }
    assert fields == expected_fields


def test_thesis_to_registry_mapping_is_consistent():
    """Every generator we use must be cross-referenced in the mapping."""
    used_keys = {s.generator_name for s in CURRICULUM_STAGES}
    for key in used_keys:
        assert key in THESIS_GENERATOR_NAMES, (
            f"Generator {key!r} used by curriculum but missing from "
            f"THESIS_GENERATOR_NAMES."
        )
