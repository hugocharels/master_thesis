"""Generate, persist, and reload level pools as plain .txt files.

Each level is stored as a raw ``world.world_string`` in a .txt file,
matching the convention used by LLE and the rest of the thesis code.
"""

from __future__ import annotations

from pathlib import Path

from lle import World

from experiments.learnability.configs import GridConfig
from generators.registry import GENERATOR_REGISTRY


def pool_dir(base_dir: Path, config: GridConfig, split: str) -> Path:
    """Return the canonical directory for a pool split.

    Layout::

        levels/
          {h}x{w}_{n_agents}a_{n_lasers}L_{generator}/
            train/
            test/
    """
    folder = (
        f"{config.height}x{config.width}"
        f"_{config.n_agents}a"
        f"_{config.n_lasers}L"
        f"_{config.generator_name}"
    )
    return Path(base_dir) / "levels" / folder / split


def build_pool(
    config: GridConfig,
    seed: int,
    n_levels: int,
    max_attempts_per_level: int = 1000,
) -> list[World]:
    """Generate ``n_levels`` cooperative levels deterministically."""
    cls = GENERATOR_REGISTRY[config.generator_name]
    generator = cls(
        size=(config.height, config.width),
        agents=config.n_agents,
        lasers=config.n_lasers,
        t_max=config.t_max,
        seed=seed,
    )
    generator.max_attempts = max_attempts_per_level
    pool: list[World] = []
    for i in range(n_levels):
        try:
            world = generator.generate()
        except RuntimeError as exc:
            raise RuntimeError(
                f"Failed to generate level {i + 1}/{n_levels} "
                f"({config.generator_name}, {config.height}x{config.width})"
            ) from exc
        pool.append(world)
    return pool


def save_pool(worlds: list[World], directory: Path | str) -> list[Path]:
    """Persist worlds as ``level_NNN.txt`` (raw world string)."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, world in enumerate(worlds):
        path = out / f"level_{i:03d}.txt"
        path.write_text(world.world_string, encoding="utf-8")
        written.append(path)
    return written


def load_pool(directory: Path | str) -> list[World]:
    """Reload a pool of .txt world-string files."""
    d = Path(directory)
    if not d.is_dir():
        raise FileNotFoundError(f"Pool directory does not exist: {d}")
    files = sorted(
        p for p in d.iterdir()
        if p.is_file() and p.name.startswith("level_") and p.suffix == ".txt"
    )
    return [World(f.read_text(encoding="utf-8")) for f in files]
