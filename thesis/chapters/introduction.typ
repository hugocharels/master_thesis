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

In cooperative environments whose mechanics create explicit inter-agent dependencies, level design
is particularly challenging. A useful training level should not merely appear cooperative — it
should provably contain the intended coordination structure.

Procedural Content Generation (PCG) offers a way to scale level creation beyond what manual design
allows, but only if the generated instances satisfy the properties that matter for training. Two
properties are central. First, a level must be *solvable*. Second, success should *require
cooperation* in the specific sense induced by the environment's mechanics. Without those
guarantees, generation risks producing levels that are invalid, trivial, or misaligned with the
training objective.


== Research Questions and Scope

This thesis addresses the following question: how can we automatically generate levels for a
cooperative MARL environment that are provably solvable and provably require the target cooperative
interaction?

More precisely, the work is organised around five research questions:

- *RQ1:* How can we formally verify that a level is solvable by the agents?
- *RQ2:* How can we formally verify that solving a level genuinely requires cooperation between
  agents, rather than allowing independent solutions?
- *RQ3:* How can formal verification be embedded inside a procedural generator so that every
  accepted level comes with certified properties?
- *RQ4:* Can agents trained exclusively on procedurally generated levels transfer their behaviour
  to human-designed levels?
- *RQ5:* Can we control the cooperation structure of generated levels by targeting specific
  profiles such as asymmetric, mutual, chain, distributed, or fully coupled dependencies?

The thesis instantiates this framework on one concrete cooperative environment, focusing on a
restricted but explicit subset of its mechanics. The formal model covers agent movement,
inter-agent blocking interactions, and a bounded-horizon solvability criterion. Additional
environment mechanics are outside the scope of the formal guarantees developed here. The broader
methodology — coupling procedural generation with a formal verification oracle — is
environment-agnostic: it applies to any setting where the target properties are expressible as
decision problems.


== Contributions

This thesis makes the following contributions:

- *A decision procedure for bounded-horizon solvability.* We provide a propositional encoding of
  the solvability decision problem over a bounded time horizon. The procedure either returns a
  certificate — a valid joint trajectory — or proves that no such trajectory exists within the
  chosen horizon (@sat-reduction).

- *A formal cooperation detector.* We define a strict variant of the environment semantics in
  which agents cannot exploit same-agent blocking to bypass constraints imposed by others. A level
  requires cooperative interaction if and only if it is solvable under standard semantics and
  unsolvable under the strict variant (@cooperation-detection).

- *A solver-in-the-loop generation framework.* Building on the solver and cooperation detector, we
  implement six generators across two property families — solvable and cooperative. Each accepted
  level is certified by the solver to satisfy the advertised property (@generators).

- *A cooperation profile taxonomy and profile-targeted generation.* We define a set of cooperation
  profiles — asymmetric, mutual, chain, distributed, fully coupled — that characterise the
  dependency structure of cooperative levels. Generators can target a specific profile, producing
  levels whose cooperation type is controlled, not merely certified (@cooperation-detection,
  @generators).

- *An empirical evaluation.* We compare two alternative propositional encodings of the
  agent-uniqueness constraint, measuring their effect on formula size and solver runtime. We also
  measure generator acceptance rates and cooperation profile distributions across grid sizes
  (@benchmarking, @experiments).


== Thesis Structure

The remainder of this thesis is organised as follows.

Chapter 2 positions the work relative to cooperative MARL benchmarks, procedural content
generation, and compilation-based planning literature. Chapter 3 introduces the environment model
and formalises bounded-horizon solvability and the cooperation requirement. Chapter 4 presents the
experimental work in two parts: Part 1 develops the original contribution — the SAT encoding, the
cooperation detector, the cooperation profile taxonomy, and the generator family; Part 2 reports
the results of the evaluation experiments. Chapter 5 concludes with a summary and future work.
