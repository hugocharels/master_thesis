"""LLE -> marl env adapter for the curriculum-transfer experiment.

This module bridges this thesis' procedurally generated `lle.World` objects
into something `marl` (yamoling/marl, dev branch) can train on, while
exposing a `gem_reward` knob that LLE itself does not provide as a public
parameter.

Design references:
- ``docs/superpowers/notes/marl-api.md`` (Section 1: ``EnvConfig`` adapter
  contract; Section 4 / 6: post-build reward-strategy injection for the
  ``gem_reward`` override).

Why a custom ``EnvConfig`` rather than ``LLEConfig``:
``marl.env.LLEConfig`` only accepts a hard-coded LLE level (1..6) or a
``.toml`` path on disk. Thesis generators produce in-memory ``lle.World``
objects, so we round-trip them through ``World.world_string`` and
``LLE.from_str(...)`` to keep the config JSON/dataclass serialisable while
still consuming any ``lle.World`` we like.

Why post-build mutation for ``gem_reward``:
Neither LLE's ``Builder`` nor any public LLE API exposes a per-event reward
weight. The cleanest hook is to swap ``env.reward_strategy`` after the
builder runs. ``LLE.__init__`` stores the strategy as a writable attribute,
so this is safe and survives ``env.reset()`` (which calls
``reward_strategy.reset()`` on the swapped instance).
"""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass

import lle
import numpy as np
from lle import EventType, World
from lle.env.reward_strategy import (
    REWARD_DEATH,
    REWARD_DONE,
    REWARD_EXIT,
    SingleObjective,
)
from marl.env import EnvConfig


@dataclass
class WeightedSingleObjective(SingleObjective):
    """Single-objective LLE reward with a configurable per-gem reward.

    Mirrors :class:`lle.env.reward_strategy.SingleObjective` but reads the
    gem reward from ``self.gem_reward`` instead of the module-level
    ``REWARD_GEM`` constant. ``exit``, ``death`` and ``done`` rewards keep
    their default values from LLE so that the only behavioural change is
    whether collecting a gem yields a positive scalar.
    """

    def __init__(self, n_agents: int, gem_reward: float = 1.0):
        super().__init__(n_agents)
        self.gem_reward = float(gem_reward)

    def compute_reward(self, events):
        reward = 0.0
        for event in events:
            match event.event_type:
                case EventType.AGENT_DIED:
                    reward += REWARD_DEATH
                    self.n_deads += 1
                case EventType.GEM_COLLECTED:
                    reward += self.gem_reward
                case EventType.AGENT_EXIT:
                    reward += REWARD_EXIT
                    self.n_arrived += 1
        if self.n_arrived == self.n_agents:
            reward += REWARD_DONE
        return np.array([reward], dtype=np.float32)


@dataclass
class ThesisLLEConfig(EnvConfig[lle.LLE]):
    """``marl.EnvConfig`` for any in-memory ``lle.World``.

    Parameters
    ----------
    world_toml:
        Serialised form of the world (``World.world_string``). Stored as a
        string so the config remains a plain dataclass and serialises cleanly
        through marl's :class:`Serializable` mixin.
    t_max:
        Episode horizon (truncation length) forwarded to marlenv's time-limit
        wrapper. Must be a positive integer.
    gem_reward:
        Reward emitted on each ``GEM_COLLECTED`` event. Defaults to ``0.0`` —
        the "no-shaping" arm of the curriculum experiment. Set to ``1.0`` to
        recover stock LLE behaviour.
    obs_type:
        Observation format (forwarded to ``lle.Builder.obs_type``). Defaults
        to ``"layered"`` (the canonical CNN format documented in
        ``marl-api.md`` section 1.3).
    state_type:
        Global-state format (forwarded to ``lle.Builder.state_type``).

    Notes
    -----
    The base ``EnvConfig.__post_init__`` calls ``self.make()`` and stores the
    fully wrapped env in ``self.env``. ``make()`` itself calls
    ``make_base_env()``, which is where we inject the ``WeightedSingleObjective``
    reward strategy.
    """

    world_toml: str
    _: KW_ONLY
    t_max: int = 21
    gem_reward: float = 0.0
    obs_type: str = "layered"
    state_type: str = "state"

    def __post_init__(self):
        # ``EnvConfig.time_limit`` is the field that marlenv's Builder uses to
        # add a time-limit wrapper. We expose ``t_max`` as the public name (it
        # matches the thesis solver's vocabulary) and keep them in sync.
        if self.t_max is not None and self.t_max <= 0:
            raise ValueError(f"t_max must be positive, got {self.t_max}")
        self.time_limit = self.t_max
        super().__post_init__()

    def make_base_env(self) -> lle.LLE:
        env = (
            lle.from_str(self.world_toml)
            .obs_type(self.obs_type)
            .state_type(self.state_type)
            .build()
        )
        # Post-build reward-strategy swap (notes section 6). LLE has no public
        # gem-reward parameter, so we replace the strategy on the freshly
        # constructed env. The new strategy is reset by ``env.reset()`` via
        # ``self.reward_strategy.reset()``.
        env.reward_strategy = WeightedSingleObjective(
            env.n_agents, gem_reward=self.gem_reward
        )
        return env

    @classmethod
    def from_world(
        cls,
        world: World,
        *,
        t_max: int = 21,
        gem_reward: float = 0.0,
        obs_type: str = "layered",
        state_type: str = "state",
    ) -> "ThesisLLEConfig":
        """Construct a config directly from an in-memory ``lle.World``.

        Convenience for thesis generators that hand back ``World`` objects
        rather than serialised strings.
        """
        return cls(
            world_toml=world.world_string,
            t_max=t_max,
            gem_reward=gem_reward,
            obs_type=obs_type,
            state_type=state_type,
        )
