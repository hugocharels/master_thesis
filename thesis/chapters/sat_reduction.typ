=== Definition of Sets
The following sets are used to represent the domain of the problem.
- $C$: colors of agents, $C in {{1}, {1,2}, {1,2,3}, {1,2,3,4}}$ depending on the number of agents in the level
- $D$: direction of lasers ${N,S,E,W}$
- $P$: all possible positions for the level in a coordinate $(x,y)$
- $T$: all time steps from $0$


=== Definition of Variables

In this section, we define all propositional variables used in the SAT encoding.
- $a_(c,x,y,t)$ : agent with color $c in C$ at position $(x,y)$ after $t$ time steps
- $b_(c,d,x,y,t)$ : beam of color $c in C$ with direction $d in D$ at position $(x,y)$ after $t$ time steps
- $l_(c,x,y,t)$ : laser of color $c in C$ active at position $(x,y)$ after $t$ time steps


=== Constraints and Logical Encoding
We now formalize the constraints ensuring the correctness of the reduction. Each group of clauses corresponds to one logical component of the problem.

+ Initialization:
  - Agents: \
    The initial position of the agents is fixed by the level design. We also say where it can so there is no duplication of agent.
    $
      and.big_(c in C) and.big_((x, y) in P) cases(a_(c,x,y,0) "    if there is a starting tile", not a_(c,x,y,0) "  else")
    $

  - Lasers: \
    We define a beam always active at the source of the laser, and then I will propagate it with the rules of the laser activity.
    $
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) b_(c,d,x,y,t) "    if there is a laser source"
    $

+ Agents movements

  - Legal movement: \
    If there is an agent at position $(x,y)$ at time $t$, then there must be an agent at position $(x,y)$ or one of its neighbors at time $t+1$ (forward consistency).
    $
      and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1)
      \ arrow.t.b.double \ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) not a_(c,x,y,t) or or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1)
    $
    $"where" "next"(x,y) = { (x',y') in {(x,y), (x-1,y), (x+1,y), (x,y-1), (x,y+1)} | "If the position" (x',y') "is in the grid and there is no wall or laser source" }$


  Two different method to constraint the duplication of agents, so an agent cannot be in two different positions at the same time.

  - Global Method: \
    There is at most one agent of color $c$ at time $t$.
    $
      and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1),(x_2,y_2) in P \ (x_1,y_1) eq.not (x_2,y_2)) not a_(c,x_1,y_1,n) or not a_(c,x_2,y_2,n)
    $


  - Local Method: \
    At most one agent per time step between next positions.
    $
      and.big_(c in C) and.big_(t in T) and.big_((x',y'),(x'',y'') in "next"(x,y) \ (x',y') eq.not (x'',y'')) not a_(c,x',y',n) or not a_(c,x'',y'',n)
    $

    Agents should come from a legal movement, so if there is an agent at position $(x,y)$ at time $t+1$, then there must be an agent at position $(x,y)$ or one of its neighbors at time $t$ (backward consistency).
    $
      and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t) \ arrow.t.b.double \
      and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) not a_(c,x,y,t+1) or or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
    $

  - Overlapping agents: \
    Two different agents cannot be on the same position at the same time and can not move on an occupied position.
    $
      and.big_(c_1,c_2 in C \ c_1 eq.not c_2) and.big_((x,y) in P) and.big_(t in T) not a_(c_1,x,y,t) or not a_(c_2,x,y,t) \
      and.big_(c_1,c_2 in C \ c_1 eq.not c_2) and.big_((x,y) in P) and.big_(t in T) not a_(c_1,x,y,t+1) or not a_(c_2,x,y,t) \
      and.big_(c_1,c_2 in C \ c_1 eq.not c_2) and.big_((x,y) in P) and.big_(t in T) not a_(c_1,x,y,t) or not a_(c_2,x,y,t+1)
    $

  - Agents must be on exit to win:
    $ and.big_((x,y) in P) or.big_(c in C) a_(c,x,y,t_("MAX")) "  if there is an exit tile at position" (x,y) $


+ Lasers activity

  - A beam can not propagates if there is a wall:
    $
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) not b_(c,d,x,y,t) " if there is a wall at position " (x,y)
    $

  - A beam propagates if and only if there is no agent to block it:
    $
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) (b_(c,d,x,y,t) and not a_(c,x',y',t)) arrow.r.l b_(c,d,x',y',t)
      \ arrow.t.b.double \
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) (not (b_(c,d,x,y,t) and not a_(c,x',y',t)) or b_(c,d,x',y',t)) and ((b_(c,d,x,y,t) and not a_(c,x',y',t)) or not b_(c,d,x',y',t))
      \ arrow.t.b.double \
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) (not b_(c,d,x,y,t) or a_(c,x',y',t) or b_(c,d,x',y',t)) and (b_(c,d,x,y,t) or not b_(c,d,x',y',t)) and (not a_(c,x',y',t) or not b_(c,d,x',y',t))
    $

    where $(x',y') = cases((x,y-1) text("if") d=N, (x+1,y) text("if") d=E, (x,y+1) text("if") d=S, (x-1,y) text("if") d=W,)$

  - Link value of laser and beam:
    $
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) b_(c, d, x, y, t) arrow.l.r l_(c, x, y, t) \ arrow.t.b.double \
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) (b_(c, d, x, y, t) arrow.r l_(c, x, y, t)) and (l_(c, x, y, t) arrow.r b_(c, d, x, y, t)) \ arrow.t.b.double \
      and.big_(c in C) and.big_(d in D) and.big_((x,y) in P) and.big_(t in T) (not b_(c, d, x, y, t) or l_(c, x, y, t)) and (not l_(c, x, y, t) or b_(c, d, x, y, t))
    $

  - Agents can not step on active laser:
    $
      and.big_(c_1,c_2 in C \ c_1 eq.not c_2) and.big_((x,y) in P) and.big_(t in T) l_(c,x,y,t) arrow.r not a_(c,x,y,t) \ arrow.t.b.double \
      and.big_(c_1,c_2 in C \ c_1 eq.not c_2) and.big_((x,y) in P) and.big_(t in T) not l_(c,x,y,t) or not a_(c,x,y,t)
    $
