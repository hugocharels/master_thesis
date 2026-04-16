== Cooperative MARL and Coordination-Critical Benchmarks

This thesis is motivated by a benchmark-design question inside cooperative Multi-Agent
Reinforcement Learning (MARL): how can one generate training instances whose coordination structure
is both non-trivial and formally controlled?

In the fully cooperative setting, all agents optimise a shared return, so the quality of the
environment matters as much as the quality of the learning algorithm. If the environment admits only
trivial solutions, it does not meaningfully test coordination. If it contains unsolvable instances,
it provides no useful training signal at all. For the present thesis, the central issue is
therefore not MARL in general, but the design of instances in which inter-agent dependence is both
structurally present and formally decidable.


== The Laser Learning Environment

The Laser Learning Environment (LLE) was introduced precisely to study coordination-critical
multi-agent tasks @LLE. The paper identifies three properties that make the benchmark difficult for
value-based MARL methods: *perfect coordination*, *interdependence*, and *zero-incentive dynamics*.
Together, these properties create bottlenecks in which one agent must perform a locally unrewarded
action that enables another agent to progress.

This benchmark framing is directly relevant to the present work. The thesis does not attempt to
improve MARL training algorithms on LLE. Instead, it addresses an upstream question left open by
the benchmark paper: how can we generate LLE levels that are guaranteed to be solvable and that
guarantee the presence of the beam-blocking dependency on which the benchmark relies?

The LLE paper therefore plays two roles in this thesis. First, it justifies why LLE is an
interesting target domain. Second, it provides the conceptual vocabulary used here to discuss
cooperation: the key object is not generic teamwork, but a concrete interdependence mechanism
created by coloured lasers and same-colour blocking.


== Procedural Generation Under Structural Constraints

Procedural Content Generation (PCG) is useful in reinforcement-learning settings because it can
replace a small fixed benchmark set with a larger and more diverse stream of instances
@Shaker2016. However, generic PCG is not sufficient for the present problem. The difficulty is not
merely to produce varied levels, but to produce levels that satisfy logically defined properties.

This distinction matters. A constructive or search-based generator may bias generation toward
interesting layouts, but without a verifier it cannot certify that a sampled level is solvable or
that success genuinely depends on cooperation. For that reason, the present thesis adopts a
constraint-aware view of PCG: generation is coupled to a formal decision procedure, and the solver
acts as an acceptance oracle rather than as a post-hoc descriptive tool.


== Compilation-Based Multi-Agent Path Finding

The closest methodological precedent is not PCG for MARL, but compilation-based Multi-Agent Path
Finding (MAPF). In standard MAPF, agents move on a discrete graph from start vertices to goal
vertices while avoiding collisions. The computational difficulty comes from the interaction between
multiple agents and the optimality criterion imposed on the solution.

Surynek's survey @Surynek2022CompilationMAPF shows that MAPF has become a major testbed for
compilation-based solving. Instead of searching directly in the original state space, one reduces a
MAPF instance to a target formalism such as CSP, SAT, or MILP, then relies on the target solver to
handle the combinatorial burden. The survey is especially relevant here for two reasons.

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
design. The paper by Frommknecht and Surynek @FrommknechtSurynek2024 studies SAT-based MAPF solving
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

The literature leaves a clear opening for the present work.

- The LLE paper @LLE establishes the benchmark and explains why its coordination bottlenecks are
  difficult for MARL algorithms, but it does not provide a formal generator for certified
  cooperative levels.
- The MAPF compilation survey @Surynek2022CompilationMAPF shows that SAT is an effective backend
  for multi-agent planning problems, but it addresses standard MAPF rather than LLE-specific laser
  dynamics.
- The MAPF SAT-engineering paper @FrommknechtSurynek2024 shows that encoding design affects solver
  performance in practice, but it remains within the standard MAPF framework and does not address
  cooperation as a semantic property of the instance.

This thesis sits at the intersection of those lines of work. It transfers the compilation-based SAT
mindset from MAPF into the LLE setting, formalises bounded-horizon solvability for an LLE-specific
model, and introduces a strict-semantics counterfactual that turns a benchmark-level intuition
about cooperation into a decidable property used inside procedural generation.
