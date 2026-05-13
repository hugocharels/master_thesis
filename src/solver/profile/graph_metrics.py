"""Pure graph metrics over a dependency-edge set."""

from __future__ import annotations

from collections import defaultdict

from .result import HelperEvent


def mutual_pairs(edges: set[tuple[int, int]]) -> set[tuple[int, int]]:
    result = set()
    for src, dst in edges:
        if (dst, src) in edges and src < dst:
            result.add((src, dst))
    return result


def largest_scc_size(edges: set[tuple[int, int]], num_agents: int) -> int:
    if num_agents == 0:
        return 0
    adjacency: dict[int, set[int]] = {i: set() for i in range(num_agents)}
    reverse: dict[int, set[int]] = {i: set() for i in range(num_agents)}
    for src, dst in edges:
        adjacency[src].add(dst)
        reverse[dst].add(src)

    visited: set[int] = set()
    order: list[int] = []

    def dfs(node: int) -> None:
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

    def reverse_dfs(node: int, component: list[int]) -> None:
        visited.add(node)
        component.append(node)
        for nxt in reverse[node]:
            if nxt not in visited:
                reverse_dfs(nxt, component)

    for node in reversed(order):
        if node in visited:
            continue
        component: list[int] = []
        reverse_dfs(node, component)
        largest = max(largest, len(component))
    return largest


def longest_chain_length(edges: set[tuple[int, int]], num_agents: int) -> int:
    adjacency: dict[int, set[int]] = {i: set() for i in range(num_agents)}
    indegree: dict[int, int] = {i: 0 for i in range(num_agents)}
    for src, dst in edges:
        if dst not in adjacency[src]:
            adjacency[src].add(dst)
            indegree[dst] += 1

    queue = [node for node in range(num_agents) if indegree[node] == 0]
    topo: list[int] = []
    while queue:
        node = queue.pop()
        topo.append(node)
        for nxt in adjacency[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(topo) != num_agents:
        return 0

    dist: dict[int, int] = {i: 0 for i in range(num_agents)}
    for node in topo:
        for nxt in adjacency[node]:
            dist[nxt] = max(dist[nxt], dist[node] + 1)
    return max(dist.values(), default=0)


def synchronous_width(helper_events: set[HelperEvent]) -> int:
    helpers_by_time: dict[int, set[int]] = defaultdict(set)
    for event in helper_events:
        helpers_by_time[event.time].add(event.helper)
    return max((len(helpers) for helpers in helpers_by_time.values()), default=0)
