"""Static configuration for the learnability experiment.

Single configuration: 8x8 grid, 3 agents, 2 lasers, cooperative generator.
Train on 20 generated levels, eval on 20 held-out generated levels.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridConfig:
    """Grid geometry and generator for the learnability experiment."""

    height: int
    width: int
    n_agents: int
    n_lasers: int
    t_max: int
    generator_name: str


GRID = GridConfig(
    height=8,
    width=8,
    n_agents=3,
    n_lasers=2,
    t_max=16,
    generator_name="cooperative",
)

RNG_SEED: int = 20260615
TRAIN_POOL_SIZE: int = 20
TEST_POOL_SIZE: int = 20

ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")
TOTAL_STEPS: int = 200_000
EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200
