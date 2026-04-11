import time

from lle import Action
from pysat.solvers import Minisat22

from .constraints import (
    ConstraintContext,
    InitializationConstraints,
    LaserConstraints,
    MovementConstraints,
)
from .constraints.movements import METHOD_LOCAL
from .model import SATModel
from .profiler import SolverProfiler
from .variables import VariableFactory
from .world_data import WorldData


class WorldSolver:
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
            LaserConstraints(self.ctx),
        ]
        self._model_built = False

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
