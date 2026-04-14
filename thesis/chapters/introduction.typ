== Context

Cooperative Multi-Agent Reinforcement Learning (MARL) studies settings in which several agents
must learn behaviours that succeed only through coordination. In such settings, the environment is
not merely a benchmark container: its structure determines which coordination patterns are possible,
which ones are necessary, and how difficult they are to discover.

This dependence on environment design is especially strong in sparse-reward cooperative tasks.
When reward is issued only after a full joint objective has been achieved, a training level is
useful only if it exposes a meaningful coordination challenge while remaining actually solvable.
Levels that are unsolvable, trivial, or solvable without genuine inter-agent dependence provide
poor training signal and limit what the agents can learn.


== Motivation

Procedural Content Generation (PCG) offers a way to scale environment design, but only if the
generated instances satisfy the properties that matter for training. In the present setting, two
properties are central.

First, a level must be *solvable*: the agents must admit at least one valid joint execution that
reaches the exits. Second, a level should *require cooperation*: success should depend on at least
one agent enabling another agent's progress, rather than on several agents independently solving
parallel subproblems.

This thesis studies these questions in the Laser Learning Environment (LLE) @LLE, a 2D cooperative
benchmark whose laser mechanics create explicit inter-agent dependencies. LLE is a useful case
study because its grid structure is simple enough to formalise, yet rich enough to express
non-trivial cooperative bottlenecks.


== Problem Statement

The central problem this thesis addresses is the following: how can we automatically generate LLE
levels that are provably solvable and provably require inter-agent cooperation?

We target two formal properties and one broader design objective:

+ *Solvability* - the level admits at least one valid joint action sequence through which the
  agents collectively occupy all exit tiles. This is a necessary baseline: a level that cannot be
  completed is useless for training.

+ *Cooperation requirement* - the level cannot be solved without at least one agent performing a
  cooperative act, namely using same-colour occupancy to make a teammate's path traversable. This
  property ensures that the level is not trivially solvable by independent agent behaviour.

+ *Learnability* - the generated instances should expose coordination patterns that are plausible
  training signals for MARL algorithms. Unlike solvability and cooperation, learnability is not
  formalised or certified in this thesis; we treat it as a design objective and discuss it in
  terms of structural affordances that may facilitate exploration.

The approach we adopt to address the first two properties is a reduction to Boolean
Satisfiability (SAT): we encode the constraints of an LLE level as a propositional formula in
conjunctive normal form (CNF), and delegate the decision procedure to a modern SAT solver. The
generation algorithms then use these SAT checks as acceptance criteria.


== Contributions

This thesis makes the following contributions:

- *A SAT-based solver for bounded-horizon LLE solvability.* We provide a CNF encoding of the LLE
  decision problem over a bounded time horizon. The solver either returns a satisfying assignment
  encoding a valid joint trajectory or certifies that no such trajectory exists within the chosen
  horizon (<sat-reduction>).

- *A formal cooperation detector.* We define a strict variant of the LLE beam semantics in which
  agents can no longer use same-colour occupancy to truncate their own beams. We show that a level
  requires this blocking-based cooperative action if and only if the standard encoding is
  satisfiable and the strict encoding is unsatisfiable (<cooperation-detection>).

- *A family of procedural level generators.* Building on the solver and cooperation detector, we
  implement six generators: random solvable, constrained random solvable, random cooperative,
  constrained random cooperative, constructive solvable, and constructive cooperative. Each
  accepted level is certified by the solver to satisfy the advertised properties of its output
  (<generators>).

- *An empirical comparison of two SAT formulations.* We compare two alternative encodings of the
  agent-uniqueness constraint on four benchmark levels, measuring their effect on CNF size, model
  generation time, and solver runtime (<benchmarking>, <experiments>).

The resulting framework is specific to LLE at the encoding level, but the broader methodology is
more general: formalise the desired level properties, decide them with a solver, and place that
verifier inside the generation loop.


== Thesis Structure

The remainder of this thesis is organised as follows.

Chapter 2 introduces only the background needed for the rest of the thesis. Chapter 3 positions
the work relative to prior literature. Chapter 4 presents the formalisation, SAT reduction,
cooperation detector, generators, and benchmarking protocol. Chapter 5 reports the experimental
results. Chapter 6 concludes.
