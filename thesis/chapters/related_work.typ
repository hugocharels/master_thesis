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
@Shapley1953, generalised to the Markov game model that has become the standard formalism for
MARL @Littman1994. The single-agent reinforcement-learning machinery on which cooperative MARL
builds is covered comprehensively in @SuttonBarto2018.

Two algorithm families dominate the cooperative MARL literature. *Value-decomposition* methods
factor a shared team value into per-agent components to enable decentralised execution: VDN
@Sunehag2018 uses an additive decomposition, and QMIX @Rashid2018 generalises this to a
state-dependent monotonic mixing network. *Centralised-critic actor-critic* methods take a
different route, training a joint critic that conditions on full state at training time while
each agent retains a local actor at execution time: MADDPG @Lowe2017MADDPG is the canonical
deterministic-policy instance, COMA @Foerster2018COMA refines the credit-assignment signal with
a counterfactual baseline, and MAVEN @Mahajan2019MAVEN extends QMIX with latent-variable
exploration to escape the monotonicity bottleneck on coordination-critical tasks.

Both families perform well when individual contributions are roughly additive, and both struggle
on the coordination-critical, low-reward bottlenecks that LLE is designed to expose @LLE. The
empirical chapter of this thesis (@experiments) accordingly uses three points along the
value-decomposition spectrum — independent $Q$-learning (IQL, no credit assignment), VDN
(additive), and QMIX (monotonic mixing) — to train on generated cooperative levels and on the
curriculum-transfer target.


== The Laser Learning Environment

The Laser Learning Environment (LLE), whose mechanics we formalise in @lle-background, was
introduced precisely to study coordination-critical multi-agent tasks @LLE. It sits alongside
other cooperative-MARL benchmarks such as SMAC @Samvelyan2019SMAC (StarCraft micro-management
with partially observable team play) and Overcooked @Carroll2019Overcooked (a constrained
cooperative kitchen with temporal synchronisation), but differs in that its hardness comes from
explicit *inter-agent blocking* rather than from partial observability or large action spaces. The LLE paper identifies three
properties that make the benchmark difficult for value-based MARL methods: *perfect
coordination*, *interdependence*, and *zero-incentive dynamics*. Together, these properties
create bottlenecks in which one agent must perform a locally unrewarded action that enables
another agent to progress.

This benchmark framing is directly relevant to the present work. The thesis does not attempt to
improve MARL training algorithms on LLE. Instead, it addresses an upstream question left open by
the benchmark paper: how can we generate LLE levels that are guaranteed to be solvable and that
contain the beam-blocking dependency on which the benchmark relies?

The LLE paper therefore plays two roles in this thesis. First, it justifies why LLE is an
interesting target domain. Second, it provides the conceptual vocabulary used here to discuss
cooperation: the key object is not generic teamwork, but a concrete interdependence mechanism
created by coloured lasers and same-colour blocking.


== Dependency Structures in Cooperative MARL

The same-colour beam-truncation mechanism on which LLE relies admits a "cooperation required /
not required" verdict per level, but cooperative behaviour at finer granularity can vary
considerably: in a level with several agents and several lasers, helping relations can form a
one-way edge, a mutual pair, a directed chain, a fan-in (one beneficiary, multiple helpers), or
a fully connected graph. The cooperation profile analyzer of @cooperation-detection extracts
this dependency graph from a SAT model of a solution and labels it as, respectively,
*asymmetric*, *mutual*, *chain*, *distributed*, or *fully coupled*. The structural categories themselves are
standard graph-theory vocabulary; to our knowledge, this is the first taxonomy that *recovers*
such structures from a SAT certificate of solvability in LLE. The prior MARL literature
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

PCG has been increasingly developed *for* reinforcement learning, where the role of the
generated content is not to entertain a human player but to provide training material for a
learning agent. #cite(<RisiTogelius2020>, form: "prose") survey this line and argue that PCG is
a natural lever for moving beyond fixed-benchmark RL toward generalisation across infinite
environment families. Within that line, PCGRL @Khalifa2020PCGRL inverts the relationship between
PCG and RL: rather than using PCG to feed RL agents, it trains an RL agent to *act as* the level
designer. The thesis here runs in the opposite direction — a fixed solver-in-the-loop generator
produces certified levels that feed RL training — and PCGRL is therefore a useful contrast
rather than a comparable system.

What distinguishes this thesis from the lines above is the *verification* step. A constructive
or search-based generator may bias generation toward interesting layouts, but without a verifier
it cannot certify that a sampled level is solvable or that success genuinely depends on
cooperation. The present thesis therefore adopts a constraint-aware view of PCG: generation is
coupled to a formal decision procedure, and the solver acts as an acceptance oracle rather than
as a post-hoc descriptive tool.


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
emits levels certified to satisfy fixed structural properties (solvability, cooperation,
profile) at a chosen difficulty configuration. The curriculum used in @experiments is hand-
staged — four manually ordered configurations of growing grid size and cooperation requirement.


== SAT-based Planning

A second compilation lineage directly relevant to this thesis is *SAT-based planning* (we recall
the propositional satisfiability background in @sat-background).
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
vertices while avoiding collisions. The computational difficulty comes from the interaction
between multiple agents and the optimality criterion imposed on the solution.

The survey by #cite(<Surynek2022CompilationMAPF>, form: "prose") shows that MAPF has become a
major testbed for compilation-based solving: instead of searching directly in the original state
space, one reduces a MAPF instance to a target formalism (CSP, SAT, or MILP) and relies on the
target solver to handle the combinatorial burden. MAPF research is not exclusively
compilation-based; the dominant search-based alternative, Conflict-Based Search @Sharon2015CBS,
achieves optimal solutions through a two-level constraint-satisfaction tree without reducing to
a target formalism. We adopt the compilation route rather than CBS-style search because the
property of interest in this thesis is the *existence* of a valid joint plan within a fixed
horizon, not its makespan optimality: a SAT decision procedure matches the question we ask,
whereas CBS would need substantial extension to encode the laser-propagation and
strict-counterfactual semantics introduced in @cooperation-detection.

Within the compilation route, encoding design materially affects solver performance. The work of
#cite(<FrommknechtSurynek2024>, form: "prose") studies SAT-based MAPF under the makespan
objective using an MDD-SAT formulation and compares solver-facing choices such as eager versus
lazy encodings and informative initial assignments. The point of citing this paper is not that it
solves the same problem, but that it confirms a recurring lesson: performance is not determined
only by the underlying decision problem; it also depends on how the problem is encoded and on
how the resulting CNF interacts with the chosen SAT solver. The empirical chapter of this thesis
(@experiments) compares two alternative uniqueness encodings in the same spirit.

At the same time, the distance from standard MAPF must be stated explicitly. Standard MAPF
encodings reason about graph motion and collisions. The present thesis must additionally encode
time-dependent laser propagation, same-colour immunity, and a strict-counterfactual semantics
used to define cooperation. The MAPF literature therefore supplies a methodological template,
not a drop-in solution.


== Formal Methods Coupled to Reinforcement Learning

A separate line of work uses formal methods as an explicit component of the reinforcement
learning loop rather than as a post-hoc analysis. The canonical example is *shielded RL*
@Alshiekh2018Shielding, where a formally synthesised reactive shield filters the agent's
candidate actions at runtime so that no policy update can ever violate a stated temporal-logic
specification. The shield is computed once from the specification and the environment model, then
inserted between the agent and the environment as a hard constraint.

The connection to this thesis is methodological rather than direct. Shielded RL inserts a formal
acceptance oracle on the *action* side of the loop, at runtime; we insert one on the *training-
material* side, at generation time. Both follow the same recipe — encode a target property in a
decidable formalism, run a solver, and reject anything that fails — but they apply it to opposite
ends of the agent-environment interface. Shielded RL therefore does not provide a drop-in
technique, but it does demonstrate that "formal-methods filter on top of an RL system" is a
working pattern.


== Positioning of the Thesis

Taken together, the MARL benchmarking literature, the PCG and curriculum-learning literature,
and the SAT-planning / compilation-based MAPF literature mark the conceptual neighbourhood of
this thesis. None of them, however, fully covers the problem we address: each line studies one
side of the problem in isolation. The remaining gap can be summarised under four headings.

- *Cooperative MARL benchmarks and inter-agent structure.* The LLE paper @LLE establishes the
  benchmark and explains why its coordination bottlenecks are difficult for MARL algorithms,
  but it does not provide a formal generator for certified cooperative levels. The
  coordination-graph line @Guestrin2002CoordinatedRL gives a representation for known
  inter-agent dependencies but does not classify the *types* of dependency that emerge from a
  specific cooperation mechanism.
- *Compilation-based multi-agent planning.* The MAPF compilation literature
  @Surynek2022CompilationMAPF @FrommknechtSurynek2024 shows that SAT is an effective backend
  for multi-agent planning and that encoding design matters in practice, but it solves a
  different problem (path optimality on a collision graph) and does not address either the
  laser-propagation semantics or cooperation as a semantic property of the instance.
- *Procedural generation, curriculum learning, and environment design.* The PCG-for-RL line
  @RisiTogelius2020 @Khalifa2020PCGRL frames generation as a tool for RL generalisation, and
  the environment-design line @Wang2019POET @Dennis2020PAIRED treats curriculum generation as
  adaptive co-evolution. Neither embeds a decision procedure that *proves* each generated
  instance satisfies a target structural property.
- *Formal methods on top of RL.* The shielded-RL line @Alshiekh2018Shielding shows that formal
  methods integrate cleanly with RL when used as a runtime *action* filter, but does not
  address the upstream question of whether the *training material* itself satisfies the
  specification.

This thesis sits at the intersection of those four lines. It transfers the compilation-based
SAT mindset from MAPF into the LLE setting, formalises bounded-horizon solvability for an
LLE-specific model, introduces a strict-semantics counterfactual that turns a benchmark-level
intuition about cooperation into a decidable property inside procedural generation, and
classifies the resulting dependency structures into a taxonomy that downstream generators can
target as a parameter.
