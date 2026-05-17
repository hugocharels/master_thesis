"""Static configuration for the curriculum-transfer MARL experiment.

This module is the single source of truth for the per-stage geometry
(grid size, agent count, laser count, horizon, generator) and for the
training-budget constants shared across the four conditions
(``B1``, ``B2``, ``B3``, ``CURR``) and the three algorithms
(``QMIX``, ``VDN``, ``IQL``).

References
----------
- Thesis chapter ``thesis/chapters/experiments.typ``: motivates the
  RQ4 transfer protocol and lists the thesis-side names of the
  generators (``constructive_solvable``, ``constructive_cooperative``,
  ``constructive_level6_style``).
- ``src/generators/registry.py``: the authoritative registry of
  generator string keys actually accepted at runtime (``random``,
  ``constructive``, ``cooperative``, ``level6_style``, ...).

Generator-name discrepancy (important):
    The thesis text uses **descriptive** generator names
    (``constructive_solvable`` for ``constructive``,
    ``constructive_cooperative`` for ``cooperative``,
    ``constructive_level6_style`` for ``level6_style``). The runtime
    ``GENERATOR_REGISTRY`` uses the shorter, canonical keys. We expose
    the registry keys here because they are what
    :func:`generators.registry.GENERATOR_REGISTRY.__getitem__` actually
    accepts. The constants ``THESIS_GENERATOR_NAMES`` document the
    1:1 mapping for cross-referencing.
"""

from __future__ import annotations

from dataclasses import dataclass


# -- Random-number-generator master seed -----------------------------------
#
# Used as the base for every per-stage seed in the experiment. A single
# integer is enough to make the entire pre-flight pool generation
# deterministic (see ``pool_generator.build_pool`` and
# ``_preflight_generate_pools``).
RNG_SEED: int = 20260514


# -- Per-stage geometry --------------------------------------------------------


@dataclass(frozen=True)
class StageConfig:
    """Frozen per-stage geometry / generator / training-budget parameters.

    Attributes
    ----------
    stage_id:
        1-based curriculum stage index. Used for pool-folder names and
        for deriving per-stage seeds from :data:`RNG_SEED`.
    height, width:
        Grid dimensions (rows, columns). Match the thesis design table.
    n_agents:
        Number of cooperating agents. Constant at 4 across the
        curriculum to keep the trained Q-networks compatible across
        stages.
    n_lasers:
        Number of laser beams placed by the generator.
    t_max:
        Episode horizon used both at generation time (SAT solver
        ``T_MAX``) and at training time (env time-limit).
    generator_name:
        Key into :data:`generators.registry.GENERATOR_REGISTRY`. Must
        be one of the registered names (see module docstring).
    pool_size:
        Number of distinct training levels to generate for this stage.
    eval_pool_size:
        Number of held-out evaluation levels to generate for this stage
        (only stage 4 has a non-zero eval pool in the current design;
        earlier stages reuse the training pool for evaluation).
    per_stage_step_cap_full, per_stage_step_cap_pilot:
        Maximum number of environment steps the curriculum scheduler
        may spend on this stage before forcing a transition. ``full``
        corresponds to the 1.5M-step budget; ``pilot`` halves it.
    """

    stage_id: int
    height: int
    width: int
    n_agents: int
    n_lasers: int
    t_max: int
    generator_name: str
    pool_size: int
    eval_pool_size: int
    per_stage_step_cap_full: int
    per_stage_step_cap_pilot: int


# -- Generator-name mapping (thesis text <-> runtime registry) ----------------
#
# The thesis uses long descriptive names; the registry uses short keys.
# Phase 3 / 4 implementers should consume ``stage.generator_name`` (the
# registry key); this dict is documentation-only.
THESIS_GENERATOR_NAMES: dict[str, str] = {
    # registry key                : thesis text name
    "random":            "constrained_random_solvable",
    "constructive":      "constructive_solvable",
    "cooperative":       "constructive_cooperative",
    "level6_style":      "constructive_level6_style",
}


# -- The four-stage curriculum (thesis design) --------------------------------

CURRICULUM_STAGES: tuple[StageConfig, ...] = (
    # Per-stage step caps are intentionally asymmetric: early-stage
    # navigation / single-laser tasks need less training than the
    # level-6-style target stage. The totals sum to FULL_RUN_TOTAL_STEPS
    # (1,500,000) and PILOT_RUN_TOTAL_STEPS (750,000) below.
    #
    #   Stage 1 (warmup):       200k full /  100k pilot
    #   Stage 2 (1 laser):      250k full /  125k pilot
    #   Stage 3 (2 lasers):     300k full /  150k pilot
    #   Stage 4 (level6 style): 750k full /  375k pilot
    #
    # Sums:                   1,500k full / 750k pilot.
    StageConfig(
        stage_id=1,
        height=6,
        width=6,
        n_agents=4,
        # Laser count follows the curriculum progression: 0, 1, 2, 3 from
        # stage 1 to stage 4. Stage 1 is a pure-navigation warmup (no
        # laser, no cooperation pressure), generated by the random
        # solvable generator.
        n_lasers=0,
        t_max=12,
        generator_name="random",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=200_000,
        per_stage_step_cap_pilot=100_000,
    ),
    StageConfig(
        stage_id=2,
        height=8,
        width=8,
        n_agents=4,
        n_lasers=1,
        t_max=16,
        # Thesis name: ``constructive_cooperative`` -> registry key ``cooperative``
        generator_name="cooperative",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=250_000,
        per_stage_step_cap_pilot=125_000,
    ),
    StageConfig(
        stage_id=3,
        height=10,
        width=10,
        n_agents=4,
        n_lasers=2,
        t_max=18,
        generator_name="cooperative",
        pool_size=50,
        eval_pool_size=0,
        per_stage_step_cap_full=300_000,
        per_stage_step_cap_pilot=150_000,
    ),
    StageConfig(
        stage_id=4,
        height=12,
        width=13,
        n_agents=4,
        n_lasers=3,
        t_max=21,
        # Thesis name: ``constructive_level6_style`` -> registry key ``level6_style``
        generator_name="level6_style",
        pool_size=50,
        eval_pool_size=50,
        per_stage_step_cap_full=750_000,
        per_stage_step_cap_pilot=375_000,
    ),
)


# -- Curriculum advancement criterion ----------------------------------------
#
# The scheduler advances from stage k to stage k+1 once the rolling
# success rate over the most recent ``ADVANCEMENT_WINDOW_EPISODES``
# training episodes reaches ``ADVANCEMENT_SUCCESS_THRESHOLD``. If the
# threshold is not met within the per-stage step cap, the scheduler
# advances anyway (preventing pathological lock-ups on a hard stage).
ADVANCEMENT_SUCCESS_THRESHOLD: float = 0.80
ADVANCEMENT_WINDOW_EPISODES: int = 100


# -- Total training budgets ---------------------------------------------------
#
# Phase 4 chooses between the two by passing ``--pilot`` or not.
FULL_RUN_TOTAL_STEPS: int = 1_500_000
PILOT_RUN_TOTAL_STEPS: int = 750_000


# -- Periodic-evaluation cadence ---------------------------------------------

EVAL_FREQUENCY_STEPS: int = 20_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200


# -- Experimental design space -----------------------------------------------

CONDITIONS: tuple[str, ...] = ("B1", "B2", "B3", "CURR")
ALGORITHMS: tuple[str, ...] = ("QMIX", "VDN", "IQL")
