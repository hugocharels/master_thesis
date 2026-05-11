"""Shared matplotlib style for benchmark plots.

Configures a serif/LaTeX-friendly look with softer colours and alpha so figures
embed cleanly into the thesis. LaTeX text rendering is enabled when a TeX
distribution is available; otherwise the plain mathtext renderer is used.
"""

from __future__ import annotations

import shutil

import matplotlib as mpl
import matplotlib.pyplot as plt

_HAS_LATEX = shutil.which("latex") is not None

# Soft, low-saturation palette inspired by the thesis review feedback.
SOFT_PALETTE = [
    "#4C78A8",  # muted blue
    "#F58518",  # muted orange
    "#54A24B",  # muted green
    "#E45756",  # muted red
    "#72B7B2",  # muted teal
    "#EECA3B",  # muted yellow
    "#B279A2",  # muted purple
    "#FF9DA6",  # muted pink
]

DEFAULT_BAR_ALPHA = 0.75
GRID_ALPHA = 0.3


def apply_thesis_style() -> None:
    """Apply the shared thesis plotting style.

    Call once at the top of a plotting script (after importing matplotlib).
    """
    rc = {
        "font.family": "serif",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.prop_cycle": mpl.cycler(color=SOFT_PALETTE),
        "axes.edgecolor": "#444444",
        "axes.linewidth": 0.8,
        "axes.grid": False,
        "grid.color": "#999999",
        "grid.alpha": GRID_ALPHA,
        "grid.linewidth": 0.5,
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "legend.edgecolor": "#cccccc",
        "savefig.dpi": 200,
        "figure.dpi": 110,
    }
    if _HAS_LATEX:
        rc.update({
            "text.usetex": True,
            "text.latex.preamble": r"\usepackage{amsmath}",
        })
    plt.rcParams.update(rc)


def pretty_label(raw: str) -> str:
    """Format a snake_case identifier as a human-readable label.

    Replaces underscores with spaces and capitalises the first word.
    """
    if not raw:
        return raw
    text = raw.replace("_", " ").strip()
    # Capitalise first character only — leave acronyms untouched.
    return text[:1].upper() + text[1:]


def soft_color(index: int) -> str:
    """Return a soft palette colour by index, wrapping around if needed."""
    return SOFT_PALETTE[index % len(SOFT_PALETTE)]
