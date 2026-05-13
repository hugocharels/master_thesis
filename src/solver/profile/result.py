"""Dataclasses describing the cooperation-profile analysis result."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class HelperEvent:
    """A single blocking event where one agent shields another from a laser."""

    helper: int
    beneficiary: int
    time: int
    position: tuple[int, int]
    laser_source: tuple[int, int]


@dataclass(frozen=True)
class CooperationProfileResult:
    """Full cooperation-profile analysis result for an LLE world."""

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
            return (
                self.cooperation_required
                and self.largest_scc_size == self.num_agents
            )
        raise ValueError(f"Unknown cooperation profile: {target}")

    def _has_distributed_support(self) -> bool:
        indegree: dict[int, int] = defaultdict(int)
        for _, dst in self.dependency_edges:
            indegree[dst] += 1
        return any(count >= 2 for count in indegree.values())

    def _is_chain_like(self) -> bool:
        if not self.dependency_edges:
            return False
        indegree: dict[int, int] = defaultdict(int)
        outdegree: dict[int, int] = defaultdict(int)
        nodes: set[int] = set()
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
