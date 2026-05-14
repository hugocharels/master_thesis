"""Tests for the LLE -> marl env adapter.

Run with the marl venv:

    & C:\\Users\\hugoc\\Projects\\marl\\.venv\\Scripts\\python.exe -m pytest \\
        src/tests/experiments/curriculum/test_lle_marl_env.py
"""

from __future__ import annotations

import numpy as np
import pytest
from lle import World

from experiments.curriculum.lle_marl_env import ThesisLLEConfig

# Reference for marl/lle API contracts: docs/superpowers/notes/marl-api.md.
# In particular:
#   - EnvConfig.__post_init__ builds env into self.env (notes section 1.1).
#   - LLE.reset() returns (Observation, State); env.step(action) returns a Step
#     dataclass with .reward (np.ndarray, shape (1,) for SingleObjective) and
#     .done (bool); see notes section 1.3.
#   - gem_reward override is applied post-build by swapping reward_strategy
#     (notes section 6).


def _build_config(gem_reward: float = 0.0, t_max: int = 21) -> ThesisLLEConfig:
    """Build a ThesisLLEConfig for LLE level 6 with the given gem_reward."""
    world = World.level(6)
    return ThesisLLEConfig.from_world(world, t_max=t_max, gem_reward=gem_reward)


def test_construction_from_world_succeeds():
    """The adapter accepts an lle.World and exposes a usable env."""
    cfg = _build_config()
    assert cfg.n_agents == 4  # LLE level 6 has 4 agents
    # EnvConfig wraps make_base_env() into self.env via __post_init__.
    assert cfg.env is not None
    # Time limit was passed through to the marlenv wrapper.
    assert cfg.time_limit == 21


def test_reset_returns_observation_for_all_agents():
    """env.reset() returns (Observation, State) where Observation covers all agents."""
    cfg = _build_config()
    env = cfg.env
    obs, state = env.reset()
    # marlenv Observation has .data of shape (n_agents, ...) for layered obs.
    assert obs.data.shape[0] == cfg.n_agents
    # State has .data for the global state vector.
    assert state.data is not None


def test_step_with_noop_returns_numeric_reward_and_bool_done():
    """A single noop step yields a numeric reward array and a bool done flag."""
    cfg = _build_config()
    env = cfg.env
    env.reset()
    # Action 4 is STAY (noop) per lle.Action.variants() ordering:
    # NORTH, SOUTH, EAST, WEST, STAY.
    noop = np.full(cfg.n_agents, 4, dtype=np.int64)
    step = env.step(noop)
    assert step.reward is not None
    assert step.reward.shape == (1,), f"expected SingleObjective reward, got shape {step.reward.shape}"
    assert np.issubdtype(step.reward.dtype, np.floating)
    assert isinstance(step.done, (bool, np.bool_))
    assert step.done is False or step.done == False  # noqa: E712  - first noop should not terminate


def test_gem_reward_zero_keeps_reward_nonpositive_for_noops():
    """With gem_reward=0 and noop actions, no positive reward can accumulate.

    Standing still cannot collect gems and (from the level 6 spawn tiles)
    cannot trigger an own-color laser death within a few steps. The cumulative
    reward must therefore be 0 for a short noop trajectory. We assert <= 0 to
    leave room for a hypothetical death penalty (which should not happen here
    but is the only other reward source after disabling gems).
    """
    cfg = _build_config(gem_reward=0.0)
    env = cfg.env
    env.reset()
    noop = np.full(cfg.n_agents, 4, dtype=np.int64)
    cumulative = 0.0
    for _ in range(5):
        step = env.step(noop)
        cumulative += float(step.reward[0])
        if step.done:
            break
    assert cumulative <= 0.0, f"gem_reward=0 should yield non-positive cumulative reward, got {cumulative}"


def test_n_agents_property_matches_world():
    """The adapter exposes the underlying world's agent count."""
    cfg = _build_config()
    # Level 6 has 4 agents; the property must agree with the env.
    assert cfg.n_agents == cfg.env.n_agents == 4


def test_default_gem_reward_is_zero():
    """The default `gem_reward` is 0.0 (the no-shaping arm of the experiment)."""
    world = World.level(6)
    cfg = ThesisLLEConfig.from_world(world, t_max=21)
    assert cfg.gem_reward == 0.0


@pytest.mark.parametrize("t_max", [5, 21, 50])
def test_time_limit_is_propagated(t_max):
    """`t_max` is forwarded to the marlenv time-limit wrapper."""
    cfg = _build_config(t_max=t_max)
    assert cfg.time_limit == t_max
