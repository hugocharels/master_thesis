from dataclasses import dataclass

from .constraints.movements import METHOD_LOCAL
from .world_data import AgentData, LaserSourceData, Position, WorldData
from .world_solver import WorldSolver


@dataclass(frozen=True)
class FilteredWorldData:
    width: int
    height: int
    agents: list[AgentData]
    laser_sources: list[LaserSourceData]
    exit_positions: list[Position]
    wall_positions: list[Position]

    def all_positions(self) -> list[Position]:
        return [(i, j) for i in range(self.height) for j in range(self.width)]

    def is_within_bounds(self, pos: Position) -> bool:
        i, j = pos
        return 0 <= i < self.height and 0 <= j < self.width

    def get_neighbors(self, pos: Position) -> list[Position]:
        i, j = pos
        result = []
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.height and 0 <= nj < self.width:
                result.append((ni, nj))
        return result

    def is_wall(self, pos: Position) -> bool:
        return pos in self.wall_positions


@dataclass
class CooperationResult:
    cooperation_needed: bool
    independent_reachability: dict[int, set[int]]
    agent_colors: list[int]
    exit_indices: list[int]


class CooperationSolver:
    """
    Assumes the original world is solvable.
    Cooperation is needed iff agents cannot be matched to distinct exits
    using only individually-solvable (agent, exit) pairs.
    """

    def __init__(self, world: WorldData, T_MAX: int = 10, movement_method=METHOD_LOCAL):
        self.world = world
        self.T_MAX = T_MAX
        self.movement_method = movement_method

    def analyze(self) -> CooperationResult:
        agent_colors = [a.color for a in self.world.agents]
        exit_indices = list(range(len(self.world.exit_positions)))

        if not agent_colors:
            return CooperationResult(False, {}, [], exit_indices)

        reachability: dict[int, set[int]] = {c: set() for c in agent_colors}

        for agent in self.world.agents:
            for exit_idx in exit_indices:
                sub_world = self._single_agent_single_exit_world(agent.color, exit_idx)
                sat, _ = WorldSolver(
                    sub_world,
                    T_MAX=self.T_MAX,
                    movement_method=self.movement_method,
                ).solve()
                if sat:
                    reachability[agent.color].add(exit_idx)

        has_perfect_matching = self._has_agent_perfect_matching(
            agent_colors, exit_indices, reachability
        )

        return CooperationResult(
            cooperation_needed=not has_perfect_matching,
            independent_reachability=reachability,
            agent_colors=agent_colors,
            exit_indices=exit_indices,
        )

    def _single_agent_single_exit_world(
        self, keep_agent_color: int, keep_exit_index: int
    ) -> FilteredWorldData:
        kept_agents = [a for a in self.world.agents if a.color == keep_agent_color]
        kept_lasers = [
            l for l in self.world.laser_sources if l.color == keep_agent_color
        ]
        kept_exit = [self.world.exit_positions[keep_exit_index]]

        return FilteredWorldData(
            width=self.world.width,
            height=self.world.height,
            agents=kept_agents,
            laser_sources=kept_lasers,
            exit_positions=kept_exit,
            wall_positions=list(self.world.wall_positions),
        )

    def _has_agent_perfect_matching(
        self,
        agent_colors: list[int],
        exit_indices: list[int],
        reachability: dict[int, set[int]],
    ) -> bool:
        if len(exit_indices) < len(agent_colors):
            return False

        match_exit_to_agent: dict[int, int] = {}

        def dfs(agent_color: int, seen: set[int]) -> bool:
            for ex in reachability.get(agent_color, set()):
                if ex in seen:
                    continue
                seen.add(ex)
                if ex not in match_exit_to_agent or dfs(match_exit_to_agent[ex], seen):
                    match_exit_to_agent[ex] = agent_color
                    return True
            return False

        matched = 0
        for agent_color in agent_colors:
            if dfs(agent_color, set()):
                matched += 1

        return matched == len(agent_colors)
