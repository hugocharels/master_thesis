#import "../../macros.typ": formalbox, fref

== Problem formalization <formalization>

We now define the semantic objects and decision problems used throughout the thesis. Two
properties are central: *solvability* — whether there exists a valid joint trajectory bringing
all agents to exits within a bounded horizon — and the *cooperation requirement* — whether
every such trajectory must rely on the same-colour beam-truncation mechanism. Both are formally
decidable and certified by the solver for every accepted level; the SAT encoding itself is
developed in @sat-reduction. Throughout, we assume $1 <= n_a <= 4$ in line with the LLE engine;
this bound is an engine artefact, not a limitation of the encoding, which remains correct for
any finite $n_a$.

#formalbox([Definition 3.1 (LLE Level)], [
  An LLE level is a tuple $L = (H, W, C, s, cal(W), cal(S), cal(E))$ where:

  - $H, W in NN^+$ are the height and width of the grid.
  - $P = {(x, y) | 0 <= x < W, 0 <= y < H}$ is the set of all grid positions, with $x$ the
    column index and $y$ the row index (image-coordinates convention).
  - $C = {0, 1, ..., n_a - 1}$ is the set of agent colours, with $1 <= n_a <= 4$.
  - $s : C -> P$ assigns an initial position to each agent, and $s$ is injective.
  - $D = {N, S, E, W}$ is the set of laser directions.
  - $cal(W) subset.eq P$ is the set of wall positions.
  - $cal(S) subset.eq C times D times P$ is the set of laser sources. A source
    $(c, d, p) in cal(S)$ emits a laser of colour $c$ in direction $d$ from position $p$.
  - $cal(E) subset.eq P$ is the set of exit positions; we assume $|cal(E)| = |C|$ as an input
    invariant of LLE levels.
  - In the instances studied in this thesis, each colour appears in at most one laser source.
  - The sets $s(C)$, $cal(W)$, $cal(E)$, and
    $
      P_("src") = {p in P | exists c in C, d in D : (c, d, p) in cal(S)}
    $
    are pairwise disjoint.
]) <def-3-1>

We also write
$
  C_("src") = {c in C | exists d in D, p in P : (c, d, p) in cal(S)}
$
for the set of colours that actually have a source.

#formalbox([Definition 3.2 (Active Beams)], [
  Fix a time step $t$ and a joint position map $p_t : C -> P$.

  For a source $(c, d, p_s) in cal(S)$, consider the grid ray starting at $p_s$ and extending in
  direction $d$.

  - Under the *standard beam semantics*, the beam of source $(c, d, p_s)$ is active on every cell
    of that ray up to, but not including, the first wall or the cell occupied by the unique agent
    of colour $c$ (if any such cell lies on the ray).
  - Under the *strict beam semantics*, the beam of source $(c, d, p_s)$ is active on every cell of
    that ray up to, but not including, the first wall.

  For $c in C_("src")$, a laser of colour $c$ is active at a position when the beam of the
  unique source of colour $c$ is active there.
]) <def-3-2>

#formalbox([Definition 3.3 (Valid Joint Trajectory)], [
  A *horizon* $T_("max") in NN$ is the maximum number of joint moves allowed in a candidate
  solution.

  A *joint trajectory* of length $T_("max")$ is a sequence of joint positions
  $sigma = (p_0, p_1, ..., p_(T_("max")))$ where each $p_t : C -> P$ assigns a position to every
  agent at time step $t$.

  A joint trajectory is *valid* if it satisfies the following conditions:

  - *Initialization:* $p_0(c) = s(c)$ for all $c in C$.
  - *Movement:* For all $t < T_("max")$ and all $c in C$, $p_(t+1)(c)$ is reachable from $p_t(c)$
    in one step: the agent may stay in place or move to a 4-neighbouring cell. Walls and
    laser-source cells are the only blocked destinations; exit tiles and cells crossed by the
    agent's own-colour laser are admissible.
  - *No collision:* $p_t(c_1) eq.not p_t(c_2)$ for all $t$ and all distinct $c_1, c_2 in C$.
  - *Conservative hand-off rule:* For all $t < T_("max")$ and all distinct $c_1, c_2 in C$,
    agents may not enter a cell occupied by another agent at the previous time step; that is,
    $p_(t+1)(c_1) eq.not p_t(c_2)$ and $p_t(c_1) eq.not p_(t+1)(c_2)$. This follows the LLE
    engine convention: agents act simultaneously without coordinating their moves, so an agent
    cannot enter a cell that another agent only vacates in the same step — it must wait one
    step. The same rule rules out direct swaps.
  - *Laser safety:* No agent $c_1$ occupies a cell at time $t$ where a laser of colour
    $c_2 in C_("src")$, with $c_2 eq.not c_1$, is active under the standard beam semantics of
    #fref(<def-3-2>, [Definition 3.2]). The restriction $c_2 eq.not c_1$ encodes *immunity*:
    an agent is unaffected by — and may stand inside — a laser of its own colour.
  - *Stay on exit:* If $p_t(c) in cal(E)$ for some $t < T_("max")$, then
    $p_(t+1)(c) = p_t(c)$. This follows the LLE engine convention: once an agent enters an
    exit tile, it remains there for the rest of the episode.
]) <def-3-3>

#formalbox([Definition 3.4 (Solvability)], [
  A level $L$ is *solvable* with horizon $T_("max")$ if there exists a valid joint trajectory
  $sigma$ of length $T_("max")$ such that the set of occupied positions at time $T_("max")$ is
  exactly the set of exits:

  $
    {p_(T_("max"))(c) | c in C} = cal(E)
  $

  A level is *solvable* without qualification if it is solvable for some $T_("max") in NN$.
]) <def-3-4>

The restriction to a bounded horizon is natural for the SAT encoding. In the model studied here,
beam activity at time $t$ is a deterministic function of the joint position map $p_t$, so the
full game state is determined by the joint agent positions. Any valid trajectory that visits the
same joint position map twice can have the intervening segment excised without affecting
reachability of later states; the stay-on-exit rule does not break this argument, since any
agent on an exit at the start of the loop must remain on that same exit throughout the loop.
Hence, if a level is solvable at all, it admits a valid trajectory whose length is at most the
number of collision-free joint position maps, which is bounded by $|P|^(n_a)$. A sufficient $T_("max")$ therefore always exists. In practice $T_("max")$ is
chosen by the generation process, and all formal guarantees in this thesis are stated relative
to that choice.

#formalbox([Definition 3.5 (Bounded-Horizon LLE Solvability Problem)], [
  The *bounded-horizon LLE solvability problem* is the following decision problem.

  - *Input:* an LLE level $L$ and a horizon $T_("max") in NN$.
  - *Question:* does $L$ admit a valid joint trajectory of length $T_("max")$ whose final occupied
    positions are exactly the exits?
]) <def-3-5>

#formalbox([Definition 3.6 (Strict Beam Semantics)], [
  A *strict trajectory* of length $T_("max")$ is defined exactly as in #fref(<def-3-3>, [Definition 3.3]), except that
  beam activity is computed using the strict beam semantics of #fref(<def-3-2>, [Definition 3.2]): same-colour
  occupancy no longer truncates the corresponding beam.
]) <def-3-6>

In the model studied here, the relevant cooperative action is precisely this same-colour
beam-truncation mechanism: an agent occupies a position that would otherwise allow its own beam to
continue, thereby opening a path for another agent.

#formalbox([Definition 3.7 (Cooperation Requirement with Horizon $T_("max")$)], [
  A level $L$ is said to *require cooperation* with horizon $T_("max")$ if:

  - $L$ is solvable under the standard semantics.
  - $L$ admits no strict trajectory of length $T_("max")$ whose final positions occupy all exit
    tiles.
]) <def-3-7>

When the horizon is clear from context, we simply say that $L$ requires cooperation. This bounded
form is the one used throughout the rest of the methods chapter, since both the SAT solver and the
cooperation detector operate at a fixed finite horizon.
