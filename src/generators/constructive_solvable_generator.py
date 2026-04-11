from __future__ import annotations

from generators.constrained_random_solvable_generator import (
    CandidateLayout,
    ConstrainedRandomSolvableGenerator,
)
from generators.registry import register_generator
from generators.world_builder import Direction


@register_generator("constructive_solvable")
class ConstructiveSolvableGenerator(ConstrainedRandomSolvableGenerator):
    """
    Constructive solvable generator.

    Instead of sampling a full layout blindly, it first reserves one disjoint
    lane per agent so a joint solution exists by construction, then places
    walls and lasers only outside those lanes. SAT is still used as a final
    verifier before acceptance.
    """

    @classmethod
    def from_args(cls, args):
        obj = super().from_args(args)
        obj.last_attempts = 0
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_attempts = 0

    def _make_candidate_layout(self) -> CandidateLayout:
        layout = self._make_constructive_candidate_layout()
        if layout is None:
            return super()._make_candidate_layout()
        return layout

    def _make_constructive_candidate_layout(self) -> CandidateLayout | None:
        orientations = []
        if self.rows >= self.agents:
            orientations.append(("horizontal", self.area - self.agents * self.cols))
        if self.cols >= self.agents:
            orientations.append(("vertical", self.area - self.agents * self.rows))

        if not orientations:
            return None

        orientations.sort(key=lambda item: item[1], reverse=True)
        for orientation, free_cells in orientations:
            if free_cells < self.num_walls + self.lasers:
                continue
            layout = self._build_lane_layout(orientation)
            if layout is not None:
                return layout
        return None

    def _build_lane_layout(self, orientation: str) -> CandidateLayout | None:
        if orientation == "horizontal":
            lane_ids = sorted(self._rng.sample(range(self.rows), self.agents))
            agents = [(row, 0) for row in lane_ids]
            exits = [(row, self.cols - 1) for row in lane_ids]
            reserved = {(row, col) for row in lane_ids for col in range(self.cols)}
        else:
            lane_ids = sorted(self._rng.sample(range(self.cols), self.agents))
            agents = [(0, col) for col in lane_ids]
            exits = [(self.rows - 1, col) for col in lane_ids]
            reserved = {(row, col) for col in lane_ids for row in range(self.rows)}

        free_positions = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if (row, col) not in reserved
        ]

        if len(free_positions) < self.num_walls + self.lasers:
            return None

        self._rng.shuffle(free_positions)
        walls = free_positions[: self.num_walls]
        laser_pool = free_positions[self.num_walls :]

        lasers = self._place_safe_lasers(
            reserved=reserved,
            wall_positions=walls,
            candidate_positions=laser_pool,
        )
        if lasers is None:
            return None

        return CandidateLayout(
            agents=agents,
            exits=exits,
            walls=walls,
            lasers=lasers,
        )

    def _place_safe_lasers(
        self,
        reserved: set[tuple[int, int]],
        wall_positions: list[tuple[int, int]],
        candidate_positions: list[tuple[int, int]],
    ) -> list[tuple[int, tuple[int, int], Direction]] | None:
        walls = set(wall_positions)
        used_sources: set[tuple[int, int]] = set()
        lasers: list[tuple[int, tuple[int, int], Direction]] = []

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
                beam_tiles = self._beam_tiles(pos, direction, walls, used_sources)
                if not beam_tiles:
                    continue
                if any(tile in reserved for tile in beam_tiles):
                    continue
                candidates.append((pos, direction, beam_tiles))

        self._rng.shuffle(candidates)

        for pos, direction, beam_tiles in candidates:
            if len(lasers) >= self.lasers:
                break
            if pos in used_sources:
                continue
            if any(existing_pos in beam_tiles for _, existing_pos, _ in lasers):
                continue
            if any(tile in reserved for tile in beam_tiles):
                continue
            owner = len(lasers) % self.agents if self.agents > 0 else 0
            lasers.append((owner, pos, direction))
            used_sources.add(pos)

        if len(lasers) != self.lasers:
            return None
        return lasers

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
                if self._meets_difficulty_window(world):
                    if self.debug_rejections:
                        print(f"[accept #{attempt}] constructive_satisfiable")
                    return world
                if self.debug_rejections:
                    print(
                        f"[reject #{attempt}] outside_difficulty_window"
                        f"[t_min={self.t_min}, t_max={self.t_max}]"
                    )
            except Exception as exc:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] solver_error={type(exc).__name__}")
                continue

        raise RuntimeError(
            "Could not find a valid constructive solvable world in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )
