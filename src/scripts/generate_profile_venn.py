"""Generate the cooperation-profile category Euler diagram.

Existential (substructure) reading on the dependency graph $G_L$ ($n_a >= 3$):

  - C (chain): contains a directed path of length >= 2.
  - D (distributed): contains a vertex of in-degree >= 2.
  - M (mutual): contains a reciprocal pair.
  - F (fully coupled): strongly connected on all agents.

Relations drawn:

  - C, D, M are three overlapping circles (classical 3-circle layout).
  - F is a shape inside C covering the regions C n D n M, C n D, and C-only,
    because F subset.eq C and F n M subset.eq D (a fully-coupled graph always
    contains a chain, and a mutual + fully-coupled graph is also distributed,
    so F never touches the "C and M but not D" region).
  - For n_a = 2 the only fully-coupled graph is the reciprocal pair, which
    contains no chain; it sits as a small separate circle in the residual.

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

    # F: an ellipse inside C covering C-only, C n D, and the triple C n D n M,
    # reaching the D-M overlap while staying clear of the C n M (no D) lens
    # above D. Knobs: raise xy[1] to cover more of the triple, ease `angle`
    # toward 0 to lift the right end, raise `height` to make it taller.
    f_ellipse_kwargs = dict(xy=(4.6, 4.67), width=4.0, height=2.1, angle=-6)
    ax.add_patch(
        patches.Ellipse(
            **f_ellipse_kwargs,
            facecolor=PREDICATE_COLOR["F"],
            edgecolor=PREDICATE_COLOR["F"],
            linewidth=2.0,
            alpha=0.32,
        )
    )
    ax.add_patch(
        patches.Ellipse(
            **f_ellipse_kwargs,
            facecolor="none",
            edgecolor=PREDICATE_COLOR["F"],
            linewidth=2.0,
        )
    )

    # F for n_a = 2: small separate circle in the residual region.
    f2_center = (9.4, 1.4)
    f2_radius = 0.62
    ax.add_patch(
        patches.Circle(
            f2_center,
            f2_radius,
            facecolor=PREDICATE_COLOR["F"],
            edgecolor=PREDICATE_COLOR["F"],
            linewidth=2.0,
            alpha=0.32,
        )
    )
    ax.add_patch(
        patches.Circle(
            f2_center,
            f2_radius,
            facecolor="none",
            edgecolor=PREDICATE_COLOR["F"],
            linewidth=2.0,
        )
    )

    # Predicate names (placed outside their shapes for breathing room)
    ax.text(
        2.4,
        7.85,
        "chain (C)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["C"],
    )
    ax.text(
        9.1,
        7.85,
        "mutual (M)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["M"],
    )
    ax.text(
        5.9,
        0.55,
        "distributed (D)",
        fontsize=15,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["D"],
    )
    ax.text(
        1.35,
        3.95,
        "fully\ncoupled (F)",
        fontsize=12.5,
        fontweight="bold",
        ha="center",
        color=PREDICATE_COLOR["F"],
    )
    ax.text(
        9.4,
        2.35,
        r"fully coupled" + "\n" + r"($n_a = 2$)",
        fontsize=10.5,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=PREDICATE_COLOR["F"],
    )

    ax.text(
        0.35,
        0.4,
        "asymmetric",
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
