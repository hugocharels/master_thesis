=== Definition of Sets

We consider a rectangular grid of height $H$ and width $W$. Positions are identified by pairs $(x, y)$, where $x in {0, ..., W-1}$ denotes the column index and $y in {0, ..., H-1}$ denotes the row index. The following sets are used throughout.

- $C = {0, 1, ..., n_a - 1}$: set of agent colors, where $n_a >= 1$ is the number of agents.
- $D = {N, S, E, W}$: set of laser beam directions (North, South, East, West).
- $P = {(x, y) | 0 <= x < W, 0 <= y < H}$: set of all grid positions.
- $cal(W) subset.eq P$: set of wall positions.
- $cal(S) subset.eq C times D times P$: set of laser sources; $(c, d, p) in cal(S)$ denotes a laser of color $c$ shooting in direction $d$ from position $p in P$.
- $cal(E) subset.eq P$: set of exit positions, with $|cal(E)| = n_a$.
- $T = {0, 1, ..., T_("max")}$: set of discrete time steps.

We also write $"start"(c) in P$ for the initial position of agent $c in C$.


=== Definition of Variables

We introduce three families of propositional variables.

- $a_(c,x,y,t)$: true iff agent $c in C$ occupies position $(x,y) in P$ at time step $t in T$.
- $b_(c,d,x,y,t)$: true iff the beam of laser source $(c, d, -) in cal(S)$ is active at position $(x,y) in P$ at time $t in T$.
- $l_(c,x,y,t)$: true iff a laser of color $c in C$ is active at position $(x,y) in P$ at time $t in T$.


=== Constraints and Logical Encoding

We now formalize the constraints ensuring the correctness of the reduction. Each group of clauses corresponds to one logical component of the problem.

+ *Initialization*

  - *Agents:* \
    Each agent $c in C$ is placed at its designated starting position $"start"(c)$ at $t = 0$; all other positions are unoccupied by that agent:
    $
      and.big_(c in C) and.big_((x, y) in P) cases(a_(c,x,y,0) & "if" (x,y) = "start"(c), not a_(c,x,y,0) & "otherwise")
    $

  - *Laser sources:* \
    For each laser source $(c, d, (x_s, y_s)) in cal(S)$, the beam is always active at its origin, at every time step:
    $
      and.big_((c, d, (x_s, y_s)) in cal(S)) and.big_(t in T) b_(c, d, x_s, y_s, t)
    $


+ *Agent Movements*

  We define the set of positions reachable from $(x,y)$ in one step as $(x,y)$ itself together with its four grid neighbors, excluding walls and laser source positions:
  $
    "next"(x,y) = { (x',y') in {(x,y),(x,y-1),(x+1,y),(x,y+1),(x-1,y)} | \ (x',y') in P, (x',y') in.not cal(W), (x',y') in.not {p | (c,d,p) in cal(S)} }
  $

  - *Forward consistency:* \
    If agent $c$ is at position $(x,y)$ at time $t$, it must be at some position in $"next"(x,y)$ at time $t+1$:
    $
      and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P) a_(c,x,y,t) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1)
    $
    $
      arrow.t.b.double
    $
    $
      and.big_(c in C) and.big_(t = 0)^(T_("max") - 1) and.big_((x,y) in P) not a_(c,x,y,t) or or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1)
    $

  Two methods are proposed to enforce that each agent occupies at most one position at each time step.

  - *Global uniqueness:* \
    No two distinct positions can both be occupied by agent $c$ at time $t$:
    $
      and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1) in P) and.big_((x_2,y_2) in P, \ (x_2,y_2) eq.not (x_1,y_1)) not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t)
    $

  - *Local uniqueness:* \
    No two distinct positions in $"next"(x,y)$ can simultaneously be occupied by agent $c$ at time $t+1$:
    $
      and.big_(c in C) and.big_(t = 0)^(T_("max")-1) and.big_((x,y) in P) and.big_((x',y') in "next"(x,y)) and.big_((x'',y'') in "next"(x,y), \ (x'',y'') eq.not (x',y')) not a_(c,x',y',t+1) or not a_(c,x'',y'',t+1)
    $

    *Backward consistency:* \
    If agent $c$ is at position $(x,y)$ at time $t+1$, it must have been at some position in $"next"(x,y)$ at time $t$:
    $
      and.big_(c in C) and.big_(t = 0)^(T_("max")-1) and.big_((x,y) in P) a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
    $
    $
      arrow.t.b.double
    $
    $
      and.big_(c in C) and.big_(t = 0)^(T_("max")-1) and.big_((x,y) in P) not a_(c,x,y,t+1) or or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
    $

  - *No simultaneous occupation:* \
    Two distinct agents cannot share the same position at the same time, nor can they move to a position already occupied by the other agent:
    $
      and.big_(c_1 in C) and.big_(c_2 in C, c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t in T) not a_(c_1,x,y,t) or not a_(c_2,x,y,t)
    $
    $
      and.big_(c_1 in C) and.big_(c_2 in C, c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t = 0)^(T_("max")-1) not a_(c_1,x,y,t+1) or not a_(c_2,x,y,t)
    $
    $
      and.big_(c_1 in C) and.big_(c_2 in C, c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t = 0)^(T_("max")-1) not a_(c_1,x,y,t) or not a_(c_2,x,y,t+1)
    $

  - *Victory condition:* \
    Each exit must be occupied by at least one agent at time $T_("max")$. Since $|cal(E)| = n_a$ and agents cannot share positions, this enforces a bijection between agents and exits:
    $
      and.big_((x,y) in cal(E)) or.big_(c in C) a_(c,x,y,T_("max"))
    $

  - *Stay on exit:* \
    Once an agent reaches an exit, it remains there for all subsequent time steps:
    $
      and.big_(c in C) and.big_((x,y) in cal(E)) and.big_(t = 0)^(T_("max")-1) not a_(c,x,y,t) or a_(c,x,y,t+1)
    $


+ *Laser Activity*

  We define $"next"_d(x,y)$ as the position immediately adjacent to $(x,y)$ in direction $d$:
  $
    "next"_d (x,y) = cases(
      (x, y-1) & "if" d = N,
      (x+1, y) & "if" d = E,
      (x, y+1) & "if" d = S,
      (x-1, y) & "if" d = W
    )
  $

  - *Walls block beams:* \
    A beam cannot be active at a wall position:
    $
      and.big_((c,d,-) in cal(S)) and.big_((x,y) in cal(W)) and.big_(t in T) not b_(c,d,x,y,t)
    $

  - *Beam propagation:* \
    For each laser source $(c, d, -) in cal(S)$ and each non-wall position $(x,y)$ whose successor $(x',y') = "next"_d(x,y)$ also lies outside $cal(W)$, the beam propagates from $(x,y)$ to $(x',y')$ if and only if no agent of color $c$ is present at $(x',y')$:
    $
      and.big_((c,d,-) in cal(S)) and.big_(t in T) and.big_((x,y) in P without cal(W), \ "next"_d (x,y) in P without cal(W)) b_(c,d,x',y',t) arrow.l.r (b_(c,d,x,y,t) and not a_(c,x',y',t))
      \ arrow.t.b.double \
      and.big_((c,d,-) in cal(S)) and.big_(t in T) and.big_((x,y) in P without cal(W), \ "next"_d (x,y) in P without cal(W)) not b_(c,d,x,y,t) or a_(c,x',y',t) or b_(c,d,x',y',t)
      \
      and.big_((c,d,-) in cal(S)) and.big_(t in T) and.big_((x,y) in P without cal(W), \ "next"_d (x,y) in P without cal(W)) b_(c,d,x,y,t) or not b_(c,d,x',y',t)
      \
      and.big_((c,d,-) in cal(S)) and.big_(t in T) and.big_((x,y) in P without cal(W), \ "next"_d (x,y) in P without cal(W)) not a_(c,x',y',t) or not b_(c,d,x',y',t)
    $

  - *Link between beam and laser variables:* \
    For each laser source $(c, d, -) in cal(S)$, the laser variable $l_(c,x,y,t)$ is true at a position if and only if the beam of that source is active there:
    $
      and.big_((c,d,-) in cal(S)) and.big_((x,y) in P) and.big_(t in T) b_(c,d,x,y,t) arrow.l.r l_(c,x,y,t)
    $
    $
      arrow.t.b.double
    $
    $
      and.big_((c,d,-) in cal(S)) and.big_((x,y) in P) and.big_(t in T) (not b_(c,d,x,y,t) or l_(c,x,y,t)) and (not l_(c,x,y,t) or b_(c,d,x,y,t))
    $

  - *Agents cannot step on active lasers:* \
    An agent of color $c_1$ cannot occupy a position where a laser of color $c_2 eq.not c_1$ is active. Agents are immune only to lasers of their own color:
    $
      and.big_(c_1 in C) and.big_(c_2 in C, \ c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t in T) l_(c_2,x,y,t) arrow.r not a_(c_1,x,y,t)
    $
    $
      arrow.t.b.double
    $
    $
      and.big_(c_1 in C) and.big_(c_2 in C, \ c_2 eq.not c_1) and.big_((x,y) in P) and.big_(t in T) not l_(c_2,x,y,t) or not a_(c_1,x,y,t)
    $
