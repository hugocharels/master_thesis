"""Minimal, deterministic reproducer for the LLE / pysat SIGSEGV.

Unlike ``reproduce_lle_segfault.py`` (which samples thousands of random worlds
until one happens to crash), this script rebuilds the *single* world that
crashed in the rejection benchmark and replays exactly the operation that
segfaulted: the cooperation-profile analysis, which calls the pysat / Minisat
C extension repeatedly. No regeneration, no sampling -- just the one problematic
instance.

The world below was captured verbatim from ``lle_segfault_capture.log``
(attempt 1164): an 8x8 grid, 4 agents, 3 lasers, t_max = 20. The crash signature
recorded there was::

    Windows fatal exception: access violation
      pysat/solvers.py", line 6706 in solve
      src/solver/world_solver.py", line 98 in solve
      src/solver/profile/analyzer.py", line 109 in _find_necessary_helpers
      src/solver/profile/analyzer.py", line 58 in analyze

Usage::

    python src/scripts/reproduce_lle_segfault_minimal.py

Expected outcome: a "Windows fatal exception: access violation" with a C-level
faulthandler traceback, and a non-zero (SIGSEGV / exit code 139) process exit.
If the run instead prints "completed WITHOUT crashing", the fault depends on
accumulated solver heap state rather than on this single instance -- use
``reproduce_lle_segfault.py`` (the sampling reproducer) in that case.
"""

from __future__ import annotations

import faulthandler
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# --- the exact world that crashed (lle_segfault_capture.log, attempt 1164) ---
ROWS = 8
COLS = 8
T_MAX = 20
AGENTS = [(3, 2), (7, 7), (1, 2), (0, 5)]
EXITS = [(6, 2), (6, 3), (3, 7), (2, 1)]
WALLS = [(3, 6), (1, 0), (3, 3), (7, 6), (0, 2), (7, 4)]
LASERS = [(0, (3, 5), "S"), (1, (7, 2), "W"), (2, (1, 7), "W")]


def _direction(letter: str):
    from lle.tiles import Direction

    return {
        "N": Direction.NORTH,
        "S": Direction.SOUTH,
        "E": Direction.EAST,
        "W": Direction.WEST,
    }[letter]


def build_world():
    """Rebuild the captured world via the same WorldBuilder the generator uses."""
    from generators.world_builder import WorldBuilder

    b = WorldBuilder(COLS, ROWS)
    for agent_id, pos in enumerate(AGENTS):
        b.add_agent(agent_id, pos)
    for pos in EXITS:
        b.add_exit(pos)
    for pos in WALLS:
        b.add_wall(pos)
    for owner, pos, direction in LASERS:
        b.add_laser(owner, pos, _direction(direction))
    return b.build()


def main() -> None:
    faulthandler.enable(all_threads=True)

    import lle
    import numpy

    print("=== minimal LLE / pysat segfault reproducer ===")
    print(f"python   = {sys.version.split()[0]}")
    print(f"platform = {platform.platform()}")
    print(f"lle      = {getattr(lle, '__version__', 'unknown')}")
    print(f"numpy    = {numpy.__version__}")
    print(
        f"config   = {ROWS}x{COLS}, agents={len(AGENTS)}, lasers={len(LASERS)}, t_max={T_MAX}"
    )
    print()

    print("building the captured world ...", flush=True)
    world = build_world()

    from solver import CooperationProfileAnalyzer, WorldSolver

    world.reset()
    sat, _ = WorldSolver(world, T_MAX=T_MAX).solve()
    print(f"satisfiability solve OK (sat={bool(sat)})", flush=True)

    print(
        "running cooperation-profile analysis (this is what segfaulted) ...", flush=True
    )
    world.reset()
    result = CooperationProfileAnalyzer(world, T_MAX=T_MAX).analyze()

    print(
        f"profile analysis completed WITHOUT crashing: profile={result.profile}",
        flush=True,
    )
    print()
    print(
        "This run did NOT reproduce the segfault on the captured instance. "
        "The crash likely depends on accumulated solver heap state across many "
        "solves rather than on this single world; use reproduce_lle_segfault.py."
    )


if __name__ == "__main__":
    main()
