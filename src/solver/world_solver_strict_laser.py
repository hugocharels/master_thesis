from .constraints import (
    ConstraintContext,
    InitializationConstraints,
    MovementConstraints,
    StrictLaserConstraints,
)
from .constraints.movements import METHOD_LOCAL
from .model import SATModel
from .profiler import SolverProfiler
from .variables import VariableFactory
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
        self.world = world
        self.T_MAX = T_MAX
        self.var = VariableFactory()
        self.model = SATModel()
        self.enable_profiling = enable_profiling
        self.profiler = SolverProfiler() if enable_profiling else None
        self.movement_method = movement_method

        self.ctx = ConstraintContext(world, self.var, T_MAX)

        self.constraints = [
            InitializationConstraints(self.ctx),
            MovementConstraints(self.ctx, movement_method=movement_method),
            StrictLaserConstraints(self.ctx),
        ]
