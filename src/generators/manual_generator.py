from core import Agent, CellType, Direction, Entity, Laser, World

from generators.base_generator import BaseGenerator
from generators.registry import register_generator


@register_generator("manual")
class ManualGenerator(BaseGenerator):
    """
    Hardcoded deterministic level generator
    """

    @staticmethod
    def add_arguments(parser):
        pass  # no arguments needed

    @classmethod
    def from_args(cls, args):
        return cls()

    def generate(self) -> World:
        world = World(10, 10)
        world.add_entity((0, 0), Agent(0))
        world.add_entity((0, 9), Agent(1))
        world.add_entity((5, 9), Entity(CellType.WALL))
        world.add_entity((5, 8), Laser(0, Direction.WEST))
        world.add_entity((9, 9), Entity(CellType.EXIT))
        world.add_entity((9, 0), Entity(CellType.EXIT))
        return world
