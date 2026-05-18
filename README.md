# Procedural Generation of Solvable Cooperative Levels for Curriculum Learning in LLE

### Master Thesis — Hugo Charels (ULB, 2025–2026)

This repository contains the code, the experiments, and the Typst source of my master thesis:

> **Procedural Generation of Solvable Cooperative Levels for Curriculum Learning in the Laser Learning Environment**

The work targets the [Laser Learning Environment (LLE)][lle], a 2D cooperative grid-based
benchmark for Multi-Agent Reinforcement Learning (MARL). The thesis develops a SAT-based level
generator that produces levels which are (i) provably solvable by some joint trajectory,
(ii) provably requiring cooperation in a precise sense, and (iii) configurable along every axis
that matters for an experimental study — grid size, number of agents, number and orientation of
lasers, wall budget, cooperation profile, generator family, time horizon. The end goal is to
use those levels as the building blocks of a curriculum that brings off-the-shelf MARL agents
up to the hand-crafted LLE Level 6.

[lle]: https://github.com/yamoling/lle

---

## Research Questions

The thesis is structured around four research questions.

- **RQ1 — Encoding.** How can solvability of an LLE level under a fixed horizon `T_max` be
  encoded as a single SAT formula, in a way that is both sound and modular over the
  laser-propagation rules?
- **RQ2 — Cooperation detection.** Can a binary "this level requires cooperation" property be
  expressed as the conjunction of two SAT calls, and refined into a richer profile
  (asymmetric, mutual, chain, distributed, fully coupled) using counterfactual selective-strict
  semantics?
- **RQ3 — Procedural generation.** Given the encoding of RQ1 and the cooperation criterion of
  RQ2, how can we sample cooperative levels that are diverse along well-defined axes
  (geometry, cooperation profile, solution length) while keeping rejection rates manageable?
- **RQ4 — Curriculum transfer.** Do generated levels accelerate or unlock learning on the
  hand-crafted LLE Level 6 target, compared to MARL baselines trained directly on the target?

RQ1 and RQ2 are addressed in the SAT-encoding and cooperation-detection chapters of the thesis.
RQ3 is the procedural-generators chapter together with the rejection / profile benchmarks. RQ4
is the empirical chapter (5×5 learnability rerun and curriculum-transfer experiment).

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
- `cooperative` — `random` plus a binary cooperation filter and an optional cooperation-profile
  target.
- `constructive` — lane-based layout that admits one solution by construction.
- `constructive_cooperative` — `constructive` plus the cooperation filter and profile target.
- `level6_style` — clustered start / exit blocks inspired by LLE Level 6.
- `manual` — load a level from a JSON or text world string.

Every generator exposes the same axes: `--size`, `--agents`, `--lasers`, `--num-walls`,
`--t-max`, `--seed`, plus generator-specific flags (notably `--profile` for the cooperative
generators).

### Experiments

- `src/experiments/learnability/` — train IQL, VDN, QMIX on pools generated by the cooperative
  generator and measure success on a held-out pool of the same family.
- `src/experiments/curriculum_learnability/` — same algorithms, trained over a 4-stage
  curriculum (5×5 → 6×6 → 7×7 → 8×8) of growing difficulty.
- `src/experiments/curriculum/` — RQ4 transfer-to-Level-6 experiment with the four conditions
  B1 / B2 / B3 / CURR.

Each experiment has its own `configs.py`, `run_experiment.py`, and `plot_results.py`. Pools
are generated once by `pool_generator.py` and reused across all seeds.

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

# Constructive cooperative level (lane-based, faster acceptance)
python generate.py constructive_cooperative --size 6 6 --agents 2 --lasers 1

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

Developed for academic research. A formal licence will be attached on thesis submission.
