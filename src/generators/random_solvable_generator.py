import random
from dataclasses import dataclass
from typing import Any

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
      1) can be successfully built by LLE, and
      2) is solvable by the SAT solver within T_MAX steps.

    This class is designed for extension: subclasses can override
    `validate_candidate` to enforce additional layout constraints.
    """

    def __init__(
        self,
        size: tuple[int, int],
        agents: int = 2,
        lasers: int | None = None,
        num_walls: int | None = None,
        t_max: int | None = None,
        max_attempts: int = 10_000,
        seed: int | None = None,
    ):
        self.rows, self.cols = size
        self.area = self.rows * self.cols

        self.agents = agents
        self.lasers = (agents - 1) if lasers is None else lasers
        self.num_walls = (self.area // 10) if num_walls is None else num_walls
        self.t_max = (self.area // 2) if t_max is None else t_max
        self.max_attempts = max_attempts

        # Requested logical constraint
        if self.num_walls >= (self.area / 2):
            raise ValueError(
                f"num_walls must be < size/2. Got num_walls={self.num_walls}, size={self.area}"
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
            max_attempts=args.max_attempts,
            seed=args.seed,
        )

    # ----------------------------
    # Sampling helpers
    # ----------------------------
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

    # ----------------------------
    # Extension hook
    # ----------------------------
    def validate_candidate(self, layout: CandidateLayout) -> tuple[bool, str]:
        """
        Subclasses override this to enforce extra constraints before build/solve.
        Return (True, "ok") if accepted; otherwise (False, "<reason>").
        """
        return True, "ok"

    # ----------------------------
    # Solvability
    # ----------------------------
    def _is_solvable(self, world: World) -> bool:
        world.reset()
        adapted = LLEAdapter(world)
        solver = WorldSolver(adapted, T_MAX=self.t_max)
        result, _ = solver.solve()
        return bool(result)

    def generate(self) -> World:
        for _ in range(self.max_attempts):
            layout = self._make_candidate_layout()

            valid, _reason = self.validate_candidate(layout)
            if not valid:
                continue

            try:
                world = self._build_world_from_layout(layout)  # LLE may reject
            except Exception:
                continue

            try:
                if self._is_solvable(world):
                    return world
            except Exception:
                continue

        raise RuntimeError(
            f"Could not find a valid solvable world in {self.max_attempts} attempts."
        )
