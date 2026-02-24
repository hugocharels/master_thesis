from pysat.solvers import Minisat22

from .constraints import (
    InitializationConstraints,
    LaserConstraints,
    MovementConstraints,
)
from .model import SATModel
from .variables import VariableFactory


class WorldSolver:
    def __init__(self, world, T_MAX=10):
        self.world = world
        self.T_MAX = T_MAX
        self.var = VariableFactory()
        self.model = SATModel()

        self.constraints = [
            InitializationConstraints(world, self.var, T_MAX),
            MovementConstraints(world, self.var, T_MAX),
            LaserConstraints(world, self.var, T_MAX),
        ]

    def build_model(self):
        for constraint in self.constraints:
            self.model.extend(constraint.generate())

    def solve(self):
        self.build_model()
        solver = Minisat22()
        solver.append_formula(self.model.cnf)
        return solver.solve(), solver.get_model()

    def print_model(self, model):
        for lit in model:
            name = self.var.name(lit)
            print(f"{'-' if lit < 0 else ''}{name}")
