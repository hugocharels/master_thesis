== Problem Formalization

We now formally define the objects and properties at the centre of this thesis. This section
operates at the level of the game semantics; the SAT encoding of these properties follows in
<sat-reduction>.

=== LLE Level

An LLE level is a tuple $L = (H, W, C, s, cal(W), cal(S), cal(E))$ where:

- $H, W in NN^+$ are the height and width of the grid.
- $P = {(x, y) | 0 <= x < W, 0 <= y < H}$ is the set of all grid positions.
- $C = {0, 1, ..., n_a - 1}$ is the set of agent colours, with $n_a >= 1$.
- $s : C -> P$ assigns an initial position to each agent.
- $cal(W) subset.eq P$ is the set of wall positions.
- $D = {N, S, E, W}$ is the set of laser directions.
- $cal(S) subset.eq C times D times P$ is the set of laser sources. A source
  $(c, d, p) in cal(S)$ emits a laser of colour $c$ in direction $d$ from position $p$.
- $cal(E) subset.eq P$ is the set of exit positions, with $|cal(E)| = |C|$.


=== Joint Trajectory

A *joint trajectory* of length $T$ is a sequence of joint positions
$sigma = (p_0, p_1, ..., p_T)$ where each $p_t : C -> P$ assigns a position to every agent at
time step $t$.

A joint trajectory is *valid* if it satisfies the following conditions:

+ *Initialization:* $p_0(c) = s(c)$ for all $c in C$.
+ *Movement:* For all $t < T$ and all $c in C$, $p_(t+1)(c)$ is reachable from $p_t(c)$ in one
  step: the agent may stay in place or move to a 4-neighbouring cell, but it may not move into a
  wall or a laser-source cell.
+ *No collision:* $p_t(c_1) eq.not p_t(c_2)$ for all $t$ and all distinct $c_1, c_2 in C$.
+ *Laser safety:* No agent $c_1$ occupies a cell at time $t$ where a laser of colour
  $c_2 eq.not c_1$ is active.
+ *Stay on exit:* If $p_t(c) in cal(E)$ for some $t < T$, then $p_(t+1)(c) = p_t(c)$.


=== Solvability

A level $L$ is *solvable* with horizon $T$ if there exists a valid joint trajectory $sigma$ of
length $T$ such that the set of occupied positions at time $T$ is exactly the set of exits:

$
  {p_T(c) | c in C} = cal(E)
$

A level is *solvable* without qualification if it is solvable for some finite horizon.

The restriction to a bounded horizon is natural for the SAT encoding. In the LLE mechanics studied
here, laser activity at time $t$ is a deterministic function of the joint agent positions at time
$t$. Consequently, the full game state is determined by the joint position map $p_t$. If a
trajectory repeats the same joint position twice, the intervening segment forms a loop and can be
removed without affecting reachability of later states. Therefore, if a level is solvable at all,
it is solvable within a finite horizon bounded by the number of collision-free joint configurations.


=== Cooperation Requirement

Informally, a level *requires cooperation* if no solution exists unless at least one agent blocks a
laser of its own colour to make progress possible for another agent.

We make this precise via *strict laser semantics*. In the strict variant, agents are no longer
immune to lasers of their own colour. Every agent is blocked by every active laser, regardless of
colour matching. A valid trajectory under strict semantics is called a *strict trajectory*.

This definition matches the current LLE mechanics because, in the model studied here, an agent can
change the traversable space available to its teammates only by standing on a beam of its own
colour. Strict semantics removes exactly this possibility while leaving the rest of the level
dynamics unchanged.

*Definition (Cooperation Requirement).* A level $L$ is said to *require cooperation* if:

+ $L$ is solvable under the standard semantics, and
+ $L$ admits no valid strict trajectory whose final positions occupy all exit tiles.

The formal proof that this captures the intended notion of cooperation is given in
<cooperation-detection>.

#v(16pt)

#figure(
  grid(
    columns: 3,
    gutter: 10pt,
    align: center,
    [*(a)* Unsolvable \ _no valid joint trajectory_],
    [*(b)* Solvable, no cooperation \ _agents reach the exits independently_],
    [*(c)* Solvable and cooperative \ _laser blocking required_],
    image("../../../assets/unsolvable_map_example.png", width: 100%),
    image("../../../assets/bad_map_example.png", width: 100%),
    image("../../../assets/good_map_example.png", width: 100%),
  ),
  caption: [The three level categories defined by the solvability and cooperation properties.],
)
