#import "../../macros.typ": formalbox, proofbox

== Strict SAT Encoding

Recall from Definition 3.6 that strict beam semantics changes only one aspect of the dynamics:
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


== Why This Captures Cooperation

Under the LLE mechanics studied here, the cooperative action of interest is for an agent to occupy
a cell that would otherwise allow its own beam to continue, thereby making another agent's path
safe. Standard solvability allows this beam-truncation mechanism; strict solvability removes it.

Therefore, if a level is solvable under the standard semantics but unsatisfiable under the strict
semantics, every successful standard solution must rely on at least one same-colour beam-truncation
step.


== Formal Theorem and Proof

#formalbox([Theorem 4.9 (Cooperation Detection Criterion)], [
  Let $L$ be an LLE level and $T_("max")$ a time horizon. Then $L$ requires cooperation with
  horizon $T_("max")$ if and only if $Phi(L, T_("max"))$ is satisfiable and
  $Phi_("strict")(L, T_("max"))$ is unsatisfiable.
])

#proofbox([
  $(arrow.r)$ Assume that $L$ requires cooperation with horizon $T_("max")$. By Definition 3.7,
  $L$ is solvable under the standard semantics, so $Phi(L, T_("max"))$ is satisfiable. Suppose for
  contradiction that $Phi_("strict")(L, T_("max"))$ is also satisfiable. Then there exists a strict
  trajectory whose final positions occupy all exit tiles. Since strict beam semantics differs from
  the standard one only by removing same-colour beam truncation, such a trajectory is also a valid
  standard trajectory that succeeds without using that mechanism. This contradicts Definition 3.7.
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


== Horizon-Dependence of the Cooperation Criterion <horizon-dependence>

Theorem 4.9 binds cooperation to a fixed horizon $T_("max")$. This is not an artefact of the SAT
encoding: it is the only sense in which cooperation is decidable in this framework. Solvability
itself is a horizon-indexed property (Definition 3.4), and so is the companion cooperation
requirement (Definition 3.7). The horizon is therefore a true parameter of the cooperation label,
and the same level can switch classification when $T_("max")$ changes.

The mechanism behind this sensitivity is straightforward. The strict SAT encoding refuses
same-colour beam truncation but leaves every other movement and timing constraint identical to the
standard one. Hence the strict solver can find a satisfying trajectory simply because there exists
a path long enough to walk *around* the laser geometry rather than *through* it, even though the
short, natural solution would step into the beam and shield another agent. As soon as the horizon
$T_("max")$ admits such a detour, the strict formula becomes satisfiable and the level stops being
labelled cooperative — regardless of what the natural solution does.

*Example: detour bypass.* @fig-horizon-demo shows a $4 times 4$ grid that makes this concrete.
Two agents start in the top row; their only exits sit in the bottom row, and a single red laser
covers two cells of row 1. Running the cooperation analyzer on this level at three different
horizons reproduces all three failure modes at once (@tab-horizon-demo).

#figure(
  image("../../../results/cooperation_examples/horizon_demo.png", width: 28%),
  caption: [
    Horizon-dependence demo level. Two agents in the top row; a red laser spans two cells of
    row 1; two exits in the bottom row.
  ],
) <fig-horizon-demo>

#figure(
  table(
    columns: 3,
    stroke: black,
    inset: 8pt,
    align: horizon,
    table.header([*$T_("max")$*], [*Standard SAT*], [*Profile label*]),
    [2],  [UNSAT],         [— (rejected as unsolvable)],
    [3],  [SAT, strict UNSAT], [`asymmetric`, edges ${(0, 1)}$],
    [9], [SAT, strict SAT],   [`independent`],
  ),
  caption: [
    Cooperation classification of the level in @fig-horizon-demo at three horizons. With
    $T_("max") = 2$ no agent has time to reach an exit, so the standard solver returns UNSAT
    and cooperation is never tested. With $T_("max") = 3$ — the tightest horizon at which the
    level is solvable — cooperation is required: the only feasible plan uses red same-colour
    truncation. With $T_("max") = 9$ — the smallest horizon admitting a detour around the beam
    — the strict solver finds a trajectory in which the blue agent walks around the beam, so
    cooperation is no longer flagged.
  ],
) <tab-horizon-demo>

The same level therefore receives three qualitatively different labels depending on the chosen
horizon — *unsolvable*, *cooperative*, or *non-cooperative* — without the level itself changing.
The phenomenon generalises: any level whose natural short solution uses beam truncation can be
made to look non-cooperative by raising $T_("max")$ until a geometric detour fits, and can be
made to look unsolvable by lowering $T_("max")$ until even the natural solution does not.

*Practical consequence.* The criterion is *sound* but *horizon-sensitive*. Choosing $T_("max")$
too generously under-detects cooperation by allowing geometric detours; choosing it too tightly
makes the standard solver itself UNSAT, so the level is rejected as unsolvable before cooperation
is even tested. Both failure modes shift the operating point in opposite directions, and neither
contradicts Theorem 4.9, which states cooperation strictly *relative to* a chosen horizon.

The recipe used throughout this thesis is to pick $T_("max")$ as the smallest horizon at which a
representative short solution of the geometry is expected to fit, with a small additive slack. For
the parameter configurations of @experiments this means horizons proportional to the grid
diameter (concrete values are listed alongside each experimental configuration). Under that
choice, the criterion is tight enough that accepted levels reliably exhibit the intended
beam-truncation behaviour at their stated horizon, and loose enough that the underlying standard
solver does not spuriously reject solvable instances.


== Practical Algorithm

The cooperation detector runs two SAT calls on the same level:

+ Run $"Solver"(L, T_("max"))$. If the result is UNSAT, the level is unsolvable for that horizon,
  so it is rejected before cooperation is considered.
+ Run $"StrictSolver"(L, T_("max"))$. If the result is UNSAT, the level requires cooperation for
  the same horizon.

Both calls share the same bounded horizon and differ only in the beam-propagation clauses. For
benchmark levels, the horizon can be chosen from known solution lengths; for generated levels, it
is the user-supplied generation parameter $T_("max")$.


== Cooperation Profiles <cooperation-profiles>

Theorem 4.9 yields a *binary* answer: a level either requires cooperation or it does not. Once the
binary criterion holds, however, several qualitatively different cooperation structures fall under
that single label, and the generators of @generators rely on this finer distinction to target
specific patterns. The cooperation profile analyzer operates on top of the binary detector and
produces a richer classification by combining three pieces of derived data:

+ a *helper-event set* extracted from one satisfying assignment of $Phi(L, T_("max"))$;
+ a *necessary-helper set* identified by colour-wise counterfactual SAT calls; and
+ a *dependency graph* between agents, built from the helper events.

The decision procedure produces one of seven labels:

- *unsolvable*: $Phi(L, T_("max"))$ is UNSAT.
- *independent*: cooperation is not required.
- *cooperative*: cooperation is required, but the extracted plan exhibits no observable helper
  event (a fallback used when the dependency graph happens to be empty).
- *asymmetric*: at least one one-way helping relation exists, with none of the richer
  structures below.
- *mutual*: two agents help each other.
- *chain*: helper events form a directed path with no branching.
- *distributed*: at least one agent benefits from two or more distinct helpers.
- *fully coupled*: every agent belongs to a single strongly connected component of the
  dependency graph.

The remainder of this section makes each underlying object precise and gives one geometric example
per family.

=== Selective-Strict Semantics

Some profile decisions require asking whether a single agent is *individually* indispensable as a
helper. To support this, the SAT encoding offers a *selective-strict* laser mode, parameterised
by a set of colours $S subset.eq C_("src")$:

- for every source $(c, d, p_s) in cal(S)$ with $c in S$, the beam-propagation clauses use the
  strict equivalence of @sat-reduction;
- for every source $(c, d, p_s) in cal(S)$ with $c in.not S$, the standard equivalence is used.

When $S = nothing$, the encoding coincides with the standard semantics; when $S = C_("src")$, it
coincides with the strict semantics of Definition 3.6. Intermediate choices forbid same-colour
truncation for the colours in $S$ while leaving the remaining beams untouched. The implementation
uses
```python
WorldSolver(world, laser_mode=LaserMode.SELECTIVE_STRICT, strict_colors=S)
```
for an arbitrary colour set $S$. Selective-strict is the SAT lever that lets us single out one
helper at a time without affecting the other beams.

=== Helper Events from a SAT Model

Given a satisfying assignment of $Phi(L, T_("max"))$, the analyzer recovers the joint trajectory
$sigma = (p_0, ..., p_(T_("max"))).$ For each time step $t$ and each ordered pair of distinct
agents $(c, c')$, a *helper event* with helper $c$, beneficiary $c'$, and time $t$ is recorded if
two geometric conditions hold:

+ agent $c$ stands at time $t$ on a cell that lies on the unblocked beam path of the source of
  colour $c$, so the beam of colour $c$ is truncated by $c$ at position $p_t(c)$; and
+ agent $c'$ stands at time $t$ on a cell strictly downstream of $p_t(c)$ on the same beam path,
  so $c'$ would lie inside the un-truncated beam and is therefore protected by $c$.

Helper events are an *observable of the chosen joint plan*, not an invariant of the level. A
cooperative level typically admits many joint plans, and different plans may yield different
helper-event sets.

=== Necessary Helpers

The *necessary-helper set* is, by contrast, a property of the level itself. For every colour
$c in C_("src")$ the analyzer runs one selective-strict SAT call with $S = {c}$. If the call
returns UNSAT, the colour $c$ is added to the set. Operationally, $c$ is necessary when the level
cannot be solved as soon as $c$ alone is barred from helping with its own beam, even though every
other agent retains that ability.

The necessary-helper set does not depend on which standard model the solver returns: each
counterfactual is its own one-shot satisfiability check, independent of the joint plan chosen
elsewhere.

=== Dependency Graph

Helper events induce a directed graph $G_L = (V, E)$ on the set of agents:

$
  V = C, quad E = {(c, c') | exists t : (c, c', t) "is a helper event"}.
$

Multiple helper events between the same ordered pair $(c, c')$ — possibly at different time
steps and along different beam paths — collapse into a single edge. The time dimension is
otherwise discarded; a separate scalar, the *synchronous width*, records the maximum number of
distinct helpers active at the same time step and is exposed alongside the profile label without
entering the classification decision.

=== Profile Families

The profile label is the output of a small decision procedure applied to $G_L$, with the binary
cooperation requirement as a hard precondition. The priority order is *fully coupled $succ$ mutual
$succ$ distributed $succ$ chain $succ$ asymmetric $succ$ cooperative*, so a level matching several
criteria is labelled by the strongest one. We describe each label below with a short geometric
example.

*Independent.* The binary detector returns non-cooperative: $Phi_("strict")(L, T_("max"))$ is
satisfiable, so no agent ever has to truncate a beam. The profile analyzer short-circuits and
returns `independent`. *Example.* A grid with two agents whose direct paths to their respective
exits do not cross any beam at all (@fig-profile-independent).

#figure(
  image("../../../results/cooperation_examples/independent.png", width: 35%),
  caption: [
    `independent`: two agents with disjoint direct paths to two exits. No laser is present,
    so the strict-SAT encoding admits the same trajectory as the standard one.
  ],
) <fig-profile-independent>

*Cooperative (no observed helper).* Binary cooperation holds — strict-SAT is UNSAT — yet the
extracted plan contains no helper event. This is unusual in practice; it arises when the SAT
solver returns a model in which beam truncation is realised through a timing arrangement that
the event extractor does not register as a clean helper-beneficiary pair. The label `cooperative`
is the residual classification used when the dependency graph is empty but cooperation is
required.

*Asymmetric.* The dependency graph has at least one edge $(c, c') in E$, no mutual pair, no
chain extending beyond a single edge, no shared beneficiary, and the agents do not all belong
to a single SCC. *Example.* Two agents of distinct colours; only the red beam blocks the blue
agent's path to its exit, so the red agent must step into its own beam at some moment to let
the blue agent pass. The reciprocal situation never arises since there is no blue beam. The
dependency graph has the single edge $0 arrow 1$ (@fig-profile-asymmetric).

#figure(
  image("../../../results/cooperation_examples/asymmetric.png", width: 35%),
  caption: [
    `asymmetric`: one red laser splits the grid horizontally. The red agent (top-left) crosses
    its own beam unscathed; the blue agent (top-right) requires red to truncate the beam so it
    can reach the bottom-right exit. Edges: ${(0, 1)}$.
  ],
) <fig-profile-asymmetric>

*Mutual.* The dependency graph contains a mutual pair, i.e. both edges $(c, c'), (c', c) in E$
for some pair $c eq.not c'$. *Example.* Two laser sources of distinct colours, each crossing
the other agent's path: each agent must truncate its own beam to shield the other at some
point in the plan (@fig-profile-mutual). Both edges are present, and a level is classified as
`mutual` even when additional one-way edges between other pairs also exist, as long as the
agents do not all belong to a single strongly connected component.

#figure(
  image("../../../results/cooperation_examples/mutual.png", width: 35%),
  caption: [
    `mutual`: two stacked beams of distinct colours. Each agent is immune to its own beam
    but must wait for the other to truncate the foreign beam before crossing. Edges:
    ${(0, 1), (1, 0)}$.
  ],
) <fig-profile-mutual>

*Chain.* The dependency graph is a directed path: every vertex has in-degree and out-degree at
most one, the longest chain has length at least two (i.e. at least two consecutive edges), and
that longest chain visits every participating vertex. *Example.* Three agents arranged so that
agent $0$ must shield agent $1$ across the red beam, agent $1$ must shield agent $2$ across
the blue beam, and neither agent $2$ nor agent $0$ has any further helping role
(@fig-profile-chain). The graph is $0 arrow 1 arrow 2$.

#figure(
  image("../../../results/cooperation_examples/chain.png", width: 35%),
  caption: [
    `chain`: three agents and two beams. Walls confine each agent to a separate region so
    helping flows in one direction only — red helps blue across the red beam, blue helps the
    third agent across the blue beam. Edges: ${(0, 1), (1, 2)}$.
  ],
) <fig-profile-chain>

*Distributed.* At least one agent has in-degree $>= 2$ in the dependency graph. *Example.*
Three agents in which two distinct same-colour helpers (agents $0$ and $1$) must each
truncate their respective beams to free agent $2$'s path to its exit (@fig-profile-distributed).
The edges are ${(0, 1), (0, 2), (1, 2)}$, so agent $2$ has in-degree two and the level is
`distributed`. (The extra edge $(0, 1)$ does not promote the level to `mutual` because the
reciprocal edge $(1, 0)$ is absent.)

#figure(
  image("../../../results/cooperation_examples/distributed.png", width: 35%),
  caption: [
    `distributed`: agent $2$ must traverse both the red and the blue beam to reach its exit,
    requiring truncation from both other agents. In-degree of agent $2$ is two. Edges:
    ${(0, 1), (0, 2), (1, 2)}$.
  ],
) <fig-profile-distributed>

*Fully coupled.* The largest strongly connected component of the dependency graph has size
$|C|$ and $|C| > 1$. *Example.* Three agents in which every pair of agents helps each other,
yielding a directed cycle on all three agents and a strongly connected component of size three
(@fig-profile-fully-coupled). This is the strictest profile and is rare on small grids.

#figure(
  image("../../../results/cooperation_examples/fully_coupled.png", width: 35%),
  caption: [
    `fully_coupled`: three agents and three beams stacked, so every agent must shield, and be
    shielded by, both others to reach the bottom row of exits. The complete dependency graph
    has all six edges between distinct agents. Edges:
    ${(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)}$.
  ],
) <fig-profile-fully-coupled>

The analyzer also exposes the auxiliary scalars used by the decision procedure (longest chain
length, largest SCC size, synchronous width) so downstream code can re-classify levels under a
different policy without re-running any SAT calls.


*Scope note.* The cooperation notion defined here is intentionally specific: it captures
same-colour beam-truncation as the relevant cooperative act. A level that requires two agents to
coordinate their movements for unrelated geometric reasons — without any laser blocking being
involved — would not be identified as cooperative by this detector. This definition is not claimed
to exhaust every possible interpretation of cooperation in multi-agent environments; it is the
specific mechanism studied in this benchmark, and the formal guarantee is scoped accordingly.

*Model-dependence of finer-grained analyses.* The binary detector above is a property of the
*level*: the satisfiability of $Phi(L, T_("max"))$ and $Phi_("strict")(L, T_("max"))$ does not
depend on which satisfying assignment the SAT solver happens to return. The necessary-helper set
of @cooperation-profiles is likewise an invariant of the level, being a sequence of one-shot
satisfiability checks. The full profile label, however, depends on the helper events extracted
from a single standard model, which the SAT solver chooses without any preference among
satisfying assignments. A cooperative level typically admits many valid joint plans, and
different plans may exhibit different helping patterns: an agent that helps another in one
solution may be passive in another. The profile label therefore reflects the structure of the
extracted plan, not an intrinsic invariant of the level. This is acceptable for the generation
use case considered here — the analyzer still acts as a sound filter that certifies the extracted
plan exhibits the targeted profile — but two solver runs on the same level can in principle yield
different profile labels.
