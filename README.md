# Procedural Generation of Solvable Cooperative Levels for the Laser Learning Environment

### Master Thesis — Hugo Charels (ULB, 2025–2026)

This repository contains the code, the experiments, and the Typst source of my master thesis:

> **Procedural Generation of Solvable Cooperative Levels for the Laser Learning Environment**

The work targets the [Laser Learning Environment (LLE)][lle], a 2D cooperative grid-based
benchmark for Multi-Agent Reinforcement Learning (MARL). The thesis develops a SAT-based level
generator that produces levels which are (i) provably solvable by some joint trajectory,
(ii) provably requiring cooperation in a precise sense, and (iii) configurable along every axis
that matters for an experimental study: grid size, number of agents, number and orientation of
lasers, wall budget, cooperation profile, generator family, time horizon. The thesis then asks
whether such levels, arranged as a curriculum, help off-the-shelf MARL agents reach the
hand-crafted LLE Level 6; for the value-based methods tested (IQL, VDN, QMIX), they do not, a
negative result the thesis traces to the base task being unlearnable by these methods.

[lle]: https://github.com/yamoling/lle

---

## Research Questions

The thesis is structured around six research questions.

- **RQ1 — Solvability verification.** How can we formally verify that a level is solvable, by
  encoding bounded-horizon LLE solvability as a single SAT formula?
- **RQ2 — Cooperation verification.** How can we formally verify that a level genuinely
  requires cooperation rather than admitting independent solutions, using a strict-laser
  counterfactual on top of the same encoding?
- **RQ3 — Solver-in-the-loop generation.** How can both decision procedures be embedded inside
  a procedural generator so that every accepted level comes with certified properties?
- **RQ4 — Profile-targeted generation.** Can we control the *kind* of cooperation a generated
  level exhibits — asymmetric, mutual, chain, distributed, or fully coupled — beyond the binary
  "is cooperation required" criterion?
- **RQ5 — Training on generated levels.** Can MARL agents trained exclusively on procedurally
  generated levels learn the cooperative behaviour the levels are designed to elicit, and does
  that behaviour transfer to human-designed levels?
- **RQ6 — Curriculum learning.** Can the controllability of the generator be exploited to
  organise levels into a curriculum that accelerates learning on the hand-crafted LLE Level 6
  target?

RQ1 and RQ2 are addressed in the SAT-encoding and cooperation-detection chapters of the thesis.
RQ3 and RQ4 are the procedural-generators chapter together with the rejection / profile
benchmarks. RQ5 and RQ6 are the empirical chapter (5×5 learnability rerun and curriculum-
transfer experiment).

---

## Using the Generator Without This Repo

The SAT solver, the cooperation detector, and the level generators are also implemented inside
the LLE Python package, so **for level generation alone you do not need to clone this
repository**. Install LLE from PyPI:

```bash
pip install laser-learning-environment[generator]
```

and use its built-in CLI / API. See <https://github.com/yamoling/lle> for the upstream
documentation. The upstream API mirrors the structure exposed in `src/generators/` and
`src/solver/` of this repository.

This repository is needed only for: reproducing the experiments of the thesis, building the
thesis PDF, and running the rejection / profile / learnability / curriculum-transfer
benchmarks end-to-end.

---

## What This Repository Contains

```
src/
  solver/         SAT encoding, cooperation detector, profile analyzer
  generators/    Registry-based generator framework
  benchmark/     Rejection-rate and profile benchmarks + plotting
  experiments/   Learnability and curriculum-transfer experiment runners
  scripts/       Demo and utility scripts (rendering, audits, etc.)
  tests/         pytest test suite
  cli.py         CLI argument parser
  generate.py    CLI entry point
  levels.py      LLE hand-crafted levels registry
thesis/          Typst sources of the thesis (compiled to thesis/main.pdf)
results/         Generated levels, benchmark CSVs, training runs, figures
scripts/         Repository-level utility scripts
```

### SAT Solver

- CNF encoding of LLE levels over the timestep set `T = 0 .. T_max`.
- `WorldSolver(world, T_MAX, laser_mode=…)` selects the laser semantics:
  - `LaserMode.STANDARD` — the standard LLE rule (same-colour agents truncate the matching
    beam),
  - `LaserMode.STRICT` — same-colour agents no longer truncate,
  - `LaserMode.SELECTIVE_STRICT` — strict for a chosen colour subset, standard for the rest.
- `CooperationSolver` runs the two-call binary criterion (standard SAT *and* strict UNSAT).
- `CooperationProfileAnalyzer` returns a richer label
  (`independent`, `cooperative`, `asymmetric`, `mutual`, `chain`, `distributed`,
  `fully_coupled`) by combining one standard SAT model with one selective-strict
  counterfactual per colour.

### Level Generators

All generators register themselves through `@register_generator`, share a common CLI surface,
and produce an `lle.World`. They differ in how they sample the candidate layout *before* SAT
verifies it.

- `random` — uniform random sampling with geometric pre-validation.
- `random_cooperative` — random sampling (no geometric validation) plus a cooperation-profile filter.
- `constrained_random_cooperative` — random sampling with geometric validation plus a
  cooperation-profile filter.
- `constructive` — lane-based layout that admits one solution by construction.
- `cooperative` — the constructive generator plus the cooperation requirement and profile filter
  (cheap, near-zero rejection).
- `level6_style` — clustered start / exit blocks inspired by LLE Level 6.
- `manual` — a hardcoded, deterministic level.

Every generator exposes the same axes: `--size`, `--agents`, `--lasers`, `--num-walls`,
`--t-max`, `--seed`, plus generator-specific flags (notably `--profile` for the cooperative
generators).

### Experiments

- `src/experiments/learnability/` — train IQL, VDN, QMIX on pools from the cooperative generator,
  measure success on a held-out pool, and sweep the training-pool size.
- `src/experiments/curriculum_strategy/` — curriculum-ordering study (direct / forward / reverse /
  mixed) on a reachable cooperative target.
- `src/experiments/curriculum_strategy_2L/` — the same schedules ramped toward a two-laser mutual
  target.
- `src/experiments/curriculum/` — the transfer-to-Level-6 experiment with the B1 / B2 / B3 / CURR
  conditions.
- `src/experiments/curriculum_learnability/` — supporting curriculum-learnability runs.

Each experiment directory carries its own configuration, runner, and plotting scripts. Level pools
are generated once and reused across all seeds.

### Benchmarks

- `results/rejection_benchmark/` — acceptance rate of each generator across configurations.
- `results/profile_benchmark/` — distribution of cooperation profiles across generated pools.
- `results/learnability_5x5/` — training-curve and final success-rate plots for the 5×5
  learnability rerun.
- `results/cooperation_examples/` — one hand-crafted level per cooperation-profile family,
  rendered to PNG for the thesis figures.

---

## Getting Started

### Install

```bash
pip install -e .
```

The repository targets Python ≥ 3.12. The cluster experiments additionally pin Python 3.12
inside the Docker image so that PyTorch 2.3.x ships sm_61 (GTX 1080 Ti) kernels.

### Generate a single level

```bash
cd src

# Plain solvable random level
python generate.py random --size 5 5 --agents 2

# Cooperative level with a target profile
python generate.py cooperative --size 7 7 --agents 3 --lasers 2 --profile chain

# Constructive cooperative level (lane-based, near-zero rejection)
python generate.py cooperative --size 6 6 --agents 2 --lasers 1

# Save level files (and PNG renders) under a chosen folder
python generate.py cooperative --size 6 6 --agents 2 --lasers 1 --save results/cooperative_samples
```

### Run the test suite and linter

```bash
pytest src/tests/
ruff check src/
```

### Build the thesis

```bash
typst compile --root . thesis/main.typ
```

The compiled PDF lands at `thesis/main.pdf`.

---

## Repository Conventions

- Generated benchmark and training outputs land under `results/<experiment>/`. Code paths
  reference relative paths from the repository root.
- Sample generator outputs intended for documentation go under
  `results/<generator>_samples/`, not at the repository root.
- Read-only directories — `presentation/MLG-Student-Day/`, `preparatory_work/`, `first_try/` —
  contain earlier deliverables and should not be modified.

---

## License

Developed for academic research as a master thesis at ULB (2025–2026).
