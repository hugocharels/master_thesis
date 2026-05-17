"""Render every level used in the thesis experiments to PNG and emit
a per-pool ``params.json`` describing the generation parameters.

Covers:
- results/learnability/levels/             (.txt world strings)
- results/curriculum_experiment/levels/    (4 curriculum stages, .json)

For each pool ``<pool>/{train,test,eval}/`` it writes:
- ``<pool>/{split}/images/level_NNN.png``  (LLE renderer output)
- ``<pool>/params.json``                   (geometry + generator + seed)

Also writes a top-level index ``results/level_pool_index.md`` that
maps every pool to its parameters and image folder.

Idempotent: PNGs that already exist are skipped.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lle import World

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.curriculum.configs import (
    CURRICULUM_STAGES,
    RNG_SEED as CURR_RNG_SEED,
)
from experiments.learnability.configs import (
    GRID as LEARN_GRID,
    RNG_SEED as LEARN_RNG_SEED,
    TRAIN_POOL_SIZE,
    TEST_POOL_SIZE,
)


@dataclass(frozen=True)
class PoolSpec:
    label: str
    pool_dir: Path
    file_suffix: str  # ".txt" or ".json"
    height: int
    width: int
    n_agents: int
    n_lasers: int
    t_max: int
    generator_name: str
    splits: dict[str, dict]  # split -> {"seed": int, "expected": int}


def _read_world_string(path: Path) -> str:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload["world_string"]
    return path.read_text(encoding="utf-8")


def _render_pool(spec: PoolSpec) -> dict:
    pool_dir = spec.pool_dir
    if not pool_dir.exists():
        print(f"[skip] {spec.label}: pool dir not found ({pool_dir})")
        return {"label": spec.label, "skipped": True}

    per_split = {}
    for split, meta in spec.splits.items():
        split_dir = pool_dir / split
        if not split_dir.is_dir():
            continue
        files = sorted(
            p for p in split_dir.iterdir()
            if p.is_file()
            and p.name.startswith("level_")
            and p.suffix == spec.file_suffix
        )
        images_dir = split_dir / "images"
        images_dir.mkdir(exist_ok=True)
        n_rendered = 0
        for f in files:
            out = images_dir / f"{f.stem}.png"
            if out.exists():
                continue
            world = World(_read_world_string(f))
            world.reset()
            plt.imsave(out, world.get_image())
            n_rendered += 1
        per_split[split] = {
            "seed": meta["seed"],
            "n_levels": len(files),
            "rendered_now": n_rendered,
            "images_dir": str(images_dir.relative_to(PROJECT_ROOT).as_posix()),
        }
        print(f"[ok] {spec.label}/{split}: {len(files)} levels "
              f"({n_rendered} new PNG)")

    params = {
        "label": spec.label,
        "pool_dir": str(pool_dir.relative_to(PROJECT_ROOT).as_posix()),
        "height": spec.height,
        "width": spec.width,
        "n_agents": spec.n_agents,
        "n_lasers": spec.n_lasers,
        "t_max": spec.t_max,
        "generator_name": spec.generator_name,
        "splits": per_split,
    }
    (pool_dir / "params.json").write_text(
        json.dumps(params, indent=2), encoding="utf-8"
    )
    return params


def _phase_pool_dir(base: Path, grid) -> Path:
    folder = (
        f"{grid.height}x{grid.width}"
        f"_{grid.n_agents}a"
        f"_{grid.n_lasers}L"
        f"_{grid.generator_name}"
    )
    return base / "levels" / folder


def _curriculum_pool_dir(base: Path, stage) -> Path:
    folder = (
        f"stage_{stage.stage_id}"
        f"_{stage.height}x{stage.width}"
        f"_{stage.n_agents}a"
        f"_{stage.n_lasers}L"
        f"_{stage.generator_name}"
    )
    return base / "levels" / folder


def build_specs() -> list[PoolSpec]:
    specs: list[PoolSpec] = []

    # -- Learnability -----------------------------------------------------------
    learn_base = PROJECT_ROOT / "results" / "learnability"
    specs.append(PoolSpec(
        label="learnability",
        pool_dir=_phase_pool_dir(learn_base, LEARN_GRID),
        file_suffix=".txt",
        height=LEARN_GRID.height,
        width=LEARN_GRID.width,
        n_agents=LEARN_GRID.n_agents,
        n_lasers=LEARN_GRID.n_lasers,
        t_max=LEARN_GRID.t_max,
        generator_name=LEARN_GRID.generator_name,
        splits={
            "train": {"seed": LEARN_RNG_SEED, "expected": TRAIN_POOL_SIZE},
            "test":  {"seed": LEARN_RNG_SEED + 1, "expected": TEST_POOL_SIZE},
        },
    ))

    # -- Curriculum stages ----------------------------------------------------
    curr_base = PROJECT_ROOT / "results" / "curriculum_experiment"
    for stage in CURRICULUM_STAGES:
        splits = {
            "train": {
                "seed": CURR_RNG_SEED + stage.stage_id * 100,
                "expected": stage.pool_size,
            }
        }
        if stage.eval_pool_size > 0:
            splits["eval"] = {
                "seed": CURR_RNG_SEED + stage.stage_id * 100 + 1,
                "expected": stage.eval_pool_size,
            }
        specs.append(PoolSpec(
            label=f"curriculum_stage{stage.stage_id}",
            pool_dir=_curriculum_pool_dir(curr_base, stage),
            file_suffix=".json",
            height=stage.height,
            width=stage.width,
            n_agents=stage.n_agents,
            n_lasers=stage.n_lasers,
            t_max=stage.t_max,
            generator_name=stage.generator_name,
            splits=splits,
        ))

    return specs


def write_index(all_params: list[dict], out_path: Path) -> None:
    lines = [
        "# Level Pool Index",
        "",
        "Auto-generated by ``scripts/render_level_pools.py``.",
        "Lists every level pool used in the experiments, its generation",
        "parameters, and where to find the per-level PNG renderings.",
        "",
    ]
    for p in all_params:
        if p.get("skipped"):
            continue
        lines.append(f"## {p['label']}")
        lines.append("")
        lines.append(f"- pool directory: `{p['pool_dir']}`")
        lines.append(f"- grid: {p['height']}x{p['width']}")
        lines.append(f"- agents: {p['n_agents']}")
        lines.append(f"- lasers: {p['n_lasers']}")
        lines.append(f"- horizon `t_max`: {p['t_max']}")
        lines.append(f"- generator: `{p['generator_name']}`")
        lines.append("")
        lines.append("| split | seed | n_levels | images |")
        lines.append("|-------|------|----------|--------|")
        for split, s in p["splits"].items():
            lines.append(
                f"| {split} | {s['seed']} | {s['n_levels']} "
                f"| `{s['images_dir']}/` |"
            )
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[ok] wrote index: {out_path}")


def main() -> int:
    specs = build_specs()
    all_params = [_render_pool(s) for s in specs]
    index_path = PROJECT_ROOT / "results" / "level_pool_index.md"
    write_index(all_params, index_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
