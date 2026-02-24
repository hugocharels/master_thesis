from .base import Constraint


class InitializationConstraints(Constraint):
    def generate(self):
        yield from self._agents_initial_position()
        yield from self._lasers_initial_beam()

    def _agents_initial_position(self):
        for agent, (x, y) in self.world.get_agents():
            yield [self.var.agent(agent.color, x, y, 0)]

    def _lasers_initial_beam(self):
        for laser, (x, y) in self.world.get_lasers():
            for t in range(self.T_MAX + 1):
                yield [self.var.beam(laser.color, laser.direction, x, y, t)]
