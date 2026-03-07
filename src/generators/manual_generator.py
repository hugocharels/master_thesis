from lle import World

from generators.base_generator import BaseGenerator
from generators.registry import register_generator
from generators.world_builder import Direction, WorldBuilder


@register_generator("manual")
class ManualGenerator(BaseGenerator):
    """Hardcoded deterministic level generator."""

    @staticmethod
    def add_arguments(parser):
        pass

    @classmethod
    def from_args(cls, args):
        return cls()

    def generate(self) -> World:
        return (
            WorldBuilder(10, 10)
            .add_agent(0, (0, 0))
            .add_agent(1, (0, 9))
            .add_wall((5, 9))
            .add_laser(0, (5, 8), Direction.WEST)
            .add_exit((9, 0))
            .add_exit((9, 9))
            .build()
        )
