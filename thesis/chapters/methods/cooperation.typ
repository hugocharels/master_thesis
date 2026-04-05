== Cooperation Detection <cooperation-detection>

=== Strict Laser Semantics

Recall from <sat-reduction> that the standard encoding allows agent $c$ to occupy a cell where a
laser of color $c$ is active — the agent is immune to its own color. The *strict* variant removes
this immunity: every agent is blocked by every laser, regardless of color.

Concretely, the strict encoding adds the following constraint for every agent $c in cal(A)$, every
position $(x, y) in P$, and every time step $t in T$:

$
  and.big_(c in cal(A)) and.big_((x,y) in P) and.big_(t in T) not l_(c,x,y,t) or not a_(c,x,y,t)
$

All other constraints from <sat-reduction> remain unchanged. We call the resulting CNF formula
$Phi_("strict")(L, T)$ and the corresponding solver $"StrictSolver"$.


=== Why This Captures Cooperation

In LLE, the only cooperative act available to an agent is to position itself in the path of a
laser of its own color, thereby blocking the beam and allowing other agents (who are not immune to
that laser) to pass through cells the beam would otherwise reach.

An agent that blocks its own laser receives no benefit from doing so: it is immune to that laser
anyway, so the blocked beam does not protect it. The sole beneficiary is a teammate.

Under strict semantics, stepping on one's own laser is forbidden. Therefore, a level that is
unsolvable under strict semantics is one where every valid solution requires at least one such
blocking act — i.e., genuine cooperation.


=== Formal Theorem and Proof

*Theorem.* Let $L$ be an LLE level and $T$ a time horizon. Then $L$ requires cooperation (with
horizon $T$) if and only if $Phi(L, T)$ is satisfiable and $Phi_("strict")(L, T)$ is
unsatisfiable.

*Proof.*

$(arrow.r)$ Assume $L$ requires cooperation with horizon $T$. By definition, $L$ is solvable, so
$Phi(L, T)$ is satisfiable. Suppose for contradiction that $Phi_("strict")(L, T)$ is also
satisfiable. Then there exists a valid strict trajectory $sigma$ of length $T$ reaching all exits.
In $sigma$, no agent ever occupies a cell where its own laser is active. Since $sigma$ is also
valid under standard semantics (strict constraints are a superset of standard constraints), $sigma$
is a valid standard solution in which no agent blocks its own laser. But this contradicts the
assumption that $L$ requires cooperation: every valid solution must contain a cooperative blocking
act. Therefore $Phi_("strict")(L, T)$ is unsatisfiable. $square.stroked$

$(arrow.l)$ Assume $Phi(L, T)$ is satisfiable and $Phi_("strict")(L, T)$ is unsatisfiable. The
first condition means $L$ is solvable. The second means there is no valid strict trajectory
reaching all exits — i.e., every valid standard solution contains at least one time step $t$ and
agent $c$ such that $a_(c,x,y,t)$ and $l_(c,x,y,t)$ are both true for some $(x, y)$: agent $c$
occupies a cell where its own laser is active. As argued above, this act is only beneficial to
other agents. Therefore every solution requires at least one cooperative act, so $L$ requires
cooperation. $square.stroked$


=== Practical Algorithm

The cooperation detector runs two SAT calls on the same level:

+ Run $"Solver"(L, T)$: if UNSAT, the level is unsolvable — stop.
+ Run $"StrictSolver"(L, T)$: if UNSAT, the level requires cooperation.

Both calls share the same variable factory and differ only in the additional strict constraint
clauses added in step 2. The total cost is two calls to a modern CDCL solver.

#lorem(3) // TODO: add note on time horizon choice — how T_max is determined in practice
