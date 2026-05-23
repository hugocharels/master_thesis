"""Generate, persist, and reload pools of training/evaluation levels.

This module wraps the thesis level generators (registered in
``generators.registry``) so that the curriculum-transfer experiment can:

1. Build a deterministic pool of ``n_levels`` solvable / cooperative
   levels for one curriculum stage (:func:`build_pool`).
2. Persist that pool to disk in a stable, human-inspectable layout
   (:func:`save_pool`).
3. Reload the pool from disk on subsequent runs without re-invoking the
   generator (:func:`load_pool`).

References
----------
- ``src/experiments/curriculum/configs.py`` for :class:`StageConfig`.
- ``src/generators/registry.py`` for the ``GENERATOR_REGISTRY`` lookup.
- ``src/generators/random.py``, ``constructive.py``, ``cooperative.py``,
  ``level6_style.py`` for the constructor signatures (all derive from
  :class:`generators.random.RandomGenerator` and accept the same
  ``size`` / ``agents`` / ``lasers`` / ``t_max`` / ``seed`` kwargs).

Serialization choice
--------------------
Each level is persisted as ``level_NNN.json`` containing
``{"world_string": "<lle world toml>"}``. This is the same string format
that :class:`experiments.curriculum.lle_marl_env.ThesisLLEConfig`
consumes, and ``lle.World(world_string)`` round-trips losslessly (the
LLE Builder expects a ``.toml``-like grid string), so JSON is the
simplest safe choice — diff-friendly and forward-compatible with LLE
upgrades.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import lle
from lle import World

from experiments.curriculum.configs import StageConfig
from generators.registry import GENERATOR_REGISTRY


# ----- Path helpers ---------------------------------------------------------

Split = Literal["train", "eval"]


def pool_path(base_dir: Path | str, stage: StageConfig, split: Split) -> Path:
    """Return the canonical pool directory for a stage / split.

    Layout (relative to ``base_dir``)::

        levels/
          stage_<id>_<h>x<w>_<n_agents>a_<n_lasers>L_<generator>/
            train/
              level_000.json
              level_001.json
              ...
            eval/
              ...

    The folder name encodes enough information to be uniquely identified
    by inspection; the ``train`` / ``eval`` subdir keeps the two pools
    physically separate so the scheduler cannot accidentally evaluate on
    a training level.
    """
    base = Path(base_dir)
    folder = (
        f"stage_{stage.stage_id}"
        f"_{stage.height}x{stage.width}"
        f"_{stage.n_agents}a"
        f"_{stage.n_lasers}L"
        f"_{stage.generator_name}"
    )
    return base / "levels" / folder / split


# ----- Generator factory ----------------------------------------------------


def _build_generator(stage: StageConfig, seed: int, profile: str | None = None):
    """Instantiate the registered generator for ``stage`` with ``seed``.

    All thesis generators currently in the registry share the
    :class:`generators.random.RandomGenerator` constructor signature
    (``size``, ``agents``, ``lasers``, ``t_max``, ``seed``), so a single
    factory works for ``random``, ``constructive``, ``cooperative``, and
    ``level6_style``. ``max_attempts`` is kept at the generator's default
    (10_000) — pool-level retries are handled by :func:`build_pool`.
    """
    if stage.generator_name not in GENERATOR_REGISTRY:
        raise KeyError(
            f"Generator {stage.generator_name!r} not in registry. "
            f"Known: {sorted(GENERATOR_REGISTRY)}"
        )
    cls = GENERATOR_REGISTRY[stage.generator_name]
    generator = cls(
        size=(stage.height, stage.width),
        agents=stage.n_agents,
        lasers=stage.n_lasers,
        t_max=stage.t_max,
        seed=seed,
    )
    # Profile-aware generators (e.g. ``cooperative``) expose a ``profile``
    # attribute used as an acceptance filter; non-profile generators ignore it.
    if profile is not None:
        generator.profile = profile
    return generator


# ----- Pool builder ---------------------------------------------------------


def build_pool(
    stage: StageConfig,
    seed: int,
    n_levels: int,
    max_attempts_per_level: int = 1000,
    profile: str | None = None,
) -> list[World]:
    """Generate ``n_levels`` solvable levels deterministically from ``seed``.

    Strategy: instantiate one generator with ``seed`` and call
    ``generate()`` repeatedly. Each call internally retries up to
    ``max_attempts_per_level`` times before giving up; we surface that
    failure as a clear :class:`RuntimeError` mentioning the stage and
    how many levels were already produced.

    Reproducibility: a single :class:`generators.random.RandomGenerator`
    instance with a fixed seed is the only source of randomness, so two
    invocations of ``build_pool(stage, seed, n)`` always produce the same
    sequence of worlds.
    """
    if n_levels <= 0:
        raise ValueError(f"n_levels must be positive, got {n_levels}")
    generator = _build_generator(stage, seed=seed, profile=profile)
    # Allow per-level retry budget without breaking the public default.
    generator.max_attempts = max_attempts_per_level
    pool: list[World] = []
    for i in range(n_levels):
        try:
            world = generator.generate()
        except RuntimeError as exc:
            raise RuntimeError(
                f"build_pool: failed to generate level {i + 1}/{n_levels} "
                f"for stage {stage.stage_id} ({stage.generator_name}, "
                f"{stage.height}x{stage.width}, {stage.n_lasers}L, "
                f"t_max={stage.t_max}) after {max_attempts_per_level} "
                f"attempts. Underlying error: {exc}"
            ) from exc
        pool.append(world)
    return pool


# ----- Save / load ----------------------------------------------------------


def _level_filename(index: int) -> str:
    return f"level_{index:03d}.json"


def save_pool(worlds: list[World], directory: Path | str) -> list[Path]:
    """Persist ``worlds`` to ``directory`` as ``level_NNN.json`` files.

    Returns the list of written paths (in order). Creates ``directory``
    (and any missing parents) if needed. Files use UTF-8.
    """
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, world in enumerate(worlds):
        path = out_dir / _level_filename(i)
        payload = {"world_string": world.world_string}
        path.write_text(json.dumps(payload), encoding="utf-8")
        written.append(path)
    return written


def load_pool(directory: Path | str) -> list[World]:
    """Reload a pool previously written by :func:`save_pool`.

    Files are sorted by filename so ``level_000.json`` comes first; any
    files that do not match ``level_NNN.json`` are ignored (lets the
    user drop READMEs into the same folder).
    """
    in_dir = Path(directory)
    if not in_dir.is_dir():
        raise FileNotFoundError(f"Pool directory does not exist: {in_dir}")
    files = sorted(
        p for p in in_dir.iterdir()
        if p.is_file() and p.name.startswith("level_") and p.suffix == ".json"
    )
    worlds: list[World] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            world_string = payload["world_string"]
        except KeyError as exc:
            raise ValueError(
                f"Level file {path} is missing 'world_string' key"
            ) from exc
        worlds.append(_world_from_string(world_string))
    return worlds


def _world_from_string(world_string: str) -> World:
    """Construct a fresh :class:`lle.World` from its serialised form.

    Encapsulated for easy mocking in tests and to make the ``lle`` API
    coupling explicit. ``lle.World`` accepts the world string directly.
    """
    # Touch ``lle`` so an LLE-import failure surfaces here, not in the
    # World constructor's C extension layer.
    assert lle.World is World
    return World(world_string)
