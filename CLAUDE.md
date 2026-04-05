# CLAUDE.md — Project Guide for AI Agents

## Project Purpose

Procedural generation of solvable, cooperative levels for the Laser Learning Environment (LLE), a multi-agent reinforcement learning benchmark. The project uses SAT solving to guarantee solvability and cooperation properties during generation.

## Architecture

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
  generators/                     Level generators
    base_generator.py             Abstract BaseGenerator
    registry.py                   @register_generator decorator + generator lookup
    world_builder.py              Programmatic lle.World construction
    random_solvable_generator.py
    constrained_random_solvable_generator.py
    random_cooperative_generator.py
    constrained_random_cooperative_generator.py
    manual_generator.py
  benchmark/                      Benchmarking runner, plots, report generation
  scripts/                        Demo and utility scripts
  tests/                          pytest test suite
  cli.py                          CLI argument parser builder
  generate.py                     CLI entry point (main())
  levels.py                       LLE default levels registry
```

## Python Version

Python 3.13 is required (`requires-python = ">=3.13"` in `pyproject.toml`).

## Development Commands

```bash
pytest src/tests/
ruff check src/
cd src && python generate.py random_solvable --size 5 5 --agents 2
cd src && python generate.py random_cooperative --size 6 6 --agents 2
```

## Key Design Decisions

### WorldData Protocol
`WorldData` is a structural Protocol that decouples the solver from LLE entirely. The solver never imports `lle` directly. `LLEAdapter` bridges `lle.World` to `WorldData`. New level sources must implement this Protocol.

### Cooperation Definition
A level requires cooperation iff: standard solver SAT **and** strict laser solver UNSAT. Strict semantics = agents cannot block a laser of their own color.

### SAT Encoding
Levels encoded as CNF over timesteps `T=0..T_MAX`. Variables represent agent positions, laser states, and beam propagation per timestep.

### Generator Pattern
Extend `BaseGenerator`, register with `@register_generator`, expose `from_args(cls, args)` classmethod for CLI wiring.

### Constraint Pattern
`Constraint` ABC with `generate()` that yields CNF clauses. Composed by `WorldSolver`.

## Off-Limits Directories

- `presentation/MLG-Student-Day/` — read-only, do not modify
- `first_try/` — old generated outputs, ignore
- `results/` — benchmark results, do not modify programmatically
