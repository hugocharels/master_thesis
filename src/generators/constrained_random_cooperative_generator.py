from generators.random_cooperative_generator import RandomCooperativeGenerator
from generators.random_solvable_generator import CandidateLayout
from generators.registry import register_generator
from generators.world_builder import Direction


@register_generator("constrained_random_cooperative")
class ConstrainedRandomCooperativeGenerator(RandomCooperativeGenerator):
    """
    Random cooperative generator with additional geometric constraints.
    Mirrors ConstrainedRandomSolvableGenerator but enforces cooperation too
    via the parent RandomCooperativeGenerator logic.
    """

    @staticmethod
    def add_arguments(parser):
        RandomCooperativeGenerator.add_arguments(parser)

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

    def _in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def _delta(self, d: Direction) -> tuple[int, int]:
        if d == Direction.NORTH:
            return -1, 0
        if d == Direction.SOUTH:
            return 1, 0
        if d == Direction.WEST:
            return 0, -1
        return 0, 1  # EAST

    def _beam_tiles(
        self,
        src: tuple[int, int],
        direction: Direction,
        wall_set: set[tuple[int, int]],
        laser_set: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        dr, dc = self._delta(direction)
        r, c = src[0] + dr, src[1] + dc
        tiles: list[tuple[int, int]] = []

        while self._in_bounds(r, c):
            if (r, c) in wall_set or (r, c) in laser_set:
                break
            tiles.append((r, c))
            r += dr
            c += dc

        return tiles

    def _points_out_immediately(
        self, src: tuple[int, int], direction: Direction
    ) -> bool:
        dr, dc = self._delta(direction)
        nr, nc = src[0] + dr, src[1] + dc
        return not self._in_bounds(nr, nc)

    def validate_candidate(self, layout: CandidateLayout) -> tuple[bool, str]:
        ok, reason = super().validate_candidate(layout)
        if not ok:
            return ok, reason

        wall_set = set(layout.walls)
        laser_set = {pos for _, pos, _ in layout.lasers}
        exit_set = set(layout.exits)

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

    def generate(self):
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1
            layout = self._make_candidate_layout()

            valid, reason = self.validate_candidate(layout)
            if not valid:
                if self.debug_rejections:
                    print(f"[reject #{attempts}] {reason}")
                continue

            try:
                world = self._build_world_from_layout(layout)
            except Exception as e:
                if self.debug_rejections:
                    print(f"[reject #{attempts}] lle_build_error={type(e).__name__}")
                continue

            try:
                if not self._meets_difficulty_window(world):
                    if self.debug_rejections:
                        print(
                            f"[reject #{attempts}] outside_difficulty_window"
                            f"[t_min={self.t_min}, t_max={self.t_max}]"
                        )
                    continue

                if not self._is_cooperative(world):
                    if self.debug_rejections:
                        print(f"[reject #{attempts}] non_cooperative")
                    continue

                if self.debug_rejections:
                    print(f"[accept #{attempts}] constrained_cooperative_and_solvable")
                return world

            except Exception as e:
                if self.debug_rejections:
                    print(f"[reject #{attempts}] solver_error={type(e).__name__}")
                continue

        raise RuntimeError(
            "Could not find a valid constrained cooperative world in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )
