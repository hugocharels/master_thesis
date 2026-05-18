"""Generate dependency-graph diagrams for the cooperation profile examples.

Each profile in chapter 5 already has a level screenshot under
``results/cooperation_examples``. This script writes a matching
``dep_<profile>.png`` showing the abstract dependency graph (nodes =
agent colours, directed edges = helper events) so the thesis can place
the geometric example and the graph shape side by side.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "results" / "cooperation_examples"

AGENT_COLOURS = {
    0: "#d62728",
    1: "#1f77b4",
    2: "#2ca02c",
    3: "#9467bd",
}

PROFILES: dict[str, dict] = {
    "independent": {"nodes": [0, 1], "edges": []},
    "asymmetric": {"nodes": [0, 1], "edges": [(0, 1)]},
    "mutual": {"nodes": [0, 1], "edges": [(0, 1), (1, 0)]},
    "chain": {"nodes": [0, 1, 2], "edges": [(0, 1), (1, 2)]},
    "distributed": {
        "nodes": [0, 1, 2],
        "edges": [(0, 1), (0, 2), (1, 2)],
    },
    "fully_coupled": {
        "nodes": [0, 1, 2],
        "edges": [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)],
    },
}


def render(name: str, nodes: list[int], edges: list[tuple[int, int]]) -> None:
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    fig, ax = plt.subplots(figsize=(3, 3))
    if len(nodes) == 2:
        pos = {nodes[0]: (-1.0, 0.0), nodes[1]: (1.0, 0.0)}
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
    nx.draw_networkx_labels(
        graph,
        pos,
        font_color="white",
        font_weight="bold",
        font_size=16,
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

    ax.set_aspect("equal")
    ax.margins(0.25)
    ax.axis("off")
    fig.tight_layout()

    out = OUTPUT_DIR / f"dep_{name}.png"
    fig.savefig(out, dpi=220, bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in PROFILES.items():
        render(name, spec["nodes"], spec["edges"])


if __name__ == "__main__":
    main()
