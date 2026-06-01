"""Render the cooperation-profile figures: world + dependency graph.

This is the single place to (re)make the chapter-5 cooperation-profile
examples. For each profile it writes TWO PNGs into
``results/cooperation_examples/``:

  - ``<profile>.png``      the rendered LLE level (from your world string)
  - ``dep_<profile>.png``  the abstract dependency graph (from your edges)

The thesis places these two images side by side itself
(see thesis/chapters/contribution/cooperation.typ), so the filenames
must stay as above.

To use: edit the ``PROFILES`` dict below — one entry per profile, holding
*both* the world string and the dependency-graph edges — then run from the
project root::

    python3.13 src/scripts/render_profile_figures.py

Per-entry fields:
  - ``world``  : an LLE world string (multiline). Empty/None -> skip entry.
  - ``edges``  : list of (helper, beneficiary) tuples = directed dependency
                 edges you draw by hand. Graph nodes are taken from the
                 level's agents (0 .. n_agents-1); colours come from
                 ``AGENT_COLOURS``.
  - ``t_max``  : horizon passed to the analyzer (verification only).
  - ``target`` : expected profile label. The analyzer is run as a sanity
                 check and prints OK/FAIL, but PNGs are written regardless
                 so you can iterate visually.

World-string syntax (LLE):
  .            empty cell
  @            wall
  Sn           start of agent n (n in 0..3)
  X            exit (any agent may use any exit)
  LnD          laser source of colour n firing in direction D (N/S/E/W);
               the source tile itself is impassable.
Tokens are whitespace-separated within a row; rows by newlines.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from lle import World

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from solver.profile.analyzer import CooperationProfileAnalyzer

OUTPUT_DIR = PROJECT_ROOT / "results" / "cooperation_examples"

# Node colours by agent index (used for the dependency-graph vertices).
AGENT_COLOURS = {
    0: "#d62728",  # red
    1: "#2ca02c",  # green
    2: "#1f77b4",  # blue
    3: "#9467bd",  # purple
}


@dataclass(frozen=True)
class Profile:
    target: str  # expected profile label (CooperationLevel value)
    t_max: int  # horizon for the analyzer sanity check
    world: str  # LLE world string; empty/None = skip
    edges: list[tuple[int, int]] = field(default_factory=list)  # dep edges


# --------------------------------------------------------------------------
# EDIT HERE. One entry per profile: world string + dependency edges together.
# --------------------------------------------------------------------------
PROFILES: dict[str, Profile] = {
    "independent": Profile(
        target="independent",
        t_max=20,
        edges=[],
        world="""
            S0 .  .  .  S1
            .  .  .  .  .
            .  .  .  .  .
            .  .  .  .  .
            X  .  .  .  X
        """,
    ),
    "asymmetric": Profile(
        target="asymmetric",
        t_max=20,
        edges=[(0, 1)],
        world="""
            S0  .  .  .  S1
            .   .  .  .  .
            L0E .  .  .  .
            .   .  .  .  .
            X   .  .  .  X
        """,
    ),
    "mutual": Profile(
        target="mutual",
        t_max=20,
        edges=[(0, 1), (1, 0)],
        world="""
            .   .  S0 S1 .
            .   .  .  .  .
            L0E .  .  .  .
            L1E .  .  .  .
            S2  X  X  X  .
        """,
    ),
    "chain": Profile(
        target="chain",
        t_max=20,
        edges=[(0, 1), (1, 2)],
        world="""
            @   S0  .   S1 .
            L0E .   .   .  @
            @   X   @   .  S2
            @   @   .   .  .
            @   L1E .   .  .
            @   @   X   X  .
        """,
    ),
    "distributed": Profile(
        target="distributed",
        t_max=20,
        edges=[(0, 2), (1, 2)],
        world="""
            .   .   S0 .   S2
            L0E .   .  .   .
            .   X   @  S1   .
            @   L1E .  .   .
            @   @   .  X   X
        """,
    ),
    "fully_coupled": Profile(
        target="fully_coupled",
        t_max=20,
        edges=[(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)],
        world="""
            .   S0 S1 S2 .
            L0E .  .  .  .
            L1E .  .  .  .
            L2E .  .  .  .
            .   .  X  X  X
        """,
    ),
}


def _normalize(world_str: str) -> str:
    lines = []
    for raw in world_str.splitlines():
        line = raw.strip()
        if not line:
            continue
        lines.append(" ".join(line.split()))
    return "\n".join(lines)


def _verify(world: World, target: str, t_max: int) -> tuple[bool, str]:
    """Run the analyzer as a sanity check. Returns (ok, message)."""
    world.reset()
    try:
        result = CooperationProfileAnalyzer(world, T_MAX=t_max).analyze()
    except Exception as exc:  # noqa: BLE001
        return False, f"analyzer error: {exc}"
    edges = sorted(result.dependency_edges)
    if result.profile.value != target:
        return (
            False,
            f"expected {target}, got {result.profile.value}; analyzer edges={edges}",
        )
    return True, f"profile={result.profile.value}; analyzer edges={edges}"


def _render_world(world: World, name: str) -> None:
    world.reset()
    plt.imsave(OUTPUT_DIR / f"{name}.png", world.get_image())


def _render_dep_graph(
    name: str, nodes: list[int], edges: list[tuple[int, int]]
) -> None:
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    fig, ax = plt.subplots(figsize=(3, 3))
    if len(nodes) == 2:
        pos = {nodes[0]: (-0.7, 0.0), nodes[1]: (0.7, 0.0)}
    else:
        pos = nx.circular_layout(graph)

    node_colours = [AGENT_COLOURS[n] for n in graph.nodes]
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_colours,
        node_size=1100,
        edgecolors="#222222",
        linewidths=1.2,
        ax=ax,
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        edge_color="#222222",
        arrows=True,
        arrowsize=18,
        width=1.8,
        node_size=1100,
        connectionstyle="arc3,rad=0.18",
        ax=ax,
    )
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(OUTPUT_DIR / f"dep_{name}.png", dpi=220, transparent=True)
    plt.close(fig)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fails = 0

    for name, prof in PROFILES.items():
        if not prof.world or not prof.world.strip():
            print(f"[{name:14s}] SKIP (no world string)")
            continue

        world_str = _normalize(prof.world)

        # Parse the level once; this also gives us the agent count for nodes.
        try:
            world = World(world_str)
            world.reset()
        except Exception as exc:  # noqa: BLE001
            print(f"[{name:14s}] FAIL — world parse error: {exc}")
            fails += 1
            continue

        nodes = list(range(world.n_agents))

        # Render both PNGs (always, so you can inspect while iterating).
        _render_world(world, name)
        _render_dep_graph(name, nodes, prof.edges)

        # Sanity-check the classification; never blocks rendering.
        ok, msg = _verify(world, prof.target, prof.t_max)
        status = "OK  " if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"[{name:14s}] {status} your edges={prof.edges}  {msg}")

    print(f"\nwrote PNGs to {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
