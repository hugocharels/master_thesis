#import "@preview/typslides:1.2.5": *

#show: typslides.with(
  ratio: "16-9",
  //theme: "bluey", // other options: reddy, dusky, darky, etc.
  theme: "bluey",
)

#front-slide(
  title: "Procedural Generation of Solvable Levels in MARL Environment Using Curriculum Learning",
  subtitle: [Preparatory work for the master thesis],
  authors: "Charels Hugo",
)


#table-of-contents()

#title-slide[
  Context & Motivation
]

#slide(title: "Context")[
  - The "Multi-Agent Reinforcement Learning Environment" here refers to the \ *Laser Learning Environment (LLE)*
  - LLE provides a grid-based world where multiple agents interact.
  - Each agent must cooperate to reach shared goals.

  #align(center, [
    #image("../assets/lvl6-annotated.png", width: 65%)
  ])
]

#slide(title: "Motivation")[
  - Human-designed levels can lack diversity and become repetitive.
  - Procedural generation enables a *virtually endless variety* of scenarios.
  - Can generate environments beyond human creativity.
]

#title-slide[
  Problem Statement
]

#slide(title: "Problem Statement")[
  - How can we generate *solvable* levels *automatically*?
  - How to ensure tasks are learnable and diverse?
  - How to encourage *agent cooperation* in complex environments?

  \
  #columns(3, gutter: 0%, [

    #align(center, [
      #image("../assets/wrong_checkbox.png", width: 12%)
      #image("../assets/unsolvable_map_example.png", width: 75%)
    ])

    #align(center, [
      #image("../assets/wrong_checkbox.png", width: 12%)
      #image("../assets/bad_map_example.png", width: 75%)
    ])

    #align(center, [
      #image("../assets/right_checkbox.png", width: 12%)
      #image("../assets/good_map_example.png", width: 75%)
    ])
  ])
]

#title-slide[
  State of the Art
]

#slide(title: "Related Work")[
  - *Increasing Generality in Machine Learning through Procedural Content Generation*
    A comprehensive survey of existing *PCG techniques* used in various machine learning contexts.

  - *PCGRL: Procedural Content Generation via Reinforcement Learning*
    Trains an agent to *place tiles, obstacles, ...* (e.g., in Sokoban-like environments) by receiving *reward signals* based on level quality.

  - *Classic Nintendo Games are (Computationally) Hard*
    Demonstrates the *computational complexity* of solving levels in classic games through *3-SAT reductions*, highlighting the *difficulty of level solvability*.
]


#title-slide[
  Next Steps
]

#slide(title: "Planned Work")[
  - Formalize the notion of *level solvability* as a decision problem.
  - Identify and implement algorithms for generating *valid and diverse* levels.
  - Design the generator to support *progressive difficulty* aligned with curriculum learning.
]

#slide[
  #align(center, [
    #text(size: 40pt, [Questions ?])
  ])
]
