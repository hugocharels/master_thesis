from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .cooperation_solver import CooperationSolver
from .world_solver import WorldSolver
from .world_solver_selective_strict_laser import WorldSolverSelectiveStrictLaser


@dataclass(frozen=True)
class HelperEvent:
    helper: int
    beneficiary: int
    time: int
    position: tuple[int, int]
    laser_source: tuple[int, int]


@dataclass(frozen=True)
class CooperationProfileResult:
    solvable: bool
    cooperation_required: bool
    num_agents: int
    necessary_helpers: frozenset[int]
    dependency_edges: frozenset[tuple[int, int]]
    helper_events: tuple[HelperEvent, ...]
    mutual_pairs: frozenset[tuple[int, int]]
    longest_chain_length: int
    largest_scc_size: int
    synchronous_width: int
    profile: str

    def matches_profile(self, target: str | None) -> bool:
        if target in (None, "", "any"):
            return True
        if target == "independent":
            return not self.cooperation_required
        if target == "cooperative":
            return self.cooperation_required
        if target == "asymmetric":
            return self.cooperation_required and self.profile == "asymmetric"
        if target == "mutual":
            return bool(self.mutual_pairs)
        if target == "chain":
            return self.cooperation_required and self._is_chain_like()
        if target == "distributed":
            return self.cooperation_required and self._has_distributed_support()
        if target == "fully_coupled":
            return self.cooperation_required and self.largest_scc_size == self.num_agents
        raise ValueError(f"Unknown cooperation profile: {target}")

    def _has_distributed_support(self) -> bool:
        indegree = defaultdict(int)
        for _, dst in self.dependency_edges:
            indegree[dst] += 1
        return any(count >= 2 for count in indegree.values())

    def _is_chain_like(self) -> bool:
        if not self.dependency_edges:
            return False

        indegree = defaultdict(int)
        outdegree = defaultdict(int)
        nodes = set()
        for src, dst in self.dependency_edges:
            indegree[dst] += 1
            outdegree[src] += 1
            nodes.add(src)
            nodes.add(dst)

        if any(indegree[n] > 1 for n in nodes):
            return False
        if any(outdegree[n] > 1 for n in nodes):
            return False
        return self.longest_chain_length >= max(1, len(nodes) - 1)


class CooperationProfileAnalyzer:
    def __init__(self, world, T_MAX: int = 10, movement_method="local"):
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
        num_agents = len(self.world.agents)

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

        # If selective strict checks prove a helper is necessary but the sampled plan
        # does not expose a concrete beneficiary, keep the signal by attaching a
        # conservative edge to every other agent.
        for helper in necessary_helpers:
            if any(src == helper for src, _ in dependency_edges):
                continue
            for agent in range(num_agents):
                if agent != helper:
                    dependency_edges.add((helper, agent))

        mutual_pairs = self._mutual_pairs(dependency_edges)
        largest_scc_size = self._largest_scc_size(dependency_edges, num_agents)
        longest_chain_length = self._longest_chain_length(dependency_edges, num_agents)
        synchronous_width = self._synchronous_width(helper_events)
        profile = self._classify_profile(
            cooperation_required=cooperation_required,
            dependency_edges=dependency_edges,
            mutual_pairs=mutual_pairs,
            largest_scc_size=largest_scc_size,
            num_agents=num_agents,
        )

        return CooperationProfileResult(
            solvable=True,
            cooperation_required=cooperation_required,
            num_agents=num_agents,
            necessary_helpers=frozenset(necessary_helpers),
            dependency_edges=frozenset(dependency_edges),
            helper_events=tuple(sorted(helper_events, key=lambda e: (e.time, e.helper, e.beneficiary))),
            mutual_pairs=frozenset(mutual_pairs),
            longest_chain_length=longest_chain_length,
            largest_scc_size=largest_scc_size,
            synchronous_width=synchronous_width,
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
        for agent in self.world.agents:
            sat, _ = WorldSolverSelectiveStrictLaser(
                self.world,
                strict_colors={agent.color},
                T_MAX=self.T_MAX,
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
                    downstream = set(path[helper_index + 1 :])
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
        wall_positions = frozenset(self.world.wall_positions)
        laser_sources = {src.position for src in self.world.laser_sources}

        for laser in self.world.laser_sources:
            di, dj = laser.direction
            x, y = laser.position
            x += di
            y += dj
            path: list[tuple[int, int]] = []
            while self.world.is_within_bounds((x, y)):
                if (x, y) in wall_positions or (x, y) in laser_sources:
                    break
                path.append((x, y))
                x += di
                y += dj
            paths[laser.color].append((laser.position, path))
        return paths

    def _extract_dependency_edges(self, helper_events: set[HelperEvent]) -> set[tuple[int, int]]:
        return {(event.helper, event.beneficiary) for event in helper_events}

    def _mutual_pairs(self, edges: set[tuple[int, int]]) -> set[tuple[int, int]]:
        mutual = set()
        for src, dst in edges:
            if (dst, src) in edges and src < dst:
                mutual.add((src, dst))
        return mutual

    def _classify_profile(
        self,
        cooperation_required: bool,
        dependency_edges: set[tuple[int, int]],
        mutual_pairs: set[tuple[int, int]],
        largest_scc_size: int,
        num_agents: int,
    ) -> str:
        if not cooperation_required:
            return "independent"
        if largest_scc_size == num_agents and num_agents > 1:
            return "fully_coupled"
        if mutual_pairs:
            return "mutual"
        indegree = defaultdict(int)
        for _, dst in dependency_edges:
            indegree[dst] += 1
        if any(count >= 2 for count in indegree.values()):
            return "distributed"
        if dependency_edges:
            return "asymmetric"
        return "cooperative"

    def _largest_scc_size(self, edges: set[tuple[int, int]], num_agents: int) -> int:
        if num_agents == 0:
            return 0
        adjacency = {i: set() for i in range(num_agents)}
        reverse = {i: set() for i in range(num_agents)}
        for src, dst in edges:
            adjacency[src].add(dst)
            reverse[dst].add(src)

        visited = set()
        order = []

        def dfs(node):
            visited.add(node)
            for nxt in adjacency[node]:
                if nxt not in visited:
                    dfs(nxt)
            order.append(node)

        for node in range(num_agents):
            if node not in visited:
                dfs(node)

        visited.clear()
        largest = 1

        def reverse_dfs(node, component):
            visited.add(node)
            component.append(node)
            for nxt in reverse[node]:
                if nxt not in visited:
                    reverse_dfs(nxt, component)

        for node in reversed(order):
            if node in visited:
                continue
            component = []
            reverse_dfs(node, component)
            largest = max(largest, len(component))
        return largest

    def _longest_chain_length(self, edges: set[tuple[int, int]], num_agents: int) -> int:
        adjacency = {i: set() for i in range(num_agents)}
        indegree = {i: 0 for i in range(num_agents)}
        for src, dst in edges:
            if dst not in adjacency[src]:
                adjacency[src].add(dst)
                indegree[dst] += 1

        queue = [node for node in range(num_agents) if indegree[node] == 0]
        topo = []
        while queue:
            node = queue.pop()
            topo.append(node)
            for nxt in adjacency[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if len(topo) != num_agents:
            return 0

        dist = {i: 0 for i in range(num_agents)}
        for node in topo:
            for nxt in adjacency[node]:
                dist[nxt] = max(dist[nxt], dist[node] + 1)
        return max(dist.values(), default=0)

    def _synchronous_width(self, helper_events: set[HelperEvent]) -> int:
        helpers_by_time: dict[int, set[int]] = defaultdict(set)
        for event in helper_events:
            helpers_by_time[event.time].add(event.helper)
        return max((len(helpers) for helpers in helpers_by_time.values()), default=0)
