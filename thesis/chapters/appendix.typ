#import "../macros.typ": fref

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Zero-pad an integer to three digits ("0", "12", "123" -> "000", "012", "123").
#let _pad3(i) = {
  let s = str(i)
  if s.len() == 1 { "00" + s }
  else if s.len() == 2 { "0" + s }
  else { s }
}

// Build a #grid of every ``level_NNN.png`` under ``dir`` for indices 0..n-1.
#let pool_grid(dir, n, cols: 5) = grid(
  columns: cols,
  gutter: 4pt,
  ..range(n).map(i => image(dir + "/level_" + _pad3(i) + ".png", width: 100%))
)

// Compact parameter table for a generator gallery pool.
#let gallery_params(p, profile: none) = {
  let size = p.params.size
  let grid_str = str(size.at(0)) + " × " + str(size.at(1))
  let rows = (
    ([Grid], grid_str),
    ([Agents], str(p.params.agents)),
    ([Lasers], str(p.params.lasers)),
    ([Horizon $T_("max")$], str(p.params.t_max)),
    ([Wall budget], str(p.params.num_walls)),
    ([Seed], str(p.seed)),
  )
  if profile != none {
    rows = rows + (([Profile filter], profile),)
  }
  rows = rows + (([Samples in pool], str(p.n_samples_generated)),)

  table(
    columns: 2,
    stroke: black,
    inset: 6pt,
    align: (left, left),
    ..rows.map(r => (r.at(0), r.at(1))).flatten(),
  )
}


#heading(numbering: none, level: 1)[Appendix]


== Benchmark Levels for SAT Encoding Comparison <appendix-benchmark-levels>

The four levels used in the SAT encoding comparison (@experiments) are shown below with their
exact parameters.

#figure(
  table(
    columns: 5,
    stroke: black,
    inset: 8pt,
    align: horizon,
    table.header([*Level*], [*Grid*], [*Agents*], [*Lasers*], [*Horizon $T_"max"$*]),
    [Synthetic 3×3],     [3×3],   [2], [1], [4],
    [Synthetic 5×5],     [5×5],   [3], [2], [5],
    [Synthetic 8×8],     [8×8],   [4], [3], [15],
    [Benchmark Level 6], [12×13], [4], [3], [21],
  ),
  caption: [Parameters of the four benchmark levels used in the SAT encoding comparison.],
)

#figure(
  grid(
    columns: 4,
    gutter: 8pt,
    align: center,
    [*3×3*], [*5×5*], [*8×8*], [*Level 6*],
    image("../../results/MLG-Student-Day/level_3x3_agents_2_lasers_1.png", width: 100%),
    image("../../results/MLG-Student-Day/level_5x5_agents_3_lasers_2.png", width: 100%),
    image("../../results/MLG-Student-Day/level_8x8_agents_4_lasers_3.png", width: 100%),
    image("../../results/MLG-Student-Day/level_lle_level6.png", width: 100%),
  ),
  caption: [Visual representation of the four benchmark levels.],
)


== Reproducibility — Software and Seed Conventions <appendix-reproducibility>

All experiments are reproducible from a single Python source tree. The relevant versions and
seed conventions are summarised below.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Component*], [*Version / Value*]),
    [Python],                          [3.12 or later (3.13 used for the runs reported here)],
    [SAT solver],                      [Minisat22 via the PySAT interface @Ignatiev2018],
    [LLE engine],                      [`laser-learning-environment` (Python + Rust bindings)],
    [MARL trainer],                    [`marl` framework, called from `src/experiments/learnability/run_experiment.py`],
    [Plotting backend],                [`matplotlib`],
    [Solver-comparison seeds],         [None (deterministic CNF; only timings vary across runs)],
    [Rejection-benchmark seeds],       [Per-generator RNG inside `run_rejection_benchmark.py`],
    [Profile-benchmark seeds],         [Per-generator RNG inside `run_profile_benchmark.py`],
    [Learnability training-pool seed], [20260618],
    [Learnability training seeds],     [$cal(S) = {0, 1, ..., 19}$ (twenty seeds per algorithm)],
    [Appendix-gallery pool seeds],     [Distinct per pool, listed in each gallery parameter table],
  ),
  caption: [
    Software components and seed conventions. Hardware specifications are deferred; the SAT
    benchmarks run on commodity laptops and the MARL runs on a CUDA workstation with sm_61
    GPUs.
  ],
)


== Learnability Hyperparameters <appendix-learnability-hyperparams>

The learnability experiment (@learnability-experiment) and the curriculum-transfer experiment
(@transfer-experiment) share the same trainer construction in
`src/experiments/learnability/run_experiment.py` and
`src/experiments/curriculum/run_experiment.py`. The hyperparameters listed in
@tab-learnability-hyperparams are identical across the three algorithms (IQL, VDN, QMIX) and
will be reused unchanged for the curriculum-transfer runs.

#figure(
  table(
    columns: 3,
    stroke: black,
    inset: 8pt,
    align: (horizon, center, left),
    table.header([*Hyperparameter*], [*Value*], [*Source*]),
    [Optimiser],                                  [Adam],                       [`marl.algos.{DQN,VDN,QMix}` default],
    [Learning rate],                              [$5 times 10^(-4)$],          [`run_experiment.py` (`lr=5e-4`)],
    [Batch size],                                 [64],                         [`run_experiment.py` (`batch_size=64`)],
    [Discount factor $gamma$],                    [0.95],                       [`run_experiment.py` (`gamma=0.95`)],
    [Train interval],                             [1 update / 5 env steps],     [`run_experiment.py` (`train_interval=(5,"step")`)],
    [Gradient-norm clipping],                     [10.0],                       [`run_experiment.py` (`grad_norm_clipping=10`)],
    [$epsilon$ schedule (train)],                 [linear $1.0 -> 0.05$ over 100,000 steps], [`EpsilonGreedy.linear(1.0, 0.05, 100_000)`],
    [Evaluation policy],                          [greedy ($epsilon = 0$)],     [`ArgMax()`],
    [Q-network architecture],                     [marl `qnetworks.from_env` default], [marl framework default],
    [Mixer (QMIX)],                               [`mixers.QMix.from_env`],     [`run_experiment.py`],
    [Mixer (VDN)],                                [sum of agent $Q$-values],    [`marl.algos.VDN` implicit mixer],
    [Mixer (IQL)],                                [none],                       [`run_experiment.py` (`mixer=None`)],
    [Independent $Q$-network heads (IQL, VDN)],   [yes],                        [`qnetworks.from_env(..., independent=True)`],
    [Independent $Q$-network heads (QMIX)],       [no (shared)],                [`qnetworks.from_env(...)` default],
  ),
  caption: [
    Hyperparameters used in the learnability experiment (@learnability-experiment) and to be
    reused for the curriculum-transfer experiment (@transfer-experiment) once its design is
    locked.
  ],
) <tab-learnability-hyperparams>


== SAT Encoding — Per-Family Clause Counts <appendix-sat-clauses>

The figures of @experiments report total CNF size for the four benchmark levels under the two
movement formulations. @tab-sat-clauses gives the per-constraint-family decomposition behind
those totals.

#figure(
  table(
    columns: 6,
    stroke: black,
    inset: 6pt,
    align: (left, center, right, right, right, right),
    table.header(
      [*Level*], [*Method*],
      [*Initialization*], [*Movement*], [*Laser*], [*Total*],
    ),
    [3×3],     [local],  [23],     [537],     [225],    [785],
    [3×3],     [global], [23],     [505],     [225],    [753],
    [5×5],     [local],  [87],     [4 233],   [1 884],  [6 204],
    [5×5],     [global], [87],     [6 243],   [1 884],  [8 214],
    [8×8],     [local],  [304],    [54 076],  [23 136], [77 516],
    [8×8],     [global], [304],    [143 296], [23 136], [166 736],
    [Level 6], [local],  [690],    [174 592], [77 682], [252 964],
    [Level 6], [global], [690],    [1 089 268], [77 682], [1 167 640],
  ),
  caption: [
    Clause counts per constraint family for the two SAT movement formulations on the four
    benchmark levels. Source: `results/MLG-Student-Day/benchmark_results.json`.
  ],
) <tab-sat-clauses>


== SAT Encoding — Generation and Solve Times <appendix-sat-times>

@tab-sat-times reports the mean CNF generation time and mean SAT solve time for each
(level, method) pair, averaged over the 100 timing runs of the benchmark protocol described
in @benchmarking. Standard deviations follow the mean in parentheses.

#figure(
  table(
    columns: 5,
    stroke: black,
    inset: 6pt,
    align: (left, center, right, right, right),
    table.header(
      [*Level*], [*Method*],
      [*Gen time (ms)*], [*Solve time (ms)*], [*Total (ms)*],
    ),
    [3×3],     [local],  [$0.19 plus.minus 0.07$],   [$0.013 plus.minus 0.004$], [$0.20$],
    [3×3],     [global], [$0.20 plus.minus 0.07$],   [$0.013 plus.minus 0.004$], [$0.21$],
    [5×5],     [local],  [$2.0 plus.minus 2.8$],     [$0.08 plus.minus 0.02$],   [$2.1$],
    [5×5],     [global], [$2.7 plus.minus 2.5$],     [$0.21 plus.minus 0.05$],   [$2.9$],
    [8×8],     [local],  [$28 plus.minus 11$],       [$4.8 plus.minus 0.6$],     [$33$],
    [8×8],     [global], [$58 plus.minus 11$],       [$13 plus.minus 2$],        [$70$],
    [Level 6], [local],  [$104 plus.minus 50$],      [$11 plus.minus 1$],        [$115$],
    [Level 6], [global], [$418 plus.minus 36$],      [$13 plus.minus 2$],        [$431$],
  ),
  caption: [
    Mean CNF generation, SAT solve, and total times (milliseconds) per level and movement
    formulation, averaged over 100 timing runs. Source:
    `results/MLG-Student-Day/benchmark_results.json`.
  ],
) <tab-sat-times>


== Generator Rejection — Detailed Numbers <appendix-rejection-detail>

The figures of @generator-rejection-rates report per-generator rejection rates and mean
attempts. @tab-rejection-detail gives the full numbers behind those plots, including the
number of successful trials, the number of failed trials (per-trial budget exhausted), and the
mean number of attempts per accepted level.

#figure(
  table(
    columns: 6,
    stroke: black,
    inset: 6pt,
    align: (left, center, right, right, right, right),
    table.header(
      [*Generator*], [*Grid*],
      [*Success*], [*Fail*], [*Mean attempts*], [*Rejection (%)*],
    ),
    [Constrained Random (solvable)],   [3×3], [200], [0],  [3.5],   [71.2],
    [Constrained Random (solvable)],   [5×5], [200], [0],  [7.6],   [86.8],
    [Constrained Random (solvable)],   [8×8], [19],  [1],  [6.2],   [83.9],
    [Constrained Random (cooperative)],[3×3], [200], [0],  [79.5],  [98.7],
    [Constrained Random (cooperative)],[5×5], [200], [0],  [68.8],  [98.5],
    [Constrained Random (cooperative)],[8×8], [—],   [20], [—],     [—],
    [Constructive (solvable)],         [3×3], [200], [0],  [1.00],  [0.0],
    [Constructive (solvable)],         [5×5], [200], [0],  [1.10],  [9.5],
    [Constructive (solvable)],         [8×8], [20],  [0],  [1.05],  [4.8],
    [Constructive (cooperative)],      [3×3], [200], [0],  [1.00],  [0.0],
    [Constructive (cooperative)],      [5×5], [200], [0],  [1.06],  [6.1],
    [Constructive (cooperative)],      [8×8], [20],  [0],  [1.05],  [4.8],
    [Level-6-Style],                   [3×3], [200], [0],  [78.3],  [98.7],
    [Level-6-Style],                   [5×5], [200], [0],  [5.3],   [81.1],
    [Level-6-Style],                   [8×8], [20],  [0],  [4.2],   [76.2],
  ),
  caption: [
    Detailed rejection-benchmark numbers per generator setting and grid size. "Success" is
    the number of successful trials and "Fail" the number of trials that exhausted their
    per-trial budget (500 attempts for the small grids; 100 attempts or 30 seconds for the
    $8 times 8$ grid). The $8 times 8$ Constrained Random cooperative row is missing because
    the LLE C extension crashed during the benchmark on a randomly-sampled world. Source:
    `results/rejection_benchmark/benchmark_results.json`.
  ],
) <tab-rejection-detail>


== Cooperation Profile Distribution — Detailed Counts <appendix-profile-detail>

The figure of @profile-distribution shows the cooperation-profile breakdown of accepted
cooperative levels for three generator settings and two grid sizes. @tab-profile-detail gives
the raw counts.

#figure(
  table(
    columns: 8,
    stroke: black,
    inset: 6pt,
    align: (left, center, right, right, right, right, right, right),
    table.header(
      [*Generator*], [*Grid*],
      [*$n$*], [*asym.*], [*mutual*], [*chain*], [*distr.*], [*full*],
    ),
    [Constrained Random (cooperative)], [5×5], [100], [100], [0],  [0], [0], [0],
    [Constrained Random (cooperative)], [8×8], [50],  [46],  [0],  [1], [3], [0],
    [Constructive (cooperative)],       [5×5], [100], [100], [0],  [0], [0], [0],
    [Constructive (cooperative)],       [8×8], [50],  [2],   [46], [0], [2], [0],
    [Level-6-Style],                    [5×5], [100], [100], [0],  [0], [0], [0],
    [Level-6-Style],                    [8×8], [50],  [13],  [34], [0], [3], [0],
  ),
  caption: [
    Raw profile-count breakdown per generator and grid size. The columns *asym.*, *mutual*,
    *chain*, *distr.*, *full* correspond to the five cooperation-profile labels classified by
    the analyzer of @cooperation-profiles. The 5×5 configuration uses 2 agents and 1 laser;
    the 8×8 configuration uses 3 agents and 2 lasers. Source:
    `results/profile_benchmark/benchmark_results.json`.
  ],
) <tab-profile-detail>


== Learnability — Per-Seed Final Success Rates <appendix-learnability-detail>

@tab-learnability-perseed lists the final greedy success rate of every (algorithm, seed) cell
in the learnability experiment of @learnability-experiment. Each row is one trained agent;
"Train" is the success rate on the 20-level training pool and "Test" the success rate on the
20-level held-out pool, each estimated from 200 greedy evaluation episodes.

#let _runs = json("../../results/learnability_5x5/aggregated.json")

#figure(
  table(
    columns: 4,
    stroke: black,
    inset: 4pt,
    align: (left, center, center, center),
    table.header([*Algorithm*], [*Seed*], [*Train*], [*Test*]),
    ..(_runs.map(r => (
      r.algorithm,
      str(r.seed),
      str(calc.round(r.train_success, digits: 2)),
      str(calc.round(r.test_success, digits: 2)),
    )).flatten()),
  ),
  caption: [
    Per-(algorithm, seed) final greedy success rates from the learnability experiment of
    @learnability-experiment. 60 rows total (3 algorithms × 20 seeds). Source:
    `results/learnability_5x5/aggregated.json`, produced by
    `src/scripts/aggregate_learnability_results.py`.
  ],
) <tab-learnability-perseed>


== Learnability — Training Pool <appendix-learnability-train>

Cooperative pool used as $cal(D)_("train")$ for @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/learnability_5x5/levels/5x5_2a_1L_cooperative/train`],
    [Grid],               [5 × 5],
    [Agents],             [2],
    [Lasers],             [1],
    [$T_("max")$],        [10],
    [Generator],          [Constructive (cooperative mode)],
    [Pool seed],          [20260618],
    [Number of levels],   [20],
  ),
  caption: [Parameters of the learnability training pool.],
)

#figure(
  pool_grid("../../results/learnability_5x5/levels/5x5_2a_1L_cooperative/train/images", 20),
  caption: [All 20 levels of the learnability training pool, in pool order.],
) <fig-pool-learnability-train>


== Learnability — Test Pool <appendix-learnability-test>

Held-out cooperative pool used as $cal(D)_("test")$ for @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/learnability_5x5/levels/5x5_2a_1L_cooperative/test`],
    [Grid],               [5 × 5],
    [Agents],             [2],
    [Lasers],             [1],
    [$T_("max")$],        [10],
    [Generator],          [Constructive (cooperative mode)],
    [Pool seed],          [20260618],
    [Number of levels],   [20],
  ),
  caption: [Parameters of the learnability test pool.],
)

#figure(
  pool_grid("../../results/learnability_5x5/levels/5x5_2a_1L_cooperative/test/images", 20),
  caption: [All 20 levels of the learnability test pool, in pool order.],
) <fig-pool-learnability-test>


== Generator Gallery — Random Generator <appendix-gallery-random>

Uniformly-sampled levels with no geometric pre-filter. The generator only rejects candidates
that fail the SAT solvability check, so the gallery shows what unbiased random sampling
produces inside the accepted set. Pools are generated by
`src/scripts/generate_appendix_galleries.py`.

=== Random — 3×3, 2 agents, 1 laser

#let _g01 = json("../../results/appendix_galleries/01_random_3x3_2a_1L/params.json")
#figure(gallery_params(_g01), caption: [Parameters and seed for the Random 3×3 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/01_random_3x3_2a_1L/images", 16, cols: 4),
  caption: [16 Random 3×3 (2 agents, 1 laser) levels.],
)

=== Random — 5×5, 3 agents, 2 lasers

#let _g02 = json("../../results/appendix_galleries/02_random_5x5_3a_2L/params.json")
#figure(gallery_params(_g02), caption: [Parameters and seed for the Random 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/02_random_5x5_3a_2L/images", 16, cols: 4),
  caption: [16 Random 5×5 (3 agents, 2 lasers) levels.],
)

=== Random — 7×7, 4 agents, 2 lasers

#let _g03 = json("../../results/appendix_galleries/03_random_7x7_4a_2L/params.json")
#figure(gallery_params(_g03), caption: [Parameters and seed for the Random 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/03_random_7x7_4a_2L/images", 16, cols: 4),
  caption: [16 Random 7×7 (4 agents, 2 lasers) levels.],
)


== Generator Gallery — Constrained Random Generator <appendix-gallery-constrained-random>

Random sampling plus geometric filters (no laser pointing immediately out of bounds, no
zero-length beam, no exit on an unavoidable beam segment, etc.). Same parameter sweep as the
Random gallery above for direct comparison.

=== Constrained Random — 3×3, 2 agents, 1 laser

#let _g04 = json("../../results/appendix_galleries/04_constrained_random_3x3_2a_1L/params.json")
#figure(gallery_params(_g04), caption: [Parameters and seed for the Constrained Random 3×3 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/04_constrained_random_3x3_2a_1L/images", 16, cols: 4),
  caption: [16 Constrained Random 3×3 (2 agents, 1 laser) levels.],
)

=== Constrained Random — 5×5, 3 agents, 2 lasers

#let _g05 = json("../../results/appendix_galleries/05_constrained_random_5x5_3a_2L/params.json")
#figure(gallery_params(_g05), caption: [Parameters and seed for the Constrained Random 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/05_constrained_random_5x5_3a_2L/images", 16, cols: 4),
  caption: [16 Constrained Random 5×5 (3 agents, 2 lasers) levels.],
)

=== Constrained Random — 7×7, 4 agents, 2 lasers

#let _g06 = json("../../results/appendix_galleries/06_constrained_random_7x7_4a_2L/params.json")
#figure(gallery_params(_g06), caption: [Parameters and seed for the Constrained Random 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/06_constrained_random_7x7_4a_2L/images", 16, cols: 4),
  caption: [16 Constrained Random 7×7 (4 agents, 2 lasers) levels.],
)


== Generator Gallery — Constructive Generator (Solvable) <appendix-gallery-constructive-solvable>

Lane-based construction (one disjoint lane per agent) followed by random wall placement on
the remaining cells. Cooperation is not required at generation time; only solvability is
certified by the SAT oracle.

=== Constructive Solvable — 5×5, 3 agents, 1 laser

#let _g07 = json("../../results/appendix_galleries/07_constructive_5x5_3a_1L/params.json")
#figure(gallery_params(_g07), caption: [Parameters and seed for the Constructive Solvable 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/07_constructive_5x5_3a_1L/images", 16, cols: 4),
  caption: [16 Constructive Solvable 5×5 (3 agents, 1 laser) levels.],
)

=== Constructive Solvable — 7×7, 4 agents, 2 lasers

#let _g08 = json("../../results/appendix_galleries/08_constructive_7x7_4a_2L/params.json")
#figure(gallery_params(_g08), caption: [Parameters and seed for the Constructive Solvable 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/08_constructive_7x7_4a_2L/images", 16, cols: 4),
  caption: [16 Constructive Solvable 7×7 (4 agents, 2 lasers) levels.],
)

=== Constructive Solvable — 9×9, 4 agents, 3 lasers

#let _g09 = json("../../results/appendix_galleries/09_constructive_9x9_4a_3L/params.json")
#figure(gallery_params(_g09), caption: [Parameters and seed for the Constructive Solvable 9×9 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/09_constructive_9x9_4a_3L/images", 16, cols: 4),
  caption: [16 Constructive Solvable 9×9 (4 agents, 3 lasers) levels.],
)


== Generator Gallery — Constructive Generator (Cooperative) <appendix-gallery-constructive-cooperative>

Lane-based construction with planted same-colour structural lasers, certified to satisfy the
binary cooperation criterion of #fref(<thm-5-1>, [Theorem 5.1]). No profile filter is applied;
the gallery shows what the generator produces when any cooperation profile is admissible.

=== Constructive Cooperative — 5×5, 2 agents, 1 laser

#let _g10 = json("../../results/appendix_galleries/10_cooperative_5x5_2a_1L/params.json")
#figure(gallery_params(_g10, profile: "cooperative"), caption: [Parameters and seed for the Constructive Cooperative 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/10_cooperative_5x5_2a_1L/images", 16, cols: 4),
  caption: [16 Constructive Cooperative 5×5 (2 agents, 1 laser) levels.],
)

=== Constructive Cooperative — 7×7, 3 agents, 2 lasers

#let _g11 = json("../../results/appendix_galleries/11_cooperative_7x7_3a_2L/params.json")
#figure(gallery_params(_g11, profile: "cooperative"), caption: [Parameters and seed for the Constructive Cooperative 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/11_cooperative_7x7_3a_2L/images", 16, cols: 4),
  caption: [16 Constructive Cooperative 7×7 (3 agents, 2 lasers) levels.],
)

=== Constructive Cooperative — 9×9, 4 agents, 3 lasers

#let _g12 = json("../../results/appendix_galleries/12_cooperative_9x9_4a_3L/params.json")
#figure(gallery_params(_g12, profile: "cooperative"), caption: [Parameters and seed for the Constructive Cooperative 9×9 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/12_cooperative_9x9_4a_3L/images", 16, cols: 4),
  caption: [16 Constructive Cooperative 9×9 (4 agents, 3 lasers) levels.],
)


== Generator Gallery — Constructive Cooperative with Profile Filter <appendix-gallery-constructive-profile>

Same Constructive Cooperative generator as the previous section, but with an explicit profile
filter so accepted levels match a single label (e.g. *mutual* or *distributed*).

=== Constructive Cooperative — 8×8, 3 agents, 2 lasers, profile = `mutual`

#let _g13 = json("../../results/appendix_galleries/13_cooperative_mutual_8x8_3a_2L/params.json")
#figure(gallery_params(_g13, profile: "mutual"), caption: [Parameters and seed for the profile-filtered (mutual) 8×8 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/13_cooperative_mutual_8x8_3a_2L/images", 16, cols: 4),
  caption: [16 profile-filtered (mutual) 8×8 (3 agents, 2 lasers) levels.],
)

=== Constructive Cooperative — 10×10, 4 agents, 3 lasers, profile = `distributed`

#let _g14 = json("../../results/appendix_galleries/14_cooperative_distributed_10x10_4a_3L/params.json")
#figure(gallery_params(_g14, profile: "distributed"), caption: [Parameters and seed for the profile-filtered (distributed) 10×10 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/14_cooperative_distributed_10x10_4a_3L/images", 16, cols: 4),
  caption: [16 profile-filtered (distributed) 10×10 (4 agents, 3 lasers) levels.],
)


== Generator Gallery — Level-6-Style Generator <appendix-gallery-level6>

Clustered starts and exits on opposing sides of the grid with a corridor of lasers in between,
inspired by the hand-crafted LLE Level 6.

=== Level-6-Style — 8×8, 4 agents, 2 lasers

#let _g15 = json("../../results/appendix_galleries/15_level6_style_8x8_4a_2L/params.json")
#figure(gallery_params(_g15), caption: [Parameters and seed for the Level-6-Style 8×8 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/15_level6_style_8x8_4a_2L/images", 16, cols: 4),
  caption: [16 Level-6-Style 8×8 (4 agents, 2 lasers) levels.],
)

=== Level-6-Style — 10×10, 4 agents, 3 lasers

#let _g16 = json("../../results/appendix_galleries/16_level6_style_10x10_4a_3L/params.json")
#figure(gallery_params(_g16), caption: [Parameters and seed for the Level-6-Style 10×10 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/16_level6_style_10x10_4a_3L/images", 16, cols: 4),
  caption: [16 Level-6-Style 10×10 (4 agents, 3 lasers) levels.],
)

=== Level-6-Style — 12×13, 4 agents, 3 lasers (Level 6 footprint)

#let _g17 = json("../../results/appendix_galleries/17_level6_style_12x13_4a_3L/params.json")
#figure(gallery_params(_g17), caption: [Parameters and seed for the Level-6-Style 12×13 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/17_level6_style_12x13_4a_3L/images", 16, cols: 4),
  caption: [16 Level-6-Style 12×13 (4 agents, 3 lasers) levels — same footprint as the hand-crafted LLE Level 6.],
)
