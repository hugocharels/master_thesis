#import "../macros.typ": fref

== Summary

This thesis developed a SAT-based framework for reasoning about solvability and cooperation in
a modeled subset of the Laser Learning Environment. We first formalised bounded-horizon
solvability as a decision problem and reduced it to satisfiability of a CNF formula. On top of
that reduction, we introduced a strict beam-semantics counterfactual that turns the
blocking-based cooperation mechanism of LLE into a second decision problem on the same level,
and refined the binary outcome into a profile taxonomy that classifies the dependency
structure of a cooperative level.

These decision procedures were then embedded inside a family of procedural generators. The
resulting framework does not guarantee that generated levels are pedagogically optimal for
MARL, but it does guarantee that accepted levels satisfy the formal properties checked by the
solver. This is the central contribution of the thesis: procedural generation coupled to
*explicit certification* rather than procedural generation guided only by heuristic
plausibility.


== Answering the Research Questions

We restate the six research questions of @introduction and assess what each chapter delivers.

- *RQ1 — formal verification of solvability.* Answered by the bounded-horizon SAT reduction
  of @sat-reduction, whose correctness is established by
  #fref(<prop-4-1>, [Proposition 4.1]). The encoding is polynomial-time constructible, places
  bounded-horizon LLE solvability in NP, and proves the problem is at most as hard as SAT.

- *RQ2 — formal verification of the cooperation requirement.* Answered by the
  strict-counterfactual encoding of @cooperation-detection, whose correctness is established
  by #fref(<thm-5-1>, [Theorem 5.1]): a level requires cooperation if and only if the standard
  formula is SAT and the strict formula is UNSAT. The criterion is decidable on the same
  finite horizon used for solvability.

- *RQ3 — embedding verification inside a generator.* Answered by the generator family of
  @generators. Each generator uses the SAT solver as an acceptance oracle, so every emitted
  level carries a solver certificate of the advertised property.

- *RQ4 — controlling the cooperation profile.* Answered constructively. The cooperation
  profile analyzer of @cooperation-profiles labels every certified cooperative level, and the
  generators expose a profile filter that restricts acceptance to a chosen subset of the
  taxonomy. The profile-distribution experiment of @profile-distribution shows that the
  constructive generator reliably produces *mutual* profiles when $n_l >= 2$ and admits
  *distributed* profiles when $n_l >= 3$ on grids large enough. The *fully coupled* label did
  not arise in the tested parameter range and remains a target for the future-work
  parameter-sensitivity study below.

- *RQ5 — learnability of certified cooperative levels.* Answered positively on a small grid.
  The learnability experiment of @learnability-experiment shows that IQL, VDN, and QMIX all
  reach non-trivial greedy success rates ($0.59$–$0.70$ on the training pool, $0.18$–$0.23$
  on the held-out pool) on the $5 times 5$ cooperative pool within a 200,000-step budget.
  The dominant difficulty observed is generalisation to the held-out pool rather than credit
  assignment; the cross-algorithm spread is small relative to the train/test gap, which is
  the open question the next direction in @transfer-experiment is designed to probe.

- *RQ6 — curriculum transfer to LLE Level 6.* Not yet answered. The experimental design of
  @transfer-experiment is still being iterated at the time of writing and the runs have not
  been launched. This section will be expanded once the design is locked and the
  curriculum-transfer evaluation is complete.

// TODO: rewrite the RQ6 paragraph once @transfer-experiment runs are
// complete; replace "not yet answered" with the empirical answer and
// state whether the curriculum outperforms the baselines on Level 6.


== Future Work

Several directions extend the present work naturally.

- *Complexity classification of bounded-horizon LLE solvability.* This thesis shows that
  bounded-horizon LLE solvability is in NP and is polynomial-time reducible to SAT, but we do
  not settle whether the problem is NP-hard. The exact placement has both theoretical and
  practical consequences: if the problem is NP-hard, the SAT-based oracle is optimal up to
  constant factors under the standard $"P" eq.not "NP"$ assumption; if it lies in P, then in
  principle the SAT solver could be replaced by a polynomial-time algorithm tailored to the
  LLE structure, with a corresponding speed-up for every generator in the family. Establishing
  the lower bound is therefore both a theoretical complement to the present work and an
  engineering lever for the generator pipeline.
- *Model extension to gems and void tiles.* The formal model deliberately omits gems and
  treats void tiles as walls. Incorporating gem tiles would add an additional reachability
  condition — every agent must visit a designated gem cell at some point before reaching its
  exit — and would extend the property certified by the SAT oracle accordingly. Distinguishing
  void tiles from walls would require a revised movement semantics (agents cannot enter void
  cells under any condition, but the cell still propagates beams differently). Both extensions
  preserve the SAT-based architecture; only the encoding and the formal definitions need to be
  updated.
- *Parameter sensitivity and output diversity.* The acceptance-rate experiments fix the agent
  and laser counts at each grid size. A fuller characterisation would vary these parameters
  along independent axes to locate the practical frontier at which rejection rates become
  prohibitive, would measure within-pool diversity of accepted levels at a fixed parameter
  setting beyond the wall-Hamming statistics reported here, and would attempt to surface the
  *fully coupled* profile by raising $n_l$ and the grid size.
- *Richer cooperation metrics.* The cooperation-profile taxonomy of @cooperation-profiles
  captures five dependency-graph patterns. Extensions could promote the synchronous-width
  scalar already exposed by the analyzer into a first-class profile axis, and could add a
  chain-length difficulty axis on top of the qualitative chain label. These richer targets
  would let the generator family target *graded* cooperation difficulty rather than only
  qualitative profile families.
- *Algorithm-space breadth.* The learnability and curriculum-transfer experiments evaluate
  three value-decomposition algorithms (IQL, VDN, QMIX). Comparison against
  centralised-critic actor-critic methods such as MADDPG @Lowe2017MADDPG and COMA
  @Foerster2018COMA, and against latent-variable variants such as MAVEN @Mahajan2019MAVEN,
  would give a fuller picture of which algorithm families benefit most from certified
  training material on coordination-critical tasks.

// TODO: revisit this list once the curriculum-transfer design is locked
// and any directions found unworkable during that work move here.

The main open question is therefore not whether solver-based certification is possible in
LLE; the present thesis answers that positively. The open question is how far that
certification framework can be extended — in terms of richer mechanics, richer cooperation
structures, downstream learning effects, and the exact complexity status of the underlying
decision problem — before additional formal layers are required.
