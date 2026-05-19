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
from marlenv.models import MARLEnv
from marlenv.wrappers.rlenv_wrapper import RLEnvWrapper


@dataclass
class WeightedSingleObjective(SingleObjective):
    """Single-objective LLE reward with configurable gem reward and step penalty.

    Mirrors :class:`lle.env.reward_strategy.SingleObjective` but reads the
    gem reward from ``self.gem_reward`` instead of the module-level
    ``REWARD_GEM`` constant, and subtracts a small ``step_penalty`` from
    every step so the agent receives a non-trivial gradient signal even
    on stages with no lasers and no gems. Without it, stage 1 of the
    curriculum (no laser, no gem, only sparse +REWARD_EXIT on team exit)
    is identically zero-reward under random exploration and unlearnable
    from a cold start.
    """

    def __init__(self, n_agents: int, gem_reward: float = 1.0, step_penalty: float = 0.0):
        super().__init__(n_agents)
        self.gem_reward = float(gem_reward)
        self.step_penalty = float(step_penalty)

    def compute_reward(self, events):
        reward = -self.step_penalty
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
    step_penalty: float = 0.0
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
            env.n_agents,
            gem_reward=self.gem_reward,
            step_penalty=self.step_penalty,
        )
        return env

    @classmethod
    def from_world(
        cls,
        world: World,
        *,
        t_max: int = 21,
        gem_reward: float = 0.0,
        step_penalty: float = 0.0,
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
            step_penalty=step_penalty,
            obs_type=obs_type,
            state_type=state_type,
        )


class PadObservations3D(RLEnvWrapper):
    """Pad 3D ``(C, H, W)`` observations and (optionally) 1D state with zeros.

    LLE's layered observation has shape ``(C, H, W)`` whose channel count
    depends on the number of laser colours and whose spatial extent
    matches the grid. LLE's state vector also varies in length because
    it stores per-gem indicator flags (Level 6 has 4 gems, the thesis
    generators produce 0-gem worlds). The Q-network and the QMix mixer
    must each be sized once for *all* envs that will be fed in, so
    per-episode envs are wrapped to expose a single homogenised
    observation- and state-shape. Padding is bottom-right on the spatial
    axes, and at the end on the trailing axis for both channels and
    state features.

    Parameters
    ----------
    target_shape:
        Target ``(C, H, W)`` for the observation.
    target_state_shape:
        Optional target shape for the 1D state vector. ``None`` leaves
        the state untouched. When provided, must be a one-element tuple
        whose value is at least as large as the wrapped env's
        ``state_shape``.
    """

    target_shape: tuple[int, int, int]
    target_state_shape: tuple[int, ...] | None

    def __init__(
        self,
        env: MARLEnv,
        target_shape: tuple[int, int, int],
        target_state_shape: tuple[int, ...] | None = None,
    ) -> None:
        if len(env.observation_shape) != 3:
            raise ValueError(
                f"PadObservations3D expects 3D observations, "
                f"got shape {env.observation_shape}"
            )
        c, h, w = env.observation_shape
        tc, th, tw = target_shape
        if tc < c or th < h or tw < w:
            raise ValueError(
                f"target_shape {target_shape} is smaller than the wrapped "
                f"env's observation_shape {env.observation_shape}"
            )

        state_kwargs: dict = {}
        self._state_pad_width: tuple[tuple[int, int], ...] | None = None
        if target_state_shape is not None:
            if len(env.state_shape) != 1 or len(target_state_shape) != 1:
                raise ValueError(
                    f"target_state_shape only supports 1D states, got "
                    f"env.state_shape={env.state_shape}, "
                    f"target_state_shape={target_state_shape}"
                )
            s = env.state_shape[0]
            ts = target_state_shape[0]
            if ts < s:
                raise ValueError(
                    f"target_state_shape {target_state_shape} is smaller "
                    f"than the wrapped env's state_shape {env.state_shape}"
                )
            self._state_pad_width = ((0, ts - s),)
            state_kwargs["state_shape"] = target_state_shape

        super().__init__(env, observation_shape=target_shape, **state_kwargs)
        self.target_shape = target_shape
        self.target_state_shape = target_state_shape
        self._pad_widths_data = (
            (0, 0),                # n_agents axis: unchanged
            (0, tc - c),           # channels: pad at the end
            (0, th - h),           # height: pad at the bottom
            (0, tw - w),           # width: pad at the right
        )

    def _pad_obs(self, obs):
        if obs.data.shape[1:] != self.target_shape:
            obs.data = np.pad(
                obs.data, self._pad_widths_data, mode="constant", constant_values=0.0
            ).astype(np.float32, copy=False)
        return obs

    def _pad_state(self, state):
        if self._state_pad_width is None:
            return state
        if state.data.shape == self.target_state_shape:
            return state
        state.data = np.pad(
            state.data, self._state_pad_width, mode="constant", constant_values=0.0
        ).astype(np.float32, copy=False)
        return state

    def reset(self, *, seed: int | None = None):
        obs, state = super().reset(seed=seed)
        return self._pad_obs(obs), self._pad_state(state)

    def step(self, action):
        step = super().step(action)
        step.obs = self._pad_obs(step.obs)
        step.state = self._pad_state(step.state)
        return step

    def get_observation(self):
        return self._pad_obs(super().get_observation())

    def get_state(self):
        return self._pad_state(super().get_state())
