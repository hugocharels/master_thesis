== Summary

This thesis developed a SAT-based framework for reasoning about solvability and cooperation in a
modeled subset of the Laser Learning Environment. We first formalised bounded-horizon solvability as
a decision problem, then reduced it to satisfiability of a CNF formula. On top of that reduction,
we introduced a strict beam-semantics counterfactual that turns the blocking-based cooperation
mechanism of LLE into a second decision problem on the same level.

These decision procedures were then embedded inside a family of procedural generators. The resulting
framework does not guarantee that generated levels are pedagogically optimal for MARL, but it does
guarantee that accepted levels satisfy the formal properties checked by the solver. This is the
central contribution of the thesis: procedural generation coupled to explicit certification rather
than procedural generation guided only by heuristic plausibility.

The empirical results reported in this thesis are narrower than the full framework. What has been
evaluated experimentally is the effect of two alternative movement encodings inside the SAT model.
That experiment shows that the local uniqueness formulation is the preferable default on the tested
levels because it yields substantially smaller CNF formulas and lower runtimes once the instances
move beyond the smallest toy case.


== Limitations

The current work has four important limitations.

- The formal model covers only the subset of LLE needed for solvability and cooperation analysis.
  Mechanics such as gems and void tiles are outside the scope of the reduction.
- The guarantees are horizon-bounded. The solver decides whether a level is solvable within a fixed
  $T_("max")$, not whether it is solvable under an unbounded notion of play.
- The cooperation notion studied here is intentionally specific: it captures same-colour
  beam-truncation as the relevant cooperative act. It does not claim to exhaust every possible
  interpretation of cooperation in multi-agent environments.
- The downstream effect of generated levels on MARL training has not been evaluated. The generator
  framework produces certified levels, but whether those levels lead to faster or more stable
  learning than uncertified baselines remains an open empirical question.

These limitations do not invalidate the present results, but they do define their exact scope. The
thesis establishes a formal generation-and-certification framework for a specific LLE model and
provides an initial empirical characterisation of the generator family. It does not yet close the
loop with downstream learning experiments.


== Future Work

Several extensions follow directly from these limitations.

- *Downstream MARL evaluation.* The most direct open question is whether certified cooperative
  levels improve training of MARL agents compared to uncertified baselines. A natural experiment
  would train a value-decomposition agent @Sunehag2018 such as VDN or QMIX @Rashid2018 on a
  curriculum of generated levels and evaluate on the default LLE benchmark levels. The generation
  infrastructure and cooperation profile targets are already in place; only the training loop
  remains.
- *Parameter sensitivity and diversity.* The current acceptance-rate experiments use fixed agent
  and laser counts per grid size. A fuller characterisation would vary these parameters to locate
  the practical frontier at which rejection rates become prohibitive, and would measure diversity
  of accepted levels within a fixed parameter setting.
- *Richer cooperation metrics.* The cooperation profile taxonomy used here covers five dependency
  structures. Extensions could include synchronous cooperation (agents that must coordinate in the
  same timestep) and chain length as a difficulty axis. These richer targets are already defined in
  the cooperation profile notes; their generation and evaluation remain future work.
- *Model extension.* Incorporating gem tiles and void tiles into the formal model would expand the
  scope of the formal guarantees. Gems introduce an additional reachability condition; void tiles
  require a revised movement semantics. Both extensions preserve the SAT-based architecture.
- *Formal NP-hardness.* The present thesis shows that bounded-horizon LLE solvability is in NP and
  is reducible to SAT. Whether it is NP-hard — that is, whether there exists a polynomial-time
  reduction from a known NP-hard problem to LLE solvability — remains open and would be a
  worthwhile theoretical complement.

The main open question is therefore not whether solver-based certification is possible in LLE; the
present thesis answers that positively. The open question is how far that certification framework
can be extended — in terms of richer mechanics, richer cooperation structures, and downstream
learning effects — before additional formal layers are required.
