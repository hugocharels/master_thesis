from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, TypeVar

Position = Tuple[int, int]
T = TypeVar("T")


class Direction(Enum):
    NORTH = (-1, 0)
    SOUTH = (1, 0)
    EAST = (0, 1)
    WEST = (0, -1)

    def to_str(self) -> str:
        if self == Direction.NORTH:
            return "N"
        elif self == Direction.SOUTH:
            return "S"
        elif self == Direction.EAST:
            return "E"
        elif self == Direction.WEST:
            return "W"
        return "?"


class CellType(Enum):
    EMPTY = 0
    WALL = 1
    VOID = 2
    EXIT = 3
    GEM = 4
    AGENT = 5
    LASER = 6


@dataclass(frozen=True)
class Entity:
    entity_type: CellType

    def __eq__(self, value: object, /) -> bool:
        if isinstance(value, CellType):
            return self.entity_type == value
        return NotImplemented

    def to_str(self) -> str:
        if self.entity_type == CellType.EMPTY:
            return "."
        elif self.entity_type == CellType.WALL:
            return "@"
        elif self.entity_type == CellType.VOID:
            return "V"
        elif self.entity_type == CellType.EXIT:
            return "X"
        elif self.entity_type == CellType.GEM:
            return "G"
        return "?"


@dataclass(frozen=True)
class ColoredEntity(Entity):
    color: int

    def to_str(self) -> str:
        if self.entity_type == CellType.AGENT:
            return f"S{self.color}"
        return super().to_str()


@dataclass(frozen=True)
class DirectionalEntity(ColoredEntity):
    direction: Direction

    def to_str(self) -> str:
        if self.entity_type == CellType.LASER:
            return f"L{self.color}{self.direction.to_str()}"
        return super().to_str()


@dataclass(frozen=True)
class Agent(ColoredEntity):
    entity_type: CellType = field(init=False, default=CellType.AGENT)


@dataclass(frozen=True)
class Laser(DirectionalEntity):
    entity_type: CellType = field(init=False, default=CellType.LASER)
