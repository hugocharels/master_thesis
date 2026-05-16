"""Constructive cooperative generator: enforces cooperation requirement via profile filter."""

from __future__ import annotations

from lle.tiles import Direction

from .candidates import CandidateLayout
from .constructive import ConstructiveGenerator
from .geometry import beam_tiles
from .profile_choices import COOP_PROFILE_CHOICES
from .registry import register_generator
from solver import CooperationProfileAnalyzer


@register_generator("cooperative")
class CooperativeGenerator(ConstructiveGenerator):
    """
    Constructive solvable generator that additionally enforces a cooperation
    profile requirement. SAT is still used as the final verifier.

    The constructive layout places a deliberate same-colour laser-blocking
    dependency: a structural laser at row 0 points SOUTH across all agent
    lanes, so the helper must block its own-colour beam to let the beneficiary
    pass. SAT is still used as the final verifier and cooperation classifier.
    """

    @staticmethod
    def add_arguments(parser):
        ConstructiveGenerator.add_arguments(parser)
        parser.add_argument(
            "--profile",
            choices=list(COOP_PROFILE_CHOICES),
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

    # ----- cooperative layout strategy -----

    # Number of independent lane samples tried before falling back to the
    # parent's random layout.
    _LANE_SAMPLE_ATTEMPTS: int = 8

    def _make_constructive_candidate_layout(self) -> CandidateLayout | None:
        if self.agents < 2 or self.lasers < 1:
            return None
        # Need >= agents lane axis-slots and >= 1 axis-slot left for the
        # structural laser; perp axis must be >= 3 so the laser's perp
        # coordinate can land strictly inside (avoiding agent/exit columns).
        feasible: list[str] = []
        if self.rows >= self.agents + 1 and self.cols >= 3:
            feasible.append("horizontal")
        if self.cols >= self.agents + 1 and self.rows >= 3:
            feasible.append("vertical")
        if not feasible:
            return None
        # Pick orientation uniformly per call so both rotations occur
        # across attempts (rather than greedily preferring the same one
        # whenever it succeeds).
        orientation = self._rng.choice(feasible)
        for _ in range(self._LANE_SAMPLE_ATTEMPTS):
            layout = self._build_cooperative_lane_layout(orientation)
            if layout is not None:
                return layout
        # Fall back to the other orientation if the chosen one repeatedly
        # fails (e.g., lane sample kept landing at both grid edges).
        for other in feasible:
            if other == orientation:
                continue
            for _ in range(self._LANE_SAMPLE_ATTEMPTS):
                layout = self._build_cooperative_lane_layout(other)
                if layout is not None:
                    return layout
        return None

    def _build_cooperative_lane_layout(self, orientation: str) -> CandidateLayout | None:
        """One attempt: random non-contiguous lanes + random rotation +
        ``n_lasers`` distinct-colour structural lasers, each perpendicular
        to the lane band.

        Each laser is assigned a distinct colour in ``0..n_lasers - 1`` and
        sits on a non-lane axis-slot (strictly before or strictly after
        the entire lane band) so its beam crosses every lane. The
        perpendicular columns of the lasers are sampled without
        replacement, which guarantees that any two laser beams are
        parallel straight lines on different perpendicular coordinates and
        therefore do not share any cell. The full unblocked beam path of
        every laser is reserved so walls cannot clip it before it reaches
        the far lane.

        Distinct colours mean cooperation is no longer the
        single-helper "agent 0 blocks its own beam" pattern: for
        ``n_lasers >= 2`` every agent of colour $c < n_("lasers")$ is the
        only candidate blocker for laser $c$, which forces a *mutual* (or
        richer) cooperation profile rather than the *asymmetric* profile
        produced by the previous one-helper template.

        Returns ``None`` on any infeasibility:
        - the lane sample left no axis-slot on either side of the band,
        - there are not enough perpendicular columns to place
          ``n_lasers`` distinct lasers,
        - or there are too few free cells left to place ``num_walls``
          walls after laser reservation.
        """
        if orientation == "horizontal":
            lane_axis_size, perp_axis_size = self.rows, self.cols
        else:
            lane_axis_size, perp_axis_size = self.cols, self.rows

        lane_ids = sorted(self._rng.sample(range(lane_axis_size), self.agents))
        lane_set = set(lane_ids)
        non_lane = [i for i in range(lane_axis_size) if i not in lane_set]
        if not non_lane:
            return None

        # Axis slots strictly before or strictly after the lane band
        # qualify, because a laser there has its full beam pass through
        # every lane in the band.
        min_lane, max_lane = lane_ids[0], lane_ids[-1]
        before_band = [i for i in non_lane if i < min_lane]
        after_band = [i for i in non_lane if i > max_lane]
        axis_dir_options: list[tuple[int, Direction]] = []
        if orientation == "horizontal":
            axis_dir_options.extend((r, Direction.SOUTH) for r in before_band)
            axis_dir_options.extend((r, Direction.NORTH) for r in after_band)
        else:
            axis_dir_options.extend((c, Direction.EAST) for c in before_band)
            axis_dir_options.extend((c, Direction.WEST) for c in after_band)
        if not axis_dir_options:
            return None

        # Distinct perpendicular columns guarantee non-overlapping parallel
        # beams. Excluding the two edge columns keeps the laser source out
        # of the agent-start and exit columns regardless of the rotation
        # flip chosen below.
        valid_perps = list(range(1, perp_axis_size - 1))
        if len(valid_perps) < self.lasers:
            return None
        chosen_perps = self._rng.sample(valid_perps, self.lasers)

        # Place ``self.lasers`` structural lasers, one per colour, each at
        # an independently-chosen (axis, direction) on either side of the
        # band. Distinct perpendicular columns ensure source-cell
        # uniqueness and beam-cell non-overlap.
        laser_placements: list[tuple[int, tuple[int, int], Direction]] = []
        for colour, laser_perp in enumerate(chosen_perps):
            laser_axis, direction = self._rng.choice(axis_dir_options)
            if orientation == "horizontal":
                source = (laser_axis, laser_perp)
            else:
                source = (laser_perp, laser_axis)
            laser_placements.append((colour, source, direction))

        # Random rotation: independently flip the agent / exit edges so the
        # four rotations (agents on left / right / top / bottom edge) are
        # equally likely.
        flip = self._rng.random() < 0.5
        if orientation == "horizontal":
            agent_col = self.cols - 1 if flip else 0
            exit_col = 0 if flip else self.cols - 1
            agents = [(row, agent_col) for row in lane_ids]
            exits = [(row, exit_col) for row in lane_ids]
            reserved = {(row, col) for row in lane_ids for col in range(self.cols)}
        else:
            agent_row = self.rows - 1 if flip else 0
            exit_row = 0 if flip else self.rows - 1
            agents = [(agent_row, col) for col in lane_ids]
            exits = [(exit_row, col) for col in lane_ids]
            reserved = {(row, col) for col in lane_ids for row in range(self.rows)}
        reserved.update(agents)
        reserved.update(exits)

        # Reserve every laser's source cell and its full unblocked beam
        # path. Walls (placed next) and the (now-empty) extra-laser pool
        # would otherwise be allowed to land on beam cells and clip the
        # beam before it reaches the far lane.
        for _colour, source, direction in laser_placements:
            reserved.add(source)
            path = beam_tiles(
                source,
                direction,
                walls=set(),
                lasers=set(),
                rows=self.rows,
                cols=self.cols,
            )
            reserved.update(path)

        free_positions = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if (row, col) not in reserved
        ]
        if len(free_positions) < self.num_walls:
            return None
        # Shuffle so the wall set is a random subset of the free cells,
        # not the first ``num_walls`` cells in row-major order.
        self._rng.shuffle(free_positions)
        walls = free_positions[: self.num_walls]

        return CandidateLayout(
            agents=agents,
            exits=exits,
            walls=walls,
            lasers=laser_placements,
        )

    # ----- profile acceptance -----

    def _analyze_profile(self, world):
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
        return True, f"profile={analysis.profile}, constructive_cooperative"

    def _failure_description(self) -> str:
        return "a valid constructive cooperative world"
