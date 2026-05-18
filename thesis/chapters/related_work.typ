#import "../macros.typ": fref

== Cooperative MARL and Coordination-Critical Benchmarks

This thesis is motivated by a benchmark-design question within cooperative Multi-Agent
Reinforcement Learning (MARL): how can one generate training instances whose coordination structure
is both non-trivial and formally controlled?

In the fully cooperative setting, all agents optimise a shared return, so the quality of the
environment matters as much as the quality of the learning algorithm. If the environment admits only
trivial solutions, it does not meaningfully test coordination. If it contains unsolvable instances,
it provides no useful training signal at all. For the present thesis, the central issue is
therefore not MARL in general, but the design of instances in which inter-agent dependence is both
structurally present and formally decidable.

The general framework for sequential multi-agent decision-making originates in stochastic games
@Shapley1953, generalised to the Markov game model that has become the standard formalism for MARL
@Littman1994. The single-agent reinforcement-learning machinery on which cooperative MARL builds is
covered comprehensively in @SuttonBarto2018. In cooperative MARL specifically, value-decomposition
methods such as VDN @Sunehag2018 and QMIX @Rashid2018 factor a shared team value into per-agent
components to enable decentralised execution; closely related approaches include the centralized-critic
actor-critic of MADDPG @Lowe2017MADDPG, the counterfactual-baseline policy gradient COMA
@Foerster2018COMA, and MAVEN @Mahajan2019MAVEN, which extends QMIX with latent-variable exploration
to overcome its monotonicity limitations on coordination tasks. These methods perform well when
individual contributions are roughly additive, but they struggle precisely on the
coordination-critical, low-reward bottlenecks that LLE is designed to expose @LLE. The empirical
chapter of this thesis (@experiments) accordingly uses three points on this algorithm spectrum —
independent $Q$-learning (IQL, no credit-assignment baseline), VDN (additive decomposition), and
QMIX (monotonic mixing) — to train on generated cooperative levels and on the curriculum-transfer
target.


== The Laser Learning Environment

The Laser Learning Environment (LLE) was introduced precisely to study coordination-critical
multi-agent tasks @LLE. The paper identifies three properties that make the benchmark difficult for
value-based MARL methods: *perfect coordination*, *interdependence*, and *zero-incentive dynamics*.
Together, these properties create bottlenecks in which one agent must perform a locally unrewarded
action that enables another agent to progress.

This benchmark framing is directly relevant to the present work. The thesis does not attempt to
improve MARL training algorithms on LLE. Instead, it addresses an upstream question left open by
the benchmark paper: how can we generate LLE levels that are guaranteed to be solvable and that
contain the beam-blocking dependency on which the benchmark relies?

The LLE paper therefore plays two roles in this thesis. First, it justifies why LLE is an
interesting target domain. Second, it provides the conceptual vocabulary used here to discuss
cooperation: the key object is not generic teamwork, but a concrete interdependence mechanism
created by coloured lasers and same-colour blocking.


== Dependency Structures in Cooperative MARL

The cooperation criterion of #fref(<thm-4-9>, [Theorem 4.9]) returns a binary verdict, but cooperative behaviour can
be richer: in a level with several agents and several lasers, helping relations can form a
one-way edge, a mutual pair, a directed chain, a shared-beneficiary fan-in, or a fully connected
graph. In @cooperation-detection we extract this dependency graph from a SAT model and classify it under one
of five labels — *asymmetric*, *mutual*, *chain*, *distributed*, *fully coupled*. This taxonomy
is, to our knowledge, new for laser-blocking dependencies in LLE; the prior MARL literature
considers related but distinct structural notions.

The closest precedent is the *coordination graph* introduced by #cite(<Guestrin2002CoordinatedRL>, form: "prose"),
which decomposes a joint $Q$-function over agent subsets connected by hyper-edges. Coordination
graphs are a representational tool: they assume the structure is known a priori and use it to
make value computation tractable. Our taxonomy operates in the opposite direction. The structure
is not given; it is *recovered* from a SAT certificate of solvability, and the label is a
property of the level produced rather than a modelling assumption made about the agents. The two
notions are therefore complementary: a coordination graph tells the *learner* which agent subsets
interact, while our profile tells the *level designer* what kind of cooperation a generated
instance contains.


== Procedural Generation Under Structural Constraints

Procedural Content Generation (PCG) is useful in reinforcement-learning settings because it can
replace a small fixed benchmark set with a larger and more diverse stream of instances
@Shaker2016. Within PCG, search-based methods — surveyed by #cite(<Togelius2011>, form: "prose") — phrase
content creation as an optimisation problem over a content space, which is conceptually close to the
solver-driven acceptance loop adopted in this thesis. The closest precedent for the present
declarative-constraint approach is the Answer Set Programming generator of
#cite(<SmithMateas2011>, form: "prose"), which uses an ASP solver as the acceptance oracle for game content. A
complementary line of work surveyed under the PCGML banner @Summerville2018PCGML uses
machine-learned generators trained on existing levels, but typically provides no formal guarantee
on the produced output. The difficulty for the present problem is not merely to produce varied
levels, but to produce levels that satisfy logically defined properties.

This distinction matters. A constructive or search-based generator may bias generation toward
interesting layouts, but without a verifier it cannot certify that a sampled level is solvable or
that success genuinely depends on cooperation. For that reason, the present thesis adopts a
constraint-aware view of PCG: generation is coupled to a formal decision procedure, and the solver
acts as an acceptance oracle rather than as a post-hoc descriptive tool.


== Curriculum Learning and Generated Environments

The general idea of training on a sequence of progressively harder tasks predates the modern
deep-learning era; #cite(<Bengio2009>, form: "prose") formalised *curriculum learning* as a meta-learning
strategy in which the order of training examples is itself a design choice. In reinforcement
learning specifically, the survey by #cite(<Narvekar2020Curriculum>, form: "prose") catalogues the design
space along three axes — the *task generator*, the *sequencing policy*, and the *transfer
mechanism* — and shows that curriculum learning consistently helps on long-horizon and
sparse-reward problems, the regime in which LLE Level 6 sits.

A more recent line of work tightens the coupling between curriculum and environment generation.
*POET* @Wang2019POET co-evolves a population of environments and a population of agents in an
open-ended loop: environments that are too easy or too hard for the current agent population are
eliminated, and surviving environments act as a self-organising curriculum. *PAIRED*
@Dennis2020PAIRED extends this idea to *unsupervised environment design*: an adversary
parameterises environments to maximise the regret of a protagonist agent against an antagonist
baseline, which provably keeps the generated environments solvable while remaining at the
frontier of the protagonist's ability.

The present thesis sits adjacent to this line of work. Like POET and PAIRED, we generate
environments rather than reuse a fixed test set, and we use those environments as a curriculum
toward a hard target. Unlike POET and PAIRED, the generator here is not adversarial and not
adaptive to the learner's current policy: it is a *static* solver-in-the-loop generator that
emits levels certified to satisfy fixed structural properties (solvability, cooperation, profile)
and at a fixed difficulty level. The curriculum used in @experiments is hand-staged — four
manually ordered configurations of growing grid size and cooperation requirement — not learnt.
Replacing the manual staging by an adaptive scheduler in the spirit of POET / PAIRED is a
natural direction for future work, but is not pursued here.


== SAT-based Planning

A second compilation lineage directly relevant to this thesis is *SAT-based planning*.
#cite(<KautzSelman1992>, form: "prose") introduced SATPLAN, encoding bounded-horizon STRIPS planning
instances as propositional formulas; subsequent work refined both the encodings and the search
strategies @KautzSelman1996. The treatment by #cite(<Rintanen2006>, form: "prose") covers parallel-plan
encodings and modern algorithmic refinements that drove SAT-based planners to competitive
performance with dedicated planners. The bounded-horizon LLE encoding developed in this thesis sits
in the same conceptual family: a state-transition decision problem reduced to SAT, with the encoding
choices materially affecting solver performance.


== Compilation-Based Multi-Agent Path Finding

The closest methodological precedent is not PCG for MARL, but compilation-based Multi-Agent Path
Finding (MAPF). In standard MAPF, agents move on a discrete graph from start vertices to goal
vertices while avoiding collisions. The computational difficulty comes from the interaction between
multiple agents and the optimality criterion imposed on the solution.

The survey by #cite(<Surynek2022CompilationMAPF>, form: "prose") shows that MAPF has become a major testbed for
compilation-based solving. Instead of searching directly in the original state space, one reduces a
MAPF instance to a target formalism such as CSP, SAT, or MILP, then relies on the target solver to
handle the combinatorial burden. MAPF research is not exclusively compilation-based; the dominant
search-based alternative, Conflict-Based Search @Sharon2015CBS, achieves optimal solutions through a
two-level constraint-satisfaction tree without reducing to a target formalism. We adopt the
compilation route rather than CBS-style search because the property of interest in this thesis is
the *existence* of a valid joint plan within a fixed horizon, not its makespan optimality: a
SAT decision procedure matches the question we ask, whereas CBS is built to deliver optimal-cost
plans on a graph and would need substantial extension to encode the laser-propagation and
strict-counterfactual semantics introduced in @cooperation-detection. The compilation survey is
therefore especially relevant here for two reasons.

First, it demonstrates that SAT-based reductions are a mature and credible way to solve structured
multi-agent planning problems. Second, it makes clear that compilation is not a black-box slogan:
modeling choices, encoding size, and the interaction between the source problem and the target
solver all matter materially for performance.

The present thesis inherits this compilation perspective. Bounded-horizon LLE solvability is
treated as a decision problem and is reduced to SAT. The difference is that LLE is not standard
MAPF: the environment contains colour-dependent laser semantics and the property of interest is not
path optimality, but solvability and cooperation under the benchmark mechanics.


== SAT-Based MAPF Encoding Design

Beyond the general survey, the MAPF literature also provides concrete lessons about SAT encoding
design. The paper by #cite(<FrommknechtSurynek2024>, form: "prose") studies SAT-based MAPF solving
under the makespan objective using an MDD-SAT formulation and compares different solver-facing
choices, including eager versus lazy encodings and the use of informative initial assignments.

That paper is relevant to the present thesis not because it solves the same problem, but because it
shows that SAT-based multi-agent solving is sensitive to representation details. Performance is not
determined only by the underlying decision problem; it also depends on how the problem is encoded
and on how the resulting CNF interacts with the chosen SAT solver. This is directly aligned with
the experimental part of the current thesis, where two alternative uniqueness encodings are
compared empirically.

At the same time, the distance between the two settings should be stated explicitly. Standard MAPF
encodings reason about graph motion and collisions. The current thesis must additionally encode
time-dependent laser propagation, same-colour immunity, and a strict counterfactual semantics used
to define cooperation. The MAPF literature therefore supplies a methodological template, not a
drop-in solution.


== Positioning of the Thesis

Taken together, the MARL benchmarking literature, the PCG and curriculum-learning literature,
and the SAT-planning / compilation-based MAPF literature mark the conceptual neighbourhood of
this thesis. None of them, however, fully covers the problem we address: each line studies one
side of the problem in isolation, and the literature leaves a clear opening for the present
work.

- The LLE paper @LLE establishes the benchmark and explains why its coordination bottlenecks are
  difficult for MARL algorithms, but it does not provide a formal generator for certified
  cooperative levels.
- The MAPF compilation survey @Surynek2022CompilationMAPF shows that SAT is an effective backend
  for multi-agent planning problems, but it addresses standard MAPF rather than LLE-specific laser
  dynamics.
- The MAPF SAT-engineering paper @FrommknechtSurynek2024 shows that encoding design affects solver
  performance in practice, but it remains within the standard MAPF framework and does not address
  cooperation as a semantic property of the instance.
- The coordination-graph line of work @Guestrin2002CoordinatedRL gives a representation for known
  inter-agent dependencies but does not provide a *taxonomy* of dependency structures that arise
  from a specific cooperation mechanism.
- The environment-design line of work @Wang2019POET @Dennis2020PAIRED treats curriculum
  generation as an adaptive co-evolution problem but assumes a parameterised environment family
  without formal per-instance acceptance guarantees on solvability or cooperation.

This thesis sits at the intersection of those lines of work. It transfers the compilation-based SAT
mindset from MAPF into the LLE setting, formalises bounded-horizon solvability for an LLE-specific
model, and introduces a strict-semantics counterfactual that turns a benchmark-level intuition
about cooperation into a decidable property inside procedural generation.
