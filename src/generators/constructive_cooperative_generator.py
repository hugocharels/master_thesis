from __future__ import annotations

from generators.constructive_solvable_generator import ConstructiveSolvableGenerator
from generators.random_solvable_generator import CandidateLayout
from generators.registry import register_generator
from generators.world_builder import Direction
from solver import LLEAdapter
from solver.cooperation_profile_analyzer import CooperationProfileAnalyzer


@register_generator("constructive_cooperative")
class ConstructiveCooperativeGenerator(ConstructiveSolvableGenerator):
    """
    Constructive cooperative generator.

    Builds a level around a deliberate same-colour laser-blocking dependency:
    one helper lane is crossed before a beneficiary lane by a vertical beam,
    so the helper must block its own-colour beam to let the beneficiary pass.
    SAT is still used as the final verifier and cooperation classifier.
    """

    @staticmethod
    def add_arguments(parser):
        ConstructiveSolvableGenerator.add_arguments(parser)
        parser.add_argument(
            "--profile",
            choices=["cooperative", "asymmetric"],
            default="cooperative",
            help="Target cooperation profile for accepted levels",
        )

    @classmethod
    def from_args(cls, args):
        obj = super().from_args(args)
        obj.profile = getattr(args, "profile", "cooperative")
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = "cooperative"

    def _make_constructive_candidate_layout(self) -> CandidateLayout | None:
        if self.agents < 2 or self.rows < self.agents + 1 or self.cols < 4:
            return None
        if self.lasers < 1:
            return None

        lane_rows = list(range(1, self.agents + 1))
        beam_col = self._rng.randint(1, self.cols - 2)

        agents = [(row, 0) for row in lane_rows]
        exits = [(row, self.cols - 1) for row in lane_rows]

        reserved = set(agents) | set(exits)
        for row in lane_rows:
            for col in range(self.cols):
                reserved.add((row, col))
        structural_source = (0, beam_col)
        reserved.add(structural_source)

        structural_laser = (0, structural_source, Direction.SOUTH)
        lasers = [structural_laser]

        free_cells = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if (row, col) not in reserved
        ]

        extras_needed = self.lasers - len(lasers)
        if extras_needed > 0:
            extras = self._place_extra_lasers_outside(
                reserved=reserved,
                candidate_positions=list(free_cells),
                existing_sources={structural_source},
                count=extras_needed,
            )
            if extras is None or len(extras) < extras_needed:
                return None
            lasers.extend(extras)

        used_laser_positions = {pos for _, pos, _ in lasers}
        walls = [cell for cell in free_cells if cell not in used_laser_positions]

        if self.num_walls > len(walls):
            return None
        walls = walls[: self.num_walls]

        return CandidateLayout(
            agents=agents,
            exits=exits,
            walls=walls,
            lasers=lasers,
        )

    def _place_extra_lasers_outside(
        self,
        reserved: set[tuple[int, int]],
        candidate_positions: list[tuple[int, int]],
        existing_sources: set[tuple[int, int]],
        count: int,
    ) -> list[tuple[int, tuple[int, int], Direction]] | None:
        used_sources = set(existing_sources)
        placed: list[tuple[int, tuple[int, int], Direction]] = []

        candidates = []
        for pos in candidate_positions:
            for direction in [
                Direction.NORTH,
                Direction.SOUTH,
                Direction.EAST,
                Direction.WEST,
            ]:
                if self._points_out_immediately(pos, direction):
                    continue
                beam_tiles = self._beam_tiles(pos, direction, set(), used_sources)
                if not beam_tiles:
                    continue
                if any(tile in reserved for tile in beam_tiles):
                    continue
                candidates.append((pos, direction, beam_tiles))

        self._rng.shuffle(candidates)

        for pos, direction, beam_tiles in candidates:
            if len(placed) >= count:
                break
            if pos in used_sources:
                continue
            if any(existing in beam_tiles for existing in used_sources):
                continue
            owner = (1 + len(placed)) % self.agents if self.agents > 0 else 0
            placed.append((owner, pos, direction))
            used_sources.add(pos)

        return placed

    def _analyze_profile(self, world):
        world.reset()
        adapted = LLEAdapter(world)
        return CooperationProfileAnalyzer(adapted, T_MAX=self.t_max).analyze()

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

        return True, f"profile={analysis.profile}, constructive_cooperative"

    def _failure_description(self) -> str:
        return "a valid constructive cooperative world"
