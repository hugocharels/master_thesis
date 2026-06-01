"""Generate the cooperation-profile category Euler diagram.

Substructure-predicate reading on the dependency graph $G_L$ ($n_a >= 3$):

  - C (chain): contains a directed path of length >= 2.
  - D (distributed): contains a vertex of in-degree >= 2.
  - M (mutual): contains a reciprocal pair.
  - F (fully coupled): strongly connected on all agents.

This diagram shows predicates, not labels; the single label each graph
receives follows the priority cascade in the thesis (F > M > D > chain >
asymmetric). In particular the chain *label* is the strictly stronger
"whole graph is a covering path" condition, not the C predicate drawn here.

Relations drawn:

  - C, D, M are three overlapping circles (classical 3-circle layout).
  - F is a single ellipse inside M's top-right, clear of C and D, so the only
    overlap drawn is M inter F. It marks the two-agent reciprocal pair: both
    mutual and fully coupled (hence M inter F is non-empty) yet with no chain
    and no in-degree-2 vertex, so it lies outside C and D. It is labelled fully
    coupled because that label outranks mutual.
  - For n_a >= 3 a fully-coupled graph always contains a chain (F subset.eq C)
    and, when it has a reciprocal pair, is also distributed (F n M subset.eq D);
    that part of F lies inside C and is not outlined here (see the ordering
    section in the thesis).

Referenced from thesis/chapters/contribution/cooperation.typ.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import patches

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "results" / "cooperation_examples"

PREDICATE_COLOR = {
    "C": "#1f77b4",
    "D": "#d62728",
    "M": "#2ca02c",
    "F": "#9467bd",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.5, 8.2))

    universe = patches.FancyBboxPatch(
        (0.05, 0.05),
        10.5,
        8.3,
        boxstyle="round,pad=0.0,rounding_size=0.15",
        linewidth=1.4,
        edgecolor="#444444",
        facecolor="#ececec",
    )
    ax.add_patch(universe)

    c_center = (4.5, 5.5)
    m_center = (7.3, 5.5)
    d_center = (5.9, 3.5)
    big_r = 2.4

    # Three predicate circles: translucent fills + coloured outlines.
    for center, color in [
        (c_center, PREDICATE_COLOR["C"]),
        (m_center, PREDICATE_COLOR["M"]),
        (d_center, PREDICATE_COLOR["D"]),
    ]:
        ax.add_patch(
            patches.Circle(
                center,
                big_r,
                facecolor=color,
                edgecolor=color,
                linewidth=1.8,
                alpha=0.16,
            )
        )
        ax.add_patch(
            patches.Circle(
                center,
                big_r,
                facecolor="none",
                edgecolor=color,
                linewidth=1.8,
            )
        )

    # F: fully coupled, a single elongated ellipse that is the union of the two
    # regions of F: the part inside C (C-only, C n D, and the triple C n D n M,
    # for n_a >= 3 fully-coupled graphs) and the two-agent reciprocal pair in M's
    # top-right (mutual + fully coupled, outside C and D). The ellipse therefore
    # runs diagonally from inside C up into M. Knobs: `xy` is the centre, `angle`
    # tilts the major axis from C toward M's top-right, `width`/`height` are the
    # full axes. C is centred (4.5, 5.5) r 2.4; D is centred (5.9, 3.5) r 2.4.
    f_kwargs = dict(xy=(5.1, 5.35), width=5.2, height=2.1, angle=19)
    ax.add_patch(
        patches.Ellipse(
            **f_kwargs,
            facecolor=PREDICATE_COLOR["F"],
            edgecolor=PREDICATE_COLOR["F"],
            linewidth=2.0,
            alpha=0.32,
        )
    )
    ax.add_patch(
        patches.Ellipse(
            **f_kwargs,
            facecolor="none",
            edgecolor=PREDICATE_COLOR["F"],
            linewidth=2.0,
        )
    )
    # Label placed on the left, outside the ellipse, matching the other names.
    ax.text(
        1.3,
        3.9,
        "fully\n" + r"coupled ($\mathcal{F}$)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        va="center",
        color=PREDICATE_COLOR["F"],
    )

    # Predicate names (placed outside their shapes for breathing room)
    ax.text(
        2.4,
        7.85,
        r"chain ($\mathcal{C}$)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["C"],
    )
    ax.text(
        9.1,
        7.85,
        r"mutual ($\mathcal{M}$)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["M"],
    )
    ax.text(
        5.9,
        0.55,
        r"distributed ($\mathcal{D}$)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["D"],
    )

    # The bounding box is the base predicate A (cooperation required); the four
    # structural predicates are nested inside it. Labelled like the others
    # (name + symbol), placed in A's exclusive region outside every circle.
    ax.text(
        0.35,
        0.4,
        r"asymmetric ($\mathcal{A}$)",
        fontsize=13,
        fontweight="bold",
        ha="left",
        color="#333",
        style="italic",
    )

    ax.set_xlim(-0.1, 10.9)
    ax.set_ylim(-0.2, 8.6)
    ax.set_aspect("equal")
    ax.axis("off")

    out = OUTPUT_DIR / "profile_venn.png"
    fig.savefig(out, dpi=220, bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
