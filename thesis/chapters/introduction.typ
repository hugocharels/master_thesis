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

In this thesis we work with the Laser Learning Environment (LLE), a 2D grid-based cooperative
MARL benchmark in which agents of distinct colours must shield one another from same-coloured
laser beams to reach their exits. LLE is the concrete environment used throughout, but the
methodology developed here — coupling procedural generation with a formal verification oracle —
is environment-agnostic: it applies to any MARL setting where the target properties are
expressible as decision problems.


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

Generated levels are also useful beyond standalone training: the same configuration knobs that
control individual levels — grid size, number of agents, number of lasers, wall budget,
cooperation profile, horizon — also define a natural difficulty axis. A formally-verified
generator is therefore a candidate building block for *curriculum learning*: rather than train
directly on a hard hand-crafted target, an agent can be trained on a sequence of progressively
harder generated levels.


== Research Questions and Scope

This thesis addresses the following question: how can we automatically generate levels for a
cooperative MARL environment that are provably solvable and provably require the target
cooperative interaction, and how can such levels be used to support MARL training?

More precisely, the work is organised around six research questions:

- *RQ1:* How can we formally verify that a level is solvable by the agents?
- *RQ2:* How can we formally verify that solving a level genuinely requires cooperation between
  agents, rather than allowing independent solutions?
- *RQ3:* How can formal verification be embedded inside a procedural generator so that every
  accepted level comes with certified properties?
- *RQ4:* Can we control the cooperation structure of generated levels by targeting specific
  profiles such as asymmetric, mutual, chain, distributed, or fully coupled dependencies?
- *RQ5:* Can MARL agents trained exclusively on procedurally generated levels learn the
  cooperative behaviour the levels are designed to elicit, and does that behaviour transfer to
  human-designed levels?
- *RQ6:* Can the controllability of the generator be exploited to organise levels into a
  curriculum that accelerates learning on a hand-crafted target?

The thesis instantiates this framework on LLE, focusing on a restricted but explicit subset of
its mechanics. The formal model covers agent movement, inter-agent blocking interactions, and a
bounded-horizon solvability criterion. Additional LLE mechanics — gem collection, scoring
beyond exit-reaching — are outside the scope of the formal guarantees developed here.


== Thesis Structure

The remainder of this thesis is organised as follows. Chapter 2 positions the work relative to
cooperative MARL benchmarks, procedural content generation, and compilation-based planning
literature. Chapter 3 fixes the technical setting: the LLE mechanics, the SAT background, and
the formal model of bounded-horizon solvability and the cooperation requirement.

The three contribution chapters then develop the original technical content of the thesis in
logical order. Chapter 4 introduces the SAT-based solver: a propositional encoding of
bounded-horizon LLE solvability, with correctness proofs and a complexity-theoretic positioning.
Chapter 5 builds on that encoding to define the cooperation detector based on a strict
counterfactual semantics, and extends it with a profile analyzer that classifies the kind of
cooperation a level exhibits. Chapter 6 then uses both decision procedures as acceptance oracles
inside a family of procedural generators that produce levels certified to satisfy the advertised
properties.

Chapter 7 reports the empirical evaluation: the SAT encoding comparison, generator acceptance
rates and cooperation-profile distributions, the learnability of generated cooperative levels
for off-the-shelf MARL algorithms, and the curriculum-transfer pilot toward the hand-crafted LLE
Level 6. Chapter 8 concludes with a summary and directions for future work.
