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
- The experimental evaluation does not yet validate the full generator family. Acceptance rates,
  diversity, cooperation-profile frequencies, and downstream MARL usefulness remain to be studied.

These limitations do not invalidate the present results, but they do define their exact scope. The
thesis establishes a formal generation-and-certification framework for a specific LLE model; it does
not yet provide a complete empirical study of the generated level distribution.


== Future Work

Several extensions follow directly from these limitations.

- Extend the empirical section with generator-focused studies: acceptance rates, parameter
  sensitivity, diversity measures, and cooperation-profile distributions.
- Evaluate the cost of cooperation detection itself, not only the cost of the base solvability
  reduction.
- Enrich the model to cover a larger subset of LLE mechanics, while keeping the logical guarantees
  explicit.
- Investigate whether the current formal guarantees correlate with downstream learning behaviour in
  MARL, for example through curriculum design or controlled training experiments on generated level
  families.

The main open question is therefore not whether solver-based certification is possible in LLE; the
present thesis answers that positively. The open question is how far that certification framework
can be extended before richer mechanics and richer evaluation criteria require an additional formal
layer.
