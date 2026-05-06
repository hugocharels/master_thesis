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

The empirical evaluation covers three aspects of the framework. The SAT encoding comparison shows
that the local uniqueness formulation is the preferable default: it yields substantially smaller
CNF formulas and lower runtimes as instances grow. The rejection-rate and profile-distribution
experiments characterise the practical cost of the acceptance oracle and the output diversity of
the generator family. Finally, the transfer experiment evaluates whether agents trained on
certified cooperative levels can generalise to human-designed benchmark levels.



== Future Work

Several directions extend the present work naturally.

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
