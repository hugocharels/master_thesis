"""Static configuration for the learnability experiment.

Smaller-grid debug configuration: 5x5 grid, 2 agents, 1 laser,
cooperative generator. Used to test whether MARL can learn anything
at all on cooperative levels -- the 8x8/3a/2L version produced 0%
success across 60 cells, which left open the question of whether
the algorithm is fundamentally unable or whether the 8x8 task is
simply too hard for the 200k-step budget.

The earlier 8x8/3a/2L results are preserved under
``results/learnability/`` (file system) and at commit 3279ed0 onward
(git history). This run writes to ``results/learnability_5x5/``.

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
    height=5,
    width=5,
    n_agents=2,
    n_lasers=1,
    t_max=10,
    generator_name="cooperative",
)

RNG_SEED: int = 20260618
TRAIN_POOL_SIZE: int = 20
TEST_POOL_SIZE: int = 20

ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")
TOTAL_STEPS: int = 200_000
EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200
