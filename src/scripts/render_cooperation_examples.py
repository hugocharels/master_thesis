"""Render hand-written canonical levels per cooperation profile.

For each profile family in ``CooperationLevel`` (independent, asymmetric,
mutual, chain, distributed, fully_coupled) this script takes a hand-written
world string, verifies via the analyzer that the level classifies as the
target profile, and writes the rendered image to
``results/cooperation_examples/<profile>.png``.

To use: edit the ``LEVELS`` dict below, then run from the project root:

    python3.13 src/scripts/render_cooperation_examples.py

Per-entry options:
- ``world``: an LLE world string (multiline). Set to ``None`` or an empty
  string to skip the entry.
- ``t_max``: horizon used by the analyzer.
- ``target``: expected profile label. If the analyzer returns a different
  label the entry is rejected and no PNG is written for it.

The script prints a status line per entry so you can iterate. Successful
entries overwrite the existing PNG; failed entries leave any existing PNG
untouched so you can see the previous version while you fix the new one.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lle import World

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from solver import CooperationLevel
from solver.profile.analyzer import CooperationProfileAnalyzer
from solver.world_solver import WorldSolver


@dataclass(frozen=True)
class Entry:
    target: str  # expected profile label (CooperationLevel value)
    t_max: int  # horizon passed to the analyzer
    world: str  # LLE world string; empty/None = skip this entry


# --------------------------------------------------------------------------
# Hand-write your levels here. Leave ``world=""`` to skip an entry.
#
# World-string syntax (LLE):
#   .            empty cell
#   @            wall
#   Sn           start of agent n (n in 0..3)
#   X            exit (color-agnostic; any agent can occupy any exit)
#   LnD          laser source of colour n shooting in direction D
#                (D in {N, S, E, W}). The source tile itself is impassable.
#
# Tokens are separated by whitespace within a row; rows by newlines.
# --------------------------------------------------------------------------

LEVELS: dict[str, Entry] = {
    "independent": Entry(
        target="independent",
        t_max=20,
        world="""
            S0 .  .  .  S1
            .  .  .  .  .
            .  .  .  .  .
            .  .  .  .  .
            X  .  .  .  X
        """,
    ),
    "asymmetric": Entry(
        target="asymmetric",
        t_max=20,
        world="""
            S0  .  .  .  S1
            .   .  .  .  .
            L0E .  .  .  .
            .   .  .  .  .
            X   .  .  .  X
        """,
    ),
    "mutual": Entry(
        target="mutual",
        t_max=20,
        world="""
            .   .  S0 S1 .
            .   .  .  .  .
            L0E .  .  .  .
            L1E .  .  .  .
            S2  X  X  X  .
        """,
    ),
    "chain": Entry(
        target="chain",
        t_max=20,
        world="""
            @   S0  L2S  S1  .
            L0E .   .   .  @
            @   X   @   .  .
            @   @   L1E .  .
            @   @   @   .  S2
            @   L1E .   .  .
            @   @   X   X  .
        """,
    ),
    "distributed": Entry(
        target="distributed",
        t_max=20,
        world="""
            .   .   S0 S1  S2
            L0E .   .  .   .
            .   X   @  .   .
            @   L1E .  .   .
            @   @   .  X   X
        """,
    ),
    "fully_coupled": Entry(
        target="fully_coupled",
        t_max=20,
        world="""
            .   S0 S1 S2 .
            L0E .  .  .  .
            L1E .  .  .  .
            L2E .  .  .  .
            .   .  X  X  X
        """,
    ),
}


# --------------------------------------------------------------------------
# Horizon-dependence demo. One hand-written world, analyzed at several
# T_max values to illustrate that the cooperation classification depends
# on the chosen horizon. The script reports, for each T_max:
#   - whether the standard solver is SAT or UNSAT at that horizon
#     (UNSAT = level rejected as unsolvable; cooperation not even tested),
#   - and if SAT, the profile label returned by the analyzer.
# A single PNG is rendered to results/cooperation_examples/<name>.png.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class HorizonEntry:
    t_max_values: tuple[int, ...]
    world: str


HORIZON_EXAMPLES: dict[str, HorizonEntry] = {
    # TODO: fill in a small (4x4 is fine) world that switches classification
    # between low / medium / high T_max — typically:
    #   - low  T_max -> standard-SAT UNSAT (level looks unsolvable)
    #   - mid  T_max -> cooperative (intended classification)
    #   - high T_max -> independent (detour bypass: strict-SAT becomes SAT)
    "horizon_demo": HorizonEntry(
        t_max_values=(2, 3, 9),
        world="""
            . .   S0 S1
            . L0E .  .
            . .   .  .
            . .   X  X
        """,
    ),
}


def _normalize(world_str: str) -> str:
    lines = []
    for raw in world_str.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Collapse runs of whitespace to single spaces.
        tokens = line.split()
        lines.append(" ".join(tokens))
    return "\n".join(lines)


def _verify(world_str: str, target: str, t_max: int):
    """Return (ok, profile, edges, reason)."""
    try:
        world = World(world_str)
    except Exception as exc:  # noqa: BLE001
        return False, None, None, f"world parse error: {exc}"
    world.reset()
    try:
        result = CooperationProfileAnalyzer(world, T_MAX=t_max).analyze()
    except Exception as exc:  # noqa: BLE001
        return False, None, None, f"analyzer error: {exc}"
    if result.profile.value != target:
        return (
            False,
            result.profile,
            sorted(result.dependency_edges),
            f"expected {target}, got {result.profile.value}",
        )
    return True, result.profile, sorted(result.dependency_edges), "ok"


def _horizon_sweep(world_str: str, t_max_values: tuple[int, ...]):
    """Return list of (t_max, status, profile_or_none, edges_or_none, reason)."""
    rows = []
    for t_max in t_max_values:
        try:
            world = World(world_str)
        except Exception as exc:  # noqa: BLE001
            rows.append((t_max, "PARSE_ERR", None, None, str(exc)))
            continue
        world.reset()
        # Check standard-SAT first; UNSAT means the level is rejected as
        # unsolvable at this horizon and the cooperation question never
        # gets asked.
        try:
            sat, _ = WorldSolver(world, T_MAX=t_max).solve()
        except Exception as exc:  # noqa: BLE001
            rows.append((t_max, "SOLVER_ERR", None, None, str(exc)))
            continue
        if not sat:
            rows.append((t_max, "STD-UNSAT", None, None, "rejected as unsolvable"))
            continue
        world.reset()
        try:
            result = CooperationProfileAnalyzer(world, T_MAX=t_max).analyze()
        except Exception as exc:  # noqa: BLE001
            rows.append((t_max, "ANALYZER_ERR", None, None, str(exc)))
            continue
        rows.append(
            (
                t_max,
                "OK",
                result.profile.value,
                sorted(result.dependency_edges),
                "",
            )
        )
    return rows


def main() -> int:
    out_dir = PROJECT_ROOT / "results" / "cooperation_examples"
    out_dir.mkdir(parents=True, exist_ok=True)

    fails = 0
    for name, entry in LEVELS.items():
        if not entry.world or not entry.world.strip():
            print(f"[{name:14s}] SKIP (no world string)")
            continue
        world_str = _normalize(entry.world)
        ok, profile, edges, reason = _verify(world_str, entry.target, entry.t_max)
        edges_str = "" if edges is None else f"edges={edges}"

        # Render PNG whenever the world string parses, even on classification
        # failure, so you can inspect the level visually while iterating.
        try:
            world = World(world_str)
            world.reset()
            out_path = out_dir / f"{name}.png"
            plt.imsave(out_path, world.get_image())
            png_str = f"-> {out_path.relative_to(PROJECT_ROOT)}"
        except Exception:
            png_str = "(no png, parse failure)"

        if not ok:
            print(f"[{name:14s}] FAIL — {reason}  {edges_str}  {png_str}")
            fails += 1
            continue
        print(f"[{name:14s}] OK   profile={profile.value:14s} {edges_str}  {png_str}")

    # ------------------------------------------------------------------
    # Horizon-dependence sweeps. Each entry runs the analyzer on one
    # world at several T_max values to show the classification flip.
    # ------------------------------------------------------------------
    for name, entry in HORIZON_EXAMPLES.items():
        if not entry.world or not entry.world.strip():
            print(f"[{name:14s}] SKIP (no world string)")
            continue
        world_str = _normalize(entry.world)
        try:
            world = World(world_str)
            world.reset()
            out_path = out_dir / f"{name}.png"
            plt.imsave(out_path, world.get_image())
            png_str = f"-> {out_path.relative_to(PROJECT_ROOT)}"
        except Exception as exc:  # noqa: BLE001
            png_str = f"(no png, parse failure: {exc})"
        print(f"[{name:14s}] horizon sweep  {png_str}")
        for t_max, status, profile, edges, reason in _horizon_sweep(
            world_str,
            entry.t_max_values,
        ):
            if status == "OK":
                edges_str = "" if edges is None else f"edges={edges}"
                print(f"    T_max={t_max:3d}  -> {profile:14s} {edges_str}")
            else:
                print(f"    T_max={t_max:3d}  -> {status} ({reason})")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
