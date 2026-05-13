# Solver + Generator Cleanup Design

**Date:** 2026-05-13
**Author:** Hugo Charels (with Claude assistance)
**Status:** Approved for planning

## Goal

Refactor the `src/solver/` and `src/generators/` packages in this thesis repo so the code is structurally ready to be moved into the LLE upstream repository as a later, separate step. Behaviour is preserved; no new features. All existing benchmarks, scripts, and tests keep working.

## Out of scope

- The actual move to the LLE GitHub repo (a separate, later step).
- New generators, new constraints, or new cooperation metrics.
- Performance optimisation beyond what falls out of dead-code removal.
- CI configuration changes.

## Target module layout

```
src/
  solver/
    __init__.py              # public API + __all__
    world_solver.py          # single consolidated solver (replaces 3 files)
    cooperation_solver.py    # binary "needs cooperation?" check
    profile/                 # split from cooperation_profile_analyzer.py
      __init__.py            # re-exports HelperEvent, CooperationProfileResult, CooperationProfileAnalyzer
      result.py              # HelperEvent, CooperationProfileResult dataclasses
      graph_metrics.py       # largest_scc_size, longest_chain_length, synchronous_width, mutual_pairs (pure funcs)
      analyzer.py            # CooperationProfileAnalyzer orchestrator
    constraints/
      __init__.py
      base.py
      initialization.py
      movements.py
      lasers.py              # all three laser-constraint classes live here
    _internal/
      model.py               # SATModel (pysat wrapper)
      variables.py           # VariableFactory
      profiler.py            # SolverProfiler
      grid.py                # all_positions, is_within_bounds, get_neighbors helpers

  generators/
    __init__.py              # public API + __all__
    base.py                  # BaseGenerator (abstract)
    geometry.py              # beam_tiles, direction_delta, in_bounds, points_out_immediately (pure funcs)
    candidates.py            # CandidateLayout dataclass
    world_builder.py         # WorldBuilder (existing; drops local Direction enum)
    registry.py
    random.py                # RandomGenerator + RandomCooperativeGenerator + ConstrainedRandomCooperativeGenerator
    constructive.py          # ConstructiveGenerator
    cooperative.py           # CooperativeGenerator (extends ConstructiveGenerator)
    level6_style.py          # Level6StyleGenerator (extends CooperativeGenerator)
    manual.py                # ManualGenerator
```

**Files deleted:**

- `src/solver/world_data.py` (Protocol)
- `src/solver/adapter.py` (LLEAdapter)
- `src/solver/world_solver_strict_laser.py`
- `src/solver/world_solver_selective_strict_laser.py`
- `src/solver/cooperation_profile_analyzer.py` (replaced by `solver/profile/` package)
- `src/generators/constrained_random_solvable_generator.py` (merged into `random.py`)

## Component-by-component changes

### 1. Consolidate solver variants

**Before:** three classes — `WorldSolver`, `WorldSolverStrictLaser`, `WorldSolverSelectiveStrictLaser` — identical except for which laser-constraint class they instantiate.

**After:** one `WorldSolver` with a `laser_mode` parameter.

```python
class LaserMode(StrEnum):
    STANDARD = "standard"
    STRICT = "strict"
    SELECTIVE_STRICT = "selective_strict"


class WorldSolver:
    def __init__(
        self,
        world: lle.World,
        T_MAX: int = 10,
        *,
        laser_mode: LaserMode = LaserMode.STANDARD,
        strict_colors: frozenset[int] | None = None,
        enable_profiling: bool = False,
        movement_method: str = METHOD_LOCAL,
    ):
        if laser_mode is LaserMode.SELECTIVE_STRICT and not strict_colors:
            raise ValueError("laser_mode=selective_strict requires strict_colors")
        # ... build self.constraints based on laser_mode
```

Call sites that change: `cooperation_solver.py`, `cooperation_profile_analyzer.py:162`.

### 2. Drop `WorldData` Protocol and `LLEAdapter`

The solver and generators stop wrapping `lle.World` in an adapter and use it directly. Attribute mapping:

| Old (WorldData) | New (lle.World) |
|---|---|
| `width`, `height` | direct |
| `agents` (`AgentData` with `color`, `position`) | `enumerate(world.start_pos)` |
| `laser_sources[i].position` | `world.laser_sources[i].pos` |
| `laser_sources[i].direction` (tuple) | `world.laser_sources[i].direction.delta()` |
| `laser_sources[i].color` | `world.laser_sources[i].agent_id` |
| `exit_positions` | `world.exit_pos` |
| `wall_positions` | `world.wall_pos` |
| `all_positions()` | helper in `solver/_internal/grid.py` |
| `is_within_bounds(pos)` | helper or inline |
| `get_neighbors(pos)` | helper |
| `is_wall(pos)` | `pos in frozenset(world.wall_pos)` (cache once) |

The local `world_builder.Direction` enum is replaced with `lle.tiles.Direction`. `WorldBuilder.add_laser` uses `direction.name[0]` to produce the map-string letter.

### 3. Flatten generator hierarchy

**Before** (5-deep chain on the level-6 branch, 8 leaf classes):

```
BaseGenerator
├── RandomSolvableGenerator                   262 LOC
│   ├── ConstrainedRandomSolvableGenerator    123 LOC
│   │   ├── ConstructiveSolvableGenerator     150 LOC
│   │   │   └── ConstructiveCooperativeGen.   158 LOC
│   │   │       └── ConstructiveLevel6Style.  210 LOC
│   │   └── ConstrainedRandomCoopGenerator     64 LOC
│   └── RandomCooperativeGenerator             77 LOC
└── ManualGenerator                            30 LOC
```

**After** (3-deep max chain, 7 leaf classes):

```
BaseGenerator
├── RandomGenerator                            (validate_geometry: bool = True)
│   ├── RandomCooperativeGenerator             (validate_geometry=False default + profile filter)
│   └── ConstrainedRandomCooperativeGenerator  (validate_geometry=True default + profile filter)
├── ConstructiveGenerator
│   └── CooperativeGenerator
│       └── Level6StyleGenerator
└── ManualGenerator
```

Key changes:

- `ConstrainedRandomSolvableGenerator` is merged into `RandomGenerator`. Its geometric validation (no laser pointing outside, non-zero beam length, no exit on beam) becomes default-on behaviour, controlled by `validate_geometry: bool = True`.
- `_beam_tiles`, `_points_out_immediately`, `_in_bounds`, and `_delta` move from the (now-removed) `ConstrainedRandomSolvableGenerator` to module-level pure functions in `generators/geometry.py`. Generators call them as helpers; no inheritance just for code reuse.
- `RandomCooperativeGenerator` and `ConstrainedRandomCooperativeGenerator` remain as separate classes (for benchmark/experiment continuity) but become thin subclasses of `RandomGenerator` with different `validate_geometry` defaults and a profile filter in `_accept_world`.
- The constructive branch keeps its real "is-a" inheritance (`Level6StyleGenerator` IS a `CooperativeGenerator` IS a `ConstructiveGenerator`).

### 4. Split `cooperation_profile_analyzer.py`

Current file: 339 LOC mixing dataclasses, pure graph algorithms, and orchestration.

After split:

- `solver/profile/result.py` (~80 LOC) — `HelperEvent`, `CooperationProfileResult` dataclasses (including `matches_profile`).
- `solver/profile/graph_metrics.py` (~120 LOC) — `largest_scc_size`, `longest_chain_length`, `synchronous_width`, `mutual_pairs` as pure functions on edge sets.
- `solver/profile/analyzer.py` (~140 LOC) — `CooperationProfileAnalyzer` orchestrator (runs solvers, extracts helper events, classifies profile).

The `solver/profile/__init__.py` re-exports `HelperEvent`, `CooperationProfileResult`, `CooperationProfileAnalyzer` so existing import paths via `solver/__init__.py` keep working.

### 5. Public API hardening

Both `solver/__init__.py` and `generators/__init__.py` get explicit `__all__` listing the public surface.

Within each package, intra-package imports become **relative** (`from .foo import Bar`, not `from solver.foo import Bar`). This removes dependence on `src/` being on `sys.path` and makes the packages relocatable.

Public classes get one-line purpose docstrings; non-trivial classes get longer docstrings. Type hints are filled in on every public method (params and return).

### 6. CLI registry rename

New registry names (string IDs passed to `@register_generator`):

| Old name | New name |
|---|---|
| `random_solvable` | `random` |
| `constrained_random_solvable` | (removed — same class as `random`) |
| `constructive_solvable` | `constructive` |
| `constructive_cooperative` | `cooperative` |
| `constructive_level6_style` | `level6_style` |
| `random_cooperative` | `random_cooperative` (unchanged) |
| `constrained_random_cooperative` | `constrained_random_cooperative` (unchanged) |
| `manual` | `manual` (unchanged) |

`run_rejection_benchmark.py` and `run_profile_benchmark.py` are updated to use the new names. No aliases.

## Documentation updates

- `CLAUDE.md` lines 13-15, 55-57: rewrite the WorldData/LLEAdapter description to match the new structure.
- `AGENTS.md` lines 13-15, 55-57: same.
- `README.md` lines 89, 91, 97: update class names.
- `thesis/notes/cooperation_profiles.md:148`: update `WorldSolverStrictLaser` reference.
- `phd_pitch/proposal.typ:29, 56`: reframe the WorldData lines (the "generalize beyond LLE" future-work goal does not depend on preserving the current Protocol; re-introduce later if/when a non-LLE backend appears).

## Verification

Each commit in the refactor must independently pass:

```bash
python3.13 -m pytest src/tests/
ruff check src/
```

After the final commit, a smoke test confirms every registered generator can still produce a valid level:

```bash
python3.13 src/generate.py -n 1 random              --size 5 5 --agents 2
python3.13 src/generate.py -n 1 constructive        --size 5 5 --agents 2
python3.13 src/generate.py -n 1 cooperative         --size 6 6 --agents 2
python3.13 src/generate.py -n 1 level6_style        --size 13 13 --agents 4 --lasers 3 --t-max 21
python3.13 src/generate.py -n 1 random_cooperative  --size 6 6 --agents 2
python3.13 src/generate.py -n 1 constrained_random_cooperative --size 6 6 --agents 2
```

`ManualGenerator` is exempt (requires manually specified coordinates).

A new test (`src/tests/test_public_api.py`) imports every symbol in `solver.__all__` and `generators.__all__` to catch a broken `__all__`.

## Commit ordering

Each commit keeps the repo in a passing state.

1. Consolidate solver variants into a single `WorldSolver` with `laser_mode`.
2. Drop `WorldData` Protocol and `LLEAdapter`; solver/generators use `lle.World` directly. Drop local `world_builder.Direction` in favour of `lle.tiles.Direction`.
3. Split `cooperation_profile_analyzer.py` into the `solver/profile/` package; preserve import paths via re-exports.
4. Flatten generator hierarchy: rename classes, drop `ConstrainedRandomSolvableGenerator`, restructure `RandomCooperativeGenerator` + `ConstrainedRandomCooperativeGenerator` to use the `validate_geometry` flag, move shared helpers to `generators/geometry.py`.
5. File reorganisation per the target layout (new file names, helpers in `geometry.py`).
6. Public API hardening: `__all__`, relative imports, docstrings, type hints.
7. Update CLI registry strings; update benchmark scripts and tests.
8. Update documentation (`CLAUDE.md`, `AGENTS.md`, `README.md`, `thesis/notes/cooperation_profiles.md`, `phd_pitch/proposal.typ`).
9. Final verification: pytest + ruff + end-to-end CLI smoke.

## Capability impact

What the user loses:

- The `WorldData` Protocol abstraction. Currently unused by any test or production path (all callers wrap real `lle.World` via `LLEAdapter`), but listed in `phd_pitch/proposal.typ` as a future-research generalisation target. Reframed as future work in the proposal text.

What the user keeps:

- All 7 generator behaviours (Random, ConstrainedRandomCooperative, RandomCooperative, Constructive, Cooperative, Level6Style, Manual). The 8th class (`ConstrainedRandomSolvableGenerator`) merges into `RandomGenerator` with its behaviour as the default.
- All 3 solver behaviours (standard, strict, selective-strict) — same outputs via `laser_mode`.
- All cooperation profile analyses — same dataclasses, same orchestrator.
- All benchmark scripts (after import + registry-string updates).
- All 24 tests (after import + class-name updates).

## Risk and mitigation

| Risk | Mitigation |
|---|---|
| Test imports break across the refactor | Each commit updates the tests it touches; pytest gates every commit. |
| Benchmark scripts break silently | Verification step runs each registered generator end-to-end. |
| Attribute renames miss a call site | `git grep` for the old attribute name per rename; pytest + ruff catch the rest. |
| Re-export paths drift | A new `test_public_api.py` imports every `__all__` symbol. |
| Thesis prose drifts from code | `feedback-thesis-code-sync` memory; explicit doc-update step in commit ordering. |
