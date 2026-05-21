"""Example: certify a level's solvability and cooperation properties.

A minimal, self-contained tour of the three core solver queries this project
provides, run on a small hand-written cooperative level:

  1. solvable?             standard SAT encoding is satisfiable within T_MAX.
  2. cooperation required? solvable AND the strict-laser encoding is UNSAT --
                           i.e. some agent must step into a beam to shield
                           another (see CLAUDE.md, "Cooperation Definition").
  3. cooperation profile   the shape of the helper-dependency graph: one of
                           independent / asymmetric / mutual / chain /
                           distributed / fully_coupled.

Run it standalone::

    python src/scripts/cooperation_example.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lle import World

from solver import CooperationProfileAnalyzer, CooperationSolver, WorldSolver

# Two agents (S0, S1) reaching two exits (X) across two crossing beams of
# distinct colours (L0S, L1S point south). Each agent is immune to its own
# colour but blocked by the other's beam, so the level is solvable only if the
# agents take turns shielding each other -- a textbook cooperative level.
WORLD_STR = """
.   L1S L0S .
S0  .   .   X
S1  .   .   X
"""

T_MAX = 7


def main() -> None:
    world = World(WORLD_STR)
    print(f"Level: {world.width}x{world.height}, {world.n_agents} agents, T_MAX={T_MAX}\n")

    # 1. Solvability: is there any joint plan reaching all exits within T_MAX?
    solvable, _model = WorldSolver(world, T_MAX=T_MAX).solve()
    print(f"  solvable             : {bool(solvable)}")
    if not solvable:
        print("  (unsolvable within the horizon -- nothing more to analyse)")
        return

    # 2. Cooperation: required iff the strict-laser variant is UNSAT.
    cooperation_needed = CooperationSolver(world, T_MAX=T_MAX).analyze().cooperation_needed
    print(f"  cooperation required : {cooperation_needed}")

    # 3. Profile: the shape of the helper-dependency graph.
    result = CooperationProfileAnalyzer(world, T_MAX=T_MAX).analyze()
    print(f"  cooperation profile  : {result.profile}")
    print(f"  dependency edges     : {sorted(result.dependency_edges)}")
    print(f"  mutual pairs         : {sorted(result.mutual_pairs)}")


if __name__ == "__main__":
    main()
