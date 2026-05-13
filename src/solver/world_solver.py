import time
from enum import StrEnum

from lle import Action
from pysat.solvers import Minisat22

from .constraints import (
    ConstraintContext,
    InitializationConstraints,
    LaserConstraints,
    MovementConstraints,
    SelectiveStrictLaserConstraints,
    StrictLaserConstraints,
)
from .constraints.movements import METHOD_LOCAL
from .model import SATModel
from .profiler import SolverProfiler
from .variables import VariableFactory
from lle import World


class LaserMode(StrEnum):
    STANDARD = "standard"
    STRICT = "strict"
    SELECTIVE_STRICT = "selective_strict"


class WorldSolver:
    def __init__(
        self,
        world: World,
        T_MAX: int = 10,
        *,
        laser_mode: LaserMode = LaserMode.STANDARD,
        strict_colors: frozenset[int] | None = None,
        enable_profiling: bool = False,
        movement_method: str = METHOD_LOCAL,
    ):
        if laser_mode is LaserMode.SELECTIVE_STRICT and not strict_colors:
            raise ValueError(
                "laser_mode=selective_strict requires a non-empty strict_colors set"
            )

        self.world = world
        self.T_MAX = T_MAX
        self.var = VariableFactory()
        self.model = SATModel()
        self.enable_profiling = enable_profiling
        self.profiler = SolverProfiler() if enable_profiling else None
        self.movement_method = movement_method
        self.laser_mode = laser_mode
        self.strict_colors = frozenset(strict_colors) if strict_colors else frozenset()

        self.ctx = ConstraintContext(world, self.var, T_MAX)
        self.constraints = [
            InitializationConstraints(self.ctx),
            MovementConstraints(self.ctx, movement_method=movement_method),
            self._build_laser_constraint(),
        ]
        self._model_built = False

    def _build_laser_constraint(self):
        if self.laser_mode is LaserMode.STANDARD:
            return LaserConstraints(self.ctx)
        if self.laser_mode is LaserMode.STRICT:
            return StrictLaserConstraints(self.ctx)
        if self.laser_mode is LaserMode.SELECTIVE_STRICT:
            return SelectiveStrictLaserConstraints(self.ctx, self.strict_colors)
        raise ValueError(f"Unknown laser_mode: {self.laser_mode}")

    def build_model(self):
        if self._model_built:
            return

        for constraint in self.constraints:
            constraint_name = constraint.__class__.__name__

            if self.profiler:
                with self.profiler.start_constraint(
                    constraint_name
                ) as constraint_profiler:
                    constraint.set_profiler(constraint_profiler)
                    clauses = constraint.generate()
                    self.model.extend(clauses)
            else:
                self.model.extend(constraint.generate())

        self._model_built = True

    def solve(self):
        self.build_model()
        with Minisat22(bootstrap_with=self.model.cnf.clauses) as solver:
            start_solve_time = time.perf_counter()
            result = solver.solve()
            solve_time = time.perf_counter() - start_solve_time
            model = solver.get_model() if result else None

        if self.profiler:
            self.profiler.set_solve_results(solve_time, result)

        return result, model

    def get_profiling_data(self):
        return self.profiler.to_dict() if self.profiler else None

    def export_profiling_json(self, filepath: str):
        if self.profiler:
            return self.profiler.to_json(filepath)
        raise ValueError("Profiling is not enabled")

    def export_profiling_csv(self, filepath: str):
        if self.profiler:
            return self.profiler.to_csv(filepath)
        raise ValueError("Profiling is not enabled")

    def print_model(self, model):
        for lit in model:
            name = self.var.name(lit)
            print(f"{'-' if lit < 0 else ''}{name}")

    def extract_plan(self, model):
        """
        Returns:
            list of tuples, each of length (#agents),
            containing lle.Action enums.
        """
        positions = {}
        for lit in model:
            if lit <= 0:
                continue
            obj = self.var.pool.obj(abs(lit))
            if not obj or obj[0] != "agent":
                continue
            _, color, (x, y), t = obj
            positions.setdefault(color, {})[t] = (x, y)

        agent_colors = sorted(positions.keys())

        plan = []
        for t in range(self.T_MAX):
            timestep_actions = []
            for color in agent_colors:
                x1, y1 = positions[color][t]
                x2, y2 = positions[color][t + 1]
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0:
                    action = Action.STAY
                elif dx == -1 and dy == 0:
                    action = Action.NORTH
                elif dx == 1 and dy == 0:
                    action = Action.SOUTH
                elif dx == 0 and dy == -1:
                    action = Action.WEST
                elif dx == 0 and dy == 1:
                    action = Action.EAST
                else:
                    raise ValueError(
                        f"Invalid movement for agent {color} at t={t}->{t + 1}"
                    )
                timestep_actions.append(action)
            plan.append(tuple(timestep_actions))
        return plan
