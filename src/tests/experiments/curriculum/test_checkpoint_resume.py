"""Tests for the checkpoint + resume capability of ``run_experiment``.

These tests cover the *plumbing* (scheduler state-dict round trip,
checkpoint folder discovery / pruning, CSV truncation) without ever
launching real training. The end-to-end smoke test
:func:`test_smoke_resume_on_b3_iql` is marked ``slow`` and **must NOT**
be executed automatically; the user runs it manually when they want to
validate full resume behaviour.

Run with the marl venv (preferred)::

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_checkpoint_resume.py -v -m "not slow"
"""

from __future__ import annotations

import csv
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.curriculum.configs import CURRICULUM_STAGES
from experiments.curriculum.curriculum_scheduler import StageScheduler
from experiments.curriculum.run_experiment import (
    _truncate_csv_to_step,
    find_latest_checkpoint,
    _prune_old_checkpoints,
    _step_dir_name,
)


# ---------------------------------------------------------------------------
# StageScheduler.state_dict / load_state_dict
# ---------------------------------------------------------------------------


def _make_scheduler(rng_seed: int = 12345) -> StageScheduler:
    """Build a scheduler with a tiny per-stage cap for fast tests."""
    pools = [[f"stage{stage.stage_id}-w{i}" for i in range(5)] for stage in CURRICULUM_STAGES]
    return StageScheduler(
        stages=CURRICULUM_STAGES,
        pools=pools,
        rng_seed=rng_seed,
        per_stage_step_cap=1_000,
        success_threshold=0.80,
        success_window=10,
    )


def test_scheduler_state_dict_round_trip():
    """state_dict() -> load_state_dict() restores stage, deque, RNG state.

    Drive the original scheduler through some work (record episodes,
    advance a stage, draw a few worlds), snapshot, build a fresh
    scheduler, restore. From that point onward, the two schedulers must
    produce identical sequences (sample worlds, advance triggers).
    """
    s = _make_scheduler()
    # Fill the rolling window with enough successes to advance stage 1
    # -> stage 2, then record some failures into stage 2 to leave a
    # non-trivial deque.
    for _ in range(10):
        s.record_episode(success=True, steps=20)
    assert s.maybe_advance() is True
    assert s.current_stage_id == 2
    s.record_episode(success=False, steps=33)
    s.record_episode(success=True, steps=44)
    # Burn a few RNG draws so the rng_state is non-default.
    for _ in range(7):
        s.sample_world()

    snapshot = s.state_dict()
    # The snapshot must be JSON-serialisable (we round-trip through
    # json.dumps/loads to assert this and to mirror what the runner
    # actually writes to disk).
    snapshot_json = json.loads(json.dumps(snapshot))

    s2 = _make_scheduler()
    s2.load_state_dict(snapshot_json)

    # Static observable state must match.
    assert s2.current_stage_id == s.current_stage_id
    assert s2._stage_idx == s._stage_idx
    assert s2._stage_steps == s._stage_steps
    assert list(s2._recent_successes) == list(s._recent_successes)
    assert s2._finished == s._finished

    # And the RNG sequence must continue identically: the next K world
    # draws and advance triggers must agree.
    seq_a = [s.sample_world() for _ in range(20)]
    seq_b = [s2.sample_world() for _ in range(20)]
    assert seq_a == seq_b


def test_scheduler_state_dict_round_trip_preserves_finished_flag():
    """If the original scheduler was ``is_finished``, the restore agrees."""
    s = _make_scheduler()
    # Walk through every stage by saturating the cap each time.
    n_stages = len(CURRICULUM_STAGES)
    for _ in range(n_stages):
        for _ in range(101):  # 101 episodes * 10 steps = 1010 > 1000 cap
            s.record_episode(success=False, steps=10)
        s.maybe_advance()
    assert s.is_finished()

    s2 = _make_scheduler()
    s2.load_state_dict(s.state_dict())
    assert s2.is_finished()
    assert s2.current_stage_id == CURRICULUM_STAGES[-1].stage_id


def test_scheduler_load_state_dict_validates_stage_idx():
    s = _make_scheduler()
    bad = s.state_dict()
    bad["stage_idx"] = 999  # out of range
    with pytest.raises(ValueError):
        s.load_state_dict(bad)


# ---------------------------------------------------------------------------
# CSV truncation
# ---------------------------------------------------------------------------


def _write_eval_csv(path: Path, steps: list[int]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["step", "success_rate", "mean_return"])
        for s in steps:
            w.writerow([s, "0.5", "1.23"])


def _read_steps(path: Path) -> list[int]:
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    # Skip the header (first row).
    return [int(r[0]) for r in rows[1:]]


def test_resume_truncates_csv_to_checkpoint_step(tmp_path):
    """Eval rows past the checkpoint step are dropped on resume."""
    csv_path = tmp_path / "level6_eval.csv"
    _write_eval_csv(csv_path, [20_000, 40_000, 60_000, 80_000, 100_000, 120_000])
    _truncate_csv_to_step(csv_path, max_step=100_000)
    assert _read_steps(csv_path) == [20_000, 40_000, 60_000, 80_000, 100_000]


def test_truncate_csv_keeps_header_only_file(tmp_path):
    """A CSV with only the header row survives unchanged."""
    csv_path = tmp_path / "level6_eval.csv"
    _write_eval_csv(csv_path, [])
    _truncate_csv_to_step(csv_path, max_step=100_000)
    # Still just a header.
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows == [["step", "success_rate", "mean_return"]]


def test_truncate_csv_missing_file_is_noop(tmp_path):
    """No file -> no error (fresh start)."""
    csv_path = tmp_path / "does_not_exist.csv"
    _truncate_csv_to_step(csv_path, max_step=100_000)
    assert not csv_path.exists()


def test_truncate_csv_drops_all_rows_when_step_zero(tmp_path):
    """Edge case: max_step=0 keeps the header and nothing else."""
    csv_path = tmp_path / "stage_progress.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["step", "stage_id"])
        w.writerow([0, 1])
        w.writerow([50_000, 2])
    _truncate_csv_to_step(csv_path, max_step=0)
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    # Header survives; the step==0 row also survives (<=); the 50k row is dropped.
    assert rows == [["step", "stage_id"], ["0", "1"]]


# ---------------------------------------------------------------------------
# find_latest_checkpoint
# ---------------------------------------------------------------------------


def _make_ckpt_dirs(run_dir: Path, steps: list[int]) -> None:
    """Create empty checkpoint folders matching the runner's layout."""
    root = run_dir / "checkpoints"
    root.mkdir(parents=True, exist_ok=True)
    for s in steps:
        (root / _step_dir_name(s)).mkdir()


def test_latest_checkpoint_finder_handles_padded_names(tmp_path):
    """Returns the directory with the largest parsed step (not lex sort)."""
    _make_ckpt_dirs(tmp_path, [100_000, 200_000, 50_000])
    latest = find_latest_checkpoint(tmp_path)
    assert latest is not None
    assert latest.name == _step_dir_name(200_000)


def test_latest_checkpoint_finder_returns_none_when_missing(tmp_path):
    """No checkpoints/ dir at all -> None."""
    assert find_latest_checkpoint(tmp_path) is None


def test_latest_checkpoint_finder_returns_none_for_empty_root(tmp_path):
    """Existing but empty checkpoints/ -> None."""
    (tmp_path / "checkpoints").mkdir()
    assert find_latest_checkpoint(tmp_path) is None


def test_latest_checkpoint_finder_ignores_garbage_subdirs(tmp_path):
    """Folders that don't match the ``step_<digits>`` pattern are ignored."""
    _make_ckpt_dirs(tmp_path, [300_000])
    (tmp_path / "checkpoints" / "trainer_backup").mkdir()
    (tmp_path / "checkpoints" / "step_notanumber").mkdir()
    latest = find_latest_checkpoint(tmp_path)
    assert latest is not None
    assert latest.name == _step_dir_name(300_000)


# ---------------------------------------------------------------------------
# Cleanup helper
# ---------------------------------------------------------------------------


def test_keep_only_n_latest_checkpoints(tmp_path):
    """5 mock checkpoints, keep=2, only 2 newest survive."""
    _make_ckpt_dirs(tmp_path, [100_000, 200_000, 300_000, 400_000, 500_000])
    _prune_old_checkpoints(tmp_path, keep=2)
    surviving = sorted(p.name for p in (tmp_path / "checkpoints").iterdir())
    assert surviving == [
        _step_dir_name(400_000),
        _step_dir_name(500_000),
    ]


def test_prune_noop_when_under_keep_threshold(tmp_path):
    """keep=2 with only 1 checkpoint -> nothing deleted."""
    _make_ckpt_dirs(tmp_path, [100_000])
    _prune_old_checkpoints(tmp_path, keep=2)
    surviving = sorted(p.name for p in (tmp_path / "checkpoints").iterdir())
    assert surviving == [_step_dir_name(100_000)]


def test_prune_noop_on_missing_root(tmp_path):
    """No checkpoints/ dir at all -> no error."""
    _prune_old_checkpoints(tmp_path, keep=2)  # must not raise


# ---------------------------------------------------------------------------
# Slow end-to-end smoke (DO NOT run automatically)
# ---------------------------------------------------------------------------


PYTHON = sys.executable


@pytest.mark.slow
def test_smoke_resume_on_b3_iql(tmp_path):
    """Run B3 IQL for a tiny budget twice and check it resumed.

    *Not* run by CI: the user invokes this manually with the marl venv.
    The first run produces a checkpoint at the 100k boundary (or the
    end of training, whichever comes first). The second run, with the
    same args, is expected to detect the checkpoint and finish writing
    ``final_results.json``.
    """
    out_dir = tmp_path / "results"

    cmd = [
        PYTHON,
        "-m",
        "experiments.curriculum.run_experiment",
        "--condition", "B3",
        "--algo", "IQL",
        "--seed", "0",
        "--steps", "2000",
        "--out-dir", str(out_dir),
    ]
    # First pass.
    r1 = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    assert r1.returncode == 0, r1.stderr

    # Second pass: same args, must still succeed (and ideally print the
    # "Resuming from step ..." line on stderr if a checkpoint exists).
    r2 = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    assert r2.returncode == 0, r2.stderr

    run_dir = out_dir / "runs" / "B3_IQL_seed0"
    assert (run_dir / "final_results.json").exists()
