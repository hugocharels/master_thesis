#import "@preview/typslides:1.2.5": *

#show: typslides.with(
  ratio: "16-9",
  theme: "bluey"
)

#front-slide(
  title: "Procedural Generation of Solvable Levels in Multi-Agent Reinforcement Learning Environment Using Curriculum Learning",
  subtitle: [Preparatory work for the master thesis],
  authors: "Charels Hugo",
)

#table-of-contents()

#title-slide[
  Introduction & Context
]

#slide(title: "Research Context")[
  *Three key domains converge:*
  - *Procedural Content Generation (PCG)*: Algorithmic creation of game content
  - *Multi-Agent Reinforcement Learning (MARL)*: Multiple agents learning cooperatively
  - *Curriculum Learning (CL)*: Structured progression from simple to complex tasks

  #v(1em)
  *Target Environment:* *Laser Learning Environment (LLE)*
  - 2D grid-based cooperative puzzle game
  - Agents must coordinate to block colored lasers
  - Requires perfect coordination with sparse rewards and bottlenecks
]

#slide(title: "The Challenge")[
  *Current limitations:*
  - Hand-designed levels are limited in diversity, time-consuming and tedious to create
  - No systematic way to generate progressively challenging cooperative scenarios

  #v(1em)
  *Our goal:* Generate levels that are:
  1. *Solvable* - Provably completable
  2. *Learnable* - Discoverable through exploration  
  3. *Cooperative* - Require multi-agent coordination
]

#title-slide[
  Problem Formulation
]

#slide(title: "Core Research Questions")[
  1. How can we *procedurally generate levels* that are both diverse and *provably solvable* in multi-agent environments?

  2. What *metrics* can quantify solvability, cooperation requirements, and difficulty?

  3. How does *level structure* influence the learnability of tasks by MARL agents?

  4. Can *curriculum learning* be integrated into level generation to progressively increase challenge?
]

#slide(title: "The Three Pillars")[
  #columns(3, gutter: 5%, [
    #align(center, [
      #image("pictures/wrong_checkbox.png", width: 15%)
      *Unsolvable*
      #image("pictures/unsolvable_map_example.png", width: 90%)
      No valid path exists
    ])
    \
    #align(center, [
      #image("pictures/wrong_checkbox.png", width: 15%)
      *Trivial*
      #image("pictures/bad_map_example.png", width: 90%)
      Solvable without cooperation
    ])
    \
    #align(center, [
      #image("pictures/right_checkbox.png", width: 15%)
      *Target*
      #image("pictures/good_map_example.png", width: 90%)
      Requires coordinated behavior
    ])
  ])
]

#title-slide[
  Methodology Overview
]

#slide(title: "Four-Phase Approach")[
  *Phase 1: Theoretical Foundation* (Sep-Oct)
  - Complexity proof of LLE solvability
  - Establish computational complexity bounds

  *Phase 2: Method Development* (Oct-Feb)
  - Methods literature & selection
  - Prototype generator development
  - Verifier & solvability checks

  *Phase 3: Experimental Validation* (Jan-May)
  - Methods testing
  - Analysis & visualizations

  *Phase 4: Writing & Documentation* (May-Jun)
  - Thesis writing
  - Final submission
]

#slide(title: "PCG Techniques Under Investigation")[
  *Noise-Based Methods*
  - Various noise functions for wall placement

  *Rule-Based Methods*
  - Cellular Automata for cave-like environments
  - Wave Function Collapse for pattern coherence
  - Prefab-based modular construction

  *Learning-Based Methods*
  - GANs with self-attention mechanisms
  - VAEs for sequential segment generation
  - PCGRL: Reinforcement learning for content generation
]

#title-slide[
  Key Contributions
]

#slide(title: "Expected Theoretical Contributions")[
  *Complexity Analysis*
  - First formal proof that LLE solvability is NP-hard
  - Extension of gadget-based reduction framework to cooperative puzzles

  *Solvability Framework*
  - Metrics for quantifying cooperation requirements
  - Integration of solvability constraints into generation process
]

#slide(title: "Expected Practical Contributions")[
  *Generation Framework*
  - Unified system combining multiple PCG techniques
  - Curriculum-aware level progression

  *MARL Applications*
  - Diverse training environments for cooperative agents
  - Comparative analysis: training on human-designed vs. generated levels
  - Enhanced agent generalization through procedural diversity
]


#slide[
  #align(center, [
    #text(size: 32pt, [
      *Thank you for your attention!*
      
      #v(2em)
      
      Questions & Discussion
      
      #v(1em)
      
      #text(size: 20pt, [#link("mailto:hugo.charels@ulb.be")])
    ])
  ])
]