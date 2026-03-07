"""
Protocol and value objects defining what the solver needs from a world.

This is the boundary between the solver and whatever world representation
is used (lle.World, a test stub, a Rust port, etc.). The solver never
imports lle directly — it only depends on this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Tuple

Position = Tuple[int, int]


@dataclass(frozen=True)
class AgentData:
    """An agent the solver cares about: a color and a start position."""

    color: int
    position: Position


@dataclass(frozen=True)
class LaserSourceData:
    """A laser source: color, direction vector, and grid position."""

    color: int
    direction: Tuple[int, int]  # (di, dj), e.g. (0, 1) for EAST
    position: Position


class WorldData(Protocol):
    """
    The contract between the solver and any world representation.

    Implement this protocol (or use LLEAdapter) to feed a world
    into the solver. The solver only depends on this interface.
    """

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    @property
    def agents(self) -> List[AgentData]: ...

    @property
    def laser_sources(self) -> List[LaserSourceData]: ...

    @property
    def exit_positions(self) -> List[Position]: ...

    @property
    def wall_positions(self) -> List[Position]: ...

    def all_positions(self) -> List[Position]:
        """Every (i, j) cell in the grid."""
        ...

    def is_within_bounds(self, pos: Position) -> bool: ...

    def get_neighbors(self, pos: Position) -> List[Position]:
        """4-directional neighbors that are within bounds."""
        ...

    def is_wall(self, pos: Position) -> bool: ...
