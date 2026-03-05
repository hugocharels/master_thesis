from .base import Constraint


class InitializationConstraints(Constraint):
    def generate(self):
        all_clauses = []
        all_clauses.extend(
            self._profile_method(
                "agents_initial_position", self._agents_initial_position
            )
        )
        all_clauses.extend(
            self._profile_method("lasers_initial_beam", self._lasers_initial_beam)
        )
        return all_clauses

    def _agents_initial_position(self):
        for agent, (x, y) in self.world.get_agents():
            yield [self.var.agent(agent.color, x, y, 0)]
            for other_x, other_y in self.world.grid.positions():
                if (other_x, other_y) != (x, y):
                    yield [-self.var.agent(agent.color, other_x, other_y, 0)]

    def _lasers_initial_beam(self):
        for laser, (x, y) in self.world.get_lasers():
            for t in range(self.T_MAX + 1):
                yield [self.var.beam(laser.color, laser.direction, x, y, t)]
