#import "../macros.typ": fref

== Summary

This thesis developed a SAT-based framework for reasoning about solvability and cooperation in
the Laser Learning Environment. We first formalised bounded-horizon solvability as a decision
problem and reduced it to satisfiability of a CNF formula. On top of that reduction, we introduced
a strict beam-semantics counterfactual that turns the blocking-based cooperation mechanism of LLE
into a second decision problem on the same level, and refined the binary outcome into a
cooperation profile taxonomy that classifies the dependency structure of a cooperative level.

These decision procedures were then embedded inside a family of procedural generators. The
resulting framework does not guarantee that generated levels are optimal training material for
MARL, but it does guarantee that accepted levels satisfy the formal properties checked by the
solver. This is the central contribution of the thesis: procedural generation coupled to
*explicit certification* rather than procedural generation guided only by heuristic
plausibility.


== Answering the research questions

We restate the six research questions of @introduction and assess what each chapter delivers.

- *RQ1: formal verification of solvability.* We answered this in @sat-reduction by reducing
  bounded-horizon LLE solvability to the satisfiability of a CNF formula, whose correctness is
  established by #fref(<prop-4-14>, [Proposition 4.14]). The encoding is polynomial-time
  constructible, which places bounded-horizon LLE solvability in NP and shows the problem is at
  most as hard as SAT.

- *RQ2: formal verification of the cooperation requirement.* We answered this in
  @cooperation-detection with a strict beam-semantics counterfactual, whose correctness is
  established by #fref(<thm-5-1>, [Theorem 5.1]): a level requires cooperation if and only if the
  standard formula is SAT and the strict formula is UNSAT. The criterion is decidable on the same
  finite horizon used for solvability, so cooperation is certified at no extra modelling cost.

- *RQ3: embedding verification inside a generator.* We answered this with the generator family
  of @generators. Each generator calls the SAT solver as an acceptance oracle, so every emitted
  level carries a solver certificate of the property it advertises rather than a heuristic guess.

- *RQ4: controlling the cooperation profile.* We answered this constructively. The
  cooperation-profile analyser of @cooperation-profiles labels every certified cooperative level,
  and the generators expose a profile filter that restricts acceptance to a chosen subset of the
  taxonomy. The profile-distribution experiment of @profile-distribution shows that the
  constructive generator reliably produces *mutual* profiles when $n_l >= 2$ and admits
  *distributed* profiles when $n_l >= 3$ on large enough grids. The *fully coupled* label did not
  arise in the tested parameter range and remains a target for the parameter-sensitivity study
  below.

- *RQ5: learnability of certified cooperative levels.* We answered this positively on a small
  grid. The learnability experiment of @learnability-experiment shows that IQL, VDN, and QMIX all
  reach non-trivial greedy success ($0.59$–$0.70$ on the training pool, $0.18$–$0.23$ on the
  held-out pool) on the $5 times 5$ cooperative pool within a 200,000-step budget, with
  generalisation rather than credit assignment as the dominant difficulty. The data-scaling
  experiment of @data-scaling-experiment then shows this gap is a data-quantity effect, not an
  algorithmic limit: enlarging the certified training pool to five hundred levels closes the
  train–test gap from $0.50$ to approximately zero. Certification thus delivers a concrete
  downstream payoff, since more certified data converts overfitting into generalisation.

- *RQ6: curriculum transfer to LLE Level 6.* We answered this negatively, within scope. The
  experiments of @curriculum-strategy-experiment and @transfer-experiment show that, for the
  value-based algorithms evaluated here, a curriculum of generated levels confers no advantage. On
  a reachable asymmetric target, ordering the stages does not beat direct training and only data
  diversity helps; on the mutually-cooperative LLE Level 6, no condition, including a four-stage
  curriculum trained for two million steps, exceeds zero success, and neither does direct training.
  Because the agents also fail on the in-distribution generated pool, the obstacle is that the base
  task is unlearnable by these methods, not that curriculum transfer fails. We therefore read RQ6
  as a scoped negative result, and we identify the bottleneck as the inability of these value-based
  methods to learn mutual coordination at all, rather than the design of the curriculum.


== Future work

Several directions extend the present work naturally.

- *Complexity classification of bounded-horizon LLE solvability.* This thesis places the problem
  in NP and reduces it to SAT, but settles neither bound: we prove neither NP-hardness nor
  membership in P, so both remain open (see @sat-reduction). The two outcomes carry opposite
  consequences. If the problem is NP-hard, the SAT-based oracle is optimal up to constant factors
  under the standard $"P" eq.not "NP"$ assumption. If it lies in P, a polynomial-time algorithm
  tailored to the LLE structure could replace the SAT solver, with a worst-case speed-up for every
  generator in the family, although, as @sat-reduction notes, the solver is already fast on the
  instances we generate. Settling the classification either way is both a theoretical complement
  to this work and an engineering lever for the generator pipeline.
- *Model extension to gems and void tiles.* The formal model deliberately omits gems and
  treats void tiles as walls. Incorporating gem tiles would add an additional reachability
  condition (every agent must visit a designated gem cell before reaching its exit) and would
  extend the property certified by the SAT oracle accordingly. Distinguishing
  void tiles from walls would require a revised movement semantics (agents cannot enter void
  cells under any condition, but the cell still propagates beams differently). Both extensions
  preserve the SAT-based architecture; only the encoding and the formal definitions need to be
  updated.
- *Parameter sensitivity and output diversity.* The acceptance-rate experiments fix the agent
  and laser counts at each grid size. A fuller characterisation would vary these parameters
  along independent axes to locate the practical frontier at which rejection rates become
  prohibitive, would measure the within-pool diversity of accepted levels at a fixed parameter
  setting, and would attempt to surface the *fully coupled* profile by raising $n_l$ and the
  grid size.
- *Richer cooperation metrics.* The cooperation-profile taxonomy of @cooperation-profiles
  captures five dependency-graph patterns. Extensions could promote the synchronous-width
  scalar already exposed by the analyser into a first-class profile axis, and could add a
  chain-length difficulty axis on top of the qualitative chain label. The dependency graph is also
  static; making it time-indexed, with each edge active only at the timesteps where one agent's
  block actually opens a cell for another, would expose temporal properties such as how long a
  dependency must hold, which a static graph cannot capture. On larger grids with more lasers,
  where a single beneficiary may depend on several beams being blocked, the edges could also carry
  weights recording how many blocking actions each dependency requires, turning the qualitative
  graph into a quantitative one. These richer targets would let the generator family target
  *graded* cooperation difficulty rather than only qualitative profile families.
- *Algorithm-space breadth.* The learnability and curriculum-transfer experiments evaluate
  three value-based algorithms (IQL, VDN, QMIX). Comparison against
  centralised-critic actor-critic methods such as MADDPG @Lowe2017MADDPG and COMA
  @Foerster2018COMA, and against latent-variable variants such as MAVEN @Mahajan2019MAVEN,
  would give a fuller picture of which algorithm families benefit most from certified
  training material on coordination-critical tasks.
- *Making mutual coordination learnable.* The curriculum experiments of @transfer-experiment
  locate the obstacle to solving LLE Level 6 in the base learnability of *mutual* cooperation
  under a sparse joint-exit reward, not in the ordering of training levels: no curriculum can
  amplify a learning signal that is identically zero. The natural levers therefore act on the
  reward and the algorithm rather than on the curriculum. A dense or intrinsic reward that credits
  partial coordination, for instance an agent successfully blocking a beam for another, would
  supply the signal whose absence we identify as the bottleneck, and the centralised-critic or
  coordinated-exploration methods listed above could supply the representational capacity that
  monotonic value decomposition lacks. With a base learner able to acquire mutual coordination in
  isolation, the curriculum question of RQ6 could be revisited on a foundation that the present
  value-based methods do not provide.

The main open question is therefore not whether solver-based certification is possible in
LLE; the present thesis answers that positively. The open question is how far that
certification framework can be extended (in terms of richer mechanics, richer cooperation
structures, downstream learning effects, and the exact complexity status of the underlying
decision problem) before additional formal layers are required.
