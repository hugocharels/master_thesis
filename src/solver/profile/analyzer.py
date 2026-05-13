"""CooperationProfileAnalyzer orchestrator."""

from __future__ import annotations

from collections import defaultdict

from lle import World

from .._internal.grid import is_within_bounds as _is_within_bounds
from .._internal.types import agents_from_world, laser_sources_from_world
from ..cooperation_solver import CooperationSolver
from ..world_solver import LaserMode, WorldSolver
from .graph_metrics import largest_scc_size, longest_chain_length, mutual_pairs, synchronous_width
from .result import CooperationProfileResult, HelperEvent


class CooperationProfileAnalyzer:
    """Analyzes the cooperation profile of an LLE world and classifies its dependency structure."""

    def __init__(self, world: World, T_MAX: int = 10, movement_method: str = "local"):
        self.world = world
        self.T_MAX = T_MAX
        self.movement_method = movement_method

    def analyze(self) -> CooperationProfileResult:
        solver = WorldSolver(
            self.world,
            T_MAX=self.T_MAX,
            movement_method=self.movement_method,
        )
        sat, model = solver.solve()
        num_agents = len(agents_from_world(self.world))

        if not sat:
            return CooperationProfileResult(
                solvable=False,
                cooperation_required=False,
                num_agents=num_agents,
                necessary_helpers=frozenset(),
                dependency_edges=frozenset(),
                helper_events=tuple(),
                mutual_pairs=frozenset(),
                longest_chain_length=0,
                largest_scc_size=0,
                synchronous_width=0,
                profile="unsolvable",
            )

        cooperation_required = CooperationSolver(
            self.world,
            T_MAX=self.T_MAX,
            movement_method=self.movement_method,
        ).analyze().cooperation_needed

        positions_by_time = self._extract_positions_by_time(solver, model)
        helper_events = self._extract_helper_events(positions_by_time)
        necessary_helpers = self._find_necessary_helpers()
        dependency_edges = self._extract_dependency_edges(helper_events)

        mp = mutual_pairs(dependency_edges)
        lscc = largest_scc_size(dependency_edges, num_agents)
        lcl = longest_chain_length(dependency_edges, num_agents)
        sw = synchronous_width(helper_events)
        profile = self._classify_profile(
            cooperation_required=cooperation_required,
            dependency_edges=dependency_edges,
            mutual_pairs=mp,
            largest_scc_size=lscc,
            longest_chain_length=lcl,
            num_agents=num_agents,
        )

        return CooperationProfileResult(
            solvable=True,
            cooperation_required=cooperation_required,
            num_agents=num_agents,
            necessary_helpers=frozenset(necessary_helpers),
            dependency_edges=frozenset(dependency_edges),
            helper_events=tuple(sorted(helper_events, key=lambda e: (e.time, e.helper, e.beneficiary))),
            mutual_pairs=frozenset(mp),
            longest_chain_length=lcl,
            largest_scc_size=lscc,
            synchronous_width=sw,
            profile=profile,
        )

    def _extract_positions_by_time(self, solver: WorldSolver, model) -> dict[int, dict[int, tuple[int, int]]]:
        positions_by_time: dict[int, dict[int, tuple[int, int]]] = defaultdict(dict)
        for lit in model:
            if lit <= 0:
                continue
            obj = solver.var.pool.obj(abs(lit))
            if not obj or obj[0] != "agent":
                continue
            _, color, position, t = obj
            positions_by_time[t][color] = position
        return positions_by_time

    def _find_necessary_helpers(self) -> set[int]:
        necessary = set()
        for agent in agents_from_world(self.world):
            sat, _ = WorldSolver(
                self.world,
                T_MAX=self.T_MAX,
                laser_mode=LaserMode.SELECTIVE_STRICT,
                strict_colors=frozenset({agent.color}),
                movement_method=self.movement_method,
            ).solve()
            if not sat:
                necessary.add(agent.color)
        return necessary

    def _extract_helper_events(self, positions_by_time) -> set[HelperEvent]:
        events: set[HelperEvent] = set()
        beam_paths = self._raw_beam_paths()

        for t, positions in positions_by_time.items():
            for helper, helper_pos in positions.items():
                for source_pos, path in beam_paths.get(helper, []):
                    if helper_pos not in path:
                        continue
                    helper_index = path.index(helper_pos)
                    downstream = set(path[helper_index + 1:])
                    if not downstream:
                        continue
                    for beneficiary, beneficiary_pos in positions.items():
                        if beneficiary == helper:
                            continue
                        if beneficiary_pos in downstream:
                            events.add(
                                HelperEvent(
                                    helper=helper,
                                    beneficiary=beneficiary,
                                    time=t,
                                    position=helper_pos,
                                    laser_source=source_pos,
                                )
                            )
        return events

    def _raw_beam_paths(self) -> dict[int, list[tuple[tuple[int, int], list[tuple[int, int]]]]]:
        paths: dict[int, list[tuple[tuple[int, int], list[tuple[int, int]]]]] = defaultdict(list)
        wall_positions = frozenset(self.world.wall_pos)
        _lasers = laser_sources_from_world(self.world)
        laser_source_positions = {src.position for src in _lasers}

        for laser in _lasers:
            di, dj = laser.direction
            x, y = laser.position
            x += di
            y += dj
            path: list[tuple[int, int]] = []
            while _is_within_bounds(self.world, (x, y)):
                if (x, y) in wall_positions or (x, y) in laser_source_positions:
                    break
                path.append((x, y))
                x += di
                y += dj
            paths[laser.color].append((laser.position, path))
        return paths

    def _extract_dependency_edges(self, helper_events: set[HelperEvent]) -> set[tuple[int, int]]:
        return {(event.helper, event.beneficiary) for event in helper_events}

    def _classify_profile(
        self,
        cooperation_required: bool,
        dependency_edges: set[tuple[int, int]],
        mutual_pairs: set[tuple[int, int]],
        largest_scc_size: int,
        longest_chain_length: int,
        num_agents: int,
    ) -> str:
        if not cooperation_required:
            return "independent"
        if largest_scc_size == num_agents and num_agents > 1:
            return "fully_coupled"
        if mutual_pairs:
            return "mutual"
        indegree = defaultdict(int)
        outdegree = defaultdict(int)
        nodes: set[int] = set()
        for src, dst in dependency_edges:
            indegree[dst] += 1
            outdegree[src] += 1
            nodes.add(src)
            nodes.add(dst)
        if any(count >= 2 for count in indegree.values()):
            return "distributed"
        if (
            dependency_edges
            and longest_chain_length >= 2
            and all(indegree[n] <= 1 for n in nodes)
            and all(outdegree[n] <= 1 for n in nodes)
            and longest_chain_length >= max(1, len(nodes) - 1)
        ):
            return "chain"
        if dependency_edges:
            return "asymmetric"
        return "cooperative"
