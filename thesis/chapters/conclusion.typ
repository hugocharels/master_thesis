== Summary

This thesis developed a SAT-based framework for generating LLE levels with formal guarantees. We
first reduced bounded-horizon LLE solvability to satisfiability of a CNF formula, then defined a
strict beam-semantics counterfactual that turns cooperation detection into a second SAT query on
the same level. On top of these decision procedures, we implemented a family of random,
constrained, and constructive generators whose outputs are certified by the solver before
acceptance.

The first experimental evaluation compared two movement formulations inside the SAT encoding. The
results showed that the local formulation is the better default for the levels studied here: once
the instances move beyond the smallest toy case, it produces substantially smaller CNF formulas and
lower runtimes than the global all-pairs formulation.


== Limitations

The current framework remains deliberately scoped. The encoding is tailored to the subset of LLE
mechanics needed for solvability and cooperation analysis, so features such as gems and void tiles
are abstracted away. The guarantees are also horizon-bounded: the solver decides whether a level is
solvable within a fixed $T_("max")$, not whether it is solvable under an unbounded notion of play.
Finally, the empirical results reported here cover only the movement-formulation comparison; they
do not yet constitute a full evaluation of generator acceptance rates, diversity, or downstream
learnability.


== Future Work

Several natural extensions follow from these limitations.

- Extend the experimental section with generator-focused studies: acceptance rates, cooperation
  profile frequencies, and diversity measures across parameter regimes.
- Generalise the encoding to richer LLE mechanics or to other cooperative grid environments, while
  preserving the same solver-in-the-loop methodology.
- Investigate whether learnability can be linked to structural properties of the generated levels,
  for example by combining the current formal guarantees with curriculum design or MARL training
  experiments.
- Refine the cooperation-profile analysis so that it becomes not only a filtering mechanism for
  generators, but also an evaluation tool for the qualitative structure of cooperative tasks.
