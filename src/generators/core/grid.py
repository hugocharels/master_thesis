from typing import Generic, List, Optional, Tuple

from core.types import Position, T


class Grid(Generic[T]):
    def __init__(self, width: int, height: int, default_value: T):
        self.width = width
        self.height = height
        self.grid = [[default_value for _ in range(width)] for _ in range(height)]

    def is_within_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.height and 0 <= y < self.width

    def get(self, pos: Position) -> Optional[T]:
        if not self.is_within_bounds(pos):
            return None
        return self.grid[pos[0]][pos[1]]

    def set(self, pos: Position, value: T) -> bool:
        if not self.is_within_bounds(pos):
            return False
        self.grid[pos[0]][pos[1]] = value
        return True

    def get_neighbors(
        self, pos: Position, include_diagonals: bool = False
    ) -> List[Tuple[Position, T]]:
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        if include_diagonals:
            directions.extend([(1, 1), (-1, -1), (1, -1), (-1, 1)])

        neighbors = []
        for dx, dy in directions:
            new_pos = (pos[0] + dx, pos[1] + dy)
            if self.is_within_bounds(new_pos):
                neighbors.append((new_pos, self.get(new_pos)))
        return neighbors
