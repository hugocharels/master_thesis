== Context

Cooperative Multi-Agent Reinforcement Learning (MARL) studies settings in which several agents
must learn behaviours whose value appears only at the team level. In such settings, the environment
is not a neutral container: it determines which coordination patterns are possible, which ones are
necessary, and how difficult they are to discover.

This dependence on environment structure is especially strong in sparse-reward cooperative tasks.
When reward is issued only after the team objective has been achieved, two failure modes make a
training level useless. An unsolvable level provides no learning signal at all. A level solvable
without cooperation defeats the purpose, since we are training the agents precisely to learn how
to cooperate.

We instantiate this work on the Laser Learning Environment (LLE), a cooperative MARL benchmark
whose mechanics are formalised in @lle-background; its hand-crafted Level 6 serves as the
canonical hard target throughout the thesis. We expect this methodology (coupling
procedural generation with a formal verification oracle) to generalise to any MARL setting whose
target properties are expressible as decision problems, but we evaluate it on LLE only and leave
broader transfer to future work.


== Motivation

In cooperative environments whose mechanics create explicit inter-agent dependencies, level design
is particularly challenging. A useful training level should not merely appear cooperative, it
should provably contain the intended coordination structure.

Procedural Content Generation (PCG) offers a way to scale level creation beyond what manual design
allows, but only if the generated instances satisfy the properties that matter for training. Two
properties are central. First, a level must be *solvable*. Second, success should *require
cooperation* in the specific sense induced by the environment's mechanics. Without those
guarantees, PCG risks producing levels that are invalid, trivial, or misaligned with the
training objective.

Generated levels are also useful beyond standalone training. The same knobs that control a single
level also define a natural difficulty axis: grid size, number of agents, number of lasers, wall
budget, cooperation profile, and time horizon (the bounded number of joint steps allowed for a
solution). A formally-verified generator is therefore a candidate building block for *curriculum
learning*: rather than train directly on a hard hand-crafted target, an agent can be trained on a
sequence of progressively harder generated levels.

The thesis delivers three contributions and an empirical study. The contributions are a
bounded-horizon SAT encoding of LLE solvability with a correctness proof and complexity
placement; a strict-semantics counterfactual that turns the informal "cooperation required"
intuition into a decidable property, refined into five increasingly rich cooperation profiles; and a
solver-in-the-loop generator family that accepts only certified levels and exposes the
structural axes above as user-facing parameters. The empirical study covers SAT-encoding
cost, generator acceptance rates and profile distributions, learnability of generated
cooperative levels for off-the-shelf MARL, and a curriculum-transfer study toward LLE Level 6.

Beyond the thesis itself, the SAT-based solver, the cooperation detector, and the procedural
generator family have been contributed upstream to the official `laser-learning-environment`
library#footnote[#link("https://pypi.org/project/laser-learning-environment/")] (released on PyPI
as `laser-learning-environment[generator]`, version 2.9.0 and onwards), where they are exposed as
the public functions `lle.solve`, `lle.is_cooperative`, `lle.cooperation_level`, and `lle.generate`.


== Research questions and scope

This thesis addresses one overarching question: how can we automatically generate levels for a
cooperative MARL environment that are provably solvable and provably require the target
cooperative interaction, and how can such levels be used to support MARL training? We decompose
this question into six research questions:

- *RQ1:* How can we formally verify that a level is solvable by the agents?
- *RQ2:* How can we formally verify that solving a level genuinely requires cooperation between
  agents, rather than allowing independent solutions?
- *RQ3:* How can formal verification be embedded inside a procedural generator so that every
  accepted level comes with certified properties?
- *RQ4:* Can we control the cooperation structure of generated levels by targeting specific
  profiles such as asymmetric, mutual, chain, distributed, or fully coupled dependencies?
- *RQ5:* Can MARL agents trained exclusively on procedurally generated cooperative levels
  reach a non-trivial greedy success rate on a held-out pool of generated levels at a fixed
  training budget, and how does that performance vary across IQL, VDN, and QMIX?
- *RQ6:* Does a staged curriculum of generated levels of growing geometric and cooperative
  complexity yield a higher greedy success rate on hand-crafted LLE Level 6 than a baseline
  trained directly on Level 6 (or on the union of all stage pools) at the same total training
  budget?

The thesis instantiates this framework on LLE, focusing on the *exit-reaching task*: each agent
must reach an exit tile. The formal model covers agent movement, inter-agent blocking interactions,
and a bounded-horizon solvability criterion. Collectible gems and the incentive-scoring layer that
rewards them are outside the scope of this thesis. Void tiles are not handled in our model either;
to use the solver on a level containing void tiles, the user must first replace each void tile with
a wall, which yields the same verdict. These restrictions are deferred to future work.


== Thesis structure

The remainder of this thesis is organised as follows. @related-work positions the work relative
to cooperative MARL benchmarks, procedural content generation, and compilation-based planning
literature. @background fixes the technical setting: the LLE mechanics, the Boolean satisfiability
background, and the formal problem statement that defines bounded-horizon solvability as well as
the cooperation requirement.

The three contribution chapters then develop the original technical content of the thesis in
logical order. @sat-reduction introduces the SAT-based solver: a propositional encoding of
bounded-horizon LLE solvability, with correctness proofs and a complexity-theoretic positioning.
@cooperation-detection builds on that encoding to define the cooperation detector based on a
strict counterfactual semantics, and extends it with a profile analyser that classifies the kind
of cooperation a level exhibits. @generators then uses both decision procedures as acceptance
oracles inside a family of procedural generators that produce levels certified to satisfy the
advertised properties.

@experiments reports the empirical evaluation: the SAT encoding comparison, generator acceptance
rates and cooperation-profile distributions, the learnability of generated cooperative levels
for off-the-shelf MARL algorithms, the effect of training-pool size on generalisation, and the
curriculum-transfer study toward the hand-crafted LLE Level 6. @conclusion concludes with a summary and directions for future work.
