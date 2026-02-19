from typing import List, Tuple

from core.grid import Grid
from core.types import CellType, ColoredEntity, DirectionalEntity, Entity, Position


class World:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = Grid(width, height, Entity(CellType.EMPTY))

    def add_entity(self, pos: Position, entity: Entity) -> None:
        self.grid[pos] = entity

    def get_entity(self, pos: Position) -> Entity:
        return self.grid[pos]

    def is_position_free(self, pos: Position) -> bool:
        return self.grid[pos] == CellType.EMPTY

    def to_str(self) -> str:
        return "\n".join(
            " ".join(self.grid[(x, y)].to_str() for y in range(self.width))
            for x in range(self.height)
        )

    def get_entities_by_type(
        self, entity_type: CellType
    ) -> List[Tuple[Entity, Position]]:
        result = []
        for pos in self.grid.positions():
            entity = self.grid[pos]
            if entity.entity_type == entity_type:
                result.append((entity, pos))
        return result

    def get_agents(self) -> List[Tuple[ColoredEntity, Position]]:
        """Get all agents with their color information."""
        return [
            (entity, pos)
            for entity, pos in self.get_entities_by_type(CellType.AGENT)
            if isinstance(entity, ColoredEntity)
        ]

    def get_lasers(self) -> List[Tuple[DirectionalEntity, Position]]:
        """Get all lasers with their color and direction information."""
        return [
            (entity, pos)
            for entity, pos in self.get_entities_by_type(CellType.LASER)
            if isinstance(entity, DirectionalEntity)
        ]

    def get_walls(self) -> List[Position]:
        """Get all wall positions."""
        return [pos for _, pos in self.get_entities_by_type(CellType.WALL)]

    def get_exits(self) -> List[Position]:
        """Get all exit positions."""
        return [pos for _, pos in self.get_entities_by_type(CellType.EXIT)]
