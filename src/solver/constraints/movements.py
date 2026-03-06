from itertools import combinations

from .base import Constraint

# Movement method constants
METHOD_LOCAL = "local"  # Inline uniqueness via neighbor combinations (current default)
METHOD_GLOBAL = "global"  # Separate global all-pairs uniqueness constraint


class MovementConstraints(Constraint):
    def __init__(self, world, var_factory, T_MAX, movement_method=METHOD_LOCAL):
        super().__init__(world, var_factory, T_MAX)
        self.movement_method = movement_method

    def generate(self):
        all_clauses = []

        if self.movement_method == METHOD_LOCAL:
            # Current approach: movement rules include inline uniqueness
            all_clauses.extend(
                self._profile_method("movement_rules", self._movement_rules_local)
            )
        elif self.movement_method == METHOD_GLOBAL:
            # Alternative: movement rules without inline uniqueness + global uniqueness
            all_clauses.extend(
                self._profile_method("movement_rules", self._movement_rules_global)
            )
            all_clauses.extend(
                self._profile_method("unique_position", self._unique_position)
            )
        else:
            raise ValueError(f"Unknown movement method: {self.movement_method}")

        all_clauses.extend(self._profile_method("no_overlap", self._no_overlap))
        all_clauses.extend(
            self._profile_method("must_be_on_exit", self._must_be_on_exit)
        )
        all_clauses.extend(self._profile_method("stays_on_exit", self._stays_on_exit))
        return all_clauses

    def _movement_rules_local(self):
        """Movement rules with inline uniqueness (neighbor-based pairwise exclusion)."""
        for agent, _ in self.world.get_agents():
            c = agent.color
            for t in range(self.T_MAX):
                for x, y in self.world.grid.positions():
                    if (x, y) in self.world.get_walls() or (x, y) in [
                        pos for _, pos in self.world.get_lasers()
                    ]:
                        continue
                    n_pos = [(x, y)] + [
                        (nx, ny)
                        for (nx, ny), _ in self.world.grid.get_neighbors((x, y))
                        if (nx, ny) not in self.world.get_walls()
                        and (nx, ny) not in [pos for _, pos in self.world.get_lasers()]
                    ]
                    yield [-self.var.agent(c, x, y, t)] + [
                        self.var.agent(c, nx, ny, t + 1) for (nx, ny) in n_pos
                    ]
                    yield [-self.var.agent(c, x, y, t + 1)] + [
                        self.var.agent(c, nx, ny, t) for (nx, ny) in n_pos
                    ]
                    # Inline uniqueness: only neighbor pairs excluded
                    for (x1, y1), (x2, y2) in combinations(n_pos, 2):
                        yield [
                            -self.var.agent(c, x1, y1, t + 1),
                            -self.var.agent(c, x2, y2, t + 1),
                        ]

    def _movement_rules_global(self):
        """Movement rules without inline uniqueness (used with _unique_position)."""
        for agent, _ in self.world.get_agents():
            c = agent.color
            for t in range(self.T_MAX):
                for x, y in self.world.grid.positions():
                    if (x, y) in self.world.get_walls() or (x, y) in [
                        pos for _, pos in self.world.get_lasers()
                    ]:
                        continue
                    n_pos = [(x, y)] + [
                        (nx, ny)
                        for (nx, ny), _ in self.world.grid.get_neighbors((x, y))
                        if (nx, ny) not in self.world.get_walls()
                        and (nx, ny) not in [pos for _, pos in self.world.get_lasers()]
                    ]
                    yield [-self.var.agent(c, x, y, t)] + [
                        self.var.agent(c, nx, ny, t + 1) for (nx, ny) in n_pos
                    ]

    def _unique_position(self):
        """Global uniqueness: all-pairs exclusion for every timestep."""
        for agent, _ in self.world.get_agents():
            c = agent.color
            for t in range(1, self.T_MAX + 1):
                for (x1, y1), (x2, y2) in combinations(self.world.grid.positions(), 2):
                    yield [-self.var.agent(c, x1, y1, t), -self.var.agent(c, x2, y2, t)]

    def _no_overlap(self):
        for (agent1, _), (agent2, _) in combinations(self.world.get_agents(), 2):
            c1, c2 = agent1.color, agent2.color
            for t in range(self.T_MAX + 1):
                for x, y in self.world.grid.positions():
                    yield [-self.var.agent(c1, x, y, t), -self.var.agent(c2, x, y, t)]
                    yield [
                        -self.var.agent(c1, x, y, t + 1),
                        -self.var.agent(c2, x, y, t),
                    ]
                    yield [
                        -self.var.agent(c1, x, y, t),
                        -self.var.agent(c2, x, y, t + 1),
                    ]

    def _must_be_on_exit(self):
        for x, y in self.world.get_exits():
            yield [
                self.var.agent(agent.color, x, y, self.T_MAX)
                for agent, _ in self.world.get_agents()
            ]

    def _stays_on_exit(self):
        for agent, _ in self.world.get_agents():
            c = agent.color
            for t in range(self.T_MAX):
                for x, y in self.world.get_exits():
                    yield [
                        -self.var.agent(c, x, y, t),
                        self.var.agent(c, x, y, t + 1),
                    ]
