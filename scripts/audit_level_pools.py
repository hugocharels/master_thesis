"""Audit every pool used by the thesis experiments for within-pool diversity.

For each pool under
    results/learnability/levels/
    results/curriculum_experiment/levels/
this script:

1. Loads every level (via raw .txt world_string or via .json {"world_string"}).
2. Computes structural-diversity metrics (exact duplicates, distinct
   agent-start sets, distinct exit sets, distinct laser-source sets,
   distinct wall masks, mean / min / max pairwise normalised Hamming
   distance over wall masks).
3. Stitches every level_NNN.png (already produced by render_level_pools.py)
   into one contact-sheet PNG per split.
4. Writes a Markdown report to results/level_pool_audit/REPORT.md and the
   contact sheets to results/level_pool_audit/contact_sheets/.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = PROJECT_ROOT / "results" / "level_pool_audit"
CONTACT_ROOT = AUDIT_ROOT / "contact_sheets"


# ---------------------------------------------------------------------------
# Pool discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolSplit:
    label: str            # e.g. "learnability / train"
    split_dir: Path       # contains level_NNN.{txt,json} + images/
    file_suffix: str      # ".txt" or ".json"
    grid: tuple[int, int]


def discover_pools() -> list[PoolSplit]:
    pools: list[PoolSplit] = []

    learn_root = PROJECT_ROOT / "results/learnability/levels/8x8_3a_2L_cooperative"
    for split in ("train", "test"):
        split_dir = learn_root / split
        if split_dir.is_dir():
            pools.append(PoolSplit(f"learnability / {split}", split_dir, ".txt", (8, 8)))

    curr_root = PROJECT_ROOT / "results/curriculum_experiment/levels"
    if curr_root.is_dir():
        for pool_dir in sorted(curr_root.iterdir()):
            if not pool_dir.is_dir():
                continue
            # Parse grid from folder name: stage_N_HxW_..._
            m = re.match(r"stage_(\d+)_(\d+)x(\d+)_", pool_dir.name)
            if not m:
                continue
            stage_id = int(m.group(1))
            grid = (int(m.group(2)), int(m.group(3)))
            for split in ("train", "eval"):
                split_dir = pool_dir / split
                if split_dir.is_dir():
                    pools.append(
                        PoolSplit(
                            f"curriculum_stage{stage_id} / {split}",
                            split_dir,
                            ".json",
                            grid,
                        )
                    )

    return pools


# ---------------------------------------------------------------------------
# Level loading + parsing
# ---------------------------------------------------------------------------


def load_world_strings(split_dir: Path, suffix: str) -> list[tuple[str, str]]:
    """Return [(level_name, world_string), ...] sorted by level index."""
    items: list[tuple[str, str]] = []
    for p in sorted(split_dir.iterdir()):
        if not p.is_file() or p.suffix != suffix or not p.name.startswith("level_"):
            continue
        if suffix == ".txt":
            ws = p.read_text(encoding="utf-8")
        else:
            ws = json.loads(p.read_text(encoding="utf-8"))["world_string"]
        items.append((p.stem, ws.strip()))
    return items


_AGENT_RX = re.compile(r"^S(\d+)$")
_LASER_RX = re.compile(r"^L(\d+)([NSEW])$")


@dataclass(frozen=True)
class LevelStructure:
    agents: tuple[tuple[int, int], ...]       # by colour id, ascending
    exits: frozenset[tuple[int, int]]
    lasers: frozenset[tuple[int, tuple[int, int], str]]  # (colour, pos, dir)
    walls: frozenset[tuple[int, int]]
    beam_cells: frozenset[tuple[int, int]]    # source cells of any laser
    rows: int
    cols: int


def parse_structure(world_string: str) -> LevelStructure:
    lines = [line for line in world_string.splitlines() if line.strip()]
    rows = len(lines)
    cols = len(lines[0].split()) if rows else 0
    agents: dict[int, tuple[int, int]] = {}
    exits: set[tuple[int, int]] = set()
    lasers: set[tuple[int, tuple[int, int], str]] = set()
    walls: set[tuple[int, int]] = set()
    beam_cells: set[tuple[int, int]] = set()
    for r, line in enumerate(lines):
        cells = line.split()
        for c, tok in enumerate(cells):
            if tok == "." or tok == "G":
                continue
            if tok == "@":
                walls.add((r, c))
                continue
            if tok == "X":
                exits.add((r, c))
                continue
            m = _AGENT_RX.match(tok)
            if m:
                agents[int(m.group(1))] = (r, c)
                continue
            m = _LASER_RX.match(tok)
            if m:
                colour = int(m.group(1))
                direction = m.group(2)
                lasers.add((colour, (r, c), direction))
                beam_cells.add((r, c))
                continue
    agents_tuple = tuple(agents[k] for k in sorted(agents.keys()))
    return LevelStructure(
        agents=agents_tuple,
        exits=frozenset(exits),
        lasers=frozenset(lasers),
        walls=frozenset(walls),
        beam_cells=frozenset(beam_cells),
        rows=rows,
        cols=cols,
    )


# ---------------------------------------------------------------------------
# Diversity metrics
# ---------------------------------------------------------------------------


@dataclass
class PoolMetrics:
    n_levels: int
    n_unique_world_strings: int
    n_unique_agent_tuples: int
    n_unique_exit_sets: int
    n_unique_laser_sets: int
    n_unique_wall_masks: int
    n_unique_beam_cells: int
    hamming_mean: float
    hamming_min: int
    hamming_max: int
    hamming_normalised_mean: float
    grid: tuple[int, int]


def pairwise_hamming_walls(structs: list[LevelStructure]) -> tuple[float, int, int]:
    if len(structs) < 2:
        return (0.0, 0, 0)
    distances: list[int] = []
    for a, b in itertools.combinations(structs, 2):
        d = len(a.walls.symmetric_difference(b.walls))
        distances.append(d)
    return (sum(distances) / len(distances), min(distances), max(distances))


def compute_metrics(structs: list[LevelStructure], world_strings: list[str]) -> PoolMetrics:
    if not structs:
        return PoolMetrics(0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0.0, (0, 0))
    grid = (structs[0].rows, structs[0].cols)
    n_cells = grid[0] * grid[1]
    h_mean, h_min, h_max = pairwise_hamming_walls(structs)
    return PoolMetrics(
        n_levels=len(structs),
        n_unique_world_strings=len(set(world_strings)),
        n_unique_agent_tuples=len({s.agents for s in structs}),
        n_unique_exit_sets=len({s.exits for s in structs}),
        n_unique_laser_sets=len({s.lasers for s in structs}),
        n_unique_wall_masks=len({s.walls for s in structs}),
        n_unique_beam_cells=len({s.beam_cells for s in structs}),
        hamming_mean=h_mean,
        hamming_min=h_min,
        hamming_max=h_max,
        hamming_normalised_mean=h_mean / n_cells if n_cells else 0.0,
        grid=grid,
    )


# ---------------------------------------------------------------------------
# Contact sheet
# ---------------------------------------------------------------------------


def build_contact_sheet(split_dir: Path, level_names: list[str], out_path: Path,
                        max_columns: int = 10) -> Path | None:
    images_dir = split_dir / "images"
    paths = [images_dir / f"{name}.png" for name in level_names]
    paths = [p for p in paths if p.is_file()]
    if not paths:
        return None
    thumbs = [Image.open(p).convert("RGB") for p in paths]
    cell_w = max(im.size[0] for im in thumbs)
    cell_h = max(im.size[1] for im in thumbs)
    cols = min(max_columns, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), color=(255, 255, 255))
    for i, im in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(im, (c * cell_w, r * cell_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="PNG")
    return out_path


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def render_report(rows: list[tuple[PoolSplit, PoolMetrics, Path | None]]) -> str:
    lines = ["# Level Pool Audit",
             "",
             "Auto-generated by `scripts/audit_level_pools.py`.",
             "",
             "## Per-pool diversity metrics",
             "",
             "Columns:",
             "- `n` = number of levels in the pool",
             "- `uniq_ws` = distinct `world_string` values (exact duplicates)",
             "- `uniq_agents` = distinct ordered agent-start tuples",
             "- `uniq_exits` = distinct exit-position sets",
             "- `uniq_lasers` = distinct (colour, position, direction) source sets",
             "- `uniq_walls` = distinct wall-mask sets",
             "- `uniq_beam_src` = distinct laser-source cell sets",
             "- `hamming_walls` = mean / min / max pairwise symmetric-difference size on walls",
             "- `hamming_norm` = mean wall-Hamming distance divided by grid-cell count",
             "",
             "| Pool | Grid | n | uniq_ws | uniq_agents | uniq_exits | uniq_lasers | uniq_walls | uniq_beam_src | hamming_walls (mean / min / max) | hamming_norm |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for split, m, _sheet in rows:
        lines.append(
            f"| {split.label} | {m.grid[0]}x{m.grid[1]} | {m.n_levels} | "
            f"{m.n_unique_world_strings} | {m.n_unique_agent_tuples} | "
            f"{m.n_unique_exit_sets} | {m.n_unique_laser_sets} | "
            f"{m.n_unique_wall_masks} | {m.n_unique_beam_cells} | "
            f"{m.hamming_mean:.2f} / {m.hamming_min} / {m.hamming_max} | "
            f"{m.hamming_normalised_mean:.3f} |"
        )
    lines.append("")
    lines.append("## Contact sheets")
    lines.append("")
    for split, _m, sheet in rows:
        if sheet is None:
            lines.append(f"- {split.label}: _no rendered PNGs found_")
        else:
            rel = sheet.relative_to(AUDIT_ROOT)
            lines.append(f"- {split.label}: `{rel.as_posix()}`")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    pools = discover_pools()
    if not pools:
        print("No pools discovered.", file=sys.stderr)
        return 1
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[PoolSplit, PoolMetrics, Path | None]] = []
    for split in pools:
        items = load_world_strings(split.split_dir, split.file_suffix)
        if not items:
            print(f"warning: empty pool {split.label}", file=sys.stderr)
            continue
        names = [name for name, _ in items]
        world_strings = [ws for _, ws in items]
        structs = [parse_structure(ws) for ws in world_strings]
        m = compute_metrics(structs, world_strings)

        sheet_path = CONTACT_ROOT / (
            split.label.replace(" / ", "__").replace(" ", "_") + ".png"
        )
        sheet_out = build_contact_sheet(split.split_dir, names, sheet_path)
        rows.append((split, m, sheet_out))
        print(f"{split.label:45s}  n={m.n_levels:3d}  uniq_walls={m.n_unique_wall_masks:3d}  "
              f"uniq_agents={m.n_unique_agent_tuples:3d}  uniq_lasers={m.n_unique_laser_sets:3d}  "
              f"ham_norm={m.hamming_normalised_mean:.3f}")
    report = render_report(rows)
    out = AUDIT_ROOT / "REPORT.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport: {out}")
    print(f"Contact sheets: {CONTACT_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
