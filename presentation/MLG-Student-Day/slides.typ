#import "@preview/polylux:0.4.0": *
#import "progress_bar.typ": my-slide

#set text(size: 16pt, font: "Lato")

#set page(
  paper: "presentation-16-9",
  margin: 1cm,
  footer: align(bottom, toolbox.full-width-block(inset: 8pt)[#align(right, text(size: 12pt, (toolbox.slide-number)))]),
)

#let beamerbox(title, body, color: rgb("#1f77b4")) = block(
  stroke: color + 1.5pt,
  fill: color.lighten(85%),
  radius: 4pt,
  inset: 12pt,
  width: 100%,
)[
  #text(weight: "bold")[
    #title
  ]
  #v(6pt)
  #body
]

#let definition(body, name: none) = {
  let title = if name == none {
    [Definition]
  } else {
    [Definition (#name)]
  }

  beamerbox(title, body, color: rgb("#1f77b4"))
}

#let theorem(body, name: none) = {
  let title = if name == none {
    [Theorem]
  } else {
    [Theorem (#name)]
  }

  beamerbox(title, body, color: rgb("#2ca02c"))
}


/*
#slide[
  #set align(horizon)

  #place(
    top + right,
    dx: 0cm,
    dy: 0cm,
    image(height: 20%, "cover/MLG_logo.png")
  )

  #place(
    top + left,
    dx: 0cm,
    dy: 0cm,
    image(height: 20%, "cover/Université_libre_de_Bruxelles_logo.svg")
  )


  #place(
    bottom + right,
    dx: 0cm,
    dy: 0cm,
    image(height: 40%, "cover/lvl6-annotated.png")
  )

  #text("")

  = Procedural Generation of Solvable Levels in MARL Environment

  Hugo Charels

  April 01, 2026
]
*/

// #my-slide[
#slide[
  #set align(horizon)
  #set text(size: 25pt)
  #set page(margin: 2cm)

  #place(
    top + right,
    dx: 0cm,
    dy: 0cm,
    image(height: 20%, "../../assets/logos/MLG_logo.png"),
  )

  #place(
    top + left,
    dx: 0cm,
    dy: 0cm,
    image(height: 20%, "../../assets/logos/Université_libre_de_Bruxelles_logo.svg"),
  )

  #place(
    bottom + right,
    dx: 0.5cm,
    dy: -1cm,
    image(height: 60%, "../../assets/lvl6-annotated.png"),
  )

  #text("")

  = Procedural Generation of \ Solvable Levels in \ MARL Environment

  Hugo Charels

  April 01, 2026
]



#my-slide[

  = Context & Motivation

  #toolbox.side-by-side(columns: (1.6fr, 1fr))[
    == Laser Learning Environment (LLE)
    - 2D grid-based fully cooperative multi-agent puzzle
    - Each agent must reach its exit tile *simultaneously* with all others
    - Laser beams are passable only by an agent of the *matching color*
    - Reward signal is sparse: zero credit for intermediate coordination steps

    == Research problem
    - MARL training requires *diverse, solvable* levels with genuine cooperative structure
    - Hand-crafted levels are expensive, non-scalable, and inherently biased

    #beamerbox([Objective])[
      Procedurally generate LLE levels that are *solvable*, *learnable* by RL agents, and *structurally require* inter-agent cooperation.
    ]
  ][
    #set align(center + horizon)
    #image("../../assets/lvl6-annotated.png", width: 100%)
  ]
]


#my-slide[

  = LLE Solvability

  == Single-agent case
  - Reduces to graph reachability: solvable in polynomial time via BFS, DFS, $dots$
  - Laser avoidance is a static constraint; no interaction between agents

  #v(0.4em)

  == Multi-agent case — structurally harder
  - Agents *actively modify the environment*: blocking a laser opens a path for another agent
  - Agent actions are *mutually dependent*: feasibility of a move depends on others' positions
  - Hard synchronization constraint: all agents must exit *simultaneously*
  - Naive joint-state search is exponential in the number of agents

  #v(0.4em)

  #theorem(name: [NP-membership])[
    A valid joint execution trace is a polynomial-size certificate, checkable in polynomial time — hence LLE Solvability $in$ NP.
  ]

  *Open question:* Is LLE Solvability NP-hard?

]


#my-slide[

  // just explain what is SAT because after I will make a reduction of my problem to SAT and I want the audience to understand what I am talking about

  = Background: Satisfiability Problem

  #definition(name: [SAT])[
    Given a Boolean formula $phi.alt$ over variables
    $x_1, dots, x_n$, decide whether there exists an assignment
    $alpha : {x_1,dots,x_n} arrow {0,1}$
    such that $phi.alt(alpha) = top$.
  ]

  // #v(-10pt)

  #definition(name: [CNF])[
    A formula is in conjunctive normal form if it is a conjunction of one or more clauses, where a clause is a disjunction of literals
    #v(-20pt)
    $ F = and.big_(i=1)^(m) ( or.big_(j=1)^(k_i) l_(i,j) ) $
  ]

  // #v(-10pt)

  #theorem(name: [Cook–Levin])[
    SAT is NP-complete.
  ]

]


#my-slide[

  // suppose to initiate the reduction like give only essential information to understand what I talk after

  = Solver

  #definition(name: [Reduction])[
    A *reduction* from a problem $A$ to a problem $B$ is a transformation
    that maps any instance of $A$ to an instance of $B$ such that the answer
    is preserved. In particular, solving $B$ allows us to solve $A$.
  ]

  == Variables

  - $a_(c,x,y,t)$ : agent with color $c$ at position $(x,y)$ after $t$ time steps
  - $b_(c,d,x,y,t)$ : beam of color $c$ with direction $d$ at position $(x,y)$ after $t$ time steps
  - $l_(c,x,y,t)$ : laser of color $c$ active at position $(x,y)$ after $t$ time steps

  == Constraints

  #toolbox.side-by-side()[
    === Initialization
    - starting tiles
    - laser sources
  ][
    === Movements
    - legal movements
    - unique position
    - no overlap between agents
    - exit tiles
  ][
    === Lasers
    - beam propagation
    - no step on active laser
    - link between beams and lasers
  ]

]

#my-slide[

  = Agents movements

  Legal movement: $ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t+1) $

  #toolbox.side-by-side(gutter: 5%)[

    #uncover((2, 3, 4, 5))[
      #uncover((3, 4, 5))[== Global]

      At most one agent per tile:
      $
        and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1), \ (x_2,y_2) in P \ (x_1,y_1) eq.not (x_2,y_2)) not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t)
      $
    ]
  ][
    #uncover((4, 5))[== Local]

    #uncover(5)[
      Agent should come from a legal movement:

      $
        and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
      $

      At most one future position:

      $
        and.big_(c in C) and.big_(t in T) and.big_((x',y'), (x'',y'') in "next"(x,y) \ (x',y') eq.not (x'',y'')) not a_(c,x',y',t) or not a_(c,x'',y'',t)
      $
    ]
  ]

]

#my-slide[

  = Agents movements

  // #set align(horizon)

  #toolbox.side-by-side(gutter: 5%)[


    Legal movement: $ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t) arrow.r or.big_((x',y') in \ "next"(x,y)) a_(c,x',y',t+1) $

    == Global

    At most one agent per tile:
    $
      and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1), \ (x_2,y_2) in P \ (x_1,y_1) eq.not (x_2,y_2)) not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t)
    $

    // #uncover((1, 2, 3))[- $f(x) = (x-1)x/2 approx O(n^2)$]

  ][
    == Local

    Agent should come from a legal movement:

    $
      and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t)
    $

    At most one future position:

    $
      and.big_(c in C) and.big_(t in T) and.big_((x',y'), (x'',y'') in "next"(x,y) \ (x',y') eq.not (x'',y'')) not a_(c,x',y',t) or not a_(c,x'',y'',t)
    $

    // #uncover((2, 3))[- $g(n) = (f(5) + 1)n = 11n approx O(n)$]
  ]


  #set align(center)
  #toolbox.side-by-side()[
    #uncover((1, 2, 3))[$f(n) = binom(n, 2) = ((n-1)n)/2 in O(n^2)$]
  ][
    #uncover((2, 3))[$g(n) = (f(5) + 1)n = 11n in O(n)$]
  ]


  #v(15pt)

  #uncover(3)[
    #toolbox.side-by-side()[
      $f(n)<g(n)$ when $n<23$
    ][
      $f(n)=g(n)$ when $n=23$
    ][
      $f(n)>g(n)$ when $n>23$
    ]
  ]

]



#my-slide[

  = Plots clauses number difference

  #set align(center + horizon)

  #toolbox.side-by-side(columns: (1fr, 2fr))[
    #toolbox.side-by-side()[
      #image("../../results/MLG-Student-Day/level_3x3_agents_2_lasers_1.png", height: 20%)
    ][
      #image("../../results/MLG-Student-Day/level_5x5_agents_3_lasers_2.png", height: 20%)
    ]
    #toolbox.side-by-side[
      #image("../../results/MLG-Student-Day/level_8x8_agents_4_lasers_3.png", width: 90%)
    ][
      #image("../../results/MLG-Student-Day/level_lle_level6.png", width: 90%)
    ]
  ][
    #image("../../results/MLG-Student-Day/clauses_per_level.png")
  ]

]

#my-slide[
  = Plots time difference

  #set align(center + horizon)

  #image("../../results/MLG-Student-Day/times_per_level.png", width: 100%)

]



#my-slide[

  = Future Work

  == Solver with cooperation constraints
  - Extend the SAT encoding to include cooperation-specific constraints
  - Use the solver to analyze the cooperative structure of levels and identify key coordination points

  == Procedural Level Generation
  - Explore the use of SAT solvers for generating levels
  - Develop algorithms to generate solvable levels with specific properties (e.g., difficulty, required cooperation patterns)

  == Experimental Validation
  - Train state-of-the-art MARL agents on generated curricula
  - Compare convergence and generalization against hand-designed baselines

  == Complexity
  - Formal reduction from a known NP-hard problem to LLE Solvability and Establish NP-completeness of the decision problem
  - Or find a polynomial-time algorithm for LLE Solvability, which would be a surprising result
]



#my-slide[
  = Summary

  #v(25pt)


  #place(
    top + right,
    dx: 0cm,
    dy: 0cm,
    image(height: 15%, "../../assets/logos/MLG_logo.png"),
  )

  #place(
    top + right,
    dx: -9cm,
    dy: 0cm,
    image(height: 15%, "../../assets/logos/Université_libre_de_Bruxelles_logo.svg"),
  )

  #place(
    bottom + right,
    dx: -1cm,
    dy: -2cm,
    image(height: 60%, "../../assets/qr-code_repo-link.png"),
  )


  #toolbox.side-by-side(columns: (1fr, 1fr))[
    *Topics covered*

    + *Context & Motivation* — LLE, cooperative MARL, PCG
    + *LLE Solvability* — hardness analysis, NP-membership
    + *SAT Background* — CNF, Cook–Levin theorem
    + *SAT Encoding* — polynomial reduction from LLE to SAT
    + *Movement Constraints* — comparaison of two constraint formulations
    + *Empirical Results* — solver performance across levels
    + *Future Work* — solver with cooperation constraints, procedural generation, experimental validation, complexity analysis
  ][
  ]

]
