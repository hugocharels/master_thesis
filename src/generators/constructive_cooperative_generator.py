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

        lane_rows = list(range(1, self.agents + 1))
        helper_row = lane_rows[0]
        beneficiary_row = lane_rows[1]
        beam_col = self._rng.randint(1, self.cols - 2)

        agents = [(row, 0) for row in lane_rows]
        exits = [(row, self.cols - 1) for row in lane_rows]

        reserved = set(agents) | set(exits)
        for row in lane_rows:
            for col in range(self.cols):
                reserved.add((row, col))
        reserved.add((0, beam_col))

        walls = []
        for row in range(self.rows):
            for col in range(self.cols):
                pos = (row, col)
                if pos in reserved:
                    continue
                walls.append(pos)

        lasers = [(0, (0, beam_col), Direction.SOUTH)]

        extra_lasers = self.lasers - len(lasers)
        if extra_lasers > 0:
            return None

        if self.num_walls > len(walls):
            return None

        # Keep the structural walls that force the cooperation pattern.
        # If the caller asks for fewer walls, we still keep the minimum needed.
        return CandidateLayout(
            agents=agents,
            exits=exits,
            walls=walls,
            lasers=lasers,
        )

    def _analyze_profile(self, world):
        world.reset()
        adapted = LLEAdapter(world)
        return CooperationProfileAnalyzer(adapted, T_MAX=self.t_max).analyze()

    def generate(self):
        self.last_attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            self.last_attempts = attempt
            layout = self._make_candidate_layout()

            valid, reason = self.validate_candidate(layout)
            if not valid:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] {reason}")
                continue

            try:
                world = self._build_world_from_layout(layout)
            except Exception as exc:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] lle_build_error={type(exc).__name__}")
                continue

            try:
                if not self._meets_difficulty_window(world):
                    if self.debug_rejections:
                        print(
                            f"[reject #{attempt}] outside_difficulty_window"
                            f"[t_min={self.t_min}, t_max={self.t_max}]"
                        )
                    continue

                analysis = self._analyze_profile(world)
                if not analysis.matches_profile(self.profile):
                    if self.debug_rejections:
                        print(
                            f"[reject #{attempt}] "
                            f"profile={analysis.profile}, required={self.profile}"
                        )
                    continue

                if self.debug_rejections:
                    print(
                        f"[accept #{attempt}] "
                        f"profile={analysis.profile}, constructive_cooperative"
                    )
                return world
            except Exception as exc:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] solver_error={type(exc).__name__}")
                continue

        raise RuntimeError(
            "Could not find a valid constructive cooperative world in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )
