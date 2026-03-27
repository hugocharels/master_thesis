#import "@preview/polylux:0.4.0": *
#import "progress_bar.typ": my-slide

#set text(size: 18pt, font: "Lato")

#set page(
  paper: "presentation-16-9",
  margin: 1cm,
  footer: align(bottom, toolbox.full-width-block(inset: 8pt)[#align(right, text(size: 15pt, ( toolbox.slide-number)))]),
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
    image(height: 20%, "../../assets/logos/MLG_logo.png")
  )

  #place(
    top + left,
    dx: 0cm,
    dy: 0cm,
    image(height: 20%, "../../assets/logos/Université_libre_de_Bruxelles_logo.svg")
  )

  #place(
    bottom + right,
    dx: 0.5cm,
    dy: -1cm,
    image(height: 60%, "../../assets/lvl6-annotated.png")
  )

  #text("")

  = Procedural Generation of \ Solvable Levels in \ MARL Environment

  Hugo Charels

  April 01, 2026
]



#my-slide[

  = Context & Motivation

  - Say what I do and why

]


#my-slide[

  = LLE Solvability

  - Say that the problem is harder than pathfinding
  - Talk a bit about complexity
  - Show options to make solver

]


#my-slide[
  = Background: Satisfiability Problem

  #definition(name: [SAT])[
    Given a Boolean formula $phi.alt$ over variables
    $x_1, dots, x_n$, decide whether there exists an assignment
    $alpha : {x_1,dots,x_n} arrow {0,1}$
    such that $phi.alt(alpha) = top$.
  ]

  #v(-10pt)

  #definition(name: [CNF])[
    A formula is in conjunctive normal form if it is a conjunction of one or more clauses, where a clause is a disjunction of literals
    #v(-20pt)
    $ F = and.big_(i=1)^(m) ( or.big_(j=1)^(k_i) l_(i,j) ) $
  ]

  #v(-10pt)

  #theorem(name: [Cook–Levin])[
    SAT is NP-complete.
  ]

]


#my-slide[

  = Solver

  - Find a reduction (a way to transform a LLE solvability instance into a SAT instance)

  == Variables

  - $a_(c,x,y,t)$ : agent with color $c$ at position $(x,y)$ after $t$ time steps
  - $b_(c,d,x,y,t)$ : beam of color $c$ with direction $d$ at position $(x,y)$ after $t$ time steps
  - $l_(c,x,y,t)$ : laser of color $c$ active at position $(x,y)$ after $t$ time steps

  == Constraints
  - Initializations : starting tiles and laser sources
  - Movements : legal movements, unique position, no overlap and exit tiles
  - Lasers : beam propagation

]

#my-slide[

  = Agents movements

  Legal movement: $ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t) arrow.r or.big_((x',y') in  "next"(x,y)) a_(c,x',y',t+1) $

  #toolbox.side-by-side(gutter: 5%,)[

    #uncover((2, 3, 4, 5))[
    #uncover((3, 4, 5))[== Global]

    At most one agent per tile:
    $ and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1), \ (x_2,y_2) in P \ (x_1,y_1) eq.not (x_2,y_2)) not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t) $
    ]
  ][
    #uncover((4, 5))[== Local]

    #uncover(5)[
    Agent should come from a legal movement:

    $ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t) $

    At most one future position:

    $ and.big_(c in C) and.big_(t in T) and.big_((x',y'), (x'',y'') in "next"(x,y) \ (x',y') eq.not (x'',y'')) not a_(c,x',y',t) or not a_(c,x'',y'',t) $
    ]
  ]

]

#my-slide[

  = Agents movements

  // #set align(horizon)

  #toolbox.side-by-side(gutter: 5%,)[


    Legal movement: $ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t) arrow.r or.big_((x',y') in \ "next"(x,y)) a_(c,x',y',t+1) $

    == Global

    At most one agent per tile:
    $ and.big_(c in C) and.big_(t in T) and.big_((x_1,y_1), \ (x_2,y_2) in P \ (x_1,y_1) eq.not (x_2,y_2)) not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t) $

    // #uncover((1, 2, 3))[- $f(x) = (x-1)x/2 approx O(n^2)$]

  ][
    == Local

    Agent should come from a legal movement:

    $ and.big_(c in C) and.big_(t in T) and.big_((x,y) in P) a_(c,x,y,t+1) arrow.r or.big_((x',y') in "next"(x,y)) a_(c,x',y',t) $

    At most one future position:

    $ and.big_(c in C) and.big_(t in T) and.big_((x',y'), (x'',y'') in "next"(x,y) \ (x',y') eq.not (x'',y'')) not a_(c,x',y',t) or not a_(c,x'',y'',t) $

    // #uncover((2, 3))[- $g(n) = (f(5) + 1)n = 11n approx O(n)$]
  ]


  #set align(center)
  #toolbox.side-by-side()[
    #uncover((1, 2, 3))[$f(n) = binom(n,2) = ((n-1)n)/2 in O(n^2)$]
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

  = Plots difference

  #set align(horizon)

  #toolbox.side-by-side()[
    #image("results/clauses_per_level.png")
  ][
    #image("results/total_time_per_level.png")
  ]


]



#my-slide[

  = Future work


]



#my-slide[
  = End

  Outline

]
