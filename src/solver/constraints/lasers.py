from itertools import combinations

from .base import Constraint


class LaserConstraints(Constraint):
    def generate(self):
        yield from self._no_step_on_active_laser()
        # yield from self._beam_propagation()
        yield from self._link_beam_and_laser()

    def _no_step_on_active_laser(self):
        for (agent, _), (laser, _) in combinations(
            self.world.get_agents() + self.world.get_lasers(), 2
        ):
            c1, c2 = agent.color, laser.color
            if c1 == c2:
                continue
            for t in range(self.T_MAX + 1):
                for x, y in self.world.grid.positions():
                    yield [-self.var.agent(c1, x, y, t), -self.var.laser(c2, x, y, t)]

    def _beam_propagation(self):
        # TODO:
        ...

    def _link_beam_and_laser(self):
        for laser, _ in self.world.get_lasers():
            c = laser.color
            for x, y in self.world.grid.positions():
                for t in range(self.T_MAX + 1):
                    yield [
                        -self.var.beam(c, laser.direction.id(), x, y, t),
                        self.var.laser(c, x, y, t),
                    ]
                    yield [
                        self.var.beam(c, laser.direction.id(), x, y, t),
                        -self.var.laser(c, x, y, t),
                    ]
