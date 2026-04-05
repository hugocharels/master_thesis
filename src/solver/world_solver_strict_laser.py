from .constraints import (
    InitializationConstraints,
    MovementConstraints,
    StrictLaserConstraints,
)
from .constraints.movements import METHOD_LOCAL
from .world_data import WorldData
from .world_solver import WorldSolver


class WorldSolverStrictLaser(WorldSolver):
    def __init__(
        self,
        world: WorldData,
        T_MAX=10,
        enable_profiling=False,
        movement_method=METHOD_LOCAL,
    ):
        super().__init__(world, T_MAX, enable_profiling, movement_method)
        self.constraints = [
            InitializationConstraints(self.ctx),
            MovementConstraints(self.ctx, movement_method=movement_method),
            StrictLaserConstraints(self.ctx),
        ]
