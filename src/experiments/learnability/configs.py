"""Static configuration for the learnability experiment.

Phase 1: 6x6 grid, 2 agents, 1 laser, cooperative generator.
Phase 2: 8x8 grid, 3 agents, 2 lasers, cooperative generator.
Train on 20 generated levels, eval on 20 held-out generated levels.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridConfig:
    """Grid geometry and generator for one experimental phase."""

    height: int
    width: int
    n_agents: int
    n_lasers: int
    t_max: int
    generator_name: str


PHASE1_GRID = GridConfig(
    height=6,
    width=6,
    n_agents=2,
    n_lasers=1,
    t_max=10,
    generator_name="cooperative",
)

PHASE2_GRID = GridConfig(
    height=8,
    width=8,
    n_agents=3,
    n_lasers=2,
    t_max=16,
    generator_name="cooperative",
)

PHASES: dict[int, GridConfig] = {1: PHASE1_GRID, 2: PHASE2_GRID}

RNG_SEED: int = 20260515
TRAIN_POOL_SIZE: int = 20
TEST_POOL_SIZE: int = 20

ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")
TOTAL_STEPS: int = 200_000
EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200
