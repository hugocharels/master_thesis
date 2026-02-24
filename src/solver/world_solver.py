from enum import Enum

from pysat.solvers import Minisat22

from .constraints import (
    InitializationConstraints,
    LaserConstraints,
    MovementConstraints,
)
from .model import SATModel
from .variables import VariableFactory


class Action(Enum):
    Stay = 0
    North = 1
    South = 2
    West = 3
    East = 4


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
        num_agents = len(agent_colors)

        # 3. Build plan per timestep
        plan = []
        for t in range(self.T_MAX):
            timestep_actions = []

            for color in agent_colors:
                x1, y1 = positions[color][t]
                x2, y2 = positions[color][t + 1]
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0:
                    action = Action.Stay
                elif dx == -1 and dy == 0:
                    action = Action.North
                elif dx == 1 and dy == 0:
                    action = Action.South
                elif dx == 0 and dy == -1:
                    action = Action.West
                elif dx == 0 and dy == 1:
                    action = Action.East
                else:
                    raise ValueError(
                        f"Invalid movement for agent {color} between t={t} and t={t + 1}"
                    )
                timestep_actions.append(action)
            plan.append(tuple(timestep_actions))
        return plan
