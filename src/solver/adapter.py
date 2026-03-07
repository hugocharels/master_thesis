"""
Adapter that wraps lle.World and exposes it as WorldData.

This is the only place in the solver package that knows about lle.
"""

from __future__ import annotations

from typing import List

from lle import World as LLEWorld

from .world_data import AgentData, LaserSourceData, Position


class LLEAdapter:
    """Adapts an lle.World into the WorldData protocol."""

    def __init__(self, lle_world: LLEWorld):
        self._world = lle_world
        self._wall_set: frozenset[Position] | None = None

    @property
    def width(self) -> int:
        return self._world.width

    @property
    def height(self) -> int:
        return self._world.height

    @property
    def agents(self) -> List[AgentData]:
        return [
            AgentData(color=i, position=pos)
            for i, pos in enumerate(self._world.start_pos)
        ]

    @property
    def laser_sources(self) -> List[LaserSourceData]:
        return [
            LaserSourceData(
                color=src.agent_id,
                direction=src.direction.delta(),
                position=src.pos,
            )
            for src in self._world.laser_sources
        ]

    @property
    def exit_positions(self) -> List[Position]:
        return list(self._world.exit_pos)

    @property
    def wall_positions(self) -> List[Position]:
        return list(self._world.wall_pos)

    def all_positions(self) -> List[Position]:
        return [(i, j) for i in range(self.height) for j in range(self.width)]

    def is_within_bounds(self, pos: Position) -> bool:
        i, j = pos
        return 0 <= i < self.height and 0 <= j < self.width

    def get_neighbors(self, pos: Position) -> List[Position]:
        i, j = pos
        result = []
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.height and 0 <= nj < self.width:
                result.append((ni, nj))
        return result

    def is_wall(self, pos: Position) -> bool:
        if self._wall_set is None:
            self._wall_set = frozenset(self._world.wall_pos)
        return pos in self._wall_set
