#import "../../macros.typ": formalbox, fref, proofbox
#import "@preview/lovelace:0.3.0": pseudocode-list

== Strict SAT encoding

Recall from #fref(<def-3-6>, [Definition 3.6]) that strict beam semantics changes only one aspect of the dynamics:
same-colour occupancy no longer blocks the corresponding beam. Same-colour immunity is
unchanged.

Accordingly, the strict SAT encoding keeps the standard laser-safety clauses and replaces only the
same-colour beam-propagation rule. For every source $(c, d, p_s) in cal(S)$, every admissible
propagation edge from $(x, y)$ to $(x', y')$ (in the sense of @sat-reduction, i.e. a successor
inside the grid, not a wall, and not a source cell), and every time step $t in T$, the strict
encoding uses

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


== Why this captures cooperation

Under the LLE mechanics studied here, the cooperative action of interest is for an agent to occupy
a cell that would otherwise allow its own beam to continue, thereby making another agent's path
safe. Standard solvability allows this beam-blocking mechanism; strict solvability removes it.

Therefore, if a level is solvable under the standard semantics but unsatisfiable under the strict
semantics, every successful standard solution must rely on at least one same-colour beam-blocking
step.


== Formal theorem and proof

#formalbox(kind: "theorem", [Theorem 5.1 (Cooperation Detection Criterion)], [
  Let $L$ be an LLE level and $T_("max")$ a time horizon. Then $L$ requires cooperation with
  horizon $T_("max")$ if and only if $Phi(L, T_("max"))$ is satisfiable and
  $Phi_("strict")(L, T_("max"))$ is unsatisfiable.
]) <thm-5-1>

#proofbox([
  $(arrow.r)$ Assume that $L$ requires cooperation with horizon $T_("max")$. By #fref(<def-3-7>, [Definition 3.7]),
  $L$ is solvable under the standard semantics, so $Phi(L, T_("max"))$ is satisfiable. Suppose for
  contradiction that $Phi_("strict")(L, T_("max"))$ is also satisfiable. Then there exists a strict
  trajectory whose final positions occupy all exit tiles. Since strict beam semantics differs from
  the standard one only by removing same-colour beam-blocking, such a trajectory is also a valid
  standard trajectory that succeeds without using that mechanism. This contradicts #fref(<def-3-7>, [Definition 3.7]).
  Therefore $Phi_("strict")(L, T_("max"))$ is unsatisfiable.

  $(arrow.l)$ Assume that $Phi(L, T_("max"))$ is satisfiable and
  $Phi_("strict")(L, T_("max"))$ is unsatisfiable. The first condition implies that $L$ is solvable
  under the standard semantics. Suppose, for contradiction, that some successful standard
  trajectory uses no same-colour beam-blocking step: no agent $c$ ever stands on a
  cell of the unblocked beam path of the source of colour $c$. Under that hypothesis the two semantics produce identical beam
  states for this trajectory: the standard rule blocks the beam of colour $c$ only at a cell
  occupied by agent $c$, and by assumption no such occupancy occurs, so each beam reaches the
  same wall or grid boundary as it would under the strict rule. The same variable assignment
  therefore satisfies $Phi_("strict")(L, T_("max"))$, contradicting unsatisfiability. Hence every
  successful standard trajectory must use at least one same-colour beam-blocking step, so $L$
  requires cooperation with horizon $T_("max")$. $square.stroked$
])


== Horizon-dependence of the cooperation criterion <horizon-dependence>

#fref(<thm-5-1>, [Theorem 5.1]) binds cooperation to a fixed horizon $T_("max")$. This is not an artefact of the SAT
encoding: it is the only sense in which cooperation is decidable in this framework. Solvability
itself is a horizon-indexed property (#fref(<def-3-4>, [Definition 3.4])), and so is the companion cooperation
requirement (#fref(<def-3-7>, [Definition 3.7])). The horizon is therefore a true parameter of the cooperation label,
and the same level can switch classification when $T_("max")$ changes.

The mechanism behind this sensitivity is straightforward. The strict SAT encoding refuses
same-colour beam-blocking but leaves every other movement and timing constraint identical to the
standard one. Hence the strict solver can find a satisfying trajectory simply because there exists
a path long enough to walk *around* the laser geometry rather than *through* it, even though the
short, natural solution would step into the beam and shield another agent. As soon as the horizon
$T_("max")$ admits such a detour, the strict formula becomes satisfiable and the level stops being
labelled cooperative, regardless of what the natural solution does.

*Example: detour bypass.* @fig-horizon-demo shows a $4 times 4$ grid that makes this concrete.
Two agents start in the top row; their only exits sit in the bottom row, and a single red laser
covers two cells of row 1. Running the cooperation analyser on this level at three different
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
    stroke: none,
    inset: (x: 12pt, y: 4pt),
    align: (left, center, center),
    table.hline(stroke: 1pt),
    table.header([*Horizon range*], [*Solvable*], [*Cooperation required*]),
    table.hline(stroke: 0.5pt),
    [$0 <= T_("max") <= 2$], [no], [n/a],
    [$3 <= T_("max") <= 8$], [yes], [yes],
    [$T_("max") >= 9$], [yes], [no],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Cooperation classification of the level in @fig-horizon-demo across three horizon ranges.
    For $T_("max") <= 2$ no agent has time to reach an exit, so the standard solver returns
    UNSAT and cooperation is never tested. For $3 <= T_("max") <= 8$ the level is solvable
    but only via red same-colour blocking, so cooperation is required. For $T_("max") >= 9$ a
    detour around the beam fits: the strict solver finds a trajectory in which the green agent
    walks around the beam, and cooperation is no longer flagged.
  ],
) <tab-horizon-demo>

The same level therefore receives three qualitatively different labels depending on the chosen
horizon (*unsolvable*, *cooperative*, or *non-cooperative*), without the level itself changing.
The phenomenon generalises: any level whose natural short solution uses beam-blocking can be
made to look non-cooperative by raising $T_("max")$ until a geometric detour fits, and can be
made to look unsolvable by lowering $T_("max")$ until even the natural solution does not.

In practice, the criterion correctly identifies cooperation at any *fixed* horizon, but the label
it assigns is not an intrinsic property of the level: it depends on the choice of $T_("max")$.
Two opposing failure modes follow. If $T_("max")$ is set too generously, geometric detours
become available and cooperation is under-detected; if it is set too tightly, the standard solver
returns UNSAT and the level is rejected as unsolvable before cooperation is tested at all.
Neither outcome contradicts #fref(<thm-5-1>, [Theorem 5.1]), which applies strictly relative to
the chosen horizon.

The recipe used throughout this thesis is to pick $T_("max")$ as the smallest horizon at which a
representative short solution of the geometry is expected to fit, with a small margin
proportional to the grid diameter (concrete values are listed alongside each experimental
configuration in @experiments). Under that
choice, the criterion is tight enough that accepted levels reliably exhibit the intended
beam-blocking behaviour at their stated horizon, and loose enough that the underlying standard
solver does not spuriously reject solvable instances.


== Practical algorithm

The cooperation detector runs two SAT calls on the same level, in the order shown in
@alg-cooperation. The first call rejects unsolvable levels; the second decides cooperation by
checking the strict counterfactual under the same horizon. Both calls share the same bounded
horizon and differ only in the beam-propagation clauses. For benchmark levels, the horizon can
be chosen from known solution lengths; for generated levels, it is the user-supplied generation
parameter $T_("max")$.

#figure(
  kind: "algorithm",
  supplement: [Algorithm],
  pseudocode-list(booktabs: true, numbered-title: [*CooperationDetection* ($L$, $T_("max")$)])[
    - *Input:* level $L$, horizon $T_("max")$
    - *Output:* one of `UNSOLVABLE`, `COOPERATIVE`, `NON_COOPERATIVE`
    + *if* $"Solver"(L, T_("max")) = "UNSAT"$ *then return* `UNSOLVABLE`
    + *if* $"StrictSolver"(L, T_("max")) = "UNSAT"$ *then return* `COOPERATIVE`
    + *return* `NON_COOPERATIVE`
  ],
  caption: [
    Cooperation detection on level $L$ at horizon $T_("max")$. The first call rejects
    unsolvable levels; the second decides cooperation by checking the strict counterfactual
    under the same horizon.
  ],
) <alg-cooperation>


== Cooperation profiles <cooperation-profiles>

#fref(<thm-5-1>, [Theorem 5.1]) yields a *binary* answer: a level either requires cooperation or it does not. Once the
binary criterion holds, however, several qualitatively different cooperation structures fall under
that single label. This section refines the binary verdict into a *cooperation profile*, computed
by a *profile analyser* layered on top of the binary detector. The profile is not an end in
itself: it is the *generation target* that lets the generators of @generators request a specific
kind of cooperation, and the quantity whose per-generator distribution we report in @experiments.

Two properties shape everything that follows. First, the profile
is computed from a *dependency graph* between agents, itself built from a *helper-event set*
extracted from *one* satisfying assignment of $Phi(L, T_("max"))$. It therefore describes the
cooperation structure of a single extracted plan and is *not* an invariant of the level: two
solver runs can in principle disagree (we return to this in the closing remark of the chapter). It
is best read as a sound *filter*: when the analyser returns a profile, the extracted plan provably
exhibits it. Second, alongside the label the analyser reports a *necessary-helper set*, identified
by colour-wise counterfactual SAT calls; unlike the label, this set *is* a level invariant, and it
complements the label without entering the classification decision.

The decision procedure produces one of seven labels, previewed here by their intuition and defined
precisely, with geometric examples, in @sec-profile-families:

- *unsolvable*: $Phi(L, T_("max"))$ is UNSAT.
- *independent*: cooperation is not required.
- *asymmetric*: one-way helping.
- *chain*: help relayed along a line of agents.
- *distributed*: one agent helped by several others.
- *mutual*: two agents help each other.
- *fully coupled*: every agent helps every other and is helped by every other (not necessarily a direct help).

Every label is constructible within LLE's $1 <= n_a <= 4$ regime: `asymmetric` and `fully_coupled`
need at least two agents; the remaining labels are reachable from three agents upward.
The taxonomy therefore does not require any structural configuration that LLE cannot host.

When several of these patterns occur in the same level, the analyser reports only the one we
consider most cooperative, following the priority
$ "fully coupled" succ "mutual" succ "distributed" succ "chain" succ "asymmetric" $
from strongest to weakest, which guarantees every level a unique top-ranked label. This order is
total by deliberate choice rather than mathematical necessity: the graph structure alone fixes only
a coarser partial order, and we extend it by ranking all-to-all coupling above a single one-way
relation, a judgement another author could reasonably make differently. @sec-ordering-structure
makes the partial order, its structural basis, and this extension precise.

The remainder of the section is organised as follows. @sec-helper-events and @sec-dep-graph
introduce the two pieces of machinery, helper events and the dependency graph, needed to
read the profile catalogue, which is then presented with geometric LLE examples in
@sec-profile-families. @sec-ordering-structure formalises the priority order used by the
classifier when a single graph matches several profiles and clarifies why the order is a
labelling rule rather than a hierarchy on the underlying graph categories. The remaining two
subsections cover auxiliary analyser outputs that do not affect the label decision:
selective-strict semantics (@sec-selective-strict) and the necessary-helper set
(@sec-necessary-helpers).

=== Helper events from a SAT model <sec-helper-events>

Given a satisfying assignment of $Phi(L, T_("max"))$, the analyser recovers the joint trajectory
$sigma = (p_0, ..., p_(T_("max"))).$ For each time step $t$ and each ordered pair of distinct
agents $(c, c')$, a *helper event* with helper $c$, beneficiary $c'$, and time $t$ is recorded if
two geometric conditions hold:

+ agent $c$ stands at time $t$ on a cell that lies on the unblocked beam path of a source of
  colour $c$, so that source's beam is blocked by $c$ at position $p_t(c)$; and
+ agent $c'$ stands at time $t$ on a cell strictly downstream of $p_t(c)$ on the same beam path,
  so $c'$ would lie inside the unblocked beam and is therefore protected by $c$.

Helper events are a *property of the chosen joint plan*: a different satisfying plan may yield
a different set. A helper event records only that $c$ *did* shield $c'$ in this plan, not that
$c'$ *needed* $c$, since in another plan the beneficiary might reach its exit by a different
route. Edges therefore assert observed help, not necessity; necessity is certified separately by
the necessary-helper set of @sec-necessary-helpers.

=== Dependency graph <sec-dep-graph>

Fix the satisfying assignment $sigma$ of $Phi(L, T_("max"))$ from which the helper events of
@sec-helper-events were read. These events induce a directed graph $G_(L, sigma) = (V, E)$ on the
set of agents,

$
  V = C, quad E = {(c, c') | exists t : (c, c', t) "is a helper event of" sigma},
$

in which an edge $c arrow c'$ points from helper to beneficiary. If $c$ helps $c'$ several times,
possibly at different time steps or along different beams, the two are still joined by a single
edge. The time dimension is otherwise discarded by the graph; to retain one
trace of it we expose a separate scalar, the *synchronous width*, the maximum number of distinct
helpers active at the same time step. It captures a difficulty axis the time-collapsed graph
cannot express, namely whether cooperation must occur *simultaneously* (several agents shielding
at once) or can be spread sequentially over the horizon. It is reported alongside the profile
label but does not enter the classification decision.

Since the helper events are read from a single model $sigma$, so is $G_(L, sigma)$; where the
model is fixed or immaterial we abbreviate it to $G_L$.

=== Profile families <sec-profile-families>

The profile label is the output of a small decision procedure applied to $G_L$, with the binary
cooperation requirement as a hard precondition. When a single graph matches several profiles,
a priority order over labels (formalised in @sec-ordering-structure) selects the strongest one;
the two non-cooperative labels (`unsolvable` and `independent`) short-circuit before this order
is consulted. We describe each label below with a short geometric example.

*Independent.* The binary detector returns non-cooperative: $Phi_("strict")(L, T_("max"))$ is
satisfiable, so no agent ever has to block a beam. The profile analyser short-circuits and
returns `independent`. *Example.* A grid with two agents whose direct paths to their respective
exits do not cross any beam at all (@fig-profile-independent).

#figure(
  grid(
    columns: (auto, auto),
    column-gutter: 1.5em,
    align: center + horizon,
    image("../../../results/cooperation_examples/independent.png", height: 4cm),
    image("../../../results/cooperation_examples/dep_independent.png", width: 3.5cm),
  ),
  caption: [
    `independent`: two agents with disjoint direct paths to two exits. No laser is present,
    so the strict-SAT encoding admits the same trajectory as the standard one. The
    dependency graph (right) has no edges.
  ],
) <fig-profile-independent>

*Asymmetric.* The residual category: cooperation is required, but $G_L$ matches none of the four
structural patterns below: no relay (chain), no agent helped by two others (distributed), no
reciprocal pair (mutual), and no strong connectivity (fully coupled). The label covers both the
typical case (a small set of one-way edges) and the degenerate case where the extracted plan
contains no observable helper event at all (e.g. when the helper sits at the last cell of its own
beam path).
*Example.* Two agents of distinct colours; only the red beam blocks the green agent's path
to its exit, so the red agent must step into its own beam at some moment to let the green
agent pass. The reciprocal situation never arises since there
is no green beam. The dependency graph has the single edge $"red" arrow "green"$
(@fig-profile-asymmetric).

#figure(
  grid(
    columns: (auto, auto),
    column-gutter: 1.5em,
    align: center + horizon,
    image("../../../results/cooperation_examples/asymmetric.png", height: 4cm),
    image("../../../results/cooperation_examples/dep_asymmetric.png", width: 3.5cm),
  ),
  caption: [
    `asymmetric`: one red laser splits the grid horizontally. The red agent (top-left) crosses
    its own beam unscathed; the green agent (top-right) requires red to block the beam so it
    can reach the bottom-right exit. Edges: $"red" arrow "green"$.
  ],
) <fig-profile-asymmetric>

*Chain.* Cooperation is required, the dependency graph contains a directed *simple* path of length
at least two (a relay through at least three distinct agents: some agent helps one agent and is
helped by a different one), and none of the richer profiles below applies. The simplest case is a single linear handoff, as in the example. *Example.* Three agents arranged so that
the red agent must shield the green agent across the red beam, the green agent must shield the
blue agent across the green beam, and neither the blue agent nor the red agent has any further
helping role (@fig-profile-chain). The graph is $"red" arrow "green" arrow "blue"$.

#figure(
  grid(
    columns: (auto, auto),
    column-gutter: 1.5em,
    align: center + horizon,
    image("../../../results/cooperation_examples/chain.png", height: 4cm),
    image("../../../results/cooperation_examples/dep_chain.png", width: 3.5cm),
  ),
  caption: [
    `chain`: three agents and two beams. Walls confine each agent to a separate region so
    helping flows in one direction only: red helps green across the red beam, green helps blue
    across the green beam. Edges: ${"red" arrow "green", "green" arrow "blue"}$.
  ],
) <fig-profile-chain>

*Distributed.* At least one agent has in-degree $>= 2$ in the dependency graph. *Example.*
Three agents in which two distinct same-colour helpers (the red and green agents) must each
block their respective beams to free the blue agent's path to its exit (@fig-profile-distributed).
The edges are ${"red" arrow "blue", "green" arrow "blue"}$, so the blue
agent has in-degree two and the level is
`distributed`. Note that the taxonomy grades cooperation by *in-degree*,
how many distinct helpers a single beneficiary depends on, and deliberately gives no separate
profile to the mirror case of one helper that shields several beneficiaries (a high *out-degree*
hub). We classify the structure of *support received* rather than of *help given*; such a hub
therefore contributes only through the in-degrees it induces and, absent any richer pattern, falls
under `asymmetric`.

#figure(
  grid(
    columns: (auto, auto),
    column-gutter: 1.5em,
    align: center + horizon,
    image("../../../results/cooperation_examples/distributed.png", height: 4cm),
    image("../../../results/cooperation_examples/dep_distributed.png", width: 3.5cm),
  ),
  caption: [
    `distributed`: the blue agent must traverse both the red and the green beam to reach its exit,
    requiring blocking from both other agents. In-degree of the blue agent is two. Edges:
    ${"red" arrow "blue", "green" arrow "blue"}$.
  ],
) <fig-profile-distributed>

*Mutual.* The dependency graph contains a mutual pair, i.e. both edges $(c, c'), (c', c) in E$
for some pair $c eq.not c'$. *Example.* Two laser sources of distinct colours, each crossing
the other agent's path: each agent must block its own beam to shield the other at some
point in the plan (@fig-profile-mutual). Both edges are present, and a level is classified as
`mutual` even when additional one-way edges between other pairs also exist, as long as the
agents do not all belong to a single strongly connected component. Because *fully coupled* takes
priority in the decision order, the `mutual` label is only reachable with $n_a >= 3$ agents:
when $n_a = 2$, a reciprocal pair is itself a strongly connected component spanning the whole
agent set (size $2 = n_a > 1$), so the level is labelled `fully_coupled` and the `mutual` branch
is never reached. The example in @fig-profile-mutual therefore includes a third agent (blue) on an
independent path, outside the reciprocal pair, which keeps the largest strongly connected
component at size two while $n_a = 3$.

#figure(
  grid(
    columns: (auto, auto),
    column-gutter: 1.5em,
    align: center + horizon,
    image("../../../results/cooperation_examples/mutual.png", height: 4cm),
    image("../../../results/cooperation_examples/dep_mutual.png", width: 3.5cm),
  ),
  caption: [
    `mutual`: a red and a green beam stacked. Each agent is immune to its own beam
    but must wait for the other to block the foreign beam before crossing. A third agent (blue)
    on an independent path is required to keep the profile distinct from `fully_coupled`: with
    only the reciprocal pair the red and green agents would form a strongly connected component
    spanning the whole agent set. The blue agent participates in no helper relationship, hence
    appears as an isolated vertex in the dependency graph. Edges: ${"red" arrow "green", "green" arrow "red"}$.
  ],
) <fig-profile-mutual>

*Fully coupled.* The dependency graph is strongly connected: its single strongly connected
component (SCC) spans the entire agent set (size $n_a > 1$). *Example.* Three agents in which every
pair helps each other, so the dependency graph is the complete
digraph#footnote[A digraph is a directed graph: every edge has a direction. "Complete" means there
  is an arc between every ordered pair of distinct vertices.] $K_(n_a)^("*")$, which is
trivially strongly connected (@fig-profile-fully-coupled). This is the highest-priority profile and is rare on
small grids.

#figure(
  grid(
    columns: (auto, auto),
    column-gutter: 1.5em,
    align: center + horizon,
    image("../../../results/cooperation_examples/fully_coupled.png", height: 4cm),
    image("../../../results/cooperation_examples/dep_fully_coupled.png", width: 3.5cm),
  ),
  caption: [
    `fully_coupled`: three agents and three beams stacked, so every agent must shield, and be
    shielded by, both others to reach the bottom row of exits. The complete dependency graph
    has all six edges between distinct agents (every directed pair among red, green, and blue).
  ],
) <fig-profile-fully-coupled>

The analyser also exposes the auxiliary scalars used by the decision procedure (longest chain
length, largest SCC size, synchronous width) so downstream code can re-classify levels under a
different policy without re-running any SAT calls.


=== Ordering structure of the profile labels <sec-ordering-structure>

The analyser flags each level with a single label, yet a level can exhibit several cooperation
patterns at once: they are not mutually exclusive, and one dependency graph
$G_L = (V, E)$, with $V = C$ the agent set and $n_a = |V| > 1$, can satisfy several simultaneously.
The analyser must therefore decide which pattern takes precedence, and flagging the single
*most important* match is the entire reason for the priority order formalised here. It is cleaner
to read the patterns first as predicates on $G_L$, before deciding which one to report. We use one
base predicate and four structural refinements of it:

- $cal(A)$ (asymmetric): cooperation is required, i.e. #fref(<thm-5-1>, [Theorem 5.1]) holds for
  $L$. This is the base case; the analyser builds $G_L$ only when cooperation is required, so each
  structured pattern below is a property of a cooperative level and hence a special case of it:
  $cal(C), cal(D), cal(M), cal(F) subset cal(A)$.
- $cal(C)$ (chain): $G_L$ contains a directed *simple* path of length at least two, i.e. some agent
  helps one agent and is helped by a *different* one (equivalently, the relay runs through at least
  three distinct agents). A bare reciprocal pair $c arrow.l.r c'$ is therefore not a chain: it
  revisits $c$ and involves only two agents, so it falls under $cal(M)$ rather than $cal(C)$.
- $cal(D)$ (distributed): some vertex has in-degree at least two.
- $cal(M)$ (mutual): some pair $c eq.not c'$ has both $(c, c'), (c', c) in E$.
- $cal(F)$ (fully coupled): $G_L$ is strongly connected, i.e. its single strongly connected
  component spans all $n_a$ agents.

Each label coincides with its predicate once the higher-priority predicates are removed (the
exact correspondence is the priority below). The `asymmetric` label is therefore the residual
$cal(A) without (cal(C) union cal(D) union cal(M) union cal(F))$, assigned only when cooperation
is required but none of the four structural patterns holds.

@fig-profile-venn shows these predicates as an Euler diagram, with the base predicate $cal(A)$
enclosing the four structural ones. They overlap rather than partition: chain, distributed, and
mutual can co-occur freely. For $n_a >= 3$, fully coupled lies inside chain (and inside distributed
when a reciprocal pair is present); the sole two-agent fully-coupled graph is the reciprocal pair,
which carries no chain and instead sits inside mutual.

#figure(
  image("../../../results/cooperation_examples/profile_venn.png", width: 90%),
  caption: [
    Euler diagram of the cooperation predicates on $G_L$. The bounding box is the base predicate
    $cal(A)$; chain ($cal(C)$), distributed ($cal(D)$), and mutual ($cal(M)$) overlap. The fully
    coupled ($cal(F)$) ellipse runs from inside $cal(C)$ up into $cal(M)$'s upper region: for
    $n_a >= 3$ a fully-coupled graph always contains a chain (and is distributed when it has a
    reciprocal pair), so that part of $cal(F)$ lies inside $cal(C)$ (and $cal(D)$); the two-agent
    reciprocal pair carries no chain and reaches the part of $cal(M)$ outside $cal(C)$ and $cal(D)$.
    Since fully coupled outranks mutual, that two-agent case is still labelled `fully_coupled`. Each
    graph is labelled by the priority of @tab-profile-priority, predicate minus the inner ones,
    leaving `asymmetric` as the residual area.
  ],
) <fig-profile-venn>

The classifier collapses these coexisting predicates into a single label by the priority
$cal(F) succ cal(M) succ cal(D) succ cal(C) succ cal(A)$ and returns the most cooperative
pattern a graph exhibits; @tab-profile-priority gives each label as its predicate with the
higher-priority ones removed. The non-cooperative labels `unsolvable` and `independent` are
decided beforehand by the binary detector and do not appear there.

#figure(
  table(
    columns: 4,
    stroke: none,
    inset: (x: 10pt, y: 4pt),
    align: (center, left, left, left),
    table.hline(stroke: 1pt),
    table.header([*Priority*], [*Profile*], [*Predicate form*], [*Meaning*]),
    table.hline(stroke: 0.5pt),
    [1], [`fully_coupled`], [$cal(F)$],
    [every agent reaches every other],
    [2], [`mutual`], [$cal(M) without cal(F)$],
    [direct reciprocal helping],
    [3], [`distributed`], [$cal(D) without (cal(M) union cal(F))$],
    [one beneficiary, several helpers],
    [4], [`chain`], [$cal(C) without (cal(M) union cal(D) union cal(F))$],
    [a relayed dependency (handoff)],
    [5], [`asymmetric`], [$cal(A) without (cal(C) union cal(D) union cal(M) union cal(F))$],
    [one-way help, no relay],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Priority-based labelling of cooperation-required levels. The classifier walks the rows from
    top to bottom and assigns the first label whose predicate matches.
  ],
) <tab-profile-priority>

The priority of @tab-profile-priority is *total*, but it refines a coarser *partial* order forced
by the graph structure, which we read through *subgraph containment*: one profile is at least as
cooperative as another exactly when the characteristic subgraph of the second is present in every
dependency graph realising the first, equivalently when the first predicate entails the second.

*Why some pairs are ordered.* `asymmetric` is the base predicate, so it lies below all four
structural patterns. Beyond that, the only entailment between two structural patterns is
$cal(F) arrow.r.double cal(C)$, and only for $n_a >= 3$: a graph strongly connected on three or more
agents always contains a directed simple path of length two. Hence every fully
coupled graph on $n_a >= 3$ agents is also a chain, so `fully_coupled` sits above `chain` (the
two-agent reciprocal pair is the exception: mutual, not a chain).

*Why the rest are incomparable.* Every other pair is incomparable, which four *pure* witness graphs
on three distinct agents $c_1, c_2, c_3 in C$ (the agents being identified by their colour) settle
at once: each realises the predicates listed in @tab-profile-witnesses and no others. The
pure chain, fan-in, and reciprocal pair each isolate a single structural pattern, so any two of
`chain`, `distributed`, and `mutual` are separated by a witness that has one but not the other,
making the three pairwise incomparable. The three-cycle is fully coupled (and a chain) yet neither
distributed nor mutual, while the fan-in and the reciprocal pair are distributed resp. mutual
without being strongly connected; hence `fully_coupled` is incomparable to both `distributed` and
`mutual`. The intuition is that strong connectivity is a *global* property whereas reciprocity and
shared dependence are *local* ones, so neither forces the other.

#figure(
  table(
    columns: 4,
    stroke: none,
    inset: (x: 10pt, y: 4pt),
    align: (left, center, left, left),
    table.hline(stroke: 1pt),
    table.header([*Witness* ($n_a = 3$)], [*Edges*], [*Realises*], [*Excludes*]),
    table.hline(stroke: 0.5pt),
    [pure chain], [$c_1 arrow c_2 arrow c_3$], [$cal(C)$], [$cal(D), cal(M), cal(F)$],
    [pure fan-in], [$c_1 arrow c_3$, $c_2 arrow c_3$], [$cal(D)$], [$cal(C), cal(M), cal(F)$],
    [reciprocal pair], [$c_1 arrow.l.r c_2$, $c_3$ isolated], [$cal(M)$], [$cal(C), cal(D), cal(F)$],
    [three-cycle], [$c_1 arrow c_2 arrow c_3 arrow c_1$], [$cal(C), cal(F)$], [$cal(D), cal(M)$],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Pure witness graphs on $n_a = 3$ agents, each realising the listed predicates and no others.
    They establish every incomparability in @tab-profile-partial-order: for any two patterns, some
    witness exhibits one without the other.
  ],
) <tab-profile-witnesses>


Since no pattern sits above every other, the relation is a genuine *partial* order, listed in
@tab-profile-partial-order; the priority of @tab-profile-priority is one linear extension that
settles the incomparable pairs by convention.

#figure(
  table(
    columns: 3,
    stroke: none,
    inset: (x: 10pt, y: 4pt),
    align: (left, left, left),
    table.hline(stroke: 1pt),
    table.header([*Profile*], [*Structurally more cooperative than*], [*Incomparable (ordered by convention)*]),
    table.hline(stroke: 0.5pt),
    [`fully_coupled`], [`chain`, `asymmetric`], [`mutual`, `distributed`],
    [`mutual`], [`asymmetric`], [`chain`, `distributed`, `fully_coupled`],
    [`distributed`], [`asymmetric`], [`chain`, `mutual`, `fully_coupled`],
    [`chain`], [`asymmetric`], [`mutual`, `distributed`],
    [`asymmetric`], [none (least cooperative)], [none],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Structural partial order on the cooperation profiles (for $n_a >= 3$): each profile's strictly
    more cooperative peers and its incomparable ones, the latter fixed only by the convention of
    @tab-profile-priority.
  ],
) <tab-profile-partial-order>


=== Selective-strict semantics <sec-selective-strict>

Some profile decisions require asking whether a single agent is *individually* indispensable as a
helper. To support this, the SAT encoding offers a *selective-strict* laser mode, parameterised
by a set of colours $K subset.eq C_("src")$ (chosen distinct from the source-set symbol
$cal(S)$ to avoid confusion):

- for every source $(c, d, p_s) in cal(S)$ with $c in K$, the beam-propagation clauses use the
  strict equivalence of @sat-reduction;
- for every source $(c, d, p_s) in cal(S)$ with $c in.not K$, the standard equivalence is used.

When $K = nothing$, the encoding coincides with the standard semantics; when $K = C_("src")$, it
coincides with the strict semantics of #fref(<def-3-6>, [Definition 3.6]). Intermediate choices
forbid same-colour blocking for the colours in $K$ while leaving the remaining beams
untouched. Selective-strict is the SAT lever that lets us single out one helper at a time
without affecting the other beams.

The same argument used in the proof of #fref(<thm-5-1>, [Theorem 5.1]) generalises to this
intermediate encoding: the selective-strict clauses for the colours in $K$ are exactly the strict
clauses of @sat-reduction restricted to those colours, while every other colour keeps its standard
clauses, so the model-transfer construction of the theorem applies colour by colour. Concretely,
$Phi$ with the selective-strict encoding parameterised by $K$ is
satisfiable if and only if $L$ admits a successful standard trajectory in which no agent of
colour $c in K$ ever stands on the unblocked beam path of the source of colour $c$. We
therefore use the selective-strict encoding as a sound decision oracle for "$L$ remains
solvable when each colour in $K$ is individually barred from blocking its own beam", which
is exactly what the necessary-helper analysis below requires.


=== Necessary helpers <sec-necessary-helpers>

The *necessary-helper set* is, by contrast, a property of the level itself. For every colour
$c in C_("src")$ the analyser runs one selective-strict SAT call with $K = {c}$. If the call
returns UNSAT, the colour $c$ is added to the set. Operationally, $c$ is necessary when the level
cannot be solved as soon as $c$ alone is barred from helping with its own beam, even though every
other agent retains that ability.

The necessary-helper set does not depend on which standard model the solver returns: each
counterfactual is its own one-shot satisfiability check, independent of the joint plan chosen
elsewhere.


*Scope note.* The cooperation notion defined here is intentionally specific: it captures
same-colour beam-blocking as the relevant cooperative act. A level that requires two agents to
coordinate their movements for unrelated geometric reasons (without any laser blocking being
involved) would not be identified as cooperative by this detector. This definition is not
claimed to exhaust every possible interpretation of cooperation in multi-agent environments;
it is the specific mechanism studied in this benchmark, and the formal guarantee is scoped
accordingly.

*Model-dependence of finer-grained analyses.* It is worth restating which outputs are intrinsic
to the level and which are not. The binary detector is: the satisfiability of
$Phi(L, T_("max"))$ and $Phi_("strict")(L, T_("max"))$ does not depend on which satisfying
assignment the solver returns, and the necessary-helper set is likewise an invariant, being a
sequence of one-shot counterfactual checks. The profile label is not: it is read from a single
model the solver picks arbitrarily, so two runs on the same level can in principle return
different labels. As stated at the start of the section, this is acceptable because the label
serves as a sound filter on the extracted plan rather than as a claim about the level.
