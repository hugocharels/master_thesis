from typing import Set

from core.grid import Grid
from core.types import CellType, Entity, Position


class World:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = Grid(width, height, CellType.EMPTY)
        self.entities: Set[Entity] = set()

    def add_entity(self, entity: Entity) -> bool:
        if not self.grid.is_within_bounds(entity.position):
            return False
        self.entities.add(entity)
        return True

    def get_entities_at(self, pos: Position) -> Set[Entity]:
        return {entity for entity in self.entities if entity.position == pos}

    def is_position_free(self, pos: Position) -> bool:
        return (
            self.grid.is_within_bounds(pos)
            and self.grid.get(pos) == CellType.EMPTY
            and not self.get_entities_at(pos)
        )

    def to_str(self) -> str:
        """
        Converts the world state to a string representation.
        Empty cells are represented by '.'
        """
        # Initialize empty grid with dots
        string_grid = [["." for _ in range(self.width)] for _ in range(self.height)]

        # Fill in all entities
        for entity in self.entities:
            x, y = entity.position
            string_grid[x][y] = entity.to_str()

        # Convert to string with spaces between cells
        return "\n".join(" ".join(row) for row in string_grid)
