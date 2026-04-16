== Context

Cooperative Multi-Agent Reinforcement Learning (MARL) studies settings in which several agents
must learn behaviours whose value appears only at the team level. In such settings, the environment
is not a neutral container: it determines which coordination patterns are possible, which ones are
necessary, and how difficult they are to discover.

This dependence on environment structure is especially strong in sparse-reward cooperative tasks.
When reward is issued only after the team objective has been achieved, a training level is useful
only if it exposes a meaningful coordination challenge while remaining actually solvable.
Unsolvable levels provide no valid signal, and levels that admit independent solutions fail to test
the cooperative mechanism they are meant to study.


== Motivation

The Laser Learning Environment (LLE) @LLE is a particularly relevant case study because its laser
mechanics create explicit inter-agent dependencies. One agent may need to occupy the path of its own
laser so that another agent can pass. This makes LLE a natural benchmark for studying
coordination-critical tasks, but it also makes level design difficult: a useful level should not
merely appear cooperative, it should provably contain the intended dependency.

Procedural Content Generation (PCG) offers a way to scale level creation, but only if the generated
instances satisfy the properties that matter for training. In the present setting, two properties
are central. First, a level must be *solvable*. Second, success should *require cooperation* in the
specific sense induced by the LLE laser mechanics. Without those guarantees, generation risks
producing levels that are invalid, trivial, or misaligned with the benchmark objective.


== Research Questions and Scope

This thesis addresses the following question: how can we automatically generate LLE levels that are
provably solvable and that provably require the blocking-based cooperative interaction studied in
the benchmark?

More precisely, the work is organised around three research questions:

- *RQ1:* How can bounded-horizon solvability of an LLE level be formalised as a decision problem and
  reduced to Boolean Satisfiability (SAT)?
- *RQ2:* How can the cooperation mechanism of interest in LLE be turned into a formally decidable
  property rather than an informal design intuition?
- *RQ3:* How can these decision procedures be embedded inside procedural generators so that accepted
  levels come with formal guarantees?

The thesis focuses on a restricted but explicit subset of the LLE mechanics. The formal model
includes walls, start positions, exits, laser sources, beam propagation, and same-colour blocking.
Additional benchmark mechanics such as gems and void tiles are outside the scope of the formal
guarantees developed here. Likewise, the thesis does not claim to solve the downstream MARL problem
of training agents on the generated levels. Its contribution is on the generation and certification
side.


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

- *A solver-in-the-loop generation framework.* Building on the solver and cooperation detector, we
  implement six generators: random solvable, constrained random solvable, random cooperative,
  constrained random cooperative, constructive solvable, and constructive cooperative. Each accepted
  level is certified by the solver to satisfy the advertised properties of its output
  (<generators>).

- *An empirical comparison of two SAT formulations.* We compare two alternative encodings of the
  agent-uniqueness constraint on four benchmark levels, measuring their effect on CNF size, model
  generation time, and solver runtime (<benchmarking>, <experiments>).

The broader methodological idea is to couple procedural generation with formal verification. In the
present thesis, that idea is instantiated for LLE and for the specific cooperation mechanism induced
by coloured laser blocking.


== Thesis Structure

The remainder of this thesis is organised as follows.

Chapter 2 positions the work relative to the LLE benchmark, procedural generation, and
compilation-based multi-agent planning literature. Chapter 3 introduces the modeled subset of LLE,
formalises bounded-horizon solvability, and presents the SAT reduction and evaluation protocol.
Chapter 4 presents the original contribution of the thesis: the cooperation detector and the
generator family built around it. Chapter 5 reports the current experimental results on alternative
SAT encodings. Chapter 6 concludes with limitations and future work.
