from .lasers import LaserConstraints


class SelectiveStrictLaserConstraints(LaserConstraints):
    """
    Laser constraints where only a selected subset of colors loses the ability
    to truncate their own beam. Same-colour immunity is preserved for every
    colour, matching the strict beam semantics of Definition 3.6: agents can
    still occupy cells crossed by their own beam, but the beam continues
    through them when their colour is in strict_colors.
    """

    def __init__(self, ctx, strict_colors):
        super().__init__(ctx)
        self.strict_colors = frozenset(strict_colors)

    def _beam_propagation(self):
        agent_var = self.ctx.agent_var
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

                        if c in self.strict_colors:
                            yield [-bv_src, bv_dst]
                            yield [bv_src, -bv_dst]
                        else:
                            av_dst = agent_var[c, nx, ny, t]
                            yield [-bv_src, av_dst, bv_dst]
                            yield [bv_src, -bv_dst]
                            yield [-av_dst, -bv_dst]
