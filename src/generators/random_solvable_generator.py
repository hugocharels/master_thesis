import random
from dataclasses import dataclass

from lle import World

from generators.base_generator import BaseGenerator
from generators.registry import register_generator
from generators.world_builder import Direction, WorldBuilder
from solver import LLEAdapter, WorldSolver


@dataclass(frozen=True)
class CandidateLayout:
    agents: list[tuple[int, int]]
    exits: list[tuple[int, int]]
    walls: list[tuple[int, int]]
    lasers: list[tuple[int, tuple[int, int], Direction]]  # (owner, pos, dir)


@register_generator("random_solvable")
class RandomSolvableGenerator(BaseGenerator):
    """
    Random world generator that keeps sampling until it finds a world that:
      1) can be successfully built by LLE,
      2) is solvable by the SAT solver within T_MAX,
      3) optionally requires at least T_MIN steps (if T_MIN is set).
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
    ):
        self.rows, self.cols = size
        if self.rows < 1 or self.cols < 1:
            raise ValueError(
                f"grid dimensions must be >= 1. Got size={size}"
            )
        self.area = self.rows * self.cols

        if agents < 1:
            raise ValueError(f"agents must be >= 1. Got {agents}")
        self.agents = agents
        self.lasers = (agents - 1) if lasers is None else lasers
        self.num_walls = (self.area // 10) if num_walls is None else num_walls
        self.t_max = (self.area // 2) if t_max is None else t_max
        self.t_min = t_min
        self.max_attempts = max_attempts

        if self.lasers < 0:
            raise ValueError(f"lasers must be >= 0. Got {self.lasers}")

        if self.num_walls < 0:
            raise ValueError(f"num_walls must be >= 0. Got {self.num_walls}")

        if self.t_max < 0:
            raise ValueError(f"t_max must be >= 0. Got {self.t_max}")

        # Requested logical constraint
        if self.num_walls >= (self.area / 2):
            raise ValueError(
                f"num_walls must be < size/2. Got num_walls={self.num_walls}, size={self.area}"
            )

        if self.t_min < 0:
            raise ValueError(f"t_min must be >= 0. Got {self.t_min}")

        if self.t_min > self.t_max:
            raise ValueError(
                f"t_min must be <= t_max. Got t_min={self.t_min}, t_max={self.t_max}"
            )

        if self.max_attempts < 1:
            raise ValueError(
                f"max_attempts must be >= 1. Got {self.max_attempts}"
            )

        total_needed = (2 * self.agents) + self.num_walls + self.lasers
        if total_needed > self.area:
            raise ValueError(
                f"layout requires {total_needed} unique cells, but grid has only {self.area}"
            )

        self._rng = random.Random(seed)

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

    @classmethod
    def from_args(cls, args):
        return cls(
            size=tuple(args.size),
            agents=args.agents,
            lasers=args.lasers,
            num_walls=args.num_walls,
            t_max=args.t_max,
            t_min=args.t_min,
            max_attempts=args.max_attempts,
            seed=args.seed,
        )

    def _sample_unique_positions(self, k: int) -> list[tuple[int, int]]:
        all_positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        return self._rng.sample(all_positions, k)

    def _random_direction(self) -> Direction:
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

        lasers = []
        for i, pos in enumerate(laser_positions):
            owner = i % self.agents if self.agents > 0 else 0
            lasers.append((owner, pos, self._random_direction()))

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

    def validate_candidate(self, layout: CandidateLayout) -> tuple[bool, str]:
        return True, "ok"

    def _accept_world(self, world: World) -> tuple[bool, str]:
        if not self._meets_difficulty_window(world):
            return (
                False,
                f"outside_difficulty_window[t_min={self.t_min}, t_max={self.t_max}]",
            )
        return True, "satisfiable"

    def _failure_description(self) -> str:
        return "a valid solvable world"

    def _debug_reject(self, attempt: int, reason: str) -> None:
        if getattr(self, "debug_rejections", False):
            print(f"[reject #{attempt}] {reason}")

    def _debug_accept(self, attempt: int, reason: str) -> None:
        if getattr(self, "debug_rejections", False):
            print(f"[accept #{attempt}] {reason}")

    def _is_satisfiable(self, world: World, t: int) -> bool:
        world.reset()
        adapted = LLEAdapter(world)
        solver = WorldSolver(adapted, T_MAX=t)
        result, _ = solver.solve()
        return bool(result)

    def _meets_difficulty_window(self, world: World) -> bool:
        # Must be solvable by t_max
        if not self._is_satisfiable(world, self.t_max):
            return False

        # If t_min == 0, no lower-bound constraint
        if self.t_min == 0:
            return True

        # Must NOT be solvable by t_min - 1
        return not self._is_satisfiable(world, self.t_min - 1)

    def generate(self) -> World:
        self.last_attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            self.last_attempts = attempt
            layout = self._make_candidate_layout()

            valid, _reason = self.validate_candidate(layout)
            if not valid:
                self._debug_reject(attempt, f"invalid_layout={_reason}")
                continue

            try:
                world = self._build_world_from_layout(layout)
            except Exception as exc:
                self._debug_reject(
                    attempt, f"lle_build_error={type(exc).__name__}"
                )
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
