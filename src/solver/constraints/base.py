from abc import ABC, abstractmethod

from core import CellType


class ConstraintContext:
    """Pre-computed data shared across all constraint classes. Built once."""

    def __init__(self, world, var_factory, T_MAX):
        self.world = world
        self.var = var_factory
        self.T_MAX = T_MAX

        # Pre-compute sets
        self.walls = frozenset(world.get_walls())
        self.laser_positions = frozenset(pos for _, pos in world.get_lasers())
        self.blocked = self.walls | self.laser_positions
        self.agents = world.get_agents()
        self.lasers = world.get_lasers()
        self.exits = world.get_exits()
        self.all_positions = list(world.grid.positions())
        self.valid_positions = [p for p in self.all_positions if p not in self.blocked]

        # Pre-compute neighbor map: pos -> [pos] + unblocked neighbors
        self.neighbor_map = {}
        for pos in self.valid_positions:
            neighbors = [
                (nx, ny)
                for (nx, ny), _ in world.grid.get_neighbors(pos)
                if (nx, ny) not in self.blocked
            ]
            self.neighbor_map[pos] = [pos] + neighbors

        # Pre-compute variable IDs
        self.agent_var = {}
        for agent, _ in self.agents:
            c = agent.color
            for t in range(T_MAX + 2):
                for x, y in self.all_positions:
                    self.agent_var[c, x, y, t] = var_factory.agent(c, x, y, t)

        self.laser_var = {}
        for laser, _ in self.lasers:
            c = laser.color
            for t in range(T_MAX + 1):
                for x, y in self.all_positions:
                    self.laser_var[c, x, y, t] = var_factory.laser(c, x, y, t)

        self.beam_var = {}
        for laser, _ in self.lasers:
            c = laser.color
            d = laser.direction
            for t in range(T_MAX + 1):
                for x, y in self.all_positions:
                    self.beam_var[c, d, x, y, t] = var_factory.beam(c, d, x, y, t)

        # Pre-compute beam propagation map per laser:
        # For each laser, for each position, what is the neighbor in that
        # laser's direction, and is it a wall?
        # beam_propagation_map[(laser_color, laser_direction)] = list of
        #   (x, y, nx, ny, is_wall) for all valid (pos, neighbor) pairs
        self.beam_propagation_map = {}
        for laser, _ in self.lasers:
            key = (laser.color, laser.direction)
            entries = []
            direction_vec = laser.direction.value
            for x, y in self.all_positions:
                nx = x + direction_vec[0]
                ny = y + direction_vec[1]
                if not world.grid.is_within_bounds((nx, ny)):
                    continue
                is_wall = world.grid[nx, ny] == CellType.WALL
                entries.append((x, y, nx, ny, is_wall))
            self.beam_propagation_map[key] = entries


class Constraint(ABC):
    def __init__(self, ctx: ConstraintContext):
        self.ctx = ctx
        # Shortcuts for convenience
        self.world = ctx.world
        self.var = ctx.var
        self.T_MAX = ctx.T_MAX
        self.profiler = None

    def set_profiler(self, constraint_profiler):
        """Set the profiler for this constraint"""
        self.profiler = constraint_profiler

    @abstractmethod
    def generate(self):
        """Yield CNF clauses"""
        return []

    def _profile_method(self, method_name: str, method_func):
        """Helper to profile a method that generates clauses"""
        if self.profiler:
            with self.profiler.profile_method(method_name) as method_profiler:
                clauses = method_profiler.count_clauses(method_func())
                return clauses
        else:
            return list(method_func())
