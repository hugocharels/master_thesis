"""Tests for the level-pool builder / saver / loader.

These tests deliberately use the smallest, fastest stage (a 6x6 random
solvable level with a single laser) and ``n_levels=2`` so they finish
in well under a second. Bigger pools (the full 50-level ones) are the
job of the pre-flight script, which is intentionally not exercised
here.

Run with the marl venv (preferred -- it has both ``lle`` and ``marl``):

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_pool_generator.py
"""

from __future__ import annotations

from pathlib import Path

from experiments.curriculum.configs import CURRICULUM_STAGES, RNG_SEED, StageConfig
from experiments.curriculum.pool_generator import (
    _world_from_string,
    build_pool,
    load_pool,
    pool_path,
    save_pool,
)


# ---- Test fixtures ---------------------------------------------------------
#
# We use stage 1 (6x6, 4 agents, 0 lasers, ``random`` generator) for
# almost every test because it is the cheapest stage in the curriculum:
# random generation on a 6x6 grid with no lasers is essentially first-
# attempt accept after geometric validation. (Stage 1 is the pure-
# navigation warmup; cooperation pressure starts at stage 2.)
SMALL_STAGE: StageConfig = CURRICULUM_STAGES[0]
TINY_N_LEVELS = 2

TRAIN_SPLIT = "train"
HELDOUT_SPLIT = "eval"  # noqa: S105 - this is a directory name, not code execution


# ---- pool_path -------------------------------------------------------------


def test_pool_path_includes_stage_id_and_dimensions(tmp_path: Path):
    p = pool_path(tmp_path, SMALL_STAGE, TRAIN_SPLIT)
    # The folder name must encode the discriminating fields. Stage 1
    # has 0 lasers (pure-navigation warmup), so the laser-count token
    # is "0L".
    folder_name = p.parent.name
    assert "stage_1" in folder_name
    assert "6x6" in folder_name
    assert "4a" in folder_name
    assert "0L" in folder_name
    assert "random" in folder_name


def test_pool_path_split_subdir_is_train_or_heldout(tmp_path: Path):
    p_train = pool_path(tmp_path, SMALL_STAGE, TRAIN_SPLIT)
    p_held = pool_path(tmp_path, SMALL_STAGE, HELDOUT_SPLIT)
    assert p_train.name == "train"
    assert p_held.name == "eval"
    # Same parent, different leaf -> distinct folders, same naming convention.
    assert p_train.parent == p_held.parent


def test_pool_path_uses_levels_top_level(tmp_path: Path):
    p = pool_path(tmp_path, SMALL_STAGE, TRAIN_SPLIT)
    # tmp_path / levels / stage_<...> / train
    assert p.parts[-3] == "levels"


# ---- build_pool reproducibility -------------------------------------------


def test_build_pool_returns_requested_number_of_levels():
    pool = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=TINY_N_LEVELS)
    assert len(pool) == TINY_N_LEVELS


def test_build_pool_is_reproducible_for_same_seed():
    """Same (stage, seed, n_levels) -> same world strings."""
    pool_a = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=TINY_N_LEVELS)
    pool_b = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=TINY_N_LEVELS)
    a_strings = [w.world_string for w in pool_a]
    b_strings = [w.world_string for w in pool_b]
    assert a_strings == b_strings


def test_build_pool_changes_with_seed():
    """Different seeds usually produce different pools.

    On stage 1 the generator is plain ``random`` over a 6x6 grid, so
    two arbitrary seeds almost certainly produce different worlds. We
    don't assert all-different (degenerate seeds could collide on tiny
    grids), only that the two pools are not byte-identical.
    """
    pool_a = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=TINY_N_LEVELS)
    pool_b = build_pool(SMALL_STAGE, seed=RNG_SEED + 1, n_levels=TINY_N_LEVELS)
    a_strings = [w.world_string for w in pool_a]
    b_strings = [w.world_string for w in pool_b]
    assert a_strings != b_strings


# ---- save / load round-trip ------------------------------------------------


def test_save_pool_creates_files_with_padded_indices(tmp_path: Path):
    pool = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=TINY_N_LEVELS)
    written = save_pool(pool, tmp_path)
    assert len(written) == TINY_N_LEVELS
    names = sorted(p.name for p in written)
    # 3-digit zero-padded indices.
    assert names[0] == "level_000.json"
    assert names[1] == "level_001.json"


def test_save_pool_creates_missing_parent_dirs(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c"
    pool = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=1)
    save_pool(pool, nested)
    assert nested.is_dir()
    assert (nested / "level_000.json").is_file()


def test_save_then_load_round_trip_preserves_world(tmp_path: Path):
    pool = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=TINY_N_LEVELS)
    save_pool(pool, tmp_path)
    reloaded = load_pool(tmp_path)
    assert len(reloaded) == TINY_N_LEVELS
    for original, restored in zip(pool, reloaded):
        # ``world_string`` is a lossless serialisation of the LLE world,
        # so the reload must produce byte-identical world strings.
        assert original.world_string == restored.world_string


def test_load_pool_ignores_unrelated_files(tmp_path: Path):
    pool = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=1)
    save_pool(pool, tmp_path)
    (tmp_path / "README.md").write_text("not a level", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    reloaded = load_pool(tmp_path)
    assert len(reloaded) == 1


def test_load_pool_raises_on_missing_directory(tmp_path: Path):
    missing = tmp_path / "does_not_exist"
    try:
        load_pool(missing)
    except FileNotFoundError:
        return
    raise AssertionError("Expected FileNotFoundError for missing pool dir")


def test_world_from_string_matches_original_world(tmp_path: Path):
    """Direct round-trip helper used by load_pool."""
    pool = build_pool(SMALL_STAGE, seed=RNG_SEED, n_levels=1)
    original = pool[0]
    rebuilt = _world_from_string(original.world_string)
    assert original.world_string == rebuilt.world_string
    assert original.n_agents == rebuilt.n_agents
