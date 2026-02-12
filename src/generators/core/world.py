from typing import Optional

from core.grid import Grid
from core.types import CellType, Entity, Position


class World:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = Grid(width, height, Entity(CellType.EMPTY))

    def add_entity(self, pos: Position, entity: Entity) -> bool:
        return self.grid.set(pos, entity)

    def get_entity(self, pos: Position) -> Optional[Entity]:
        return self.grid.get(pos)

    def is_position_free(self, pos: Position) -> bool:
        return self.grid.is_within_bounds(pos) and self.grid.get(pos) == CellType.EMPTY

    def to_str(self) -> str:
        return "\n".join(
            " ".join(self.grid.safe_get((i, j)).to_str() for j in range(self.width))
            for i in range(self.height)
        )
