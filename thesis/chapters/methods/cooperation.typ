== Cooperation Detection <cooperation-detection>

=== Strict Laser Semantics

Recall from <sat-reduction> that the standard encoding allows agent $c in C$ to occupy a cell
where a laser of colour $c$ is active - the agent is immune to its own colour. The *strict*
variant removes this immunity: every agent is blocked by every laser, regardless of colour.

Concretely, the strict encoding adds the following constraint for every agent $c in C$, every
position $(x, y) in P$, and every time step $t in T$:

$
  and.big_(c in C) and.big_((x,y) in P) and.big_(t in T) not l_(c,x,y,t) or not a_(c,x,y,t)
$

All other constraints from <sat-reduction> remain unchanged. We denote the resulting CNF formula by
$Phi_("strict")(L, T)$ and the corresponding solver by $"StrictSolver"$.


=== Why This Captures Cooperation

Under the LLE mechanics considered in this thesis, the relevant cooperative act is for an agent to
position itself on a beam of its own colour, thereby blocking that beam and allowing other agents
to traverse cells that would otherwise remain unsafe.

An agent that blocks its own laser receives no direct navigational benefit from doing so: it is
already immune to that beam. The beneficiary is a teammate whose path becomes traversable only after
the blocking action.

Strict semantics forbids exactly this action. Therefore, if a level is solvable under the standard
semantics but unsatisfiable under the strict semantics, every successful standard solution must rely
on at least one such blocking step.


=== Formal Theorem and Proof

*Theorem.* Let $L$ be an LLE level and $T$ a time horizon. Then $L$ requires cooperation with
horizon $T$ if and only if $Phi(L, T)$ is satisfiable and $Phi_("strict")(L, T)$ is unsatisfiable.

*Proof.*

$(arrow.r)$ Assume that $L$ requires cooperation with horizon $T$. By definition, $L$ is solvable,
so $Phi(L, T)$ is satisfiable. Suppose for contradiction that $Phi_("strict")(L, T)$ is also
satisfiable. Then there exists a valid strict trajectory $sigma$ of length $T$ whose final
positions occupy all exit tiles. Because the strict constraints only add restrictions, every strict
trajectory is also a valid standard trajectory. But in $sigma$, no agent ever occupies a cell where
its own laser is active. Hence $sigma$ is a valid standard solution that contains no cooperative
laser-blocking act, contradicting the assumption that cooperation is required. Therefore
$Phi_("strict")(L, T)$ is unsatisfiable. $square.stroked$

$(arrow.l)$ Assume that $Phi(L, T)$ is satisfiable and $Phi_("strict")(L, T)$ is unsatisfiable. The
first condition implies that $L$ is solvable under the standard semantics. The second condition
implies that no valid strict trajectory reaches the exits. Since the only difference between the
two semantics is whether an agent may stand on a beam of its own colour, every standard solution
must contain at least one time step $t$, one agent $c in C$, and one position $(x, y) in P$ such
that both $a_(c,x,y,t)$ and $l_(c,x,y,t)$ hold. Such a step is precisely a same-colour
laser-blocking act. Under the LLE mechanics, this act can only help another agent; it does not
create a new traversal option for the blocking agent itself. Therefore every successful standard
solution requires at least one cooperative act, so $L$ requires cooperation. $square.stroked$


=== Practical Algorithm

The cooperation detector runs two SAT calls on the same level:

+ Run $"Solver"(L, T)$. If the result is UNSAT, the level is unsolvable for horizon $T$, so it is
  rejected before cooperation is considered.
+ Run $"StrictSolver"(L, T)$. If the result is UNSAT, the level requires cooperation for the same
  horizon $T$.

Both calls share the same bounded horizon and differ only in the additional strict constraint
clauses. In practice, the detector should always use the same horizon as the standard solvability
check. For benchmark levels, this horizon can be chosen from known minimal solution lengths; for
generated levels, it is the user-supplied generation parameter $T_("max")$.
