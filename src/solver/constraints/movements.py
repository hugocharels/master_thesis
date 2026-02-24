from itertools import combinations

from .base import Constraint


class MovementConstraints(Constraint):
    def generate(self):
        yield from self._movement_rules()
        yield from self._unique_position()
        yield from self._no_overlap()
        yield from self._must_be_on_exit()

    def _movement_rules(self):
        for agent, _ in self.world.get_agents():
            c = agent.color
            for t in range(self.T_MAX):
                for x, y in self.world.grid.positions():
                    n_pos = [(x, y)] + [
                        (nx, ny)
                        for (nx, ny), _ in self.world.grid.get_neighbors((x, y))
                        if (nx, ny) not in self.world.get_walls()
                    ]
                    yield [-self.var.agent(c, x, y, t)] + [
                        self.var.agent(c, nx, ny, t + 1) for (nx, ny) in n_pos
                    ]
                    yield [-self.var.agent(c, x, y, t + 1)] + [
                        self.var.agent(c, nx, ny, t) for (nx, ny) in n_pos
                    ]

    def _unique_position(self):
        for agent, _ in self.world.get_agents():
            c = agent.color
            for t in range(self.T_MAX + 1):
                for (x1, y1), (x2, y2) in combinations(self.world.grid.positions(), 2):
                    yield [-self.var.agent(c, x1, y1, t), -self.var.agent(c, x2, y2, t)]

    def _no_overlap(self):
        for (agent1, _), (agent2, _) in combinations(self.world.get_agents(), 2):
            c1, c2 = agent1.color, agent2.color
            for t in range(self.T_MAX + 1):
                for x, y in self.world.grid.positions():
                    yield [-self.var.agent(c1, x, y, t), -self.var.agent(c2, x, y, t)]

    def _must_be_on_exit(self):
        for x, y in self.world.get_exits():
            yield [
                self.var.agent(agent.color, x, y, self.T_MAX)
                for agent, _ in self.world.get_agents()
            ]
