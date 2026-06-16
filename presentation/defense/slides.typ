#import "@preview/polylux:0.4.0": *
#import "progress_bar.typ": my-slide

// =============================================================================
//  Master thesis defense — Hugo Charels (ULB, 2025–2026)
//  "Procedural Generation of Solvable Cooperative Levels for the LLE"
//  Style inherited from presentation/MLG-Student-Day/slides.typ.
//  Speaker notes are inline Typst comments (// ...) on each slide.
//  ~20 min talk: keep spoken detail in the notes, not on the slides.
//  The progress bar (progress_bar.typ) fills to 100% on the last `my-slide`
//  ("Thank you"); backup slides use plain `#slide` and carry no bar.
// =============================================================================

#set text(size: 16pt, font: "Lato")

// A little more air: slightly looser lines and more space between bullets.
// #set par(leading: 0.75em)
// #set list(spacing: 1.0em, indent: 0.4em)
// #set enum(spacing: 1.0em, indent: 0.4em)

// Slide titles and sub-headings — bigger and bold, with space beneath.
#show heading.where(level: 1): set text(size: 22pt, weight: "bold")
#show heading.where(level: 2): set text(size: 20pt, weight: "bold")
#show heading.where(level: 3): set text(size: 18pt, weight: "bold")

#set page(
  paper: "presentation-16-9",
  margin: 1cm,
  footer: align(bottom, toolbox.full-width-block(inset: 8pt)[#align(right, text(size: 12pt, (toolbox.slide-number)))]),
)

// ─── Palette ──────────────────────────────────────────────────────────────────
// Two accents only: a clean blue for statements/info, a warm orange for the
// takeaway, plus an amber for the one caveat box. No teal/blue-green.
#let c-info = rgb("#1F5FA8")   // statements, criteria, guarantees, definitions
#let c-take = rgb("#E0701B")   // takeaways
#let c-warn = rgb("#C08A12")   // caveats

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
//  TITLE / COVER  (plain `#slide` — carries no progress bar)
// =============================================================================
#slide[
  #set align(horizon)
  #set page(margin: 2cm)

  #place(top + right, image(height: 20%, "../../assets/logos/MLG_logo.png"))
  #place(top + left, image(height: 20%, "../../assets/logos/Université_libre_de_Bruxelles_logo.svg"))
  #place(bottom + right, dx: 0.5cm, dy: -0.8cm, image(height: 60%, "../../assets/lvl6-annotated.png"))

  #text("")

  #text(size: 26pt, weight: "bold")[
    Procedural Generation of \ Solvable Cooperative Levels \ for the Laser Learning Environment
  ]
  #v(6pt)
  #text(size: 18pt)[*Hugo Charels* --- Master thesis defense]
  #v(2pt)
  #text(size: 15pt)[Supervisors: Tom Lenaerts #sym.dot.c Yannick Molinghen]
  #v(2pt)
  #text(size: 14pt, fill: luma(90))[ULB --- Academic year 2025-2026 #sym.dot.c #emph[17/06/2026]]
]

// =============================================================================
//  CONTEXT  (Context + LLE merged into one background slide)
// =============================================================================
#my-slide[
  = Context & motivation

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
  // Notes: certified levels, not plausible-looking ones. LLE is hard for value-based MARL
  // perfect coordination, interdependence, zero-incentive dynamics. Scope: exit-reaching only;
  // gems / void out of scope; n_a <= 4. Metric = team success rate (every agent exits).
]

// =============================================================================
//  RESEARCH QUESTIONS
// =============================================================================
#my-slide[
  = Research questions

  Generate levels *provably solvable* and *provably cooperative* — and use them to train MARL.

  #v(8pt)
  #toolbox.side-by-side(columns: (1fr, 1fr))[
    *Formal (contributions)*
    - *RQ1* --- verify *solvable*.
    - *RQ2* --- verify *requires cooperation*.
    - *RQ3* --- verification *inside a generator*.
    - *RQ4* --- *control* the cooperation *structure*.
  ][
    *Empirical*
    - *RQ5* --- can MARL agents *learn* generated levels?
    - *RQ6* --- does a *curriculum* reach Level 6?
  ]

  #v(8pt)
  #takeaway[Verification (RQ1–2) #sym.dot.c Construction (RQ3–4) #sym.dot.c Experiment (RQ5–6).]
]

// =============================================================================
//  FORMALISATION + REDUCTION
// =============================================================================
#my-slide[
  = Bounded-horizon solvability #sym.arrow.r SAT

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    == Model
    - Level $L = (H, W, C, s_p, cal(W), cal(S), cal(E))$, horizon $T_("max")$.
    - *Valid trajectory*: legal moves, no collisions, laser safety, all agents on exits at $T_("max")$.
    - *Solvable* = such a trajectory exists.

    == Variables (per step $t$)
    - $a_(c,x,y,t)$ #sym.dot.c $b_(c,d,x,y,t)$ #sym.dot.c $l_(c,x,y,t)$
    - Constraints: *init* #sym.dot.c *movement* #sym.dot.c *lasers*
  ][
    #beamerbox(color: c-info, [Verification tool])[
      SAT solver decides weither $Phi(L, T_("max"))$ is satisfiable #sym.arrow.l.r.double a valid trajectory of length $T_("max")$ exists.
    ]
    #v(4pt)
    #takeaway[Poly-size, poly-time encoding $=>$
      LLE solvability $in$ NP and $<= ""_p$ SAT.\ NP-hardness *open*.]
  ]
  // formulations (local vs global) are in the backup slides.
]

// =============================================================================
//  COOPERATION DETECTION
// =============================================================================
#my-slide[
  = Detecting cooperation

  #toolbox.side-by-side(columns: (1.2fr, 1fr))[
    *Idea:* keep the encoding, change *one* rule: beams no longer block same-colour agents, so the cooperation mechanic is *disabled*.

    #beamerbox(color: c-info, [Verification criterion])[
      $L$ requires cooperation with $T_("max")$ #sym.arrow.l.r.double
      $Phi(L, T_("max"))$ *SAT* and $Phi_("strict")(L, T_("max"))$ *UNSAT*.
    ]

    Solvable normally but impossible without blocking #sym.arrow.double every solution uses the mechanic.
  ][
    *Two SAT calls:*
    + $"Solver" =$ UNSAT → `UNSOLVABLE`
    + $"Strict" =$ UNSAT → `COOPERATIVE`
    + else → `NON_COOPERATIVE`

    #v(5pt)
    #beamerbox(color: c-warn, [Horizon matters])[
      Label is relative to $T_("max")$. a too-long horizon lets a detour bypass the beam.
    ]
  ]
]

// =============================================================================
//  COOPERATION PROFILES
// =============================================================================
#my-slide[
  = Cooperation profiles

  From one SAT model #sym.arrow.r a *helper #sym.arrow.r beneficiary graph* \
  classify by priority: $"fully coupled" succ "mutual" succ "distributed" succ "chain" succ "asymmetric"$.

  #v(4pt)
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr, 1fr),
    column-gutter: 10pt,
    align: center,
    image("../../results/cooperation_examples/asymmetric.png", width: 90%),
    image("../../results/cooperation_examples/chain.png", width: 90%),
    image("../../results/cooperation_examples/distributed.png", width: 90%),
    image("../../results/cooperation_examples/mutual.png", width: 90%),
    image("../../results/cooperation_examples/fully_coupled.png", width: 90%),

    text(size: 12pt)[*asymmetric*],
    text(size: 12pt)[*chain*],
    text(size: 12pt)[*distributed*],
    text(size: 12pt)[*mutual*],
    text(size: 12pt)[*fully coupled*],
  )

  #v(4pt)
  #takeaway[The profile is the *generation target* a generator can request.]
  // Notes: first taxonomy recovering dependency structure from a SAT certificate in LLE.
  // Binary verdict + necessary-helper set are level invariants; the label is plan-dependent.
]

// =============================================================================
//  GENERATORS
// =============================================================================
#my-slide[
  = Generators

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    *SAT as an acceptance oracle, in the loop.* Solvability is the floor; *cooperation* and
    *profile* are optional layers.

    #v(2pt)
    #grid(
      columns: 3,
      gutter: 6pt,
      align: center,
      image("../../assets/unsolvable_map_example.png", width: 100%),
      image("../../assets/bad_map_example.png", width: 100%),
      image("../../assets/good_map_example.png", width: 100%),

      text(size: 11pt)[(a) unsolvable\ #text(fill: red)[rejected]],
      text(size: 11pt)[(b) solvable,\ no coop.],
      text(size: 11pt)[(c) cooperative\ #text(fill: rgb("#2E8B45"))[accepted]],
    )
  ][
    #set text(size: 13pt)
    #table(
      columns: (auto, 1fr),
      stroke: none,
      inset: (x: 5pt, y: 5pt),
      table.hline(stroke: 1pt),
      [*Generator*], [*Profile tendency*],
      table.hline(stroke: 0.5pt),
      [Random], [mostly `asymmetric`],
      [Constructive], [`asym`/`mutual`/`distrib` by laser count],
      [Level-6-style], [`mutual` by design],
      table.hline(stroke: 1pt),
    )
    #v(3pt)
    #beamerbox(color: c-info, [Guarantee])[
      Every accepted level is *solvable* for a bounded horizon $T_"max"$.
    ]
  ]
]

// =============================================================================
//  RESULT 1: SAT ENCODING
// =============================================================================
#my-slide[
  = Result 1 --- SAT encoding

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/sat_encoding/clauses_per_level.png", width: 100%)
  ][
    Enforcing "one position per agent per step":
    - *global* — pairwise over the grid, $O(p^2)$;
    - *local* — neighbourhood-based, $O(p)$.

    Local scales far better: *253k vs 1.17M* clauses on Level 6, and faster to solve.

    #takeaway[The internal *encoding* drives cost. Local is the default.]
  ]
  // Notes: global wins only below the crossover (tiny grids). Level 6 has 7x more clauses
  // than 8x8 yet solves faster — runtime is search structure, not formula size.
]

// =============================================================================
//  RESULT 2: GENERATOR EFFICIENCY
// =============================================================================
#my-slide[
  = Result 2 --- Generator efficiency (RQ3)

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/rejection_benchmark/rejection_rate_by_generator.png", width: 100%)
  ][
    - *Constructive (coop.)*: $approx$ $0–6 %$ --- cooperation is *built in*.
    - *Random (coop.)*: up to $98.7%$ --- coop. levels are a rare subset.
    - *Level-6-style*: in between.

    #takeaway[Construction beats blind sampling: near-free certified data.]
  ]
]

// =============================================================================
//  RESULT 3: PROFILE DIVERSITY
// =============================================================================
#my-slide[
  = Result 3 — Output diversity (RQ4)

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/profile_benchmark/profile_distribution.png", width: 100%)
  ][
    Profiles of accepted cooperative levels (8×8, 3 agents, 2 lasers):
    - *Constructive* #sym.arrow.r $92 %$ `mutual` (by design).
    - *Level-6-style* #sym.arrow.r $68 %$ `mutual` (geometry).
    - *Random* #sym.arrow.r mostly `asymmetric`.

    #takeaway[We can *choose* the cooperation structure of generated levels.]
  ]
]

// =============================================================================
//  RESULT 4: LEARNABILITY
// =============================================================================
#my-slide[
  = Result 4 --- Learnability (RQ5)

  #toolbox.side-by-side(columns: (1.1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/learnability_5x5/figures/learning_curves.pdf", width: 100%)
  ][
    5×5, 2 agents, 1 laser #sym.dot.c IQL/VDN/QMIX #sym.dot.c 20 seeds.
    - All reach non-trivial *training* success.
    - Large *train–test gap* ($<= 0.52$): they *memorise* the 20 levels.

    #takeaway[Learnable at 5×5, but too few levels #sym.arrow.double overfitting]
  ]
  // Notes: held-out means coincide => generalisation, not credit assignment, is the bottleneck.
]

// =============================================================================
//  RESULT 5: DATA SCALING
// =============================================================================
#my-slide[
  = Result 5 --- Scaling data closes the gap (RQ5)

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/data_scaling/data_scaling_curve.pdf", width: 100%)
  ][
    Same task but only *pool size* varies ($20 arrow.r 100 arrow.r 500$).

    #table(
      columns: 4,
      stroke: none,
      inset: (x: 6pt, y: 3pt),
      align: center,
      table.hline(stroke: 1pt),
      [*|train|*], [*train*], [*test*], [*gap*],
      table.hline(stroke: 0.5pt),
      [20], [0.65], [0.14], [0.50],
      [100], [0.47], [0.28], [0.19],
      [500], [0.43], [0.43], [*0.00*],
      table.hline(stroke: 1pt),
    )

    #takeaway[Unlimited certified levels ⇒ overfitting becomes generalisation.]
  ]
]

// =============================================================================
//  RESULT 6: CURRICULUM / THE CLIFF
// =============================================================================
#my-slide[
  = Result 6 — Curriculum & its limit (RQ6)

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
    - A *cliff* at *mutual* cooperation: success → *zero*, even at 10× budget.

    #takeaway[Scoped *negative* result: the base *mutual* task is unlearnable by IQL/VDN/QMIX
      — not a curriculum failure.]
  ]
  // Notes: 3 reasons in backup — no reward to amplify, no partial skill, IGM/monotonic factorisation.
]

// =============================================================================
//  UPSTREAM CONTRIBUTION
// =============================================================================
#my-slide[
  = Beyond the thesis: upstream

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

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    == Theory & model
    - Settle *NP-hardness* of LLE solvability.
    - Add *gems* and true *void* tiles.
    - Richer (time-indexed / weighted) cooperation graphs.
  ][
    == Learning
    - *Make mutual coordination learnable*: dense / intrinsic rewards.
    - Beyond value-based: actor-critics (MADDPG, COMA), MAVEN.
    - Surface the `fully coupled` profile.
  ]

  #v(8pt)
  The certification framework is settled; the open question is *how far it extends*.
]

// =============================================================================
//  THANK YOU  (last main slide — progress bar reaches 100% here)
// =============================================================================
#my-slide[
  = Thank you

  #place(top + right, image(height: 13%, "../../assets/logos/MLG_logo.png"))
  #place(top + right, dx: -9cm, image(height: 13%, "../../assets/logos/Université_libre_de_Bruxelles_logo.svg"))
  #place(bottom + right, dx: -1cm, dy: -1.6cm, image(height: 50%, "../../assets/qr-code_repo-link.png"))

  #v(6pt)
  #toolbox.side-by-side(columns: (1.1fr, 1fr))[
    *Contributions*
    + SAT verification tool for LLE solvability.
    + Cooperation detector + five-profile taxonomy.
    + Solver-in-the-loop certified generators.
    + Merged into the official LLE library.

    *Key results*
    + Local encoding scales; constructive generator $approx$ free.
    + Scaling certified data closes the generalisation gap.
    + A learnability *cliff* at mutual cooperation.
  ][]

  #v(4pt)
  #align(center, text(size: 18pt, weight: "bold")[Questions?])
]

// #############################################################################
//  BACKUP SLIDES  (plain `#slide` — no progress bar — Q&A only, detail is fine)
// #############################################################################
#slide[
  #set align(horizon + center)
  #text(size: 22pt, weight: "bold")[Backup slides]
]

// ─── B: full encoding ────────────────────────────────────────────────────────
#slide[
  = Backup — Full SAT encoding

  == Variables
  - $a_(c,x,y,t)$: agent $c$ at $(x,y)$ at step $t$
  - $b_(c,d,x,y,t)$: beam of colour $c$, direction $d$, active at $(x,y,t)$
  - $l_(c,x,y,t)$: laser of colour $c$ active at $(x,y,t)$

  == Constraints (4.1–4.13)
  #toolbox.side-by-side()[
    *Init*
    - 4.1 agent start tiles
    - 4.2 laser-source cells
  ][
    *Movement*
    - 4.3 forward consistency
    - 4.4 global / 4.5 local uniqueness
    - 4.6 backward consistency
    - 4.7 no overlap / no following
    - 4.8 victory · 4.9 stay-on-exit
  ][
    *Lasers*
    - 4.10 walls block beams
    - 4.11 beam propagation
    - 4.12 beam↔laser link
    - 4.13 no step on foreign laser
  ]

  $O((n_a + s) p tau)$ variables; clause count polynomial in $n_a, p, s, tau$.
]

// ─── B: local vs global ───────────────────────────────────────────────────────
#slide[
  = Backup — Local vs global uniqueness

  *Global (A):* $ and.big_(c) and.big_(t) and.big_((x_1,y_1) eq.not (x_2,y_2)) not a_(c,x_1,y_1,t) or not a_(c,x_2,y_2,t) quad O(n_a tau p^2) $

  *Local (B):* neighbourhood exclusivity over $"next"(x,y)$ + backward consistency $ quad O(n_a tau p) $

  Both admit the *same* satisfying assignments. Local is asymptotically smaller in $p$ but pays a
  fixed overhead; below the *crossover* grid size the global form is more compact.

  #v(4pt)
  #table(
    columns: 5,
    stroke: none,
    inset: (x: 8pt, y: 4pt),
    align: center,
    table.hline(stroke: 1pt),
    [*Level*], [3×3], [5×5], [8×8], [Level 6],
    table.hline(stroke: 0.5pt),
    [global], [753], [8 214], [166 736], [1 167 640],
    [local], [785], [6 204], [77 516], [252 964],
    table.hline(stroke: 1pt),
  )
  #text(size: 12pt)[Clause counts. Level 6: 7× more clauses than 8×8 yet solves faster — search structure, not size.]
]

// ─── B: why the encoding is correct ──────────────────────────────────────────
#slide[
  = Backup — Why the encoding is correct

  #beamerbox(color: c-info, [Decision equivalence])[
    For either movement formulation, $Phi(L, T_("max"))$ is satisfiable #sym.arrow.l.r.double a
    valid joint trajectory of length $T_("max")$ exists.
  ]

  *SAT ⇒ trajectory.* Init fixes one start per agent; forward consistency + uniqueness (global) — or
  forward + local + backward (local) — force exactly one legal position per agent per step.
  Movement / collision / laser / exit clauses make the extracted trajectory valid.

  *Trajectory ⇒ SAT.* Given a valid trajectory, set $a$ from positions and $b, l$ from the
  deterministic beam dynamics; every clause family holds by construction.

  *Consequence.* Poly-time, poly-size reduction ⇒ bounded-horizon LLE solvability $in$ NP and
  $<=_p$ SAT. NP-hardness open.
]

// ─── B: why the cooperation criterion holds ──────────────────────────────────
#slide[
  = Backup — Why the cooperation criterion holds

  #beamerbox(color: c-info, [Verification criterion])[
    $L$ requires cooperation at $T_("max")$ #sym.arrow.l.r.double $Phi$ SAT and $Phi_("strict")$ UNSAT.
  ]

  *(⇒)* Cooperation ⇒ solvable, so $Phi$ SAT. If $Phi_("strict")$ were SAT, the strict trajectory
  would be a valid standard solution *without* blocking — contradiction.

  *(⇐)* $Phi$ SAT ⇒ solvable. If some standard solution used *no* blocking, both semantics give
  identical beams along it, so it would satisfy $Phi_("strict")$ — contradicting UNSAT. Hence every
  solution blocks at least one beam.

  Strict encoding changes one clause family:
  $b_(c,d,x',y',t) <-> b_(c,d,x,y,t)$ instead of $b_(c,d,x',y',t) <-> (b_(c,d,x,y,t) and not a_(c,x',y',t))$.
]

// ─── B: horizon dependence ─────────────────────────────────────────────────────
#slide[
  = Backup — Horizon-dependence of cooperation

  #toolbox.side-by-side(columns: (1fr, 1.3fr))[
    #set align(center + horizon)
    #image("../../results/cooperation_examples/horizon_demo.png", width: 70%)
  ][
    Same level, three labels depending on $T_("max")$:
    #table(
      columns: 3,
      stroke: none,
      inset: (x: 8pt, y: 4pt),
      align: (left, center, center),
      table.hline(stroke: 1pt),
      [*Horizon*], [*Solvable*], [*Coop.*],
      table.hline(stroke: 0.5pt),
      [$T_("max") <= 2$], [no], [n/a],
      [$3 <= T_("max") <= 8$], [yes], [yes],
      [$T_("max") >= 9$], [yes], [no],
      table.hline(stroke: 1pt),
    )
    Too generous ⇒ a *detour* fits ⇒ under-detected. Too tight ⇒ rejected as unsolvable.
    We pick the smallest horizon fitting a short solution + margin.
  ]
]

// ─── B: selective strict / necessary helpers ───────────────────────────────────
#slide[
  = Backup — Selective-strict & necessary helpers

  *Selective-strict ($K subset.eq C_("src")$):* strict clauses for colours in $K$, standard for the
  rest. $K = nothing$ → standard; $K = C_("src")$ → strict.

  *Necessary-helper set:* for each colour $c$, run one selective-strict call with $K = {c}$;
  if UNSAT, $c$ is *necessary*.

  #beamerbox(color: c-info, [Invariants vs plan-dependent])[
    - *Level invariants*: binary verdict, necessary-helper set.
    - *Plan-dependent*: helper events, dependency graph, profile *label*.
  ]
]

// ─── B: profile order ──────────────────────────────────────────────────────────
#slide[
  = Backup — Profile ordering structure

  #toolbox.side-by-side(columns: (1.1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/cooperation_examples/profile_venn.png", width: 100%)
  ][
    Predicates on $G_L$: $cal(A)$ asymmetric (base), $cal(C)$ chain, $cal(D)$ distributed,
    $cal(M)$ mutual, $cal(F)$ fully coupled.

    Only structural entailment: $cal(F) => cal(C)$. The rest are *incomparable* (pure chain /
    fan-in / reciprocal pair / 3-cycle witnesses).

    Priority $cal(F) succ cal(M) succ cal(D) succ cal(C) succ cal(A)$ is one linear extension,
    fixed by convention.
  ]
]

// ─── B: constructive generator ─────────────────────────────────────────────────
#slide[
  = Backup — Constructive generator

  - Pick orientation; sample $n_a$ distinct *lanes*; place start/exit at lane ends; reserve lane cells.
  - Cooperative mode plants a dependency per laser: distinct colour ($n_l <= n_a$), beam crossing the
    lane band; reserve the full beam segment before placing walls.
  - Shuffle remaining cells; place $n_w$ walls; verify with the SAT oracle.

  #beamerbox(color: c-info, [Profile by laser count])[
    $n_l = 1$ → `asymmetric` · $n_l = 2$ → `mutual` · $n_l >= 3$ → shifts to `distributed`.
  ]

  Level-6-style: clustered starts/exits + a laser corridor ⇒ `mutual` like Level 6.
]

// ─── B: learnability detail ────────────────────────────────────────────────────
#slide[
  = Backup — Learnability detail (5×5)

  #toolbox.side-by-side(columns: (1fr, 1fr))[
    #set align(center + horizon)
    #image("../../results/learnability_5x5/figures/final_bar_chart.pdf", width: 100%)
  ][
    #table(
      columns: 4,
      stroke: none,
      inset: (x: 8pt, y: 4pt),
      align: horizon,
      table.hline(stroke: 1pt),
      [*Algo*], [*Train*], [*Test*], [*Gap*],
      table.hline(stroke: 0.5pt),
      [IQL], [$0.60 plus.minus 0.03$], [$0.23 plus.minus 0.03$], [0.37],
      [VDN], [$0.70 plus.minus 0.05$], [$0.18 plus.minus 0.03$], [0.52],
      [QMIX], [$0.59 plus.minus 0.03$], [$0.20 plus.minus 0.03$], [0.39],
      table.hline(stroke: 1pt),
    )
    20 seeds, 200k steps. VDN fits train best yet generalises worst — capacity spent memorising.
  ]
]

// ─── B: curriculum ordering ────────────────────────────────────────────────────
#slide[
  = Backup — Curriculum ordering (reachable 6×6)

  Four budget-matched schedules, 400k steps, 6×6 / 2-agent / 1-laser (asymmetric):

  #table(
    columns: 4,
    stroke: none,
    inset: (x: 9pt, y: 4pt),
    align: horizon,
    table.hline(stroke: 1pt),
    [*Condition*], [*Train*], [*Test*], [*Gap*],
    table.hline(stroke: 0.5pt),
    [Mixed (dom. rand.)], [$0.39$], [*$0.22$*], [0.17],
    [Direct], [$0.41$], [$0.17$], [0.24],
    [Forward (easy→hard)], [$0.39$], [$0.15$], [0.24],
    [Reverse (hard→easy)], [$0.10$], [$0.07$], [0.03],
    table.hline(stroke: 1pt),
  )

  - *Forward* curriculum does *not* beat *direct* (budget stolen from the target).
  - *Reverse* collapses → *catastrophic forgetting*.
  - Only *mixed* helps — that is data *diversity*, not ordering.
]

// ─── B: why mutual is unlearnable ──────────────────────────────────────────────
#slide[
  = Backup — Why mutual cooperation is unlearnable here

  + *No reward to amplify.* Mutual reward arrives only after the whole jointly-gated sequence;
    return stays negative. A curriculum amplifies a faint signal — it cannot create one.
  + *No partial skill in easier stages.* Asymmetric coop. admits partial credit; mutual is a
    deadlock-style discontinuity — staging laser count (0→1→2) ended at ≈0.
  + *Representation limit.* VDN/QMIX monotonic factorisation enforces IGM; the mutual move is
    individually suboptimal for *both* agents (relative overgeneralisation). IQL has no joint value.

  #takeaway[Nonzero *train* but zero *held-out* = memorised trajectories, not a policy.]
]

// ─── B: related work ───────────────────────────────────────────────────────────
#slide[
  = Backup — Related work & positioning

  - *Cooperative MARL / LLE* (Molinghen et al.): coordination bottlenecks; VDN, QMIX, MADDPG, COMA, MAVEN.
  - *Dependency structure*: coordination graphs (assume structure) vs ours (recovered from a SAT certificate).
  - *PCG under constraints*: search-based / ASP oracles; PCGML (no guarantees); PCGRL (opposite direction).
  - *Curriculum / env. design*: POET, PAIRED (adaptive, adversarial) — ours is a *static* certified generator.
  - *Compilation*: SAT-planning (SATPLAN), compilation-based MAPF (we add laser propagation + strict counterfactual).
  - *Formal methods + RL*: shielded RL filters *actions*; we filter *training material*.
]

// ─── B: scope / threats ────────────────────────────────────────────────────────
#slide[
  = Backup — Scope & threats to validity

  *Scope.* Exit-reaching task only; gems and scoring out of scope; void tiles modelled as walls
  (valid only when no beam crosses a void). $1 <= n_a <= 4$ is an engine bound, not an encoding limit.

  *RQ6 caveats (we do not overclaim):*
  - Narrow algorithm family (IQL/VDN/QMIX); centralised critics / coordinated exploration untested.
  - Sparse, unshaped reward; a dense signal could change the bottleneck.
  - Small seed counts on mutual targets — enough to establish *zero*, not small effects.

  *Cooperation criterion* is horizon-relative; the profile *label* is plan-dependent.
]
