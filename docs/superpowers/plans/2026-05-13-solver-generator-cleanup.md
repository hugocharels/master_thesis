# Solver + Generator Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `src/solver/` and `src/generators/` so the structure is ready to be moved into the LLE upstream repo as a separate later step. Behaviour preserved end-to-end.

**Architecture:** Drop the `WorldData` Protocol and `LLEAdapter` (use `lle.World` directly), collapse three `WorldSolver` variants into one with a `laser_mode` flag, flatten the 5-deep generator inheritance chain into a 3-deep structure with shared helpers in `geometry.py`, split the 339-LOC `cooperation_profile_analyzer.py` into a focused `solver/profile/` subpackage, and harden the public API with `__all__` declarations and relative imports.

**Tech Stack:** Python 3.13, pysat (Minisat22), `lle` package, pytest, ruff.

**Reference:** See `docs/superpowers/specs/2026-05-13-solver-generator-cleanup-design.md` for the full design.

---

## Task ordering rationale

Each commit keeps the repo in a passing state. Tasks 1-9 each end with `pytest src/tests/ && ruff check src/` both green before commit. The order is chosen so renames cascade in one direction — earlier tasks introduce new names that later tasks consume.

---

### Task 1: Consolidate solver variants into `WorldSolver` with `laser_mode`

**Files:**
- Modify: `src/solver/world_solver.py`
- Modify: `src/solver/cooperation_solver.py`
- Modify: `src/solver/cooperation_profile_analyzer.py:160-170`
- Modify: `src/solver/__init__.py`
- Delete: `src/solver/world_solver_strict_laser.py`
- Delete: `src/solver/world_solver_selective_strict_laser.py`

- [ ] **Step 1: Add `LaserMode` enum and rewrite `WorldSolver` constructor**

Replace the constructor and `self.constraints` initialisation in `src/solver/world_solver.py`. New file content (top portion only — the methods `build_model`, `solve`, `extract_plan`, `get_profiling_data`, `export_profiling_*`, `print_model` stay unchanged):

```python
import time
from enum import StrEnum

from lle import Action
from pysat.solvers import Minisat22

from .constraints import (
    ConstraintContext,
    InitializationConstraints,
    LaserConstraints,
    MovementConstraints,
    SelectiveStrictLaserConstraints,
    StrictLaserConstraints,
)
from .constraints.movements import METHOD_LOCAL
from .model import SATModel
from .profiler import SolverProfiler
from .variables import VariableFactory
from .world_data import WorldData


class LaserMode(StrEnum):
    STANDARD = "standard"
    STRICT = "strict"
    SELECTIVE_STRICT = "selective_strict"


class WorldSolver:
    def __init__(
        self,
        world: WorldData,
        T_MAX: int = 10,
        *,
        laser_mode: LaserMode = LaserMode.STANDARD,
        strict_colors: frozenset[int] | None = None,
        enable_profiling: bool = False,
        movement_method: str = METHOD_LOCAL,
    ):
        if laser_mode is LaserMode.SELECTIVE_STRICT and not strict_colors:
            raise ValueError(
                "laser_mode=selective_strict requires a non-empty strict_colors set"
            )

        self.world = world
        self.T_MAX = T_MAX
        self.var = VariableFactory()
        self.model = SATModel()
        self.enable_profiling = enable_profiling
        self.profiler = SolverProfiler() if enable_profiling else None
        self.movement_method = movement_method
        self.laser_mode = laser_mode
        self.strict_colors = frozenset(strict_colors) if strict_colors else frozenset()

        self.ctx = ConstraintContext(world, self.var, T_MAX)
        self.constraints = [
            InitializationConstraints(self.ctx),
            MovementConstraints(self.ctx, movement_method=movement_method),
            self._build_laser_constraint(),
        ]
        self._model_built = False

    def _build_laser_constraint(self):
        if self.laser_mode is LaserMode.STANDARD:
            return LaserConstraints(self.ctx)
        if self.laser_mode is LaserMode.STRICT:
            return StrictLaserConstraints(self.ctx)
        if self.laser_mode is LaserMode.SELECTIVE_STRICT:
            return SelectiveStrictLaserConstraints(self.ctx, self.strict_colors)
        raise ValueError(f"Unknown laser_mode: {self.laser_mode}")
```

Note: `WorldData` import stays for now — it goes away in Task 2.

- [ ] **Step 2: Update `cooperation_solver.py` to use the new API**

Replace the import and constructor body in `src/solver/cooperation_solver.py`:

```python
from dataclasses import dataclass

from .constraints.movements import METHOD_LOCAL
from .world_data import WorldData
from .world_solver import LaserMode, WorldSolver


@dataclass
class CooperationResult:
    cooperation_needed: bool


class CooperationSolver:
    """
    Assumes the original level is solvable by the normal WorldSolver.
    Cooperation is needed iff the strict-laser solver is UNSAT.
    """

    def __init__(self, world: WorldData, T_MAX: int = 10, movement_method=METHOD_LOCAL):
        self.world = world
        self.T_MAX = T_MAX
        self.movement_method = movement_method

    def analyze(self) -> CooperationResult:
        strict_sat, _ = WorldSolver(
            self.world,
            T_MAX=self.T_MAX,
            laser_mode=LaserMode.STRICT,
            movement_method=self.movement_method,
        ).solve()
        return CooperationResult(cooperation_needed=not bool(strict_sat))
```

- [ ] **Step 3: Update `cooperation_profile_analyzer.py` call site**

In `src/solver/cooperation_profile_analyzer.py`:

1. Replace import line 8 `from .world_solver_selective_strict_laser import WorldSolverSelectiveStrictLaser` with:
```python
from .world_solver import LaserMode
```

2. Replace `_find_necessary_helpers` method body (lines 159-170):
```python
def _find_necessary_helpers(self) -> set[int]:
    necessary = set()
    for agent in self.world.agents:
        sat, _ = WorldSolver(
            self.world,
            T_MAX=self.T_MAX,
            laser_mode=LaserMode.SELECTIVE_STRICT,
            strict_colors=frozenset({agent.color}),
            movement_method=self.movement_method,
        ).solve()
        if not sat:
            necessary.add(agent.color)
    return necessary
```

- [ ] **Step 4: Update `solver/__init__.py`**

Replace the contents of `src/solver/__init__.py`:

```python
from .adapter import LLEAdapter
from .cooperation_profile_analyzer import (
    CooperationProfileAnalyzer,
    CooperationProfileResult,
    HelperEvent,
)
from .cooperation_solver import (
    CooperationResult,
    CooperationSolver,
)
from .profiler import SolverProfiler
from .world_data import AgentData, LaserSourceData, WorldData
from .world_solver import LaserMode, WorldSolver
```

(Note: `WorldSolverStrictLaser` and `WorldSolverSelectiveStrictLaser` removed from exports.)

- [ ] **Step 5: Delete the two obsolete solver files**

```bash
rm src/solver/world_solver_strict_laser.py
rm src/solver/world_solver_selective_strict_laser.py
```

- [ ] **Step 6: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: all 24 tests pass; ruff reports no errors.

- [ ] **Step 7: Commit**

```bash
git add -A src/solver/
git commit -m "$(cat <<'EOF'
♻️ Consolidate WorldSolver variants into laser_mode parameter

Replace WorldSolverStrictLaser and WorldSolverSelectiveStrictLaser with a
single WorldSolver(world, laser_mode=..., strict_colors=...) entry point.
Call sites in CooperationSolver and CooperationProfileAnalyzer updated.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Drop the `WorldData` Protocol and `LLEAdapter`

**Files:**
- Delete: `src/solver/world_data.py`
- Delete: `src/solver/adapter.py`
- Create: `src/solver/_internal/__init__.py`
- Create: `src/solver/_internal/grid.py`
- Modify: `src/solver/world_solver.py`
- Modify: `src/solver/cooperation_solver.py`
- Modify: `src/solver/cooperation_profile_analyzer.py`
- Modify: `src/solver/__init__.py`
- Modify: `src/solver/constraints/base.py` (and any constraint files that touch the world)
- Modify: every generator that wraps `LLEAdapter(world)` before solving
- Modify: every test that uses `LLEAdapter`

- [ ] **Step 1: Create the grid-helper module**

The Protocol provided three helpers that `lle.World` doesn't have: `all_positions()`, `is_within_bounds(pos)`, `get_neighbors(pos)`. Move them to a small helper module.

Create `src/solver/_internal/__init__.py`:
```python
```
(empty file)

Create `src/solver/_internal/grid.py`:
```python
"""Grid helpers used by the solver."""

from __future__ import annotations

from lle import World

Position = tuple[int, int]


def all_positions(world: World) -> list[Position]:
    """Every (i, j) cell in the grid."""
    return [(i, j) for i in range(world.height) for j in range(world.width)]


def is_within_bounds(world: World, pos: Position) -> bool:
    i, j = pos
    return 0 <= i < world.height and 0 <= j < world.width


def get_neighbors(world: World, pos: Position) -> list[Position]:
    """4-directional neighbors that are within bounds."""
    i, j = pos
    result = []
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ni, nj = i + di, j + dj
        if 0 <= ni < world.height and 0 <= nj < world.width:
            result.append((ni, nj))
    return result
```

- [ ] **Step 2: Inventory and update solver code attribute references**

Run this grep to find every spot that depends on the Protocol's attribute names:

```bash
grep -rn -E 'world\.(agents|laser_sources|exit_positions|wall_positions|all_positions|is_within_bounds|get_neighbors|is_wall|width|height)' src/solver/ src/generators/
```

Apply this attribute mapping everywhere in `src/solver/` (and later, in `src/generators/` for generator code that calls solver methods):

| Old (WorldData) | New (lle.World) |
|---|---|
| `world.exit_positions` | `world.exit_pos` |
| `world.wall_positions` | `world.wall_pos` |
| `world.is_wall(pos)` | `pos in self._wall_set` (cache once: `self._wall_set = frozenset(world.wall_pos)`) |
| `world.all_positions()` | `all_positions(world)` (from `_internal.grid`) |
| `world.is_within_bounds(pos)` | `is_within_bounds(world, pos)` |
| `world.get_neighbors(pos)` | `get_neighbors(world, pos)` |
| `world.width`, `world.height` | unchanged |
| `world.agents` (`AgentData` with `.color`, `.position`) | replace with `[AgentData(color=i, position=pos) for i, pos in enumerate(world.start_pos)]` — keep `AgentData` as a local dataclass inside the solver for now, or just iterate `enumerate(world.start_pos)` directly. Adopt the latter where ergonomic. |
| `world.laser_sources[i]` field `.color` | `.agent_id` |
| `world.laser_sources[i]` field `.position` | `.pos` |
| `world.laser_sources[i]` field `.direction` (tuple) | `.direction.delta()` (returns the tuple) |

`AgentData` and `LaserSourceData` value classes were used to carry these fields under uniform names. Since `lle.World`'s field names differ, we either:
1. Adapt solver code to use LLE's names directly, OR
2. Keep `AgentData`/`LaserSourceData` as small adapters constructed on demand.

Pick option 2 to minimise diff — keep `AgentData` and `LaserSourceData` as dataclasses, but move them out of `world_data.py` (which is being deleted) into the solver package. Create `src/solver/_internal/types.py`:

```python
"""Value types used internally by the solver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Position = Tuple[int, int]


@dataclass(frozen=True)
class AgentData:
    color: int
    position: Position


@dataclass(frozen=True)
class LaserSourceData:
    color: int
    direction: Tuple[int, int]
    position: Position


def agents_from_world(world) -> list[AgentData]:
    return [AgentData(color=i, position=pos) for i, pos in enumerate(world.start_pos)]


def laser_sources_from_world(world) -> list[LaserSourceData]:
    return [
        LaserSourceData(
            color=src.agent_id,
            direction=src.direction.delta(),
            position=src.pos,
        )
        for src in world.laser_sources
    ]
```

- [ ] **Step 3: Update `ConstraintContext` to take `lle.World` and call the new helpers**

Inspect `src/solver/constraints/base.py`. At the top of the file, add:
```python
from .._internal.types import agents_from_world, laser_sources_from_world
```

Then wherever it reads `self.world.agents`, replace with `agents_from_world(self.world)` (cache as `self._agents` in `__init__`). Same for `laser_sources` → `laser_sources_from_world`. For other attributes use the mapping in Step 2.

Apply the same pattern to any other file in `src/solver/constraints/` that reads `self.world.<attr>`. Run:
```bash
grep -rn "self.world\." src/solver/constraints/
```
and walk each match through the Step 2 mapping. Add the `_internal.types` import to any file that newly needs `agents_from_world` / `laser_sources_from_world`.

If `ConstraintContext.__init__` currently does `self.world = world`, leave that; just adapt subsequent accesses.

- [ ] **Step 4: Update `world_solver.py` type hint**

In `src/solver/world_solver.py`:

1. Replace `from .world_data import WorldData` with `from lle import World`.
2. Change `def __init__(self, world: WorldData, ...)` to `def __init__(self, world: World, ...)`.

- [ ] **Step 5: Update `cooperation_solver.py` type hint**

Same pattern in `src/solver/cooperation_solver.py` — `WorldData` → `lle.World`.

- [ ] **Step 6: Update `cooperation_profile_analyzer.py`**

- Remove the `world` attribute uses that go through Protocol. Use `agents_from_world(self.world)` to enumerate agents in `_find_necessary_helpers`.
- The `_raw_beam_paths` method calls `self.world.wall_positions`, `self.world.laser_sources`, `self.world.is_within_bounds`. Update to:
  - `wall_positions = frozenset(self.world.wall_pos)`
  - `laser_sources` becomes `laser_sources_from_world(self.world)` so the `.position`, `.direction`, `.color` field names still work.
  - `self.world.is_within_bounds(pos)` becomes `is_within_bounds(self.world, pos)` (import from `_internal.grid`).

- [ ] **Step 7: Update `solver/__init__.py`**

Replace contents with:
```python
from .cooperation_profile_analyzer import (
    CooperationProfileAnalyzer,
    CooperationProfileResult,
    HelperEvent,
)
from .cooperation_solver import (
    CooperationResult,
    CooperationSolver,
)
from .profiler import SolverProfiler
from .world_solver import LaserMode, WorldSolver
```

(Note: `LLEAdapter`, `AgentData`, `LaserSourceData`, `WorldData` removed from public exports. `AgentData`/`LaserSourceData` live in `_internal/types.py` and are no longer public.)

- [ ] **Step 8: Update every generator that wraps with `LLEAdapter`**

The generators that wrap worlds are:
- `src/generators/random_solvable_generator.py:212` — `LLEAdapter(world)` in `_is_satisfiable`.
- `src/generators/constructive_cooperative_generator.py:140` — in `_analyze_profile`.
- `src/generators/random_cooperative_generator.py:59` — in `_analyze_profile`.
- `src/generators/constrained_random_cooperative_generator.py:44` — in `_analyze_profile`.

For each: remove the `from solver import LLEAdapter` import; remove the `adapted = LLEAdapter(world)` line; pass `world` directly to the solver/analyser:

```python
# Before
def _is_satisfiable(self, world: World, t: int) -> bool:
    world.reset()
    adapted = LLEAdapter(world)
    solver = WorldSolver(adapted, T_MAX=t)
    result, _ = solver.solve()
    return bool(result)

# After
def _is_satisfiable(self, world: World, t: int) -> bool:
    world.reset()
    solver = WorldSolver(world, T_MAX=t)
    result, _ = solver.solve()
    return bool(result)
```

Same shape in `_analyze_profile` methods.

- [ ] **Step 9: Update tests that wrap with `LLEAdapter`**

Files: `src/tests/test_solver.py`, `src/tests/test_constructive_cooperative_generator.py`, `src/tests/test_constructive_generator.py`, `src/tests/test_cooperative_solver.py`, `src/tests/test_profile_targeting.py`, `src/tests/test_cooperation_profiles.py`, `src/benchmark/runner.py`.

For each:
1. Remove `LLEAdapter` from the `from solver import ...` line.
2. Drop the `LLEAdapter(world)` wrap; pass `world` directly.

Example diff:
```python
# Before
from solver import LLEAdapter, WorldSolver
solver = WorldSolver(LLEAdapter(world), T_MAX=2)

# After
from solver import WorldSolver
solver = WorldSolver(world, T_MAX=2)
```

- [ ] **Step 10: Delete `world_data.py` and `adapter.py`**

```bash
rm src/solver/world_data.py
rm src/solver/adapter.py
```

- [ ] **Step 11: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: all 24 tests pass; ruff reports no errors. If tests fail with `AttributeError: 'World' object has no attribute X`, that's a missed attribute rename — apply the mapping from Step 2.

- [ ] **Step 12: Commit**

```bash
git add -A src/solver/ src/generators/ src/tests/ src/benchmark/
git commit -m "$(cat <<'EOF'
♻️ Drop WorldData Protocol and LLEAdapter; use lle.World directly

The solver and generators now take lle.World instances directly. The
Protocol decoupling was theoretical (no test exercised it). Grid helpers
moved to solver/_internal/grid.py; AgentData/LaserSourceData kept as
internal value types in solver/_internal/types.py.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Replace local `Direction` enum with `lle.tiles.Direction`

**Files:**
- Modify: `src/generators/world_builder.py`
- Modify: `src/generators/random_solvable_generator.py`
- Modify: `src/generators/constrained_random_solvable_generator.py`
- Modify: `src/generators/constructive_solvable_generator.py`
- Modify: `src/generators/constructive_cooperative_generator.py`
- Modify: `src/generators/constructive_level6_style_generator.py`
- Modify: `src/generators/__init__.py`

- [ ] **Step 1: Update `WorldBuilder` to use `lle.tiles.Direction`**

In `src/generators/world_builder.py`:

```python
"""
Programmatic builder for lle.World.

Generators use this to place entities on a grid, then call .build()
to get a real lle.World. The LLE string format is an internal detail.
"""

from __future__ import annotations

from typing import Tuple

from lle import Direction, World

Position = Tuple[int, int]


def _dir_letter(direction: Direction) -> str:
    return direction.name[0]


class WorldBuilder:
    """
    Build an lle.World programmatically.

    Usage:
        world = (
            WorldBuilder(5, 5)
            .add_agent(0, (0, 0))
            .add_agent(1, (0, 4))
            .add_exit((4, 0))
            .add_exit((4, 4))
            .add_wall((2, 2))
            .add_laser(0, (1, 0), Direction.EAST)
            .build()
        )
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._grid: list[list[str]] = [
            ["." for _ in range(width)] for _ in range(height)
        ]

    def _check_bounds(self, pos: Position):
        r, c = pos
        if not (0 <= r < self.height and 0 <= c < self.width):
            raise ValueError(
                f"Position {pos} out of bounds ({self.height}x{self.width})"
            )

    def _check_free(self, pos: Position):
        r, c = pos
        if self._grid[r][c] != ".":
            raise ValueError(f"Position {pos} already occupied by '{self._grid[r][c]}'")

    def add_agent(self, agent_id: int, pos: Position) -> "WorldBuilder":
        self._check_bounds(pos)
        self._check_free(pos)
        self._grid[pos[0]][pos[1]] = f"S{agent_id}"
        return self

    def add_exit(self, pos: Position) -> "WorldBuilder":
        self._check_bounds(pos)
        self._check_free(pos)
        self._grid[pos[0]][pos[1]] = "X"
        return self

    def add_wall(self, pos: Position) -> "WorldBuilder":
        self._check_bounds(pos)
        self._check_free(pos)
        self._grid[pos[0]][pos[1]] = "@"
        return self

    def add_gem(self, pos: Position) -> "WorldBuilder":
        self._check_bounds(pos)
        self._check_free(pos)
        self._grid[pos[0]][pos[1]] = "G"
        return self

    def add_laser(self, agent_id: int, pos: Position, direction: Direction) -> "WorldBuilder":
        self._check_bounds(pos)
        self._check_free(pos)
        self._grid[pos[0]][pos[1]] = f"L{agent_id}{_dir_letter(direction)}"
        return self

    def build(self) -> World:
        """Serialize the grid and construct a real lle.World."""
        world_str = "\n".join(" ".join(row) for row in self._grid)
        world = World(world_str)
        world.reset()
        return world
```

- [ ] **Step 2: Update generators that import `Direction` from `world_builder`**

For each generator file in the list above, change:
```python
from generators.world_builder import Direction, WorldBuilder
```
to:
```python
from lle import Direction
from generators.world_builder import WorldBuilder
```

Or where only `Direction` is used:
```python
from generators.world_builder import Direction
```
to:
```python
from lle import Direction
```

Code that uses `Direction.NORTH`, `Direction.SOUTH`, etc. needs no further change — `lle.Direction` has the same enum members.

- [ ] **Step 3: Update `generators/__init__.py`**

If it currently exports `Direction`, replace the source. In `src/generators/__init__.py`:
```python
# Before
from generators.world_builder import Direction, WorldBuilder

# After
from generators.world_builder import WorldBuilder
```

(`Direction` should be imported from `lle` directly by anyone needing it.)

- [ ] **Step 4: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: all tests pass; ruff clean.

- [ ] **Step 5: Smoke test the level6_style generator**

```bash
python3.13 src/generate.py -n 1 constructive_level6_style --size 13 13 --agents 4 --lasers 3 --t-max 21
```

Expected: a valid level generated without error.

- [ ] **Step 6: Commit**

```bash
git add -A src/
git commit -m "$(cat <<'EOF'
♻️ Replace local Direction enum with lle.Direction

WorldBuilder serializes via direction.name[0] for the map-string letter.
Generators import Direction from lle.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Split `cooperation_profile_analyzer.py` into `solver/profile/`

**Files:**
- Create: `src/solver/profile/__init__.py`
- Create: `src/solver/profile/result.py`
- Create: `src/solver/profile/graph_metrics.py`
- Create: `src/solver/profile/analyzer.py`
- Delete: `src/solver/cooperation_profile_analyzer.py`
- Modify: `src/solver/__init__.py`

- [ ] **Step 1: Create `solver/profile/result.py`**

```python
"""Dataclasses describing the cooperation-profile analysis result."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class HelperEvent:
    helper: int
    beneficiary: int
    time: int
    position: tuple[int, int]
    laser_source: tuple[int, int]


@dataclass(frozen=True)
class CooperationProfileResult:
    solvable: bool
    cooperation_required: bool
    num_agents: int
    necessary_helpers: frozenset[int]
    dependency_edges: frozenset[tuple[int, int]]
    helper_events: tuple[HelperEvent, ...]
    mutual_pairs: frozenset[tuple[int, int]]
    longest_chain_length: int
    largest_scc_size: int
    synchronous_width: int
    profile: str

    def matches_profile(self, target: str | None) -> bool:
        if target in (None, "", "any"):
            return True
        if target == "independent":
            return not self.cooperation_required
        if target == "cooperative":
            return self.cooperation_required
        if target == "asymmetric":
            return self.cooperation_required and self.profile == "asymmetric"
        if target == "mutual":
            return bool(self.mutual_pairs)
        if target == "chain":
            return self.cooperation_required and self._is_chain_like()
        if target == "distributed":
            return self.cooperation_required and self._has_distributed_support()
        if target == "fully_coupled":
            return (
                self.cooperation_required
                and self.largest_scc_size == self.num_agents
            )
        raise ValueError(f"Unknown cooperation profile: {target}")

    def _has_distributed_support(self) -> bool:
        indegree: dict[int, int] = defaultdict(int)
        for _, dst in self.dependency_edges:
            indegree[dst] += 1
        return any(count >= 2 for count in indegree.values())

    def _is_chain_like(self) -> bool:
        if not self.dependency_edges:
            return False
        indegree: dict[int, int] = defaultdict(int)
        outdegree: dict[int, int] = defaultdict(int)
        nodes: set[int] = set()
        for src, dst in self.dependency_edges:
            indegree[dst] += 1
            outdegree[src] += 1
            nodes.add(src)
            nodes.add(dst)
        if any(indegree[n] > 1 for n in nodes):
            return False
        if any(outdegree[n] > 1 for n in nodes):
            return False
        return self.longest_chain_length >= max(1, len(nodes) - 1)
```

- [ ] **Step 2: Create `solver/profile/graph_metrics.py`**

```python
"""Pure graph metrics over a dependency-edge set."""

from __future__ import annotations

from collections import defaultdict

from .result import HelperEvent


def mutual_pairs(edges: set[tuple[int, int]]) -> set[tuple[int, int]]:
    result = set()
    for src, dst in edges:
        if (dst, src) in edges and src < dst:
            result.add((src, dst))
    return result


def largest_scc_size(edges: set[tuple[int, int]], num_agents: int) -> int:
    if num_agents == 0:
        return 0
    adjacency: dict[int, set[int]] = {i: set() for i in range(num_agents)}
    reverse: dict[int, set[int]] = {i: set() for i in range(num_agents)}
    for src, dst in edges:
        adjacency[src].add(dst)
        reverse[dst].add(src)

    visited: set[int] = set()
    order: list[int] = []

    def dfs(node: int) -> None:
        visited.add(node)
        for nxt in adjacency[node]:
            if nxt not in visited:
                dfs(nxt)
        order.append(node)

    for node in range(num_agents):
        if node not in visited:
            dfs(node)

    visited.clear()
    largest = 1

    def reverse_dfs(node: int, component: list[int]) -> None:
        visited.add(node)
        component.append(node)
        for nxt in reverse[node]:
            if nxt not in visited:
                reverse_dfs(nxt, component)

    for node in reversed(order):
        if node in visited:
            continue
        component: list[int] = []
        reverse_dfs(node, component)
        largest = max(largest, len(component))
    return largest


def longest_chain_length(edges: set[tuple[int, int]], num_agents: int) -> int:
    adjacency: dict[int, set[int]] = {i: set() for i in range(num_agents)}
    indegree: dict[int, int] = {i: 0 for i in range(num_agents)}
    for src, dst in edges:
        if dst not in adjacency[src]:
            adjacency[src].add(dst)
            indegree[dst] += 1

    queue = [node for node in range(num_agents) if indegree[node] == 0]
    topo: list[int] = []
    while queue:
        node = queue.pop()
        topo.append(node)
        for nxt in adjacency[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(topo) != num_agents:
        return 0

    dist: dict[int, int] = {i: 0 for i in range(num_agents)}
    for node in topo:
        for nxt in adjacency[node]:
            dist[nxt] = max(dist[nxt], dist[node] + 1)
    return max(dist.values(), default=0)


def synchronous_width(helper_events: set[HelperEvent]) -> int:
    helpers_by_time: dict[int, set[int]] = defaultdict(set)
    for event in helper_events:
        helpers_by_time[event.time].add(event.helper)
    return max((len(helpers) for helpers in helpers_by_time.values()), default=0)
```

- [ ] **Step 3: Create `solver/profile/analyzer.py`**

```python
"""Cooperation-profile analyser orchestrator."""

from __future__ import annotations

from collections import defaultdict

from .._internal.grid import is_within_bounds
from .._internal.types import agents_from_world, laser_sources_from_world
from ..cooperation_solver import CooperationSolver
from ..world_solver import LaserMode, WorldSolver
from .graph_metrics import (
    largest_scc_size,
    longest_chain_length,
    mutual_pairs,
    synchronous_width,
)
from .result import CooperationProfileResult, HelperEvent


class CooperationProfileAnalyzer:
    def __init__(self, world, T_MAX: int = 10, movement_method: str = "local"):
        self.world = world
        self.T_MAX = T_MAX
        self.movement_method = movement_method

    def analyze(self) -> CooperationProfileResult:
        solver = WorldSolver(
            self.world,
            T_MAX=self.T_MAX,
            movement_method=self.movement_method,
        )
        sat, model = solver.solve()
        num_agents = len(agents_from_world(self.world))

        if not sat:
            return CooperationProfileResult(
                solvable=False,
                cooperation_required=False,
                num_agents=num_agents,
                necessary_helpers=frozenset(),
                dependency_edges=frozenset(),
                helper_events=tuple(),
                mutual_pairs=frozenset(),
                longest_chain_length=0,
                largest_scc_size=0,
                synchronous_width=0,
                profile="unsolvable",
            )

        cooperation_required = CooperationSolver(
            self.world,
            T_MAX=self.T_MAX,
            movement_method=self.movement_method,
        ).analyze().cooperation_needed

        positions_by_time = self._extract_positions_by_time(solver, model)
        helper_events = self._extract_helper_events(positions_by_time)
        necessary_helpers = self._find_necessary_helpers()
        dependency_edges = {(e.helper, e.beneficiary) for e in helper_events}

        m_pairs = mutual_pairs(dependency_edges)
        scc = largest_scc_size(dependency_edges, num_agents)
        chain = longest_chain_length(dependency_edges, num_agents)
        sync_width = synchronous_width(helper_events)
        profile = self._classify_profile(
            cooperation_required=cooperation_required,
            dependency_edges=dependency_edges,
            mutual_pairs_value=m_pairs,
            largest_scc_size_value=scc,
            longest_chain_length_value=chain,
            num_agents=num_agents,
        )

        return CooperationProfileResult(
            solvable=True,
            cooperation_required=cooperation_required,
            num_agents=num_agents,
            necessary_helpers=frozenset(necessary_helpers),
            dependency_edges=frozenset(dependency_edges),
            helper_events=tuple(
                sorted(helper_events, key=lambda e: (e.time, e.helper, e.beneficiary))
            ),
            mutual_pairs=frozenset(m_pairs),
            longest_chain_length=chain,
            largest_scc_size=scc,
            synchronous_width=sync_width,
            profile=profile,
        )

    def _extract_positions_by_time(self, solver, model):
        positions_by_time: dict[int, dict[int, tuple[int, int]]] = defaultdict(dict)
        for lit in model:
            if lit <= 0:
                continue
            obj = solver.var.pool.obj(abs(lit))
            if not obj or obj[0] != "agent":
                continue
            _, color, position, t = obj
            positions_by_time[t][color] = position
        return positions_by_time

    def _find_necessary_helpers(self) -> set[int]:
        necessary: set[int] = set()
        for agent in agents_from_world(self.world):
            sat, _ = WorldSolver(
                self.world,
                T_MAX=self.T_MAX,
                laser_mode=LaserMode.SELECTIVE_STRICT,
                strict_colors=frozenset({agent.color}),
                movement_method=self.movement_method,
            ).solve()
            if not sat:
                necessary.add(agent.color)
        return necessary

    def _extract_helper_events(self, positions_by_time) -> set[HelperEvent]:
        events: set[HelperEvent] = set()
        beam_paths = self._raw_beam_paths()
        for t, positions in positions_by_time.items():
            for helper, helper_pos in positions.items():
                for source_pos, path in beam_paths.get(helper, []):
                    if helper_pos not in path:
                        continue
                    helper_index = path.index(helper_pos)
                    downstream = set(path[helper_index + 1 :])
                    if not downstream:
                        continue
                    for beneficiary, beneficiary_pos in positions.items():
                        if beneficiary == helper:
                            continue
                        if beneficiary_pos in downstream:
                            events.add(
                                HelperEvent(
                                    helper=helper,
                                    beneficiary=beneficiary,
                                    time=t,
                                    position=helper_pos,
                                    laser_source=source_pos,
                                )
                            )
        return events

    def _raw_beam_paths(self):
        paths: dict[int, list[tuple[tuple[int, int], list[tuple[int, int]]]]] = defaultdict(list)
        wall_positions = frozenset(self.world.wall_pos)
        sources = laser_sources_from_world(self.world)
        source_positions = {src.position for src in sources}
        for laser in sources:
            di, dj = laser.direction
            x, y = laser.position
            x += di
            y += dj
            path: list[tuple[int, int]] = []
            while is_within_bounds(self.world, (x, y)):
                if (x, y) in wall_positions or (x, y) in source_positions:
                    break
                path.append((x, y))
                x += di
                y += dj
            paths[laser.color].append((laser.position, path))
        return paths

    def _classify_profile(
        self,
        cooperation_required: bool,
        dependency_edges: set[tuple[int, int]],
        mutual_pairs_value: set[tuple[int, int]],
        largest_scc_size_value: int,
        longest_chain_length_value: int,
        num_agents: int,
    ) -> str:
        if not cooperation_required:
            return "independent"
        if largest_scc_size_value == num_agents and num_agents > 1:
            return "fully_coupled"
        if mutual_pairs_value:
            return "mutual"
        indegree: dict[int, int] = defaultdict(int)
        outdegree: dict[int, int] = defaultdict(int)
        nodes: set[int] = set()
        for src, dst in dependency_edges:
            indegree[dst] += 1
            outdegree[src] += 1
            nodes.add(src)
            nodes.add(dst)
        if any(count >= 2 for count in indegree.values()):
            return "distributed"
        if (
            dependency_edges
            and longest_chain_length_value >= 2
            and all(indegree[n] <= 1 for n in nodes)
            and all(outdegree[n] <= 1 for n in nodes)
            and longest_chain_length_value >= max(1, len(nodes) - 1)
        ):
            return "chain"
        if dependency_edges:
            return "asymmetric"
        return "cooperative"
```

- [ ] **Step 4: Create `solver/profile/__init__.py`**

```python
from .analyzer import CooperationProfileAnalyzer
from .result import CooperationProfileResult, HelperEvent

__all__ = [
    "CooperationProfileAnalyzer",
    "CooperationProfileResult",
    "HelperEvent",
]
```

- [ ] **Step 5: Update `solver/__init__.py` to import from the new subpackage**

```python
from .cooperation_solver import CooperationResult, CooperationSolver
from .profile import (
    CooperationProfileAnalyzer,
    CooperationProfileResult,
    HelperEvent,
)
from .profiler import SolverProfiler
from .world_solver import LaserMode, WorldSolver
```

- [ ] **Step 6: Delete the old analyzer file**

```bash
rm src/solver/cooperation_profile_analyzer.py
```

- [ ] **Step 7: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: all 24 tests pass; ruff clean. Existing imports (`from solver import CooperationProfileAnalyzer`) continue to work because of the re-exports.

- [ ] **Step 8: Commit**

```bash
git add -A src/solver/
git commit -m "$(cat <<'EOF'
♻️ Split cooperation_profile_analyzer.py into solver/profile/ subpackage

Three focused files: result.py (dataclasses), graph_metrics.py (pure graph
algorithms), analyzer.py (orchestrator). Old import paths preserved via
re-exports through solver/__init__.py.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Move solver internals (`model`, `variables`, `profiler`) into `solver/_internal/`

**Files:**
- Move: `src/solver/model.py` → `src/solver/_internal/model.py`
- Move: `src/solver/variables.py` → `src/solver/_internal/variables.py`
- Move: `src/solver/profiler.py` → `src/solver/_internal/profiler.py`
- Modify: `src/solver/world_solver.py`, `cooperation_profile_analyzer.py` (now in profile/analyzer.py), `__init__.py`

- [ ] **Step 1: Move the three files**

```bash
git mv src/solver/model.py src/solver/_internal/model.py
git mv src/solver/variables.py src/solver/_internal/variables.py
git mv src/solver/profiler.py src/solver/_internal/profiler.py
```

- [ ] **Step 2: Update imports inside `world_solver.py`**

Change:
```python
from .model import SATModel
from .profiler import SolverProfiler
from .variables import VariableFactory
```
to:
```python
from ._internal.model import SATModel
from ._internal.profiler import SolverProfiler
from ._internal.variables import VariableFactory
```

- [ ] **Step 3: Update `solver/__init__.py`**

Change `from .profiler import SolverProfiler` to `from ._internal.profiler import SolverProfiler`.

- [ ] **Step 4: Check `solver/constraints/*.py` files**

```bash
grep -rn -E 'from \.(model|profiler|variables) import' src/solver/constraints/
```

For any match, update the import path from `.{name}` to `.._internal.{name}` (relative imports cross package boundaries).

If grep returns nothing, skip.

- [ ] **Step 5: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: green.

- [ ] **Step 6: Commit**

```bash
git add -A src/solver/
git commit -m "$(cat <<'EOF'
♻️ Move pysat plumbing into solver/_internal/ subpackage

SATModel, VariableFactory, SolverProfiler are implementation details that
should not be part of the solver's public surface. Moving them under
_internal/ makes the boundary explicit. SolverProfiler stays re-exported
through solver/__init__.py for users that opt into profiling.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Merge the three laser-constraint files into `constraints/lasers.py`

**Files:**
- Modify: `src/solver/constraints/lasers.py`
- Delete: `src/solver/constraints/strict_laser_constraint.py`
- Delete: `src/solver/constraints/selective_strict_laser_constraint.py`
- Modify: `src/solver/constraints/__init__.py`

- [ ] **Step 1: Append `StrictLaserConstraints` and `SelectiveStrictLaserConstraints` into `lasers.py`**

Open `src/solver/constraints/lasers.py`. After the existing `LaserConstraints` class definition, append:

```python


class StrictLaserConstraints(LaserConstraints):
    """
    Variant of LaserConstraints where beam propagation does NOT stop on agents.
    It only stops at walls / bounds (same as base behavior except agent blocking).
    """

    def _beam_propagation(self):
        beam_var = self.ctx.beam_var
        propagation_map = self.ctx.beam_propagation_map

        for laser, _ in self.ctx.lasers:
            c = laser.color
            d = laser.direction
            entries = propagation_map[c, d]

            for x, y, nx, ny, is_wall in entries:
                for t in range(self.T_MAX + 1):
                    if is_wall:
                        yield [-beam_var[c, d, nx, ny, t]]
                    else:
                        bv_src = beam_var[c, d, x, y, t]
                        bv_dst = beam_var[c, d, nx, ny, t]
                        yield [-bv_src, bv_dst]
                        yield [bv_src, -bv_dst]


class SelectiveStrictLaserConstraints(LaserConstraints):
    """
    Laser constraints where only a selected subset of colors loses the ability
    to truncate their own beam. Same-colour immunity is preserved for every
    colour, matching the strict beam semantics of Definition 3.6: agents can
    still occupy cells crossed by their own beam, but the beam continues
    through them when their colour is in strict_colors.
    """

    def __init__(self, ctx, strict_colors):
        super().__init__(ctx)
        self.strict_colors = frozenset(strict_colors)

    def _beam_propagation(self):
        agent_var = self.ctx.agent_var
        beam_var = self.ctx.beam_var
        propagation_map = self.ctx.beam_propagation_map

        for laser, _ in self.ctx.lasers:
            c = laser.color
            d = laser.direction
            entries = propagation_map[c, d]

            for x, y, nx, ny, is_wall in entries:
                for t in range(self.T_MAX + 1):
                    if is_wall:
                        yield [-beam_var[c, d, nx, ny, t]]
                    else:
                        bv_src = beam_var[c, d, x, y, t]
                        bv_dst = beam_var[c, d, nx, ny, t]

                        if c in self.strict_colors:
                            yield [-bv_src, bv_dst]
                            yield [bv_src, -bv_dst]
                        else:
                            av_dst = agent_var[c, nx, ny, t]
                            yield [-bv_src, av_dst, bv_dst]
                            yield [bv_src, -bv_dst]
                            yield [-av_dst, -bv_dst]
```

- [ ] **Step 2: Update `constraints/__init__.py`**

Replace contents:
```python
from .base import ConstraintContext
from .initialization import InitializationConstraints
from .lasers import (
    LaserConstraints,
    SelectiveStrictLaserConstraints,
    StrictLaserConstraints,
)
from .movements import MovementConstraints

__all__ = [
    "ConstraintContext",
    "InitializationConstraints",
    "LaserConstraints",
    "MovementConstraints",
    "SelectiveStrictLaserConstraints",
    "StrictLaserConstraints",
]
```

- [ ] **Step 3: Delete the two single-class files**

```bash
rm src/solver/constraints/strict_laser_constraint.py
rm src/solver/constraints/selective_strict_laser_constraint.py
```

- [ ] **Step 4: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: green.

- [ ] **Step 5: Commit**

```bash
git add -A src/solver/constraints/
git commit -m "$(cat <<'EOF'
♻️ Merge strict-laser constraints into constraints/lasers.py

All three laser-constraint classes (LaserConstraints, StrictLaserConstraints,
SelectiveStrictLaserConstraints) now live in one file. Public exports
preserved via constraints/__init__.py.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Extract generator helpers to `geometry.py` and `candidates.py`

**Files:**
- Create: `src/generators/geometry.py`
- Create: `src/generators/candidates.py`
- Modify: `src/generators/constrained_random_solvable_generator.py`
- Modify: `src/generators/constructive_solvable_generator.py`
- Modify: `src/generators/constructive_cooperative_generator.py`
- Modify: `src/generators/constructive_level6_style_generator.py`
- Modify: `src/generators/random_solvable_generator.py`

- [ ] **Step 1: Create `generators/geometry.py`**

```python
"""Pure grid-geometry helpers used by generators."""

from __future__ import annotations

from lle import Direction

Position = tuple[int, int]


def direction_delta(direction: Direction) -> tuple[int, int]:
    """Return the (di, dj) delta for a Direction."""
    if direction == Direction.NORTH:
        return -1, 0
    if direction == Direction.SOUTH:
        return 1, 0
    if direction == Direction.WEST:
        return 0, -1
    return 0, 1  # EAST


def in_bounds(pos: Position, rows: int, cols: int) -> bool:
    r, c = pos
    return 0 <= r < rows and 0 <= c < cols


def points_out_immediately(
    src: Position, direction: Direction, rows: int, cols: int
) -> bool:
    dr, dc = direction_delta(direction)
    nr, nc = src[0] + dr, src[1] + dc
    return not in_bounds((nr, nc), rows, cols)


def beam_tiles(
    src: Position,
    direction: Direction,
    walls: set[Position],
    lasers: set[Position],
    rows: int,
    cols: int,
) -> list[Position]:
    """Tiles a laser beam would cover from src going direction, stopping at walls/lasers."""
    dr, dc = direction_delta(direction)
    r, c = src[0] + dr, src[1] + dc
    tiles: list[Position] = []
    while in_bounds((r, c), rows, cols):
        if (r, c) in walls or (r, c) in lasers:
            break
        tiles.append((r, c))
        r += dr
        c += dc
    return tiles
```

- [ ] **Step 2: Create `generators/candidates.py`**

```python
"""CandidateLayout: the shape sampled by generators before world-building."""

from __future__ import annotations

from dataclasses import dataclass

from lle import Direction


@dataclass(frozen=True)
class CandidateLayout:
    agents: list[tuple[int, int]]
    exits: list[tuple[int, int]]
    walls: list[tuple[int, int]]
    lasers: list[tuple[int, tuple[int, int], Direction]]  # (owner, pos, dir)
```

- [ ] **Step 3: Update `random_solvable_generator.py` to import `CandidateLayout` from `candidates.py`**

In `src/generators/random_solvable_generator.py`:
1. Delete the in-file `CandidateLayout` dataclass definition (lines 12-17).
2. Replace it with: `from generators.candidates import CandidateLayout`.

Existing `CandidateLayout` imports from `random_solvable_generator` elsewhere will still resolve because of the re-export. But to be tidy, also add at the bottom of the file:

```python
# Re-export for backwards compatibility; new code should import from generators.candidates.
__all__ = ["CandidateLayout", "RandomSolvableGenerator"]
```

- [ ] **Step 4: Update `constrained_random_solvable_generator.py` to use `geometry.py`**

In `src/generators/constrained_random_solvable_generator.py`:

1. At the top, add:
```python
from generators.geometry import beam_tiles, in_bounds, points_out_immediately
```

2. Replace the `_in_bounds`, `_delta`, `_beam_tiles`, `_points_out_immediately` methods with thin wrappers that delegate to the geometry module:

```python
def _in_bounds(self, r: int, c: int) -> bool:
    return in_bounds((r, c), self.rows, self.cols)

def _beam_tiles(self, src, direction, wall_set, laser_set):
    return beam_tiles(src, direction, wall_set, laser_set, self.rows, self.cols)

def _points_out_immediately(self, src, direction):
    return points_out_immediately(src, direction, self.rows, self.cols)
```

Drop the `_delta` method (no longer needed; geometry module owns direction_delta).

- [ ] **Step 5: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: green.

- [ ] **Step 6: Commit**

```bash
git add -A src/generators/
git commit -m "$(cat <<'EOF'
♻️ Extract generator geometry helpers and CandidateLayout to dedicated modules

Pure grid-geometry helpers (beam_tiles, in_bounds, points_out_immediately,
direction_delta) move to generators/geometry.py. CandidateLayout dataclass
moves to generators/candidates.py. Existing class methods become thin
wrappers; downstream behaviour unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Flatten generator hierarchy — rename + merge

This is the biggest task. Break into steps carefully.

**Goal:** End-state has these files in `src/generators/`:
- `base.py` — `BaseGenerator` (renamed from `base_generator.py`)
- `random.py` — `RandomGenerator` (was `RandomSolvableGenerator` + `ConstrainedRandomSolvableGenerator` merged) and the two cooperative variants `RandomCooperativeGenerator`, `ConstrainedRandomCooperativeGenerator`
- `constructive.py` — `ConstructiveGenerator` (was `ConstructiveSolvableGenerator`)
- `cooperative.py` — `CooperativeGenerator` (was `ConstructiveCooperativeGenerator`)
- `level6_style.py` — `Level6StyleGenerator` (was `ConstructiveLevel6StyleGenerator`)
- `manual.py` — `ManualGenerator` (renamed from `manual_generator.py`)
- `geometry.py`, `candidates.py`, `world_builder.py`, `registry.py` — unchanged from Task 7

**Files:**
- Rename: `src/generators/base_generator.py` → `src/generators/base.py`
- Rename: `src/generators/manual_generator.py` → `src/generators/manual.py`
- Create: `src/generators/random.py` (replaces three old files)
- Create: `src/generators/constructive.py` (replaces `constructive_solvable_generator.py`)
- Create: `src/generators/cooperative.py` (replaces `constructive_cooperative_generator.py`)
- Create: `src/generators/level6_style.py` (replaces `constructive_level6_style_generator.py`)
- Delete: `src/generators/random_solvable_generator.py`
- Delete: `src/generators/constrained_random_solvable_generator.py`
- Delete: `src/generators/random_cooperative_generator.py`
- Delete: `src/generators/constrained_random_cooperative_generator.py`
- Delete: `src/generators/constructive_solvable_generator.py`
- Delete: `src/generators/constructive_cooperative_generator.py`
- Delete: `src/generators/constructive_level6_style_generator.py`
- Modify: `src/generators/__init__.py`
- Modify: `src/tests/test_quality_guards.py`, `test_constructive_generator.py`, `test_constructive_cooperative_generator.py`, `test_profile_targeting.py`
- Modify: `src/scripts/run_profile_benchmark.py`, `src/scripts/run_rejection_benchmark.py`

- [ ] **Step 1: Rename `base_generator.py` to `base.py`**

```bash
git mv src/generators/base_generator.py src/generators/base.py
```

- [ ] **Step 2: Rename `manual_generator.py` to `manual.py`**

```bash
git mv src/generators/manual_generator.py src/generators/manual.py
```

- [ ] **Step 3: Create `random.py` merging Random + ConstrainedRandom + the two cooperative variants**

Create `src/generators/random.py`. The full content combines:
- The old `RandomSolvableGenerator` (262 LOC, becomes `RandomGenerator` with `validate_geometry: bool = True`)
- The geometric validation from `ConstrainedRandomSolvableGenerator` (now default-on, gated by the flag)
- `RandomCooperativeGenerator` (extends `RandomGenerator`, default `validate_geometry=False`)
- `ConstrainedRandomCooperativeGenerator` (extends `RandomGenerator`, default `validate_geometry=True`)

```python
"""Random-sampling generators."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from lle import World

from generators.base import BaseGenerator
from generators.candidates import CandidateLayout
from generators.geometry import beam_tiles, in_bounds, points_out_immediately
from generators.registry import register_generator
from generators.world_builder import WorldBuilder
from solver import WorldSolver

if TYPE_CHECKING:
    from solver import CooperationProfileAnalyzer  # for typing only


@register_generator("random")
class RandomGenerator(BaseGenerator):
    """
    Random world generator that samples a fully-random layout, optionally
    enforces geometric constraints (no laser-points-outside, non-zero beam,
    no exit on beam tile), and SAT-verifies solvability.
    """

    def __init__(
        self,
        size: tuple[int, int],
        agents: int = 2,
        lasers: int | None = None,
        num_walls: int | None = None,
        t_max: int | None = None,
        t_min: int = 0,
        max_attempts: int = 10_000,
        seed: int | None = None,
        validate_geometry: bool = True,
    ):
        self.rows, self.cols = size
        if self.rows < 1 or self.cols < 1:
            raise ValueError(f"grid dimensions must be >= 1. Got size={size}")
        self.area = self.rows * self.cols

        if agents < 1:
            raise ValueError(f"agents must be >= 1. Got {agents}")
        self.agents = agents
        self.lasers = (agents - 1) if lasers is None else lasers
        self.num_walls = (self.area // 10) if num_walls is None else num_walls
        self.t_max = (self.area // 2) if t_max is None else t_max
        self.t_min = t_min
        self.max_attempts = max_attempts
        self.validate_geometry = validate_geometry

        if self.lasers < 0:
            raise ValueError(f"lasers must be >= 0. Got {self.lasers}")
        if self.lasers > self.agents:
            raise ValueError(
                f"lasers must be <= agents to keep one laser source per colour "
                f"(SAT encoding assumption, see Definition 3.1). "
                f"Got lasers={self.lasers}, agents={self.agents}."
            )
        if self.num_walls < 0:
            raise ValueError(f"num_walls must be >= 0. Got {self.num_walls}")
        if self.t_max < 0:
            raise ValueError(f"t_max must be >= 0. Got {self.t_max}")
        if self.num_walls >= (self.area / 2):
            raise ValueError(
                f"num_walls must be < size/2. Got num_walls={self.num_walls}, "
                f"size={self.area}"
            )
        if self.t_min < 0:
            raise ValueError(f"t_min must be >= 0. Got {self.t_min}")
        if self.t_min > self.t_max:
            raise ValueError(
                f"t_min must be <= t_max. Got t_min={self.t_min}, t_max={self.t_max}"
            )
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1. Got {self.max_attempts}")
        total_needed = (2 * self.agents) + self.num_walls + self.lasers
        if total_needed > self.area:
            raise ValueError(
                f"layout requires {total_needed} unique cells, "
                f"but grid has only {self.area}"
            )

        self._rng = random.Random(seed)
        self.debug_rejections = False
        self.last_attempts = 0

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            "--size",
            nargs=2,
            type=int,
            metavar=("ROWS", "COLS"),
            required=True,
            help="Grid size as two integers: ROWS COLS",
        )
        parser.add_argument("--agents", type=int, default=2)
        parser.add_argument("--lasers", type=int, default=None)
        parser.add_argument("--num-walls", type=int, default=None)
        parser.add_argument("--t-max", type=int, default=None)
        parser.add_argument(
            "--t-min",
            type=int,
            default=0,
            help="Minimum number of steps required for a valid level (default: 0)",
        )
        parser.add_argument("--max-attempts", type=int, default=10_000)
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument(
            "--no-validate-geometry",
            dest="validate_geometry",
            action="store_false",
            default=True,
            help="Disable geometric validation (lasers may point outside, beams may be zero-length).",
        )
        parser.add_argument(
            "--debug-rejections",
            action="store_true",
            help="Print rejection reasons while sampling",
        )

    @classmethod
    def from_args(cls, args):
        obj = cls(
            size=tuple(args.size),
            agents=args.agents,
            lasers=args.lasers,
            num_walls=args.num_walls,
            t_max=args.t_max,
            t_min=args.t_min,
            max_attempts=args.max_attempts,
            seed=args.seed,
            validate_geometry=getattr(args, "validate_geometry", True),
        )
        obj.debug_rejections = bool(getattr(args, "debug_rejections", False))
        return obj

    # ----- sampling -----

    def _sample_unique_positions(self, k: int) -> list[tuple[int, int]]:
        all_positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        return self._rng.sample(all_positions, k)

    def _random_direction(self):
        from lle import Direction
        return self._rng.choice(
            [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
        )

    def _make_candidate_layout(self) -> CandidateLayout:
        total_needed = self.agents + self.agents + self.num_walls + self.lasers
        chosen = self._sample_unique_positions(total_needed)
        idx = 0
        agent_positions = chosen[idx : idx + self.agents]
        idx += self.agents
        exit_positions = chosen[idx : idx + self.agents]
        idx += self.agents
        wall_positions = chosen[idx : idx + self.num_walls]
        idx += self.num_walls
        laser_positions = chosen[idx : idx + self.lasers]
        lasers = [
            (i, pos, self._random_direction()) for i, pos in enumerate(laser_positions)
        ]
        return CandidateLayout(
            agents=agent_positions,
            exits=exit_positions,
            walls=wall_positions,
            lasers=lasers,
        )

    def _build_world_from_layout(self, layout: CandidateLayout) -> World:
        b = WorldBuilder(self.cols, self.rows)
        for agent_id, pos in enumerate(layout.agents):
            b.add_agent(agent_id, pos)
        for pos in layout.exits:
            b.add_exit(pos)
        for pos in layout.walls:
            b.add_wall(pos)
        for owner, pos, direction in layout.lasers:
            b.add_laser(owner, pos, direction)
        return b.build()

    # ----- validation -----

    def validate_candidate(self, layout: CandidateLayout) -> tuple[bool, str]:
        if not self.validate_geometry:
            return True, "ok"
        wall_set = set(layout.walls)
        laser_set = {pos for _, pos, _ in layout.lasers}
        exit_set = set(layout.exits)
        all_beam_tiles: set[tuple[int, int]] = set()
        for _owner, src, direction in layout.lasers:
            if points_out_immediately(src, direction, self.rows, self.cols):
                return False, f"laser_points_outside_immediately@{src}"
            tiles = beam_tiles(src, direction, wall_set, laser_set, self.rows, self.cols)
            if not tiles:
                return False, f"laser_zero_beam@{src}"
            all_beam_tiles.update(tiles)
        overlap = exit_set.intersection(all_beam_tiles)
        if overlap:
            return False, f"exit_on_laser_beam@{sorted(overlap)}"
        return True, "ok"

    # ----- SAT acceptance -----

    def _accept_world(self, world: World) -> tuple[bool, str]:
        if not self._meets_difficulty_window(world):
            return (
                False,
                f"outside_difficulty_window[t_min={self.t_min}, t_max={self.t_max}]",
            )
        return True, "satisfiable"

    def _is_satisfiable(self, world: World, t: int) -> bool:
        world.reset()
        result, _ = WorldSolver(world, T_MAX=t).solve()
        return bool(result)

    def _meets_difficulty_window(self, world: World) -> bool:
        if not self._is_satisfiable(world, self.t_max):
            return False
        if self.t_min == 0:
            return True
        return not self._is_satisfiable(world, self.t_min - 1)

    def _failure_description(self) -> str:
        return "a valid solvable world"

    def _debug_reject(self, attempt: int, reason: str) -> None:
        if self.debug_rejections:
            print(f"[reject #{attempt}] {reason}")

    def _debug_accept(self, attempt: int, reason: str) -> None:
        if self.debug_rejections:
            print(f"[accept #{attempt}] {reason}")

    def generate(self) -> World:
        self.last_attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            self.last_attempts = attempt
            layout = self._make_candidate_layout()
            valid, reason = self.validate_candidate(layout)
            if not valid:
                self._debug_reject(attempt, f"invalid_layout={reason}")
                continue
            try:
                world = self._build_world_from_layout(layout)
            except Exception as exc:
                self._debug_reject(attempt, f"lle_build_error={type(exc).__name__}")
                continue
            try:
                accepted, reason = self._accept_world(world)
                if accepted:
                    self._debug_accept(attempt, reason)
                    return world
                self._debug_reject(attempt, reason)
            except Exception as exc:
                self._debug_reject(attempt, f"solver_error={type(exc).__name__}")
                continue
        raise RuntimeError(
            f"Could not find {self._failure_description()} in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )


# ===== Cooperative random variants (thesis-only — likely not moved to LLE) =====


_COOP_PROFILE_CHOICES = (
    "cooperative",
    "asymmetric",
    "mutual",
    "chain",
    "distributed",
    "fully_coupled",
)


class _RandomCooperativeBase(RandomGenerator):
    """Shared logic for random cooperative variants — applies a profile filter."""

    def __init__(self, *args, profile: str = "cooperative", **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile

    @staticmethod
    def add_arguments(parser):
        RandomGenerator.add_arguments(parser)
        parser.add_argument(
            "--profile",
            choices=list(_COOP_PROFILE_CHOICES),
            default="cooperative",
            help="Target cooperation profile for accepted levels",
        )

    @classmethod
    def from_args(cls, args):
        obj = cls(
            size=tuple(args.size),
            agents=args.agents,
            lasers=args.lasers,
            num_walls=args.num_walls,
            t_max=args.t_max,
            t_min=args.t_min,
            max_attempts=args.max_attempts,
            seed=args.seed,
            validate_geometry=getattr(args, "validate_geometry", cls._default_validate_geometry()),
            profile=args.profile,
        )
        obj.debug_rejections = bool(getattr(args, "debug_rejections", False))
        return obj

    @staticmethod
    def _default_validate_geometry() -> bool:
        return True

    def _analyze_profile(self, world):
        from solver import CooperationProfileAnalyzer
        world.reset()
        return CooperationProfileAnalyzer(world, T_MAX=self.t_max).analyze()

    def _accept_world(self, world):
        accepted, reason = super()._accept_world(world)
        if not accepted:
            return accepted, reason
        analysis = self._analyze_profile(world)
        if not analysis.matches_profile(self.profile):
            return (
                False,
                f"profile={analysis.profile}, required={self.profile}",
            )
        return True, f"profile={analysis.profile}, cooperative_and_solvable"


@register_generator("random_cooperative")
class RandomCooperativeGenerator(_RandomCooperativeBase):
    """Random sampling (no geometric validation) + cooperation profile filter."""

    def __init__(self, *args, validate_geometry: bool = False, **kwargs):
        super().__init__(*args, validate_geometry=validate_geometry, **kwargs)

    @staticmethod
    def _default_validate_geometry() -> bool:
        return False

    def _failure_description(self) -> str:
        return "a cooperative solvable world"


@register_generator("constrained_random_cooperative")
class ConstrainedRandomCooperativeGenerator(_RandomCooperativeBase):
    """Random sampling with geometric validation + cooperation profile filter."""

    def __init__(self, *args, validate_geometry: bool = True, **kwargs):
        super().__init__(*args, validate_geometry=validate_geometry, **kwargs)

    @staticmethod
    def _default_validate_geometry() -> bool:
        return True

    def _failure_description(self) -> str:
        return "a valid constrained cooperative world"
```

- [ ] **Step 4: Create `constructive.py`**

Create `src/generators/constructive.py` containing the old `ConstructiveSolvableGenerator` renamed to `ConstructiveGenerator`. Key changes from the existing file:
- Class name: `ConstructiveSolvableGenerator` → `ConstructiveGenerator`
- Inherits from `RandomGenerator` (which now bundles the geometric validation)
- `@register_generator("constructive")` (was `"constructive_solvable"`)
- `from generators.candidates import CandidateLayout`
- Import geometry helpers from `generators.geometry`

```python
"""Constructive generator: reserves one lane per agent for a constructive solvability proof."""

from __future__ import annotations

from lle import Direction

from generators.candidates import CandidateLayout
from generators.geometry import beam_tiles, points_out_immediately
from generators.random import RandomGenerator
from generators.registry import register_generator


@register_generator("constructive")
class ConstructiveGenerator(RandomGenerator):
    """
    Reserves one disjoint lane per agent so a joint solution exists by
    construction, then places walls and lasers only outside those lanes.
    SAT is still used as a final verifier.
    """

    @classmethod
    def from_args(cls, args):
        obj = super().from_args(args)
        obj.last_attempts = 0
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_attempts = 0

    def _make_candidate_layout(self) -> CandidateLayout:
        layout = self._make_constructive_candidate_layout()
        if layout is None:
            return super()._make_candidate_layout()
        return layout

    def _make_constructive_candidate_layout(self) -> CandidateLayout | None:
        orientations = []
        if self.rows >= self.agents:
            orientations.append(("horizontal", self.area - self.agents * self.cols))
        if self.cols >= self.agents:
            orientations.append(("vertical", self.area - self.agents * self.rows))
        if not orientations:
            return None
        orientations.sort(key=lambda item: item[1], reverse=True)
        for orientation, free_cells in orientations:
            if free_cells < self.num_walls + self.lasers:
                continue
            layout = self._build_lane_layout(orientation)
            if layout is not None:
                return layout
        return None

    def _build_lane_layout(self, orientation: str) -> CandidateLayout | None:
        if orientation == "horizontal":
            lane_ids = sorted(self._rng.sample(range(self.rows), self.agents))
            agents = [(row, 0) for row in lane_ids]
            exits = [(row, self.cols - 1) for row in lane_ids]
            reserved = {(row, col) for row in lane_ids for col in range(self.cols)}
        else:
            lane_ids = sorted(self._rng.sample(range(self.cols), self.agents))
            agents = [(0, col) for col in lane_ids]
            exits = [(self.rows - 1, col) for col in lane_ids]
            reserved = {(row, col) for col in lane_ids for row in range(self.rows)}

        free_positions = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if (row, col) not in reserved
        ]
        if len(free_positions) < self.num_walls + self.lasers:
            return None
        self._rng.shuffle(free_positions)
        walls = free_positions[: self.num_walls]
        laser_pool = free_positions[self.num_walls :]

        lasers = self._place_safe_lasers(
            reserved=reserved,
            wall_positions=walls,
            candidate_positions=laser_pool,
        )
        if lasers is None:
            return None
        return CandidateLayout(
            agents=agents, exits=exits, walls=walls, lasers=lasers
        )

    def _place_safe_lasers(self, reserved, wall_positions, candidate_positions):
        walls = set(wall_positions)
        used_sources: set[tuple[int, int]] = set()
        lasers: list[tuple[int, tuple[int, int], Direction]] = []
        candidates = []
        for pos in candidate_positions:
            for direction in (
                Direction.NORTH,
                Direction.SOUTH,
                Direction.EAST,
                Direction.WEST,
            ):
                if points_out_immediately(pos, direction, self.rows, self.cols):
                    continue
                tiles = beam_tiles(
                    pos, direction, walls, used_sources, self.rows, self.cols
                )
                if not tiles:
                    continue
                if any(tile in reserved for tile in tiles):
                    continue
                candidates.append((pos, direction, tiles))
        self._rng.shuffle(candidates)
        for pos, direction, tiles in candidates:
            if len(lasers) >= self.lasers:
                break
            if pos in used_sources:
                continue
            if any(existing_pos in tiles for _, existing_pos, _ in lasers):
                continue
            if any(tile in reserved for tile in tiles):
                continue
            lasers.append((len(lasers), pos, direction))
            used_sources.add(pos)
        if len(lasers) != self.lasers:
            return None
        return lasers

    def _accept_world(self, world):
        accepted, reason = super()._accept_world(world)
        if accepted:
            return True, "constructive_satisfiable"
        return accepted, reason

    def _failure_description(self) -> str:
        return "a valid constructive solvable world"
```

- [ ] **Step 5: Create `cooperative.py`**

Create `src/generators/cooperative.py` from the existing `constructive_cooperative_generator.py` content, with these changes:
- Class name: `ConstructiveCooperativeGenerator` → `CooperativeGenerator`
- Inherits from `ConstructiveGenerator`
- `@register_generator("cooperative")` (was `"constructive_cooperative"`)
- Import path: `from generators.constructive import ConstructiveGenerator`
- Drop `LLEAdapter` usage (already done in Task 2 — verify).

```python
"""Constructive cooperative generator: enforces cooperation requirement via profile filter."""

from __future__ import annotations

from generators.constructive import ConstructiveGenerator
from generators.registry import register_generator
from solver import CooperationProfileAnalyzer


@register_generator("cooperative")
class CooperativeGenerator(ConstructiveGenerator):
    """
    Constructive solvable generator that additionally enforces a cooperation
    profile requirement. SAT is still used as the final verifier.
    """

    @staticmethod
    def add_arguments(parser):
        ConstructiveGenerator.add_arguments(parser)
        parser.add_argument(
            "--profile",
            choices=["cooperative", "asymmetric"],
            default="cooperative",
            help="Target cooperation profile for accepted levels",
        )

    @classmethod
    def from_args(cls, args):
        obj = super().from_args(args)
        obj.profile = getattr(args, "profile", "cooperative")
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = "cooperative"

    def _analyze_profile(self, world):
        world.reset()
        return CooperationProfileAnalyzer(world, T_MAX=self.t_max).analyze()

    def _accept_world(self, world):
        accepted, reason = super()._accept_world(world)
        if not accepted:
            return accepted, reason
        analysis = self._analyze_profile(world)
        if not analysis.matches_profile(self.profile):
            return (
                False,
                f"profile={analysis.profile}, required={self.profile}",
            )
        return True, f"profile={analysis.profile}, constructive_cooperative"

    def _failure_description(self) -> str:
        return "a valid constructive cooperative world"
```

- [ ] **Step 6: Create `level6_style.py`**

Create `src/generators/level6_style.py` by copying the entire content of the current `constructive_level6_style_generator.py`, then:
- Rename class `ConstructiveLevel6StyleGenerator` → `Level6StyleGenerator`
- Update `@register_generator("constructive_level6_style")` → `@register_generator("level6_style")`
- Update import: `from generators.cooperative import CooperativeGenerator` (replaces the old `ConstructiveCooperativeGenerator` import)
- Class inherits from `CooperativeGenerator`
- Update the import for `CandidateLayout` to come from `generators.candidates`
- Keep the rest of the body identical (the `_FLUSH_PROB`, `_WALL_SHAPES`, `_flush_offset`, `_cluster_shape`, `_cluster_cells`, `_make_constructive_candidate_layout`, `_place_wall_shapes`, `_failure_description` methods).

- [ ] **Step 7: Update `src/generators/__init__.py`**

Replace with:
```python
from generators.base import BaseGenerator
from generators.candidates import CandidateLayout
from generators.constructive import ConstructiveGenerator
from generators.cooperative import CooperativeGenerator
from generators.level6_style import Level6StyleGenerator
from generators.manual import ManualGenerator
from generators.random import (
    ConstrainedRandomCooperativeGenerator,
    RandomCooperativeGenerator,
    RandomGenerator,
)
from generators.registry import GENERATOR_REGISTRY, register_generator
from generators.world_builder import WorldBuilder

__all__ = [
    "BaseGenerator",
    "CandidateLayout",
    "ConstrainedRandomCooperativeGenerator",
    "ConstructiveGenerator",
    "CooperativeGenerator",
    "GENERATOR_REGISTRY",
    "Level6StyleGenerator",
    "ManualGenerator",
    "RandomCooperativeGenerator",
    "RandomGenerator",
    "WorldBuilder",
    "register_generator",
]
```

- [ ] **Step 8: Delete the obsolete generator files**

```bash
rm src/generators/random_solvable_generator.py
rm src/generators/constrained_random_solvable_generator.py
rm src/generators/random_cooperative_generator.py
rm src/generators/constrained_random_cooperative_generator.py
rm src/generators/constructive_solvable_generator.py
rm src/generators/constructive_cooperative_generator.py
rm src/generators/constructive_level6_style_generator.py
```

- [ ] **Step 9: Update tests to use new class names and import paths**

For each test file:

`src/tests/test_quality_guards.py`:
- Replace `from generators.random_solvable_generator import RandomSolvableGenerator` with `from generators.random import RandomGenerator`.
- Replace all `RandomSolvableGenerator` references with `RandomGenerator`.

`src/tests/test_constructive_generator.py`:
- Replace `from generators.constructive_solvable_generator import ConstructiveSolvableGenerator` with `from generators.constructive import ConstructiveGenerator`.
- Replace all `ConstructiveSolvableGenerator` references with `ConstructiveGenerator`.

`src/tests/test_constructive_cooperative_generator.py`:
- Replace `from generators.constructive_cooperative_generator import (ConstructiveCooperativeGenerator,)` with `from generators.cooperative import CooperativeGenerator`.
- Replace all `ConstructiveCooperativeGenerator` references with `CooperativeGenerator`.

`src/tests/test_profile_targeting.py`:
- Replace `from generators.constrained_random_cooperative_generator import ConstrainedRandomCooperativeGenerator` with `from generators.random import ConstrainedRandomCooperativeGenerator`.
- Replace `from generators.constructive_cooperative_generator import ConstructiveCooperativeGenerator` with `from generators.cooperative import CooperativeGenerator`.
- Replace `from generators.random_cooperative_generator import RandomCooperativeGenerator` with `from generators.random import RandomCooperativeGenerator`.
- Replace all `ConstructiveCooperativeGenerator` references with `CooperativeGenerator`.

- [ ] **Step 10: Update benchmark scripts**

`src/scripts/run_rejection_benchmark.py`:
- Replace the 5 generator imports at the top with:
```python
from generators.constructive import ConstructiveGenerator
from generators.cooperative import CooperativeGenerator
from generators.level6_style import Level6StyleGenerator
from generators.random import (
    ConstrainedRandomCooperativeGenerator,
    RandomGenerator,
)
```
- Replace the `GENERATOR_SPECS` dict with:
```python
GENERATOR_SPECS = {
    "random": RandomGenerator,                 # was constrained_random_solvable
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "constructive": ConstructiveGenerator,     # was constructive_solvable
    "cooperative": CooperativeGenerator,       # was constructive_cooperative
    "level6_style": Level6StyleGenerator,      # was constructive_level6_style
}
```
- Update the label dict at lines 38-42 to match the new keys:
```python
GENERATOR_LABELS = {
    "random": "Random (geom-validated)",
    "constrained_random_cooperative": "Random (geom-validated) + cooperation",
    "constructive": "Constructive (solvable)",
    "cooperative": "Constructive (cooperative)",
    "level6_style": "Constructive (Level-6 style)",
}
```
- Update lines 227-228:
```python
SOLVABLE_GENS = ["random", "constructive"]
COOPERATIVE_GENS = ["constrained_random_cooperative", "cooperative"]
```

`src/scripts/run_profile_benchmark.py`:
- Replace imports lines 25-27:
```python
from generators.cooperative import CooperativeGenerator
from generators.level6_style import Level6StyleGenerator
from generators.random import ConstrainedRandomCooperativeGenerator
```
- Update `GENERATOR_LABELS` (lines 34-36):
```python
"constrained_random_cooperative": "Random (geom-validated) + cooperation",
"cooperative": "Constructive (cooperative)",
"level6_style": "Constructive (Level-6 style)",
```
- Update `GENERATOR_SPECS` (lines 61-65):
```python
GENERATOR_SPECS = {
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "cooperative": CooperativeGenerator,
    "level6_style": Level6StyleGenerator,
}
```

- [ ] **Step 11: Update `BaseGenerator` import path (`manual.py` and `random.py` reference `generators.base_generator`)**

`src/generators/manual.py` was just renamed; open it and update the import at the top:
```python
# Before
from generators.base_generator import BaseGenerator

# After
from generators.base import BaseGenerator
```

Same check for any other generator file that still references the old module path. Run:
```bash
grep -rn "generators.base_generator" src/
```
Fix any remaining hits.

- [ ] **Step 12: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: green.

- [ ] **Step 13: End-to-end smoke test all registered generators**

```bash
python3.13 src/generate.py -n 1 random --size 6 6 --agents 2
python3.13 src/generate.py -n 1 constructive --size 6 6 --agents 2
python3.13 src/generate.py -n 1 cooperative --size 8 8 --agents 2
python3.13 src/generate.py -n 1 level6_style --size 13 13 --agents 4 --lasers 3 --t-max 21
python3.13 src/generate.py -n 1 random_cooperative --size 6 6 --agents 2 --max-attempts 200
python3.13 src/generate.py -n 1 constrained_random_cooperative --size 6 6 --agents 2 --max-attempts 200
```

Each should produce a generated level without error. If `random_cooperative` or `constrained_random_cooperative` fails to find a level within 200 attempts, that's the cooperation profile being hard to hit — bump `--max-attempts` to 500 and retry.

- [ ] **Step 14: Commit**

```bash
git add -A src/
git commit -m "$(cat <<'EOF'
♻️ Flatten generator hierarchy; rename classes and CLI registry strings

- RandomSolvableGenerator + ConstrainedRandomSolvableGenerator merge into
  RandomGenerator (validate_geometry: bool flag, default True).
- ConstructiveSolvableGenerator → ConstructiveGenerator.
- ConstructiveCooperativeGenerator → CooperativeGenerator.
- ConstructiveLevel6StyleGenerator → Level6StyleGenerator.
- RandomCooperativeGenerator and ConstrainedRandomCooperativeGenerator
  now thin subclasses of RandomGenerator with appropriate flag defaults.
- CLI registry strings updated to match new class names.
- Tests and benchmark scripts updated to use the new imports.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Public API hardening — `__all__`, relative imports, docstrings

**Files:**
- Modify: `src/solver/__init__.py`
- Modify: `src/generators/__init__.py`
- Modify: every solver/generator module that uses absolute `from solver.X import Y` or `from generators.X import Y` for intra-package imports

- [ ] **Step 1: Add `__all__` to `solver/__init__.py`**

Replace contents:
```python
"""Public API for the solver package."""

from .cooperation_solver import CooperationResult, CooperationSolver
from .profile import (
    CooperationProfileAnalyzer,
    CooperationProfileResult,
    HelperEvent,
)
from ._internal.profiler import SolverProfiler
from .world_solver import LaserMode, WorldSolver

__all__ = [
    "CooperationProfileAnalyzer",
    "CooperationProfileResult",
    "CooperationResult",
    "CooperationSolver",
    "HelperEvent",
    "LaserMode",
    "SolverProfiler",
    "WorldSolver",
]
```

- [ ] **Step 2: `generators/__init__.py` already has `__all__` from Task 8 — verify**

```bash
grep -n "__all__" src/generators/__init__.py
```

Expected: one match. If missing, add the `__all__` block from Task 8 Step 7.

- [ ] **Step 3: Switch intra-package imports in `src/solver/` to relative form**

Run:
```bash
grep -rn "from solver" src/solver/
```

For each match inside `src/solver/`, convert to a relative import:
- `from solver.constraints import X` → `from .constraints import X`
- `from solver.world_solver import X` → `from .world_solver import X`
- etc.

- [ ] **Step 4: Switch intra-package imports in `src/generators/` to relative form**

```bash
grep -rn "from generators" src/generators/
```

For each match, convert:
- `from generators.base import BaseGenerator` → `from .base import BaseGenerator`
- `from generators.candidates import CandidateLayout` → `from .candidates import CandidateLayout`
- `from generators.constructive import ConstructiveGenerator` → `from .constructive import ConstructiveGenerator`
- `from generators.registry import register_generator` → `from .registry import register_generator`
- etc.

Note: `from solver import X` stays as-is (solver is a different package from generators).

- [ ] **Step 5: Fill in missing docstrings on public classes**

Open each public class in `solver/` and `generators/` and ensure it has at least a one-line docstring. The list:
- `WorldSolver` (`src/solver/world_solver.py`)
- `LaserMode` (`src/solver/world_solver.py`)
- `CooperationSolver`, `CooperationResult` (`src/solver/cooperation_solver.py`)
- `CooperationProfileAnalyzer`, `CooperationProfileResult`, `HelperEvent` (`src/solver/profile/*.py`)
- `BaseGenerator` (`src/generators/base.py`)
- `RandomGenerator`, `RandomCooperativeGenerator`, `ConstrainedRandomCooperativeGenerator` (`src/generators/random.py`)
- `ConstructiveGenerator` (`src/generators/constructive.py`)
- `CooperativeGenerator` (`src/generators/cooperative.py`)
- `Level6StyleGenerator` (`src/generators/level6_style.py`)
- `ManualGenerator` (`src/generators/manual.py`)
- `WorldBuilder` (`src/generators/world_builder.py`)
- `CandidateLayout` (`src/generators/candidates.py`)

A class without a docstring gets one matching its existing class-level comment, or describing its purpose in one sentence. Example:

```python
class WorldSolver:
    """SAT-based solver for LLE worlds; verifies solvability within T_MAX steps."""
```

- [ ] **Step 6: Add public-API smoke test**

Create `src/tests/test_public_api.py`:
```python
"""Smoke test: every symbol in __all__ can be imported."""

import importlib


def test_solver_public_api():
    mod = importlib.import_module("solver")
    for name in mod.__all__:
        assert hasattr(mod, name), f"solver.__all__ lists {name!r} but it is missing"


def test_generators_public_api():
    mod = importlib.import_module("generators")
    for name in mod.__all__:
        assert hasattr(mod, name), f"generators.__all__ lists {name!r} but it is missing"
```

- [ ] **Step 7: Run tests and ruff**

```bash
python3.13 -m pytest src/tests/ -q
ruff check src/
```

Expected: 26 tests pass (24 existing + 2 new).

- [ ] **Step 8: Commit**

```bash
git add -A src/
git commit -m "$(cat <<'EOF'
♻️ Harden public API: __all__, relative intra-package imports, docstrings

Both solver and generators packages declare their public surface via
__all__. Intra-package imports use relative form so the packages relocate
cleanly. Every public class has at least a one-line docstring. New
test_public_api.py smoke-tests every __all__ symbol.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `thesis/notes/cooperation_profiles.md`
- Modify: `phd_pitch/proposal.typ`

- [ ] **Step 1: Update `CLAUDE.md`**

In `CLAUDE.md`:

1. Replace the architecture diagram (lines around 7-30) to reflect the new layout. Replace:
```
src/
  solver/                         SAT-based solver (pysat / Minisat22)
    world_data.py                 WorldData Protocol — solver/LLE boundary (do not break)
    adapter.py                    LLEAdapter: wraps lle.World as WorldData
    world_solver.py               WorldSolver: builds CNF model, calls SAT solver
    world_solver_strict_laser.py  Variant: agents cannot block their own color laser
    cooperation_solver.py         Detects cooperation requirement (UNSAT strict = needs cooperation)
    constraints/                  SAT constraint modules
    variables.py                  VariableFactory wrapping pysat IDPool
    model.py                      SATModel: thin CNF wrapper
    profiler.py                   SolverProfiler for timing
```
with:
```
src/
  solver/                         SAT-based solver (pysat / Minisat22)
    world_solver.py               WorldSolver with laser_mode flag (standard / strict / selective_strict)
    cooperation_solver.py         Binary "needs cooperation?" check
    profile/                      Cooperation-profile analysis
      result.py                   HelperEvent, CooperationProfileResult dataclasses
      graph_metrics.py            SCC, longest chain, synchronous width (pure functions)
      analyzer.py                 CooperationProfileAnalyzer orchestrator
    constraints/                  SAT constraint modules
    _internal/                    pysat plumbing (SATModel, VariableFactory, SolverProfiler, grid helpers)
```

2. Delete the entire `### WorldData Protocol` section (lines 55-58). Replace with:
```
### lle.World direct use

The solver imports `lle.World` directly. Grid helpers (`all_positions`,
`is_within_bounds`, `get_neighbors`) live in `solver/_internal/grid.py`.
Agent and laser-source field names are accessed via thin value-type
wrappers in `solver/_internal/types.py` (`agents_from_world`,
`laser_sources_from_world`).
```

3. Update the Generator Pattern section: replace `BaseGenerator` mentions with the renamed classes if necessary; the existing pattern description is mostly still accurate.

- [ ] **Step 2: Update `AGENTS.md`**

`AGENTS.md` mirrors `CLAUDE.md` line for line. Apply the same edits as Step 1.

- [ ] **Step 3: Update `README.md`**

In `README.md`:
- Line 89: replace `WorldSolverStrictLaser` mention with `WorldSolver(world, laser_mode=LaserMode.STRICT)`.
- Line 91: remove the `WorldData` Protocol line entirely, or replace with: "Solver takes `lle.World` directly."
- Line 97: replace `ConstrainedRandomSolvableGenerator` with `RandomGenerator` (the geometric validation is the default).

- [ ] **Step 4: Update `thesis/notes/cooperation_profiles.md`**

Line 148: replace `WorldSolverStrictLaser` with `WorldSolver` (with `laser_mode=LaserMode.STRICT`).

- [ ] **Step 5: Update `phd_pitch/proposal.typ`**

Lines 29 and 56 reference the `WorldData` Protocol as an asset. Reframe:
- Line 29: change `the #emph[WorldData]` reference to describe the generic capability without naming a specific class. Suggested phrasing: `the solver–generator infrastructure`.
- Line 56: change `Generalize the #emph[WorldData] abstraction beyond LLE` to `Re-introduce a world-data abstraction beyond LLE`, framing it as future work.

- [ ] **Step 6: Verify nothing in the repo still references removed names**

```bash
grep -rn -E 'WorldData|LLEAdapter|WorldSolverStrictLaser|WorldSolverSelectiveStrictLaser|ConstrainedRandomSolvableGenerator|ConstructiveSolvableGenerator|ConstructiveCooperativeGenerator|ConstructiveLevel6StyleGenerator|RandomSolvableGenerator' --include='*.py' --include='*.md' --include='*.typ' .
```

Expected: only matches in the spec document (`docs/superpowers/specs/...`) and git history. If any source/test/script/docs file still has a reference, fix it.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
📝 Update documentation to match solver/generator cleanup

CLAUDE.md, AGENTS.md, README.md, thesis/notes/cooperation_profiles.md and
phd_pitch/proposal.typ updated to reflect the new package layout and class
names. Removes references to WorldData, LLEAdapter, and the three
WorldSolver variants.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Final verification

- [ ] **Step 1: Full test suite**

```bash
python3.13 -m pytest src/tests/ -v
```

Expected: 26 tests pass (the public-API smoke tests plus the original 24).

- [ ] **Step 2: Lint**

```bash
ruff check src/
```

Expected: no errors.

- [ ] **Step 3: End-to-end smoke test all registered generators**

```bash
python3.13 src/generate.py -n 1 random --size 6 6 --agents 2
python3.13 src/generate.py -n 1 constructive --size 6 6 --agents 2
python3.13 src/generate.py -n 1 cooperative --size 8 8 --agents 2
python3.13 src/generate.py -n 1 level6_style --size 13 13 --agents 4 --lasers 3 --t-max 21
python3.13 src/generate.py -n 1 random_cooperative --size 6 6 --agents 2 --max-attempts 500
python3.13 src/generate.py -n 1 constrained_random_cooperative --size 6 6 --agents 2 --max-attempts 500
```

Each must produce a valid level without error.

- [ ] **Step 4: Confirm git status**

```bash
git status
git log --oneline -15
```

Working tree clean (modulo any unstaged untracked dirs unrelated to this refactor). The new commits are at the top: one per task (~11 commits).

- [ ] **Step 5: No final commit needed**

This task is verification only; no new files to commit. If `git status` is dirty from a missed change, fix and amend the appropriate task's commit (or add a follow-up commit).

---

## Self-review notes

- The CLI `random` registry name introduces a new behaviour: `--no-validate-geometry` flag. Documented in Step 8.3.
- The two cooperative random variants (`RandomCooperativeGenerator`, `ConstrainedRandomCooperativeGenerator`) keep their old CLI names (`random_cooperative`, `constrained_random_cooperative`) — only the underlying class names changed.
- `BaseGenerator` import path changes from `generators.base_generator` to `generators.base`. Internal-only — no external scripts reference it.
- The spec mentions `agents_from_world` and `laser_sources_from_world` as helpers; both are defined in `solver/_internal/types.py` (Task 2 Step 2).
- All generator files use `from .X import Y` after Task 9 Step 4, removing dependence on `src/` being on `sys.path` for intra-package imports.
