#import "../../macros.typ": formalbox, proofbox, fref

== Notation <notation>

We reuse the level objects introduced in @formalization: the grid dimensions $H$ and $W$, the
position set $P$, the colour set $C$, the direction set $D$, the wall set $cal(W)$, the source
set $cal(S)$, the exit set $cal(E)$, and the start map $s$.

The SAT reduction introduces a finite horizon $T_("max") in NN^+$, which is the maximum number of
joint moves allowed in the bounded decision problem, together with the discrete time-step set
$T = {0, 1, ..., T_("max")}$.

The sets $P_("src")$ and $C_("src")$ are as defined in @formalization. We recall that each colour
appears in at most one laser source; under this assumption, when a source of colour $c$ exists, its
position and direction are uniquely determined by $c$. We write $s(c)$ for the initial position of
agent $c in C$, as defined in #fref(<def-3-1>, [Definition 3.1]).

For the clause-count and complexity statements throughout this chapter, we use the following
shorthand:

#formalbox([Shorthand notation], [
  $
    n_a &= |C| && quad "number of agents (and exits, since" |cal(E)| = |C| ")" \
    p &= |P| = H W && quad "number of grid positions" \
    s &= |cal(S)| && quad "number of laser sources" \
    e &= |cal(E)| && quad "number of exits" \
    tau &= T_("max") + 1 && quad "number of time steps in" T = {0, ..., T_("max")} \
    V &= P without (cal(W) union P_("src")) && quad "walkable cells (no walls, no laser sources)"
  $
])


== Propositional variables

We introduce three families of propositional variables.

- $a_(c,x,y,t)$: true iff agent $c in C$ occupies position $(x, y) in P$ at time step $t in T$.
- $b_(c,d,x,y,t)$: true iff the beam emitted by the source $(c, d, p_s) in cal(S)$ is active at
  position $(x, y) in P$ at time $t in T$.
- $l_(c,x,y,t)$: true iff a laser of colour $c in C_("src")$ is active at position $(x, y) in P$
  at time $t in T$.


== Constraints and logical encoding

We now formalise the constraint families used in the reduction. Each constraint groups a
family of CNF clauses corresponding to one logical component of the bounded-horizon decision
problem. For every constraint we state the clauses in CNF and report two bounds: the maximum
number of *clauses* generated as a function of the input parameters, and the maximum number
of *literals per clause*. These bounds feed directly into the polynomial-size analysis of
@clause-complexity and use the shorthand notation introduced at the end of @notation.

=== Initialisation

#formalbox(kind: "constraint", [Constraint 4.1 (Agent initialisation)], [
  Each agent $c in C$ is placed at its designated starting position $s(c)$ at $t = 0$; all
  other positions are unoccupied by that agent:
  $
    and.big_(c in C) and.big_((x, y) in P)
    cases(
      a_(c,x,y,0) & "if" (x,y) = s(c),
      not a_(c,x,y,0) & "otherwise"
    )
  $
  *Bounds.* Exactly $n_a p$ unit clauses; 1 literal per clause.
]) <constraint-4-1>

#formalbox(kind: "constraint", [Constraint 4.2 (Laser-source initialisation)], [
  For each laser source $(c, d, (x_s, y_s)) in cal(S)$, the beam is active at its origin at
  every time step:
  $
    and.big_((c, d, (x_s, y_s)) in cal(S)) and.big_(t in T) b_(c, d, x_s, y_s, t)
  $
  *Bounds.* Exactly $s tau$ unit clauses; 1 literal per clause.
]) <constraint-4-2>

=== Agent movement

We define the set of positions reachable from $(x, y)$ in one step as $(x, y)$ itself
together with its four grid neighbours, excluding walls and laser-source positions:
$
  "next"(x,y) = {
    (x',y') in {(x,y),(x,y-1),(x+1,y),(x,y+1),(x-1,y)} |
    \ (x',y') in P, (x',y') in.not cal(W), (x',y') in.not P_("src")
  }
$

The relation $"next"$ is symmetric: $(x', y') in "next"(x, y) <==> (x, y) in "next"(x', y')$,
because every LLE move (including staying in place) is reversible by the opposite action. The
same set therefore serves as both successor and predecessor relation, which is why the
backward-consistency constraint below quantifies over $"next"(x, y)$ rather than introducing a
separate $"prev"(x, y)$.

The constraint "each agent occupies at most one position at each time step" can be encoded in
two ways, and we present both because they offer different trade-offs in clause count. The CNF
passed to the solver contains *exactly one* of them, never both: the choice is made at run-time
when the encoding is built. Both formulations admit the same set of satisfying assignments (the
same legal joint trajectories) on top of the forward-consistency clauses; they differ only in
how many clauses they generate and, consequently, in solver run-time. Chapter 7 compares the
two empirically. Schematically, the movement-related clauses of the CNF are
$
  "CNF"_("movement") = "forward consistency" union cases(
    "global uniqueness" & "(formulation A)",
    "local uniqueness" union "backward consistency" & "(formulation B)",
  )
$

#formalbox(kind: "constraint", [Constraint 4.3 (Forward consistency)], [
  If agent $c$ is at position $(x, y)$ at time $t$, it must be at some position in
  $"next"(x, y)$ at time $t + 1$:
  $
    and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P)
    a_(c,x,y,t) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1)
  $
  $
    arrow.t.b.double
  $
  $
    and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P)
    not a_(c,x,y,t) or or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1)
  $
  *Bounds.* At most $n_a (tau - 1) p$ clauses; at most 6 literals per clause (one head literal
  plus $|"next"(x, y)| <= 5$ disjuncts).
]) <constraint-4-3>

#formalbox(kind: "constraint", [Constraint 4.4 (Global uniqueness — formulation A only)], [
  No two distinct positions can both be occupied by agent $c$ at time $t$. The clauses at
  $t = 0$ are already implied by initialisation, so the family ranges over
  $t = 1, ..., T_("max")$:
  $
    and.big_(c in C) and.big_(t = 1)^(T_("max")) and.big_((x_1,y_1) in P)
    and.big_((x_2,y_2) in P, \ (x_2,y_2) eq.not (x_1,y_1))
    not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t)
  $
  *Bounds.* Exactly $n_a (tau - 1) binom(p, 2)$ clauses; 2 literals per clause.
]) <constraint-4-4>

#formalbox(kind: "constraint", [Constraint 4.5 (Local uniqueness — formulation B only)], [
  No two distinct positions in $"next"(x, y)$ can simultaneously be occupied by agent $c$ at
  time $t + 1$:
  $
    and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P)
    and.big_((x',y') in "next"(x,y))
    and.big_((x'',y'') in "next"(x,y), \ (x'',y'') eq.not (x',y'))
    not a_(c,x',y',t+1) or not a_(c,x'',y'',t+1)
  $
  *Bounds.* At most $10 n_a (tau - 1) p$ clauses (since
  $binom(|"next"(x, y)|, 2) <= binom(5, 2) = 10$); 2 literals per clause.
]) <constraint-4-5>

#formalbox(kind: "constraint", [Constraint 4.6 (Backward consistency — formulation B only)], [
  If agent $c$ is at position $(x, y)$ at time $t + 1$, it must have been at some position in
  $"next"(x, y)$ at time $t$ (recall that $"next"$ is symmetric, so it also describes the cells
  from which $(x, y)$ can be reached):
  $
    and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P)
    a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
  $
  $
    arrow.t.b.double
  $
  $
    and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P)
    not a_(c,x,y,t+1) or or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
  $
  *Bounds.* At most $n_a (tau - 1) p$ clauses; at most 6 literals per clause.
]) <constraint-4-6>

#formalbox(kind: "constraint", [Constraint 4.7 (No simultaneous occupation)], [
  Two distinct agents cannot share the same position at the same time, nor can they swap
  positions between consecutive time steps:
  $
    and.big_(c_1 in C) and.big_(c_2 in C, c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t in T)
    not a_(c_1,x,y,t) or not a_(c_2,x,y,t)
  $
  $
    and.big_(c_1 in C) and.big_(c_2 in C, c_2 eq.not c_1) and.big_((x,y) in P)
    and.big_(t = 0)^(T_("max") - 1)
    not a_(c_1,x,y,t+1) or not a_(c_2,x,y,t)
  $
  $
    and.big_(c_1 in C) and.big_(c_2 in C, c_2 eq.not c_1) and.big_((x,y) in P)
    and.big_(t = 0)^(T_("max") - 1)
    not a_(c_1,x,y,t) or not a_(c_2,x,y,t+1)
  $
  *Bounds.* At most $binom(n_a, 2) (3 tau - 2) p$ clauses; 2 literals per clause.
]) <constraint-4-7>

#formalbox(kind: "constraint", [Constraint 4.8 (Victory condition)], [
  Each exit must be occupied by at least one agent at time $T_("max")$:
  $
    and.big_((x,y) in cal(E)) or.big_(c in C) a_(c,x,y,T_("max"))
  $
  This clause only asks that the exits be *covered*; but since there are exactly $n_a$ agents,
  exactly $n_a$ exits, and no two agents can share a cell
  (#fref(<constraint-4-7>, [Constraint 4.7])), covering the $n_a$ exits with $n_a$ distinct
  agents forces every agent onto a distinct exit at $T_("max")$. Every agent therefore reaches
  an exit at the final step.

  *Bounds.* Exactly $e$ clauses; at most $n_a$ literals per clause.
]) <constraint-4-8>

#formalbox(kind: "constraint", [Constraint 4.9 (Stay on exit)], [
  Once an agent reaches an exit, it remains there for all subsequent time steps:
  $
    and.big_(c in C) and.big_((x,y) in cal(E)) and.big_(t = 0)^(T_("max") - 1)
    not a_(c,x,y,t) or a_(c,x,y,t+1)
  $
  *Bounds.* Exactly $n_a e (tau - 1)$ clauses; 2 literals per clause.
]) <constraint-4-9>

=== Laser activity

We define $"next"_d(x, y)$ as the position immediately adjacent to $(x, y)$ in direction $d$:
$
  "next"_d(x,y) = cases(
    (x, y - 1) & "if" d = N,
    (x + 1, y) & "if" d = E,
    (x, y + 1) & "if" d = S,
    (x - 1, y) & "if" d = W
  )
$

#formalbox(kind: "constraint", [Constraint 4.10 (Walls block beams)], [
  A beam cannot be active at a wall position:
  $
    and.big_((c,d,p_s) in cal(S)) and.big_((x,y) in cal(W)) and.big_(t in T)
    not b_(c,d,x,y,t)
  $
  *Bounds.* Exactly $s |cal(W)| tau$ unit clauses; 1 literal per clause.
]) <constraint-4-10>

#formalbox(kind: "constraint", [Constraint 4.11 (Beam propagation)], [
  Beam propagation clauses are instantiated only when the successor cell
  $(x', y') = "next"_d(x, y)$ lies inside the grid, is not a wall, and is not itself a source
  cell. Source cells are handled separately by #fref(<constraint-4-2>, [Constraint 4.2]).
  Under these conditions, the beam is active at $(x', y')$ iff it is active at $(x, y)$ and no
  agent of colour $c$ occupies $(x', y')$:
  $
    and.big_((c,d,p_s) in cal(S)) and.big_(t in T)
    and.big_((x,y) in P without cal(W), \ "next"_d(x,y) in P without cal(W), \ "next"_d(x,y) in.not P_("src"))
    b_(c,d,x',y',t) arrow.l.r (b_(c,d,x,y,t) and not a_(c,x',y',t))
    \ arrow.t.b.double \
    and.big_((c,d,p_s) in cal(S)) and.big_(t in T)
    and.big_((x,y) in P without cal(W), \ "next"_d(x,y) in P without cal(W), \ "next"_d(x,y) in.not P_("src"))
    not b_(c,d,x,y,t) or a_(c,x',y',t) or b_(c,d,x',y',t)
    \
    and.big_((c,d,p_s) in cal(S)) and.big_(t in T)
    and.big_((x,y) in P without cal(W), \ "next"_d(x,y) in P without cal(W), \ "next"_d(x,y) in.not P_("src"))
    b_(c,d,x,y,t) or not b_(c,d,x',y',t)
    \
    and.big_((c,d,p_s) in cal(S)) and.big_(t in T)
    and.big_((x,y) in P without cal(W), \ "next"_d(x,y) in P without cal(W), \ "next"_d(x,y) in.not P_("src"))
    not a_(c,x',y',t) or not b_(c,d,x',y',t)
  $
  *Bounds.* At most $3 s tau p$ clauses (three CNF clauses per admissible propagation edge);
  at most 3 literals per clause.
]) <constraint-4-11>

#formalbox(kind: "constraint", [Constraint 4.12 (Link between beam and laser variables)], [
  Since each colour has at most one source in the instances considered here, the laser variable
  $l_(c,x,y,t)$ is true at a position iff the beam of the unique source of colour $c$ is active
  there:
  $
    and.big_((c,d,p_s) in cal(S)) and.big_((x,y) in P) and.big_(t in T)
    b_(c,d,x,y,t) arrow.l.r l_(c,x,y,t)
  $
  $
    arrow.t.b.double
  $
  $
    and.big_((c,d,p_s) in cal(S)) and.big_((x,y) in P) and.big_(t in T)
    (not b_(c,d,x,y,t) or l_(c,x,y,t)) and (not l_(c,x,y,t) or b_(c,d,x,y,t))
  $
  *Bounds.* Exactly $2 s tau p$ clauses; 2 literals per clause.
]) <constraint-4-12>

#formalbox(kind: "constraint", [Constraint 4.13 (Agents cannot step on active lasers)], [
  An agent of colour $c_1$ cannot occupy a position where an active laser of some source colour
  $c_2 in C_("src")$, with $c_2 eq.not c_1$, is present. Agents are immune only to lasers of
  their own colour:
  $
    and.big_(c_1 in C) and.big_(c_2 in C_("src"), \ c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t in T)
    l_(c_2,x,y,t) arrow.r not a_(c_1,x,y,t)
  $
  $
    arrow.t.b.double
  $
  $
    and.big_(c_1 in C) and.big_(c_2 in C_("src"), \ c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t in T)
    not l_(c_2,x,y,t) or not a_(c_1,x,y,t)
  $
  *Bounds.* At most $n_a s tau p$ clauses; 2 literals per clause.
]) <constraint-4-13>


== Clause complexity and polynomial size <clause-complexity>

To show that the reduction has polynomial size, it is enough to bound the number of clauses
generated as a function of the input parameters introduced in @notation.

We count *clauses* rather than *literals*. A CNF formula is a conjunction of clauses, each
clause being a disjunction of literals. The total literal count is at most a constant factor
larger than the clause count in our encoding, since every clause family generated above contains
at most $max(|"next"(u)| + 1, n_a) <= 6$ literals per clause (the worst case is forward or
backward consistency, with one head literal and $|"next"(u)| <= 5$ disjuncts). Counting clauses
is therefore sufficient to establish a polynomial bound on the formula size, and the same bound
transfers to literals up to a constant factor.

Summing the per-constraint bounds reported in @sat-reduction (the *Bounds* lines of
#fref(<constraint-4-1>, [Constraints 4.1])--#fref(<constraint-4-13>, [4.13])) gives the total
clause count as a polynomial in $n_a$, $p$, $s$, and $tau$. With the global formulation
(formulation A, using Constraint 4.4) the dominant term is
$
  O(n_a tau p^2 + n_a^2 tau p + n_a s tau p)
$
while with the local formulation (formulation B, using Constraints 4.5 and 4.6) it is
$
  O(n_a tau p + n_a^2 tau p + n_a s tau p)
$
These are *asymptotic upper bounds*. The local formulation dominates the global one
asymptotically, since its uniqueness term is linear in $p$ rather than quadratic; the
dominance is not pointwise, however. On sufficiently small grids the global formulation
actually produces fewer clauses than the local one, because the local formulation pays a
constant overhead the global one avoids: a separate backward-consistency family of size
$n_a (tau - 1) p$ (#fref(<constraint-4-6>, [Constraint 4.6])) and a per-cell pairs sum
$sum_(u in V) binom(|"next"(u)|, 2)$ which is large relative to $binom(p, 2)$ when $p$ itself
is small. We therefore keep both formulations and benchmark their actual clause counts and
solver runtimes in @encoding-comparison.

The same loops introduce $O((n_a + s) p tau)$ propositional variables (agent, beam, and laser
indices), also polynomial in the input parameters. The constraints above quantify agent-position
predicates over the full position set $P$; the implementation may safely restrict these to the
walkable subset $V$, since clauses generated at walls and laser-source cells are vacuous under
the initialisation and the `next` filtering. Beam variables at wall cells are forced false by
#fref(<constraint-4-10>, [Constraint 4.10]) and play no role in any satisfying assignment; the
implementation may skip them without affecting correctness.

Since each clause is generated by a simple bounded computation inside these loops, the reduction
itself is computable in polynomial time as well. This justifies the claim that bounded-horizon LLE
solvability is polynomial-time reducible to SAT.

== Correctness of the reduction

#formalbox(kind: "proposition", [Proposition 4.14 (Correctness of the SAT Reduction)], [
  Let $L$ be an LLE level and let $T_("max")$ be a horizon. For either movement formulation
  described above, the CNF formula $Phi(L, T_("max"))$ is satisfiable if and only if there exists a
  valid joint trajectory of length $T_("max")$ for $L$.
]) <prop-4-14>

#proofbox([
  For soundness, assume $Phi(L, T_("max"))$ is satisfiable. Initialisation fixes exactly one start
  position for each agent at time $0$. For the global formulation, forward consistency together
  with pairwise exclusion ensures by induction on time that each agent occupies exactly one legal
  position at every later step. For the local formulation, the same conclusion follows from forward
  consistency, local exclusivity, and backward consistency. We may therefore derive a joint
  trajectory by setting $p_t(c) = (x, y)$, where $(x, y)$ is, for each colour $c$ and time $t$,
  the unique position at which the variable $a_(c,x,y,t)$ is true. The movement clauses enforce legal motion between consecutive steps; the collision clauses
  enforce both simultaneous separation and the no-following-conflict rule; the laser clauses
  enforce safety with respect to active beams; and the exit clauses enforce the terminal
  condition. Hence the extracted trajectory is valid.

  For completeness, assume a valid joint trajectory of length $T_("max")$ is given. Set each
  $a_(c,x,y,t)$ according to whether agent $c$ occupies $(x, y)$ at time $t$ in the trajectory.
  Set beam variables $b_(c,d,x,y,t)$ and laser variables $l_(c,x,y,t)$ according to the
  deterministic beam dynamics induced by the same agent positions. Every clause family is then
  satisfied by construction: initialisation matches the start state; the movement, uniqueness,
  and collision clauses match the trajectory semantics; the propagation iff and beam-laser link
  clauses hold because $b$ and $l$ are set exactly to those deterministic values; the
  agent-laser blocking clauses hold because trajectory validity already forbids any agent from
  standing on an active laser of a different colour; and the final positions occupy all exits.
  Therefore $Phi(L, T_("max"))$ is satisfiable.
  $square.stroked$
])


== Complexity-theoretic consequences

We can now state the consequence for the decision problem introduced in #fref(<def-3-5>, [Definition 3.5]).

The bounded-horizon LLE solvability problem lies in *NP*. A candidate trajectory can be verified in
polynomial time by simulating the joint execution and checking that all agents occupy the exit
tiles at the end without violating the movement, collision, and laser constraints defined in
@formalization.

Combined with the polynomial-time construction above and #fref(<prop-4-14>, [Proposition 4.14]), this shows that
bounded-horizon LLE solvability is polynomial-time many-one reducible to SAT:

$
  "LLE-Solvability" <=""_p "SAT"
$

Thus bounded-horizon LLE solvability is *at most as hard as SAT*: any SAT algorithm yields an
algorithm for this decision problem with only polynomial overhead from the reduction.

Whether bounded-horizon LLE solvability is also *NP-hard* remains open in the present work.
Establishing NP-hardness would require a polynomial-time reduction in the opposite direction, from
a known NP-hard problem to LLE solvability. This thesis does not claim such a result.

It is also important to distinguish proved statements from standard complexity-theoretic beliefs.
The question whether $"P" = "NP"$ remains open. Accordingly, statements here about worst-case
difficulty should be read only through the formal claims we have established: SAT is NP-complete,
bounded-horizon LLE solvability belongs to NP, and the reduction above places bounded-horizon LLE
solvability within the polynomial-time many-one image of SAT.

In practice, this positioning explains why a SAT-based approach is attractive: the solver inherits
the strong empirical performance of modern CDCL SAT solvers on many structured instances, even
though the worst-case complexity remains exponential.
