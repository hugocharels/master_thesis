import time

from lle import Action
from pysat.solvers import Minisat22

from .constraints import (
    InitializationConstraints,
    LaserConstraints,
    MovementConstraints,
)
from .constraints.movements import METHOD_LOCAL
from .model import SATModel
from .profiler import SolverProfiler
from .variables import VariableFactory


class WorldSolver:
    def __init__(
        self, world, T_MAX=10, enable_profiling=False, movement_method=METHOD_LOCAL
    ):
        self.world = world
        self.T_MAX = T_MAX
        self.var = VariableFactory()
        self.model = SATModel()
        self.enable_profiling = enable_profiling
        self.profiler = SolverProfiler() if enable_profiling else None
        self.movement_method = movement_method

        self.constraints = [
            InitializationConstraints(world, self.var, T_MAX),
            MovementConstraints(
                world, self.var, T_MAX, movement_method=movement_method
            ),
            LaserConstraints(world, self.var, T_MAX),
        ]

    def build_model(self):
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

    def solve(self):
        # Build the model
        self.build_model()

        # Solve with timing
        solver = Minisat22()
        solver.append_formula(self.model.cnf)

        start_solve_time = time.perf_counter()
        result = solver.solve()
        solve_time = time.perf_counter() - start_solve_time

        model = solver.get_model() if result else None

        # Record solve results in profiler
        if self.profiler:
            self.profiler.set_solve_results(solve_time, result)

        return result, model

    def get_profiling_data(self):
        """Get profiling data if available"""
        return self.profiler.to_dict() if self.profiler else None

    def export_profiling_json(self, filepath: str):
        """Export profiling data as JSON"""
        if self.profiler:
            return self.profiler.to_json(filepath)
        else:
            raise ValueError("Profiling is not enabled")

    def export_profiling_csv(self, filepath: str):
        """Export profiling data as CSV"""
        if self.profiler:
            return self.profiler.to_csv(filepath)
        else:
            raise ValueError("Profiling is not enabled")

    def print_model(self, model):
        for lit in model:
            name = self.var.name(lit)
            print(f"{'-' if lit < 0 else ''}{name}")

    def extract_plan(self, model):
        """
        Returns:
            tuple of length T_MAX
            each element is a tuple of size (#agents)
            containing Action enums
        """

        # 1. Extract positions from model
        positions = {}  # positions[color][t] = (x,y)
        for lit in model:
            if lit <= 0:
                continue
            obj = self.var.pool.obj(abs(lit))
            if not obj or obj[0] != "agent":
                continue
            _, color, (x, y), t = obj
            positions.setdefault(color, {})[t] = (x, y)

        # 2. Sort agents for deterministic ordering
        agent_colors = sorted(positions.keys())

        # 3. Build plan per timestep
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
                        f"Invalid movement for agent {color} between t={t} and t={t + 1}"
                    )
                timestep_actions.append(action)
            plan.append(tuple(timestep_actions))
        return plan
