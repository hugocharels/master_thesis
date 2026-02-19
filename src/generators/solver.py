from itertools import combinations

from core import World
from pysat.formula import CNF, IDPool
from pysat.solvers import Minisat22

from src.generators.core.types import Direction

################### VARIABLES ####################


class ID:
    vpool = IDPool(start_from=1)

    def __init__(self, id):
        self.id = id

    @staticmethod
    def a(c: int, x: int, y: int, t: int):
        """
        Agent with color c at position (x, y) at time t
        """
        return ID.vpool.id(f"a_{c}_{x}_{y}_{t}")

    @staticmethod
    def s(c: int, d: int, x: int, y: int):
        """
        Laser source with color c, direction d at position (x, y)
        """
        return ID.vpool.id(f"s_{c}_{d}_{x}_{y}")

    @staticmethod
    def w(x: int, y: int):
        """
        Wall at position (x, y)
        """
        return ID.vpool.id(f"w_{x}_{y}")

    @staticmethod
    def e(x: int, y: int):
        """
        Exit at position (x, y)
        """
        return ID.vpool.id(f"e_{x}_{y}")

    @staticmethod
    def l(c: int, x: int, y: int, t: int):
        """
        Laser active with color c at position (x, y) at time t
        """
        return ID.vpool.id(f"l_{c}_{x}_{y}_{t}")

    @staticmethod
    def b(c: int, d: int, x: int, y: int, t: int):
        """
        Laser beam with color c, direction d at position (x, y) at time t
        """
        return ID.vpool.id(f"b_{c}_{d}_{x}_{y}_{t}")

    # add tseitin transformation variables


##################################################


##################### SOLVER #####################


class WorldSolver:
    def __init__(self, world: World, T_MAX: int = 10):
        self.world = world
        self.agents = world.get_agents()
        self.lasers = world.get_lasers()
        self.walls = world.get_walls()
        self.exits = world.get_exits()
        self.T_MAX = T_MAX  # Maximum time steps to consider

    def generate(self):
        cnf = CNF()
        for clause in self._get_clauses():
            cnf.append(clause)
        solver = Minisat22()
        solver.append_formula(cnf)
        return solver.solve(), solver.get_model()

    def _get_clauses(self):
        for constraint in self._get_constraints():
            for clause in constraint():
                yield clause

    def _get_constraints(self) -> list:
        return [
            self._initialize_agents_pos,
            self._initialize_lasers,
            self._initialize_walls,
            self._initialize_exits,
            self._one_position_per_agent,
            self._agent_movement,
            self._agent_must_be_on_exit_to_win,
            self._agent_cannot_step_on_wall,
            self._agent_cannot_step_on_laser_sources,
            self._agent_cannot_step_on_other_agents,
            self._agent_cannot_step_on_active_lasers,
            self._laser_beam_propagation,
            self._link_var_l_and_b,
        ]

    ########## CONSTRAINTS ##########

    # Initialization constraints
    def _initialize_agents_pos(self):
        for agent, (x, y) in self.agents:
            yield [ID.a(agent.color, x, y, 0)]

    def _initialize_lasers(self):
        for laser, (x, y) in self.lasers:
            yield [ID.s(laser.color, laser.direction.id(), x, y)]

    def _initialize_walls(self):
        for x, y in self.walls:
            yield [ID.w(x, y)]

    def _initialize_exits(self):
        for x, y in self.exits:
            yield [ID.e(x, y)]

    # Agents contraints
    def _one_position_per_agent(self):
        for agent, _ in self.agents:
            c = agent.color
            for t in range(self.T_MAX):
                # At least one position
                yield [ID.a(c, x, y, t) for x, y in self.world.grid.positions()]
                # At most one position - only generate clauses for distinct pairs
                for (x1, y1), (x2, y2) in combinations(self.world.grid.positions(), 2):
                    yield [-ID.a(c, x1, y1, t), -ID.a(c, x2, y2, t)]

    def _agent_movement(self):
        for agent, _ in self.agents:
            c = agent.color
            for t in range(self.T_MAX):
                for x, y in self.world.grid.positions():
                    # If agent is at (x, y) at time t, it can move to adjacent positions at time t+1
                    adjacent_positions = self.world.grid.get_neighbors((x, y))
                    yield [-ID.a(c, x, y, t), ID.a(c, x, y, t + 1)] + [
                        ID.a(c, nx, ny, t + 1) for (nx, ny), _ in adjacent_positions
                    ]

    def _agent_must_be_on_exit_to_win(self):
        """
        This version says that at the final time step, the agent must be on an exit. This is a weaker constraint than saying that at some point in time, the agent must be on an exit.
        """
        for x, y in self.exits:
            yield [ID.a(agent.color, x, y, self.T_MAX - 1) for agent, _ in self.agents]

    # Agent steping constraints
    def _agent_cannot_step_on_wall(self):
        for agent, _ in self.agents:
            c = agent.color
            for t in range(self.T_MAX):
                for x, y in self.walls:
                    yield [-ID.a(c, x, y, t)]

    def _agent_cannot_step_on_laser_sources(self):
        for agent, _ in self.agents:
            c = agent.color
            for t in range(self.T_MAX):
                for _, (x, y) in self.lasers:
                    yield [-ID.a(c, x, y, t)]

    def _agent_cannot_step_on_other_agents(self):
        for agent1, _ in self.agents:
            c1 = agent1.color
            for agent2, _ in self.agents:
                c2 = agent2.color
                if c1 >= c2:
                    continue  # Avoid duplicate pairs and self-pairing
                for t in range(self.T_MAX):
                    for x, y in self.world.grid.positions():
                        yield [-ID.a(c1, x, y, t), -ID.a(c2, x, y, t)]

    def _agent_cannot_step_on_active_lasers(self):
        for agent, _ in self.agents:
            c1 = agent.color
            for laser, _ in self.lasers:
                c2 = laser.color
                if c1 == c2:
                    continue  # An agent can step on its own laser
                for t in range(self.T_MAX):
                    for x, y in self.world.grid.positions():
                        yield [-ID.a(c1, x, y, t), -ID.l(c2, x, y, t)]

    # Laser constraints
    def _laser_beam_propagation(self):
        for laser, (x, y) in self.lasers:
            c = laser.color
            d = laser.direction.id()
            for t in range(self.T_MAX):
                # If laser source is active, then the beam is active at the source position
                yield [-ID.s(c, d, x, y), ID.b(c, d, x, y, t)]
                yield [ID.s(c, d, x, y), -ID.b(c, d, x, y, t)]

        for c in range(len(self.lasers)):
            for dir in (
                Direction.NORTH,
                Direction.SOUTH,
                Direction.EAST,
                Direction.WEST,
            ):
                for x, y in self.world.grid.positions():
                    for t in range(self.T_MAX - 1):
                        next_x, next_y = x + dir.value[0], y + dir.value[1]
                        if not self.world.grid.is_within_bounds((next_x, next_y)):
                            continue
                        yield [
                            -ID.b(c, dir.id(), x, y, t),
                            ID.a(c, next_x, next_y, t),
                            ID.w(next_x, next_y),
                            ID.b(c, dir.id(), next_x, next_y, t + 1),
                        ]
                        yield [
                            -ID.b(c, dir.id(), next_x, next_y, t),
                            ID.b(c, dir.id(), x, y, t),
                        ]
                        yield [
                            -ID.b(c, dir.id(), next_x, next_y, t),
                            ID.a(c, next_x, next_y, t),
                        ]
                        yield [
                            -ID.b(c, dir.id(), next_x, next_y, t),
                            ID.w(next_x, next_y),
                        ]

    def _link_var_l_and_b(self):
        for laser, _ in self.lasers:
            for x, y in self.world.grid.positions():
                for t in range(self.T_MAX):
                    yield [
                        -ID.b(laser.color, laser.direction.id(), x, y, t),
                        ID.l(laser.color, x, y, t),
                    ]
                    yield [
                        ID.b(laser.color, laser.direction.id(), x, y, t),
                        -ID.l(laser.color, x, y, t),
                    ]

    #################################


##################################################
