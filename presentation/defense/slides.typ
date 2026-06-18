#import "@preview/polylux:0.4.0": *
#import "progress_bar.typ": my-slide

// =============================================================================
//  Master thesis defense — Hugo Charels (ULB, 2025–2026)
//  "Procedural Generation of Solvable Cooperative Levels for the LLE"
//  ~20 min talk: keep spoken detail in the notes, not on the slides.
// =============================================================================

#set text(size: 16pt, font: "Lato")

#show heading.where(level: 1): set text(size: 22pt, weight: "bold")
#show heading.where(level: 2): set text(size: 20pt, weight: "bold")
#show heading.where(level: 3): set text(size: 18pt, weight: "bold")

#set page(
  paper: "presentation-16-9",
  margin: 1cm,
  footer: align(bottom, toolbox.full-width-block(inset: 8pt)[#align(right, text(size: 12pt, (toolbox.slide-number)))]),
)

// ─── Palette ──────────────────────────────────────────────────────────────────
#let c-info = rgb("#1F5FA8")
#let c-take = rgb("#E0701B")
#let c-warn = rgb("#C08A12")

// ─── Coloured callout boxes ───────────────────────────────────────────────────
#let beamerbox(title, body, color: c-info) = block(
  stroke: color + 1.5pt,
  fill: color.lighten(88%),
  radius: 4pt,
  inset: 11pt,
  width: 100%,
)[
  #text(weight: "bold", fill: color.darken(15%))[#title]
  #v(5pt)
  #body
]

#let takeaway(body) = beamerbox([Takeaway], body, color: c-take)

// =============================================================================
//  TITLE / COVER
// =============================================================================
#slide[
  #set align(horizon)
  #set page(margin: 2cm)

  #place(top + right, image(height: 20%, "../../assets/logos/MLG_logo.png"))
  #place(top + left, image(height: 20%, "../../assets/logos/Université_libre_de_Bruxelles_logo.svg"))
  #place(bottom + right, dx: 0.5cm, dy: -0.8cm, image(height: 60%, "../../assets/lvl6-annotated.png"))

  #v(4cm)

  #text(size: 26pt, weight: "bold")[
    Procedural Generation of \ Solvable Cooperative Levels \ for the Laser Learning Environment
  ]
  #v(6pt)
  #text(size: 18pt)[*Hugo Charels* --- Master thesis defense]
  #v(2pt)
  #text(size: 15pt)[Supervisors: Tom Lenaerts #sym.dot.c Yannick Molinghen]
  #v(2pt)
  #text(size: 14pt, fill: luma(90))[ULB --- Academic year 2025-2026 #sym.dot.c #emph[18/06/2026]]
]

// =============================================================================
//  CONTEXT
// =============================================================================
#my-slide[
  = Context & motivation

  #v(10pt)

  #toolbox.side-by-side(columns: (1.6fr, 1fr))[
    == Laser Learning Environment (LLE)
    - 2D grid-based fully cooperative multi-agent puzzle
    - Each agent must reach its exit tile *simultaneously* with all others
    - Laser beams are passable only by an agent of the *matching color*
    - Reward signal is sparse: zero credit for intermediate coordination steps

    == The LLE cooperative mechanic
    - A beam blocks *other* colours; each agent is *immune* to its own.
    - Block your own beam #sym.arrow.r free a teammate's path (*locally unrewarded*).

    #beamerbox([Objective])[
      Generate LLE levels *solvable* and that *require cooperation*.
    ]
  ][
    #set align(center + horizon)
    #image("../../assets/lvl6-annotated.png", width: 100%)
    #text(size: 12pt)[LLE Level 6 — the hard target]
  ]
]

// =============================================================================
//  PART 1: VERIFICATION (RQ1–2)
// =============================================================================
#my-slide[
  = Part 1 — Verification (RQ1–2)

  #v(10pt)

  #text(
    size: 14pt,
  )[*How can we formally verify that a level is solvable and that solving it genuinely requires cooperation?*]

  In this part we present our SAT-based verification tool:

  #v(8pt)
  #toolbox.side-by-side(columns: (1fr, 1fr))[
    *RQ1* --- Bounded-horizon solvability
    - Formalise the decision problem
    - Reduce to SAT: level + horizon #sym.arrow.r Boolean formula
    - Verify solvability with a SAT solver
  ][
    *RQ2* --- Cooperation detection
    - Reuse the SAT encoding, change one rule
    - Detect whether cooperation is required
    - Classify cooperation structures
  ]

  #v(8pt)
  #beamerbox(color: c-info, [Key idea])[
    SAT solver as a verification oracle: given a level and a horizon $T_"max"$,
    answer "solvable?" in bounded time.
  ]
]

// =============================================================================
//  BOUNDED-HORIZON SOLVABILITY → SAT
// =============================================================================
#my-slide[
  = Bounded-horizon solvability #sym.arrow.r SAT

  #v(10pt)

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    #beamerbox(color: c-info, [Decision problem])[
      Given a level $L$ and a horizon $T_"max"$,
      does a valid joint trajectory exist?
    ]
  ][
    #beamerbox(color: c-info, [SAT reduction])[
      Build a Boolean formula $Phi(L, T_"max")$.
      Satisfiable #sym.arrow.l.r.double solvable within $T_"max"$.
    ]
  ]

  #v(12pt)

  #align(center)[
    #text(size: 20pt)[
      $(L, T_"max")$ #sym.arrow.r
      #box(stroke: c-info + 1.5pt, fill: c-info.lighten(90%), radius: 3pt, inset: 8pt, baseline: 30%)[encode $Phi$]
      #sym.arrow.r
      #box(stroke: c-info + 1.5pt, fill: c-info.lighten(90%), radius: 3pt, inset: 8pt, baseline: 30%)[SAT solver]
      #sym.arrow.r SAT / UNSAT #sym.arrow.r solvable / unsolvable
    ]
  ]

  #v(12pt)

  *Why SAT?* Fast, well-known problem, modern solvers are highly efficient.

  *Complexity:* LLE solvability $in$ NP and $<= ""_p$ SAT. NP-hardness *open*.
]

// =============================================================================
//  COOPERATION DETECTION
// =============================================================================
#my-slide[
  = Detecting cooperation

  #v(10pt)

  *Idea:* keep the SAT encoding, change *one* rule: beams no longer block same-colour agents
  #sym.arrow.r the cooperation mechanic is *disabled*.

  #v(8pt)

  #beamerbox(color: c-info, [Cooperation criterion])[
    $L$ requires cooperation with $T_"max"$ #sym.arrow.l.r.double
    $Phi(L, T_"max")$ *SAT* and $Phi_"strict" (L, T_"max")$ *UNSAT*.
  ]

  #v(8pt)

  Three possible outcomes:
  #table(
    columns: 3,
    stroke: none,
    inset: (x: 12pt, y: 6pt),
    align: (left, left, left),
    table.hline(stroke: 1pt),
    [*Condition*], [*Label*], [*Meaning*],
    table.hline(stroke: 0.5pt),
    [$Phi$ UNSAT], [UNSOLVABLE], [No valid trajectory exists],
    [$Phi_"strict"$ UNSAT], [COOPERATIVE], [Every solution blocks a beam — cooperation required],
    [Otherwise], [NON_COOPERATIVE], [A solution exists without the blocking mechanic],
    table.hline(stroke: 1pt),
  )
]

// =============================================================================
//  HORIZON MATTERS
// =============================================================================
#my-slide[
  = Horizon matters

  #v(10pt)

  #toolbox.side-by-side(columns: (1fr, 1.3fr))[
    #set align(center + horizon)
    #image("../../results/cooperation_examples/horizon_demo.png", width: 70%)
  ][
    // Same level, three labels depending on T_max:
    #table(
      columns: 3,
      stroke: none,
      inset: (x: 8pt, y: 8pt),
      align: (left, center, center),
      table.hline(stroke: 1pt),
      [*Horizon*], [*Solvable*], [*Coop.*],
      table.hline(stroke: 0.5pt),
      [$T_"max" <= 2$], [no], [n/a],
      [$3 <= T_"max" <= 8$], [yes], [yes],
      [$T_"max" >= 9$], [yes], [no],
      table.hline(stroke: 1pt),
    )

    #v(6pt)
    - *Too small* #sym.arrow.r agents run out of moves; the level is falsely marked unsolvable
    - *Too large* #sym.arrow.r agents can take longer detours that bypass cooperation requirements

    #beamerbox(color: c-warn, [Trade-off])[
      Larger $T_"max"$ #sym.arrow.r more actions (more solutions), but bigger formula (longer solve duration).
      Pick the *smallest* $T_"max"$ that still admits a solution.
    ]
  ]
]

// =============================================================================
//  COOPERATION PROFILES
// =============================================================================
#my-slide[
  = Cooperation profiles

  #v(10pt)

  From one SAT model #sym.arrow.r a *dependency graph (edges: helper #sym.arrow.r beneficiary)* \
  classify by priority: $"fully coupled" succ "mutual" succ "distributed" succ "chain" succ "asymmetric"$.

  #v(6pt)
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr, 1fr),
    column-gutter: 8pt,
    row-gutter: 6pt,
    align: center,

    // ── labels (row 1) ──
    uncover("2-")[#text(size: 11pt, weight: "bold")[*asymmetric*]],
    uncover("3-")[#text(size: 11pt, weight: "bold")[*chain*]],
    uncover("4-")[#text(size: 11pt, weight: "bold")[*distributed*]],
    uncover("5-")[#text(size: 11pt, weight: "bold")[*mutual*]],
    uncover("6-")[#text(size: 11pt, weight: "bold")[*fully coupled*]],

    // ── level images (row 2) ──
    uncover("2-")[#image("../../results/cooperation_examples/asymmetric.png", width: 85%)],
    uncover("3-")[#image("../../results/cooperation_examples/chain.png", width: 85%)],
    uncover("4-")[#image("../../results/cooperation_examples/distributed.png", width: 85%)],
    uncover("5-")[#image("../../results/cooperation_examples/mutual.png", width: 85%)],
    uncover("6-")[#image("../../results/cooperation_examples/fully_coupled.png", width: 85%)],

    // ── dependency graphs (row 3) ──
    uncover("2-")[#image("../../results/cooperation_examples/dep_asymmetric.png", width: 85%)],
    uncover("3-")[#image("../../results/cooperation_examples/dep_chain.png", width: 85%)],
    uncover("4-")[#image("../../results/cooperation_examples/dep_distributed.png", width: 85%)],
    uncover("5-")[#image("../../results/cooperation_examples/dep_mutual.png", width: 85%)],
    uncover("6-")[#image("../../results/cooperation_examples/dep_fully_coupled.png", width: 85%)],
  )
]

// =============================================================================
//  PART 2: CONSTRUCTION (RQ3–4)
// =============================================================================
#my-slide[
  = Part 2 — Construction (RQ3–4)

  #v(10pt)

  #text(
    size: 14pt,
  )[*How can we embed formal verification inside a procedural generator so that every accepted level is certified, and can we control the cooperation structure by targeting specific profiles?*]

  In this part we present our level generators:

  #v(8pt)
  #toolbox.side-by-side(columns: (1fr, 1fr))[
    *RQ3* — Generator efficiency
    - Random placement with geometric constraints
    - Constructive lane-based approach
    - Level-6-style clustered design
    - SAT oracle filters solvable / cooperative levels
  ][
    *RQ4* — Output diversity
    - Five-profile taxonomy of cooperation structures
    - Generators can steer towards specific profiles
    - Constructive #sym.arrow.r mutual by design
  ]

  #v(8pt)
  #beamerbox(color: c-info, [Key idea])[
    Place-and-check with a SAT oracle: every accepted level is *provably* solvable.
  ]
]

// =============================================================================
//  GENERATORS — RANDOM
// =============================================================================
#my-slide[
  = Random Generator

  #v(10pt)

  #align(center + horizon)[
    #grid(
      columns: (1fr, 0.05fr, 1fr),
      column-gutter: 24pt,
      align: top + center,
      // Left: bad random (always visible)
      stack(
        spacing: 6pt,
        image("generated_examples/random_bad.png", width: 60%),
        text(size: 12pt, weight: "bold")[*Pure random* \ ],
        text(size: 10pt, fill: luma(50))[Lasers point off-grid, a wall block a laser source],
      ),
      // Right: progressive reveal (single grid cell)
      only(2)[
        #align(center + horizon)[
          #text(size: 25pt)[#sym.arrow.r]
        ]
      ],
      only(2)[
        #stack(
          spacing: 6pt,
          image("generated_examples/random_constrained.png", width: 60%),
          text(size: 12pt, weight: "bold")[*Constrained random* \ ],
          text(size: 10pt, fill: luma(50))[Filters out laser sources that behave like walls.],
        )
      ],
    )
  ]
]

// =============================================================================
//  GENERATORS — CONSTRUCTIVE (step-by-step)
// =============================================================================
#my-slide[
  = Constructive Cooperative Generator

  #v(10pt)

  Oriented *lane-based* design. Each agent gets a reserved lane, cooperation
  arises from crossing lasers. Near-zero rejection rate.

  #v(12pt)

  #grid(
    columns: (1fr, 0.1fr, 1fr, 0.1fr, 1fr),
    column-gutter: 4pt,
    align: top + center,
    stack(
      spacing: 4pt,
      image("generated_examples/constructive_generated_02_agents_exits.png", width: 70%),
      text(size: 10pt)[1. Reserve lanes, place agents + exits],
    ),
    [
      #uncover("2-")[
        #align(center + horizon)[
          #text(size: 25pt)[#sym.arrow.r]
        ]
      ]
    ],
    [
      #uncover("2-")[
        #stack(
          spacing: 4pt,
          image("generated_examples/constructive_generated_03_walls.png", width: 70%),
          text(size: 10pt, weight: "bold")[2. Place walls in free cells],
        )
      ]
    ],
    [
      #uncover("3-")[
        #align(center + horizon)[
          #text(size: 25pt)[#sym.arrow.r]
        ]
      ]
    ],
    [
      #uncover("3-")[
        #stack(
          spacing: 4pt,
          image("generated_examples/constructive_generated_04_full.png", width: 70%),
          text(size: 10pt, weight: "bold")[3. Add lasers crossing lanes],
        )
      ]
    ],
  )
]

// =============================================================================
//  GENERATORS — LEVEL-6-STYLE (step-by-step)
// =============================================================================
#my-slide[
  = Level-6-Style Generator

  #v(10pt)

  Clustered starts + exits on opposite sides. Shared laser corridor = mutual
  by design. SAT verifies.

  #v(12pt)

  #grid(
    columns: (1fr, 0.1fr, 1fr, 0.1fr, 1fr),
    column-gutter: 4pt,
    align: top + center,
    stack(
      spacing: 4pt,
      image("generated_examples/level6_generated_02_agents_exits.png", width: 85%),
      text(size: 10pt)[1. Place clusters on opposite sides],
    ),
    [
      #uncover("2-")[
        #align(center + horizon)[
          #text(size: 25pt)[#sym.arrow.r]
        ]
      ]
    ],
    [
      #uncover("2-")[
        #stack(
          spacing: 4pt,
          image("generated_examples/level6_generated_03_lasers.png", width: 85%),
          text(size: 10pt)[2. Fill the central corridor with lasers],
        )
      ]
    ],
    [
      #uncover("3-")[
        #align(center + horizon)[
          #text(size: 25pt)[#sym.arrow.r]
        ]
      ]
    ],
    [
      #uncover("3-")[
        #stack(
          spacing: 4pt,
          image("generated_examples/level6_generated_04_full.png", width: 85%),
          text(size: 10pt, weight: "bold")[3. Add walls to shape the solution space],
        )
      ]
    ],
  )
]

// =============================================================================
//  RESULT 2: GENERATOR EFFICIENCY
// =============================================================================
#my-slide[
  = Generator efficiency (RQ3)

  #v(10pt)

  // #toolbox.side-by-side(columns: (2fr, 0.6fr), gutter: 30pt, align: center)[
  //   #image("../../results/rejection_benchmark/rejection_rate_by_generator.png", width: 100%)
  // ][
  //   - ""
  // ]

  // #align(center)[
  //   #image("../../results/rejection_benchmark/rejection_rate_by_generator.png", width: 75%)
  // ]

  #toolbox.side-by-side(columns: (1.6fr, 0.4fr))[
    #align(center)[
      #image("../../results/rejection_benchmark/rejection_rate_by_generator.png", width: 100%)
    ]
  ][
    - 3x3 / 2-agents / 1-laser
    - 5x5 / 3-agents / 2-lasers
    - 8x8 / 4-agents / 3-lasers
  ]
]

// =============================================================================
//  RESULT 3: PROFILE DIVERSITY
// =============================================================================
#my-slide[
  = Output diversity (RQ4)

  #v(10pt)

  // #align(center)[
  //   #image("../../results/profile_benchmark/profile_distribution.png", width: 90%)
  // ]

  // #v(8pt)
  // #align(center)[
  //   Profiles of accepted cooperative levels (8×8, 3 agents, 2 lasers):
  //   - Constructive #sym.arrow.r $92 %$ `mutual` (by design).
  //   - Level-6-style #sym.arrow.r $68 %$ `mutual` (geometry).
  //   - Random #sym.arrow.r mostly `asymmetric`.
  // ]

  #toolbox.side-by-side(columns: (1.6fr, 0.4fr))[
    #align(center)[
      #image("../../results/profile_benchmark/profile_distribution.png", width: 100%)
    ]
  ][
    - Constructive #sym.arrow.r $92 %$ `mutual`.
    - Level-6-style #sym.arrow.r $68 %$ `mutual`.
    - Random #sym.arrow.r mostly `asymmetric`.
  ]
  #align(center)[
    (8x8 / 3-agents / 2-lasers)
  ]
]

// =============================================================================
//  PART 3: EXPERIMENT (RQ5–6)
// =============================================================================
#my-slide[
  = Part 3 — Experiment (RQ5–6)

  #v(10pt)

  #text(
    size: 14pt,
  )[*Can MARL agents trained on certified levels generalise to held-out ones, and does a staged curriculum outperform direct training on a hard target?*]

  In this part we investigate whether generated levels are learnable:

  #v(8pt)
  #toolbox.side-by-side(columns: (1fr, 1fr))[
    *RQ5* — Learnability
    - Train IQL / VDN / QMIX on certified levels
    - Measure train vs. test success
    - Scale training data to close the generalisation gap
  ][
    *RQ6* — Curriculum learning
    - Compare curriculum orderings (direct, forward, mixed, reverse)
    - Test harder cooperation targets (mutual, Level-6)
  ]
]

// =============================================================================
//  RESULT 4: LEARNABILITY
// =============================================================================
#my-slide[
  = Learnability (RQ5)

  #v(10pt)

  #toolbox.side-by-side(columns: (1.4fr, 0.6fr))[
    #align(center)[
      #image("../../results/learnability_5x5/figures/learning_curves.pdf", width: 100%)
    ]
  ][
    #align(center)[
      (200k steps, 5x5 / 2-agents / 1-laser, asymmetric)
      #takeaway[Learnable at 5×5, but too few levels #sym.arrow.double overfitting]
    ]
  ]
]

// =============================================================================
//  RESULT 5: DATA SCALING
// =============================================================================
#my-slide[
  = Scaling data (RQ5)

  #v(10pt)

  #toolbox.side-by-side(columns: (1.4fr, 0.6fr))[
    #align(center)[
      #image("../../results/data_scaling/data_scaling_curve.pdf", width: 100%)
    ]
  ][
    #align(center)[
      (300k steps, 5x5 / 2-agents / 1-laser, asymmetric)
      #takeaway[Unlimited certified levels ⇒ overfitting becomes generalisation.]
    ]
  ]
]

// =============================================================================
//  RESULT 6A: CURRICULUM ORDERING
// =============================================================================
#my-slide[
  = Curriculum ordering (RQ6)

  #v(10pt)

  #align(center)[
    #image("../../results/curriculum_strategy/figures/final_success.pdf", width: 85%)
  ]

  #align(center)[
    Four budget-matched schedules (400k steps, 6×6 / 2-agents / 1-laser, asymmetric)
  ]
]

// =============================================================================
//  RESULT 6B: CURRICULUM TARGETS
// =============================================================================
#my-slide[
  = Curriculum targets (RQ6)

  #v(10pt)

  #toolbox.side-by-side(columns: (1.1fr, 1fr))[
    #set text(size: 13pt)
    #table(
      columns: (auto, auto, auto, auto, auto),
      stroke: none,
      inset: (x: 6pt, y: 3.5pt),
      align: horizon,
      table.hline(stroke: 1pt),
      [*Target*], [*Grid*], [*Coop.*], [*Budget*], [*Test*],
      table.hline(stroke: 0.5pt),
      [Learnability], [5×5], [asym], [200k], [0.20],
      [Curric. order], [6×6], [asym], [400k], [0.17],
      [Frontier], [6×6], [*mutual*], [600k], [*0.00*],
      [Frontier], [5×5], [*mutual*], [200k], [*0.00*],
      [Level-6], [12×13], [*mutual*], [2M], [*0.00*],
      table.hline(stroke: 1pt),
    )
  ][
    - Reachable target: ordering doesn't beat *direct*; only data *diversity* helps.
    - A *cliff* at *mutual* cooperation: success #sym.arrow.r *zero*, even at 10× budget.

    #takeaway[Scoped *negative* result: the base *mutual* task is unlearnable by IQL/VDN/QMIX.]
  ]
]

// =============================================================================
//  UPSTREAM CONTRIBUTION
// =============================================================================
#my-slide[
  = Beyond the thesis: upstream

  #v(10pt)

  Solver, cooperation detector, and generators are *merged into the official LLE library* \
  (`laser-learning-environment[generator]`, PyPI, v2.9.0+).

  #v(8pt)
  #beamerbox(color: c-info, [Public API])[
    `lle.solve` #sym.dot.c `lle.is_cooperative` #sym.dot.c `lle.cooperation_level` #sym.dot.c `lle.generate`
  ]

  #v(8pt)
  #takeaway[Not just thesis artefacts --- *usable tooling* for the LLE users.]
]

// =============================================================================
//  CONCLUSION
// =============================================================================
#my-slide[
  = Conclusion
  #v(10pt)

  #set text(size: 14pt)
  - *RQ1* ✓ --- SAT verification tool for solvability; in NP, $<= ""_p$ SAT.
  - *RQ2* ✓ --- strict counterfactual: coop. #sym.arrow.l.r.double SAT $and$ strict-UNSAT.
  - *RQ3* ✓ --- SAT-as-oracle generators; every accepted level *certified*.
  - *RQ4* ✓ --- five-profile taxonomy; generators steer toward `mutual`.
  - *RQ5* ✓ --- certified levels learnable; scaling data closes the gap.
  - *RQ6* ✗ --- value-based MARL can't learn *mutual* cooperation; no curriculum helps.

  #v(4pt)
  #takeaway[Central contribution: procedural generation coupled to *explicit certification*.]
]

// =============================================================================
//  FUTURE WORK
// =============================================================================
#my-slide[
  = Future work

  #v(10pt)

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    == Theory & model
    #v(10pt)
    - Settle *NP-hardness* of LLE solvability.
    - Add *gems* and true *void* tiles.
    - Richer (time-indexed / weighted) cooperation graphs.
  ][
    == Learning
    #v(10pt)
    - *Make mutual coordination learnable*: dense / intrinsic rewards.
    - Deeper research into cooperation structures: how do they affect learnability? Is the learning of one profile a stepping to another?
    - Beyond value-based: actor-critics (MADDPG, COMA), MAVEN.
  ]

  #v(8pt)
  The certification framework is settled; the open question is *how far it extends*.
]

// =============================================================================
//  THANK YOU
// =============================================================================
#my-slide[

  = Summary

  #v(10pt)

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

  #v(6pt)
  #toolbox.side-by-side(columns: (1.1fr, 1fr))[
    *Contributions*
    + SAT verification tool for LLE solvability.
    + Cooperation detector + five-profile taxonomy.
    + Solver-in-the-loop certified generators.
    + Merged into the official LLE library.

    *Key results*
    + Constructive generator $approx$ free.
    + Scaling certified data closes the generalisation gap.
    + A learnability *cliff* at mutual cooperation.
  ][
  ]
]

// ###############################################################################
//  BACKUP SLIDES
// ###############################################################################
#slide[
  #set align(horizon + center)
  #text(size: 22pt, weight: "bold")[Backup slides]
]
