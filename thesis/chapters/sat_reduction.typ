#import "../macros.typ": formalbox, proofbox

=== Definition of Sets

We reuse the level objects introduced in <formalization>: the grid dimensions $H$ and $W$, the
position set $P$, the colour set $C$, the direction set $D$, the wall set $cal(W)$, the source
set $cal(S)$, the exit set $cal(E)$, and the start map $s$.

The SAT reduction introduces a finite horizon $T_("max") in NN$, which is the maximum number of
joint moves allowed in the bounded decision problem, together with the discrete time-step set
$T = {0, 1, ..., T_("max")}$.

We also define
$
  P_("src") = {p in P | exists c in C, d in D : (c, d, p) in cal(S)}
$
for the set of source positions.

We further write
$
  C_("src") = {c in C | exists d in D, p in P : (c, d, p) in cal(S)}
$
for the set of colours that actually have a source.

To match the benchmark and generated instances studied in this thesis, we assume that each colour
appears in at most one laser source. Under this assumption, when a source of colour $c$ exists, its
position and direction are uniquely determined by $c$.

We also write $"start"(c) in P$ for the initial position of agent $c in C$.


=== Definition of Variables

We introduce three families of propositional variables.

- $a_(c,x,y,t)$: true iff agent $c in C$ occupies position $(x, y) in P$ at time step $t in T$.
- $b_(c,d,x,y,t)$: true iff the beam emitted by the source $(c, d, p_s) in cal(S)$ is active at
  position $(x, y) in P$ at time $t in T$.
- $l_(c,x,y,t)$: true iff a laser of colour $c in C_("src")$ is active at position $(x, y) in P$
  at time $t in T$.


=== Constraints and Logical Encoding

We now formalise the constraint families used in the reduction. Each group of clauses corresponds
to one logical component of the bounded-horizon decision problem.

+ *Initialization*

  - *Agents:* \
    Each agent $c in C$ is placed at its designated starting position $"start"(c)$ at $t = 0$;
    all other positions are unoccupied by that agent:
    $
      and.big_(c in C) and.big_((x, y) in P)
      cases(
        a_(c,x,y,0) & "if" (x,y) = "start"(c),
        not a_(c,x,y,0) & "otherwise"
      )
    $

  - *Laser sources:* \
    For each laser source $(c, d, (x_s, y_s)) in cal(S)$, the beam is always active at its origin,
    at every time step:
    $
      and.big_((c, d, (x_s, y_s)) in cal(S)) and.big_(t in T) b_(c, d, x_s, y_s, t)
    $


+ *Agent Movements*

  We define the set of positions reachable from $(x, y)$ in one step as $(x, y)$ itself together
  with its four grid neighbours, excluding walls and laser-source positions:
  $
    "next"(x,y) = {
      (x',y') in {(x,y),(x,y-1),(x+1,y),(x,y+1),(x-1,y)} |
      \ (x',y') in P, (x',y') in.not cal(W), (x',y') in.not P_("src")
    }
  $

  - *Forward consistency:* \
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

  Two methods are proposed to enforce that each agent occupies at most one position at each time
  step.

  - *Global uniqueness:* \
    No two distinct positions can both be occupied by agent $c$ at time $t$:
    $
      and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1) in P)
      and.big_((x_2,y_2) in P, \ (x_2,y_2) eq.not (x_1,y_1))
      not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t)
    $

  - *Local uniqueness:* \
    No two distinct positions in $"next"(x, y)$ can simultaneously be occupied by agent $c$ at
    time $t + 1$:
    $
      and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P)
      and.big_((x',y') in "next"(x,y))
      and.big_((x'',y'') in "next"(x,y), \ (x'',y'') eq.not (x',y'))
      not a_(c,x',y',t+1) or not a_(c,x'',y'',t+1)
    $

    *Backward consistency:* \
    If agent $c$ is at position $(x, y)$ at time $t + 1$, it must have been at some position in
    $"next"(x, y)$ at time $t$:
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

  - *No simultaneous occupation:* \
    Two distinct agents cannot share the same position at the same time, nor can they move to a
    position already occupied by the other agent:
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

  - *Victory condition:* \
    Each exit must be occupied by at least one agent at time $T_("max")$. Since $|cal(E)| = n_a$
    and agents cannot share positions, this enforces a bijection between agents and exits:
    $
      and.big_((x,y) in cal(E)) or.big_(c in C) a_(c,x,y,T_("max"))
    $

  - *Stay on exit:* \
    Once an agent reaches an exit, it remains there for all subsequent time steps:
    $
      and.big_(c in C) and.big_((x,y) in cal(E)) and.big_(t = 0)^(T_("max") - 1)
      not a_(c,x,y,t) or a_(c,x,y,t+1)
    $


+ *Laser Activity*

  We define $"next"_d(x, y)$ as the position immediately adjacent to $(x, y)$ in direction $d$:
  $
    "next"_d(x,y) = cases(
      (x, y - 1) & "if" d = N,
      (x + 1, y) & "if" d = E,
      (x, y + 1) & "if" d = S,
      (x - 1, y) & "if" d = W
    )
  $

  - *Walls block beams:* \
    A beam cannot be active at a wall position:
    $
      and.big_((c,d,p_s) in cal(S)) and.big_((x,y) in cal(W)) and.big_(t in T)
      not b_(c,d,x,y,t)
    $

  - *Beam propagation:* \
    Beam propagation clauses are instantiated only when the successor cell
    $(x', y') = "next"_d(x, y)$ lies inside the grid, is not a wall, and is not itself a source
    cell. Source cells are handled separately by the initialization clauses above. Under these
    conditions, the beam is active at $(x', y')$ iff it is active at $(x, y)$ and no agent of
    colour $c$ occupies $(x', y')$:
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

  - *Link between beam and laser variables:* \
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

  - *Agents cannot step on active lasers:* \
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


=== Clause Complexity and Polynomial Size

To show that the reduction has polynomial size, it is enough to bound the number of generated
clauses as a function of the input parameters. Let
$
  n = |C|,\ p = |P| = H W,\ s = |cal(S)|,\ e = |cal(E)|,\ tau = T_("max") + 1
$
and write
$
  V = P without (cal(W) union P_("src"))
$
for the walkable cells.

We count clauses rather than literals. The main families admit the following bounds.

- *Initialization.*
  The agent-initialisation clauses contribute exactly $n p$ unit clauses, and the laser-source
  initialisation contributes exactly $s tau$ unit clauses.

- *Movement constraints.*
  Forward consistency contributes at most $n (tau - 1) p$ clauses.
  The two uniqueness formulations differ here:
  $
    "global uniqueness" = n (tau - 1) binom(p, 2)
  $
  $
    "local uniqueness" = n (tau - 1) sum_(u in V) binom(|"next"(u)|, 2)
  $
  Since $|"next"(u)| <= 5$, the local uniqueness term is bounded by
  $
    n (tau - 1) 10 |V| <= 10 n (tau - 1) p
  $
  and backward consistency contributes at most $n (tau - 1) p$ further clauses.
  The collision and conservative hand-off clauses contribute at most
  $
    binom(n, 2) (tau + 2 (tau - 1)) p = binom(n, 2) (3 tau - 2) p
  $
  The exit condition contributes exactly $e$ clauses, and the stay-on-exit condition contributes
  exactly $n e (tau - 1)$ clauses.

- *Laser constraints.*
  The laser-safety clauses contribute at most $n s tau p$ clauses.
  Beam propagation contributes at most $3 s tau p$ clauses, because each admissible propagation edge
  yields either one wall-blocking clause or three equivalence clauses.
  The beam/laser linking clauses contribute exactly $2 s tau p$ clauses.

Therefore the total number of clauses is polynomial in $n$, $p$, $s$, and $tau$. More precisely,
with the global formulation the dominant term is
$
  O(n tau p^2 + n^2 tau p + n s tau p)
$
while with the local formulation it is
$
  O(n tau p + n^2 tau p + n s tau p)
$
Since each clause is generated by a simple bounded computation inside these loops, the reduction
itself is computable in polynomial time as well. This justifies the claim that bounded-horizon LLE
solvability is polynomial-time reducible to SAT.

=== Correctness of the Reduction

#formalbox([Proposition 4.8 (Correctness of the SAT Reduction)], [
  Let $L$ be an LLE level and let $T_("max")$ be a horizon. For either movement formulation
  described above, the CNF formula $Phi(L, T_("max"))$ is satisfiable if and only if there exists a
  valid joint trajectory of length $T_("max")$ for $L$.
])

#proofbox([
  For soundness, assume $Phi(L, T_("max"))$ is satisfiable. Initialization fixes exactly one start
  position for each agent at time $0$. For the global formulation, forward consistency together
  with pairwise exclusion ensures by induction on time that each agent occupies exactly one legal
  position at every later step. For the local formulation, the same conclusion follows from forward
  consistency, local exclusivity, and backward consistency. We may therefore define a joint
  trajectory $p_t(c)$ by reading off the unique true agent variable for each colour $c$ and time
  $t$. The movement clauses enforce legal motion between consecutive steps; the collision clauses
  enforce both simultaneous separation and the conservative hand-off rule; the laser clauses
  enforce safety with respect to active beams; and the exit clauses enforce the terminal
  condition. Hence the extracted trajectory is valid.

  For completeness, assume a valid joint trajectory of length $T_("max")$ is given. Set each
  $a_(c,x,y,t)$ according to whether agent $c$ occupies $(x, y)$ at time $t$ in the trajectory.
  Set beam variables $b_(c,d,x,y,t)$ and laser variables $l_(c,x,y,t)$ according to the
  deterministic beam dynamics induced by the same agent positions. Every clause family is then
  satisfied by construction: initialization matches the start state, movement and collision clauses
  match the trajectory semantics, beam propagation follows the induced laser dynamics, and the
  final positions occupy all exits. Therefore $Phi(L, T_("max"))$ is satisfiable.
  $square.stroked$
])


=== Complexity-Theoretic Consequences

We can now state the consequence for the decision problem introduced in Definition 4.5.

The bounded-horizon LLE solvability problem lies in *NP*. A candidate trajectory can be verified in
polynomial time by simulating the joint execution and checking that all agents occupy the exit
tiles at the end without violating the movement, collision, and laser constraints defined in
<formalization>.

Combined with the polynomial-time construction above and Proposition 4.8, this shows that
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
