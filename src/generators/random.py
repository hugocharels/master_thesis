"""Random-sampling generators."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from lle import World

from generators.base import BaseGenerator
from generators.candidates import CandidateLayout
from generators.geometry import beam_tiles, in_bounds, points_out_immediately
from generators.registry import register_generator
from generators.world_builder import WorldBuilder
from solver import WorldSolver

if TYPE_CHECKING:
    from solver import CooperationProfileAnalyzer  # for typing only


@register_generator("random")
class RandomGenerator(BaseGenerator):
    """
    Random world generator that samples a fully-random layout, optionally
    enforces geometric constraints (no laser-points-outside, non-zero beam,
    no exit on beam tile), and SAT-verifies solvability.
    """

    def __init__(
        self,
        size: tuple[int, int],
        agents: int = 2,
        lasers: int | None = None,
        num_walls: int | None = None,
        t_max: int | None = None,
        t_min: int = 0,
        max_attempts: int = 10_000,
        seed: int | None = None,
        validate_geometry: bool = True,
    ):
        self.rows, self.cols = size
        if self.rows < 1 or self.cols < 1:
            raise ValueError(f"grid dimensions must be >= 1. Got size={size}")
        self.area = self.rows * self.cols

        if agents < 1:
            raise ValueError(f"agents must be >= 1. Got {agents}")
        self.agents = agents
        self.lasers = (agents - 1) if lasers is None else lasers
        self.num_walls = (self.area // 10) if num_walls is None else num_walls
        self.t_max = (self.area // 2) if t_max is None else t_max
        self.t_min = t_min
        self.max_attempts = max_attempts
        self.validate_geometry = validate_geometry

        if self.lasers < 0:
            raise ValueError(f"lasers must be >= 0. Got {self.lasers}")
        if self.lasers > self.agents:
            raise ValueError(
                f"lasers must be <= agents to keep one laser source per colour "
                f"(SAT encoding assumption, see Definition 3.1). "
                f"Got lasers={self.lasers}, agents={self.agents}."
            )
        if self.num_walls < 0:
            raise ValueError(f"num_walls must be >= 0. Got {self.num_walls}")
        if self.t_max < 0:
            raise ValueError(f"t_max must be >= 0. Got {self.t_max}")
        if self.num_walls >= (self.area / 2):
            raise ValueError(
                f"num_walls must be < size/2. Got num_walls={self.num_walls}, "
                f"size={self.area}"
            )
        if self.t_min < 0:
            raise ValueError(f"t_min must be >= 0. Got {self.t_min}")
        if self.t_min > self.t_max:
            raise ValueError(
                f"t_min must be <= t_max. Got t_min={self.t_min}, t_max={self.t_max}"
            )
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1. Got {self.max_attempts}")
        total_needed = (2 * self.agents) + self.num_walls + self.lasers
        if total_needed > self.area:
            raise ValueError(
                f"layout requires {total_needed} unique cells, "
                f"but grid has only {self.area}"
            )

        self._rng = random.Random(seed)
        self.debug_rejections = False
        self.last_attempts = 0

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            "--size",
            nargs=2,
            type=int,
            metavar=("ROWS", "COLS"),
            required=True,
            help="Grid size as two integers: ROWS COLS",
        )
        parser.add_argument("--agents", type=int, default=2)
        parser.add_argument("--lasers", type=int, default=None)
        parser.add_argument("--num-walls", type=int, default=None)
        parser.add_argument("--t-max", type=int, default=None)
        parser.add_argument(
            "--t-min",
            type=int,
            default=0,
            help="Minimum number of steps required for a valid level (default: 0)",
        )
        parser.add_argument("--max-attempts", type=int, default=10_000)
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument(
            "--no-validate-geometry",
            dest="validate_geometry",
            action="store_false",
            default=True,
            help="Disable geometric validation (lasers may point outside, beams may be zero-length).",
        )
        parser.add_argument(
            "--debug-rejections",
            action="store_true",
            help="Print rejection reasons while sampling",
        )

    @classmethod
    def from_args(cls, args):
        obj = cls(
            size=tuple(args.size),
            agents=args.agents,
            lasers=args.lasers,
            num_walls=args.num_walls,
            t_max=args.t_max,
            t_min=args.t_min,
            max_attempts=args.max_attempts,
            seed=args.seed,
            validate_geometry=getattr(args, "validate_geometry", True),
        )
        obj.debug_rejections = bool(getattr(args, "debug_rejections", False))
        return obj

    # ----- sampling -----

    def _sample_unique_positions(self, k: int) -> list[tuple[int, int]]:
        all_positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        return self._rng.sample(all_positions, k)

    def _random_direction(self):
        from lle import Direction
        return self._rng.choice(
            [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
        )

    def _make_candidate_layout(self) -> CandidateLayout:
        total_needed = self.agents + self.agents + self.num_walls + self.lasers
        chosen = self._sample_unique_positions(total_needed)
        idx = 0
        agent_positions = chosen[idx : idx + self.agents]
        idx += self.agents
        exit_positions = chosen[idx : idx + self.agents]
        idx += self.agents
        wall_positions = chosen[idx : idx + self.num_walls]
        idx += self.num_walls
        laser_positions = chosen[idx : idx + self.lasers]
        lasers = [
            (i, pos, self._random_direction()) for i, pos in enumerate(laser_positions)
        ]
        return CandidateLayout(
            agents=agent_positions,
            exits=exit_positions,
            walls=wall_positions,
            lasers=lasers,
        )

    def _build_world_from_layout(self, layout: CandidateLayout) -> World:
        b = WorldBuilder(self.cols, self.rows)
        for agent_id, pos in enumerate(layout.agents):
            b.add_agent(agent_id, pos)
        for pos in layout.exits:
            b.add_exit(pos)
        for pos in layout.walls:
            b.add_wall(pos)
        for owner, pos, direction in layout.lasers:
            b.add_laser(owner, pos, direction)
        return b.build()

    # ----- validation -----

    def validate_candidate(self, layout: CandidateLayout) -> tuple[bool, str]:
        if not self.validate_geometry:
            return True, "ok"
        wall_set = set(layout.walls)
        laser_set = {pos for _, pos, _ in layout.lasers}
        exit_set = set(layout.exits)
        all_beam_tiles: set[tuple[int, int]] = set()
        for _owner, src, direction in layout.lasers:
            if points_out_immediately(src, direction, self.rows, self.cols):
                return False, f"laser_points_outside_immediately@{src}"
            tiles = beam_tiles(src, direction, wall_set, laser_set, self.rows, self.cols)
            if not tiles:
                return False, f"laser_zero_beam@{src}"
            all_beam_tiles.update(tiles)
        overlap = exit_set.intersection(all_beam_tiles)
        if overlap:
            return False, f"exit_on_laser_beam@{sorted(overlap)}"
        return True, "ok"

    # ----- SAT acceptance -----

    def _accept_world(self, world: World) -> tuple[bool, str]:
        if not self._meets_difficulty_window(world):
            return (
                False,
                f"outside_difficulty_window[t_min={self.t_min}, t_max={self.t_max}]",
            )
        return True, "satisfiable"

    def _is_satisfiable(self, world: World, t: int) -> bool:
        world.reset()
        result, _ = WorldSolver(world, T_MAX=t).solve()
        return bool(result)

    def _meets_difficulty_window(self, world: World) -> bool:
        if not self._is_satisfiable(world, self.t_max):
            return False
        if self.t_min == 0:
            return True
        return not self._is_satisfiable(world, self.t_min - 1)

    def _failure_description(self) -> str:
        return "a valid solvable world"

    def _debug_reject(self, attempt: int, reason: str) -> None:
        if self.debug_rejections:
            print(f"[reject #{attempt}] {reason}")

    def _debug_accept(self, attempt: int, reason: str) -> None:
        if self.debug_rejections:
            print(f"[accept #{attempt}] {reason}")

    def generate(self) -> World:
        self.last_attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            self.last_attempts = attempt
            layout = self._make_candidate_layout()
            valid, reason = self.validate_candidate(layout)
            if not valid:
                self._debug_reject(attempt, f"invalid_layout={reason}")
                continue
            try:
                world = self._build_world_from_layout(layout)
            except Exception as exc:
                self._debug_reject(attempt, f"lle_build_error={type(exc).__name__}")
                continue
            try:
                accepted, reason = self._accept_world(world)
                if accepted:
                    self._debug_accept(attempt, reason)
                    return world
                self._debug_reject(attempt, reason)
            except Exception as exc:
                self._debug_reject(attempt, f"solver_error={type(exc).__name__}")
                continue
        raise RuntimeError(
            f"Could not find {self._failure_description()} in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )


# ===== Cooperative random variants (thesis-only — likely not moved to LLE) =====


_COOP_PROFILE_CHOICES = (
    "cooperative",
    "asymmetric",
    "mutual",
    "chain",
    "distributed",
    "fully_coupled",
)


class _RandomCooperativeBase(RandomGenerator):
    """Shared logic for random cooperative variants — applies a profile filter."""

    def __init__(self, *args, profile: str = "cooperative", **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile

    @staticmethod
    def add_arguments(parser):
        RandomGenerator.add_arguments(parser)
        parser.add_argument(
            "--profile",
            choices=list(_COOP_PROFILE_CHOICES),
            default="cooperative",
            help="Target cooperation profile for accepted levels",
        )

    @classmethod
    def from_args(cls, args):
        obj = cls(
            size=tuple(args.size),
            agents=args.agents,
            lasers=args.lasers,
            num_walls=args.num_walls,
            t_max=args.t_max,
            t_min=args.t_min,
            max_attempts=args.max_attempts,
            seed=args.seed,
            validate_geometry=getattr(args, "validate_geometry", cls._default_validate_geometry()),
            profile=args.profile,
        )
        obj.debug_rejections = bool(getattr(args, "debug_rejections", False))
        return obj

    @staticmethod
    def _default_validate_geometry() -> bool:
        return True

    def _analyze_profile(self, world):
        from solver import CooperationProfileAnalyzer
        world.reset()
        return CooperationProfileAnalyzer(world, T_MAX=self.t_max).analyze()

    def _accept_world(self, world):
        accepted, reason = super()._accept_world(world)
        if not accepted:
            return accepted, reason
        analysis = self._analyze_profile(world)
        if not analysis.matches_profile(self.profile):
            return (
                False,
                f"profile={analysis.profile}, required={self.profile}",
            )
        return True, f"profile={analysis.profile}, cooperative_and_solvable"


@register_generator("random_cooperative")
class RandomCooperativeGenerator(_RandomCooperativeBase):
    """Random sampling (no geometric validation) + cooperation profile filter."""

    def __init__(self, *args, validate_geometry: bool = False, **kwargs):
        super().__init__(*args, validate_geometry=validate_geometry, **kwargs)

    @staticmethod
    def _default_validate_geometry() -> bool:
        return False

    def _failure_description(self) -> str:
        return "a cooperative solvable world"


@register_generator("constrained_random_cooperative")
class ConstrainedRandomCooperativeGenerator(_RandomCooperativeBase):
    """Random sampling with geometric validation + cooperation profile filter."""

    def __init__(self, *args, validate_geometry: bool = True, **kwargs):
        super().__init__(*args, validate_geometry=validate_geometry, **kwargs)

    @staticmethod
    def _default_validate_geometry() -> bool:
        return True

    def _failure_description(self) -> str:
        return "a valid constrained cooperative world"
