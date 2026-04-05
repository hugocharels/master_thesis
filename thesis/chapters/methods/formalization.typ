== Problem Formalization

We now formally define the objects and properties at the center of this thesis. This section operates
at the level of the game semantics; the SAT encoding of these properties follows in @sat-reduction.

=== LLE Level

An LLE level is a tuple $L = (H, W, cal(A), s, cal(W), cal(S), cal(E))$ where:

- $H, W in NN^+$: height and width of the grid.
- $P = {(x, y) mid 0 <= x < W, 0 <= y < H}$: set of all grid positions.
- $cal(A) = {0, 1, ..., n_a - 1}$: set of agents, each identified by a color. $n_a >= 1$.
- $s : cal(A) -> P$: initial position of each agent.
- $cal(W) subset.eq P$: set of wall positions.
- $cal(S) subset.eq cal(A) times D times P$: set of laser sources, where $D = {N, S, E, W}$.
  A source $(c, d, p) in cal(S)$ emits a laser of color $c$ in direction $d$ from position $p$.
- $cal(E) : cal(A) -> P$: exit position for each agent. We require $|{cal(E)(c) mid c in cal(A)}| = n_a$
  (distinct exits).


=== Joint Trajectory

A *joint trajectory* of length $T$ is a sequence of joint positions
$sigma = (p_0, p_1, ..., p_T)$ where each $p_t : cal(A) -> P$ assigns a position to every agent at
time step $t$.

A joint trajectory is *valid* if it satisfies:

+ *Initialization:* $p_0(c) = s(c)$ for all $c in cal(A)$.
+ *Movement:* For all $t < T$ and all $c in cal(A)$, $p_{t+1}(c)$ is reachable from $p_t(c)$
  in one step (adjacent or same cell, not a wall, not a laser source cell).
+ *No collision:* $p_t(c_1) eq.not p_t(c_2)$ for all $t$ and all $c_1 eq.not c_2$.
+ *Laser safety:* No agent $c_1$ occupies a cell at time $t$ where a laser of color
  $c_2 eq.not c_1$ is active (laser activity is determined by agent positions via the propagation rules).
+ *Stay on exit:* Once an agent reaches its exit, it remains there.


=== Solvability

A level $L$ is *solvable* with horizon $T$ if there exists a valid joint trajectory $sigma$ of
length $T$ such that $p_T(c) = cal(E)(c)$ for all $c in cal(A)$.

A level is *solvable* (without qualification) if it is solvable for some finite $T$.

#lorem(3) // TODO: note on horizon — why bounding T is sufficient (polynomial bound exists for grid worlds)


=== Cooperation Requirement

Informally, a level *requires cooperation* if no agent can reach its exit without the help of at
least one other agent — specifically, without another agent blocking a laser on its behalf.

We make this precise via the *strict laser semantics*: in the strict variant, agents are no longer
immune to lasers of their own color. Every agent is blocked by every laser regardless of color
matching. A valid trajectory under strict semantics is a *strict trajectory*.

#lorem(3) // TODO: give intuition for why this captures cooperation

*Definition (Cooperation Requirement).* A level $L$ is said to *require cooperation* if:

+ $L$ is solvable (under standard semantics), and
+ $L$ admits no valid strict trajectory reaching all exits.

The formal proof that this definition correctly captures the intuitive notion of cooperation is
given in @cooperation-detection.
