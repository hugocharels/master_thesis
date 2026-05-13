from dataclasses import dataclass

from .constraints.movements import METHOD_LOCAL
from .world_data import WorldData
from .world_solver import LaserMode, WorldSolver


@dataclass
class CooperationResult:
    cooperation_needed: bool


class CooperationSolver:
    """
    Assumes the original level is solvable by the normal WorldSolver.
    Cooperation is needed iff the strict-laser solver is UNSAT.
    """

    def __init__(self, world: WorldData, T_MAX: int = 10, movement_method=METHOD_LOCAL):
        self.world = world
        self.T_MAX = T_MAX
        self.movement_method = movement_method

    def analyze(self) -> CooperationResult:
        strict_sat, _ = WorldSolver(
            self.world,
            T_MAX=self.T_MAX,
            laser_mode=LaserMode.STRICT,
            movement_method=self.movement_method,
        ).solve()
        return CooperationResult(cooperation_needed=not bool(strict_sat))
