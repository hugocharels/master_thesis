from .lasers import LaserConstraints


class StrictLaserConstraints(LaserConstraints):
    """
    Variant of LaserConstraints where beam propagation does NOT stop on agents.
    It only stops at walls / bounds (same as base behavior except agent blocking).
    """

    def _beam_propagation(self):
        """
        Override only this method from LaserConstraints.
        Keep everything else exactly as in the parent class.
        """

        beam_var = self.ctx.beam_var
        propagation_map = self.ctx.beam_propagation_map

        for laser, _ in self.ctx.lasers:
            c = laser.color
            d = laser.direction
            entries = propagation_map[c, d]

            for x, y, nx, ny, is_wall in entries:
                for t in range(self.T_MAX + 1):
                    if is_wall:
                        yield [-beam_var[c, d, nx, ny, t]]
                    else:
                        bv_src = beam_var[c, d, x, y, t]
                        bv_dst = beam_var[c, d, nx, ny, t]
                        yield [-bv_src, bv_dst]
                        yield [bv_src, -bv_dst]
