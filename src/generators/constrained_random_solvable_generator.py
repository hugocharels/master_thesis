from generators.candidates import CandidateLayout
from generators.geometry import beam_tiles, in_bounds, points_out_immediately
from generators.random_solvable_generator import RandomSolvableGenerator
from generators.registry import register_generator


@register_generator("constrained_random_solvable")
class ConstrainedRandomSolvableGenerator(RandomSolvableGenerator):
    """
    Random solvable generator with additional geometric constraints.
    Designed to be extended as you add more rules.
    """

    @staticmethod
    def add_arguments(parser):
        RandomSolvableGenerator.add_arguments(parser)
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
        )
        obj.debug_rejections = bool(args.debug_rejections)
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_rejections = False

    def _in_bounds(self, r: int, c: int) -> bool:
        return in_bounds((r, c), self.rows, self.cols)

    def _beam_tiles(self, src, direction, wall_set, laser_set):
        return beam_tiles(src, direction, wall_set, laser_set, self.rows, self.cols)

    def _points_out_immediately(self, src, direction):
        return points_out_immediately(src, direction, self.rows, self.cols)

    def validate_candidate(self, layout: CandidateLayout) -> tuple[bool, str]:
        ok, reason = super().validate_candidate(layout)
        if not ok:
            return ok, reason

        wall_set = set(layout.walls)
        laser_set = {pos for _, pos, _ in layout.lasers}
        exit_set = set(layout.exits)

        # Build union of all beam tiles for later constraints
        all_beam_tiles: set[tuple[int, int]] = set()

        for _owner, src, direction in layout.lasers:
            # Constraint 1: laser cannot point outside level immediately.
            if self._points_out_immediately(src, direction):
                return False, f"laser_points_outside_immediately@{src}"

            # Constraint 2: laser must have non-zero beam length.
            beam_tiles = self._beam_tiles(src, direction, wall_set, laser_set)
            if len(beam_tiles) == 0:
                return False, f"laser_zero_beam@{src}"

            all_beam_tiles.update(beam_tiles)

        # Constraint 3: no exit can lie on any laser beam tile.
        overlap = exit_set.intersection(all_beam_tiles)
        if overlap:
            return False, f"exit_on_laser_beam@{sorted(overlap)}"

        return True, "ok"

    def _accept_world(self, world):
        accepted, reason = super()._accept_world(world)
        if accepted:
            return True, (
                f"sat@t_max={self.t_max} and (t_min={self.t_min} respected)"
            )
        return accepted, reason

    def _failure_description(self) -> str:
        return "a valid constrained solvable world"
