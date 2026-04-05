# AGENTS.md — Rules and Guidance for AI Agents

## Project Orientation

Python research project implementing procedural level generation for LLE (Laser Learning Environment) using SAT-based solvability guarantees. See CLAUDE.md for full architecture.

## Rules

- Run `pytest src/tests/` after any code change and ensure all tests pass before finishing.
- Run `ruff check src/` and resolve all lint errors before finishing.
- Do not modify files outside `src/` except README.md and top-level config files.
- Never touch: `presentation/MLG-Student-Day/`, `first_try/`, `results/`.

## Architecture Guidance

### WorldData is the solver/LLE boundary — do not break it
`src/solver/world_data.py` defines the `WorldData` Protocol. The solver depends only on this interface. Never add `lle` imports inside the solver package. Implement `WorldData` for new level sources; do not subclass it.

### Adding a generator
1. Create `src/generators/my_generator.py` extending `BaseGenerator`.
2. Decorate the class with `@register_generator("my_name")`.
3. Implement `from_args(cls, args)` classmethod for CLI wiring.
4. Add CLI arguments in `add_arguments(parser)`.

### Adding a constraint
1. Create a module in `src/solver/constraints/`.
2. Implement the `Constraint` ABC with a `generate()` method that yields CNF clauses.
3. Compose it in `WorldSolver` or `WorldSolverStrictLaser` as appropriate.

### Cooperation detection
Use `CooperationSolver` from `src/solver/cooperation_solver.py`. Do not reimplement the standard+strict dual-solver pattern elsewhere.

## Future Work (not yet implemented)

A cooperation metrics analyzer is planned. It will define cooperation quality metrics such as "all agents must block at least one laser" or "laser blocking is on the critical path". The metrics need to be formally defined before implementation — do not implement prematurely.
