#import "../../macros.typ": formalbox, proofbox

== Cooperation Detection <cooperation-detection>

=== Strict SAT Encoding

Recall from Definition 4.6 that strict beam semantics changes only one aspect of the dynamics:
same-colour occupancy no longer truncates the corresponding beam. Same-colour immunity is
unchanged.

Accordingly, the strict SAT encoding keeps the standard laser-safety clauses and replaces only the
same-colour beam-propagation rule. For every source $(c, d, p_s) in cal(S)$, every admissible
propagation edge from $(x, y)$ to $(x', y')$, and every time step $t in T$, the strict encoding
uses

$
  b_(c,d,x',y',t) arrow.l.r b_(c,d,x,y,t)
$

instead of the standard equivalence
$
  b_(c,d,x',y',t) arrow.l.r (b_(c,d,x,y,t) and not a_(c,x',y',t)).
$

Thus the beam continues through agents of the matching colour instead of stopping at them. We
denote the resulting CNF formula by $Phi_("strict")(L, T_("max"))$ and the corresponding solver by
$"StrictSolver"$.


=== Why This Captures Cooperation

Under the LLE mechanics studied here, the cooperative action of interest is for an agent to occupy
a cell that would otherwise allow its own beam to continue, thereby making another agent's path
safe. Standard solvability allows this beam-truncation mechanism; strict solvability removes it.

Therefore, if a level is solvable under the standard semantics but unsatisfiable under the strict
semantics, every successful standard solution must rely on at least one same-colour beam-truncation
step.


=== Formal Theorem and Proof

#formalbox([Theorem 4.9 (Cooperation Detection Criterion)], [
  Let $L$ be an LLE level and $T_("max")$ a time horizon. Then $L$ requires cooperation with
  horizon $T_("max")$ if and only if $Phi(L, T_("max"))$ is satisfiable and
  $Phi_("strict")(L, T_("max"))$ is unsatisfiable.
])

#proofbox([
  $(arrow.r)$ Assume that $L$ requires cooperation with horizon $T_("max")$. By Definition 4.7,
  $L$ is solvable under the standard semantics, so $Phi(L, T_("max"))$ is satisfiable. Suppose for
  contradiction that $Phi_("strict")(L, T_("max"))$ is also satisfiable. Then there exists a strict
  trajectory whose final positions occupy all exit tiles. Since strict beam semantics differs from
  the standard one only by removing same-colour beam truncation, such a trajectory is also a valid
  standard trajectory that succeeds without using that mechanism. This contradicts Definition 4.7.
  Therefore $Phi_("strict")(L, T_("max"))$ is unsatisfiable.

  $(arrow.l)$ Assume that $Phi(L, T_("max"))$ is satisfiable and
  $Phi_("strict")(L, T_("max"))$ is unsatisfiable. The first condition implies that $L$ is solvable
  under the standard semantics. Suppose that some successful standard trajectory used no
  same-colour beam-truncation step. Then the same joint positions would also satisfy the strict
  beam semantics, because the only semantic difference between the two models concerns exactly that
  truncation mechanism. This would yield a satisfying assignment for
  $Phi_("strict")(L, T_("max"))$, contradicting unsatisfiability. Hence every successful standard
  trajectory must use at least one same-colour beam-truncation step, so $L$ requires cooperation
  with horizon $T_("max")$. $square.stroked$
])


=== Practical Algorithm

The cooperation detector runs two SAT calls on the same level:

+ Run $"Solver"(L, T_("max"))$. If the result is UNSAT, the level is unsolvable for that horizon,
  so it is rejected before cooperation is considered.
+ Run $"StrictSolver"(L, T_("max"))$. If the result is UNSAT, the level requires cooperation for
  the same horizon.

Both calls share the same bounded horizon and differ only in the beam-propagation clauses. For
benchmark levels, the horizon can be chosen from known solution lengths; for generated levels, it
is the user-supplied generation parameter $T_("max")$.
