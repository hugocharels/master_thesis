# CLAUDE.md — Project Guide for AI Agents

## Project Purpose

This is a **Master Thesis in Computer Science** (ULB, 2025–2026) by Hugo Charels, supervised by Tom Lenaerts and Yannick Molinghen.

The subject is procedural generation of solvable, cooperative levels for the Laser Learning Environment (LLE), a multi-agent reinforcement learning benchmark. The project uses SAT solving to guarantee solvability and cooperation properties during generation.

## Architecture

```
src/
  solver/                         SAT-based solver (pysat / Minisat22)
    world_solver.py               WorldSolver with laser_mode param (standard / strict / selective_strict)
    cooperation_solver.py         Binary "needs cooperation?" check
    profile/                      Cooperation-profile analysis
      result.py                   HelperEvent, CooperationProfileResult dataclasses
      graph_metrics.py            SCC, longest chain, synchronous width (pure functions)
      analyzer.py                 CooperationProfileAnalyzer orchestrator
    constraints/                  SAT constraint modules
    _internal/                    pysat plumbing (SATModel, VariableFactory, SolverProfiler, grid + value helpers)
  generators/                     Level generators
    base.py                       Abstract BaseGenerator
    registry.py                   @register_generator decorator + generator lookup
    world_builder.py              Programmatic lle.World construction
    geometry.py                   Pure grid-geometry helpers (beam_tiles, etc.)
    candidates.py                 CandidateLayout dataclass
    random.py                     RandomGenerator + thesis-only Random{,Constrained}Cooperative variants
    constructive.py               ConstructiveGenerator (lane-based)
    cooperative.py                CooperativeGenerator (cooperation profile filter)
    level6_style.py               Level6StyleGenerator (clustered starts/exits, LLE Level 6 inspired)
    manual.py                     ManualGenerator
  benchmark/                      Benchmarking runner, plots, report generation
  scripts/                        Demo and utility scripts
  tests/                          pytest test suite
  cli.py                          CLI argument parser builder
  generate.py                     CLI entry point (main())
  levels.py                       LLE default levels registry
```

## Python Version

Python 3.13 is required (`requires-python = "=3.13"` in `pyproject.toml`).

## Development Commands

```bash
python3.13 -m pytest
ruff check src/
python3.13 src/generate.py random --size 5 5 --agents 2
python3.13 src/generate.py level6_style --size 13 13 --agents 4 --lasers 3 --t-max 21
```

## Key Design Decisions

### Direct lle.World use

The solver imports `lle.World` directly. Grid helpers (`all_positions`,
`is_within_bounds`, `get_neighbors`) live in `solver/_internal/grid.py`.
Agent and laser-source field names are accessed via thin value-type
adapters in `solver/_internal/types.py` (`agents_from_world`,
`laser_sources_from_world`).

### Cooperation Definition

A level requires cooperation iff: standard solver SAT **and** strict laser solver UNSAT. Strict semantics = agents cannot block a laser of their own color.

### SAT Encoding

Levels encoded as CNF over timesteps `T=0..T_MAX`. Variables represent agent positions, laser states, and beam propagation per timestep.

### Generator Pattern

Extend `BaseGenerator` (in `generators/base.py`), register with `@register_generator`, expose `from_args(cls, args)` classmethod for CLI wiring. Key generators: `RandomGenerator`, `ConstructiveGenerator`, `CooperativeGenerator`, `Level6StyleGenerator`, `ManualGenerator`. Geometric validation is enabled by default in `RandomGenerator` (replaces the old `ConstrainedRandomSolvableGenerator`). Strict-laser mode is selected via `WorldSolver(world, laser_mode=LaserMode.STRICT)` rather than a separate class.

### Constraint Pattern

`Constraint` ABC with `generate()` that yields CNF clauses. Composed by `WorldSolver`.

## Thesis and Writing

The thesis report is written in **Typst** and lives in `thesis/`:

- `thesis/main.typ` — main document (structure, chapters)
- `thesis/chapters/sat_reduction.typ` — SAT encoding chapter (the only written chapter so far)
- `thesis/bibliography.bib` — references

**Mathematical rigor is critical.** When editing thesis files: all formulas must be unambiguous, variable indices must be consistent, quantifiers must be precise (correct domains, correct time ranges), and prose must use "we" (not "I"). Every formula should be verifiable by a CS professor.

`preparatory_work/` contains earlier Typst documents (preparatory report and slides). Do not modify these.

## Off-Limits Directories

- `presentation/MLG-Student-Day/` — read-only, do not modify
- `preparatory_work/` — read-only, do not modify
- `first_try/` — old generated outputs, ignore
- `results/` — benchmark results, do not modify programmatically
