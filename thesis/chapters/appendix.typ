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
    stroke: none,
    inset: 6pt,
    align: (left, left),
    table.hline(stroke: 1pt),
    ..rows.map(r => (r.at(0), r.at(1))).flatten(),
    table.hline(stroke: 1pt),
  )
}

= Reproducibility and experiment configurations

== Benchmark levels for SAT encoding comparison <appendix-benchmark-levels>

The four levels used in the SAT encoding comparison (@experiments) are shown below with their
exact parameters.

#figure(
  table(
    columns: 5,
    stroke: none,
    inset: 8pt,
    align: horizon,
    table.hline(stroke: 1pt),
    table.header([*Level*], [*Grid*], [*Agents*], [*Lasers*], [*Horizon $T_"max"$*]),
    table.hline(stroke: 0.5pt),
    [Synthetic 3×3],     [3×3],   [2], [1], [4],
    [Synthetic 5×5],     [5×5],   [3], [2], [5],
    [Synthetic 8×8],     [8×8],   [4], [3], [15],
    [Benchmark Level 6], [12×13], [4], [3], [21],
    table.hline(stroke: 1pt),
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


== Reproducibility: software and seed conventions <appendix-reproducibility>

All experiments are reproducible from a single Python source tree. The relevant versions and
seed conventions are summarised below.

#figure(
  table(
    columns: 2,
    stroke: none,
    inset: 8pt,
    align: (left, left),
    table.hline(stroke: 1pt),
    table.header([*Component*], [*Version / Value*]),
    table.hline(stroke: 0.5pt),
    [Python],                          [3.12 or later (3.13 used for the runs reported here)],
    [SAT solver],                      [Minisat22 via the PySAT interface @Ignatiev2018],
    [LLE engine],                      [`laser-learning-environment` (Python + Rust bindings)],
    [MARL trainer],                    [`marl` framework, called from `src/experiments/learnability/run_experiment.py`],
    [Plotting backend],                [`matplotlib`],
    [Solver-comparison seeds],         [None (deterministic CNF; only timings vary across runs)],
    [Rejection benchmark],             [Seeded (`seed=20260530`, env `REJECTION_SEED`); 200 trials ($3 times 3$, $5 times 5$) or 20 trials ($8 times 8$); per-trial attempt distributions shown as boxplots],
    [Profile benchmark],               [Unseeded (`seed=None`); reported as counts over 100 ($5 times 5$) or 50 ($8 times 8$) accepted levels],
    [Learnability training-pool seed], [20260618],
    [Learnability training seeds],     [$cal(S) = {0, 1, ..., 19}$ (twenty seeds per algorithm)],
    [Data-scaling pool seeds],         [20260618 (train), 20260619 (test); pools nested, test size 50],
    [Data-scaling training seeds],     [$cal(S) = {0, 1, ..., 19}$ per algorithm and pool size],
    [Curriculum-strategy seeds],       [$cal(S) = {0, 1, ..., 7}$ (eight seeds per condition and algorithm)],
    [Curriculum two-laser / Level-6 seeds], [Small per-condition sets ($1$–$6$ seeds); see @appendix-transfer-detail],
    [Appendix-gallery pool seeds],     [Distinct per pool, listed in each gallery parameter table],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Software components and seed conventions. Hardware specifications are deferred; the SAT
    benchmarks run on commodity laptops and the MARL runs on a CUDA workstation with sm_61
    GPUs.
  ],
)


== Learnability hyperparameters <appendix-learnability-hyperparams>

The learnability experiment (@learnability-experiment), the data-scaling experiment
(@data-scaling-experiment), and the curriculum experiments (@curriculum-strategy-experiment,
@transfer-experiment) share the same trainer construction in
`src/experiments/learnability/run_experiment.py` and the curriculum runners under
`src/experiments/`. The hyperparameters listed in @tab-learnability-hyperparams are identical
across the three algorithms (IQL, VDN, QMIX) and are reused unchanged for the data-scaling and
curriculum runs; the only addition is the per-stage exploration reset used by the curriculum runs,
described in @curriculum-strategy-experiment.

#figure(
  table(
    columns: (auto, auto, 1fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    align: (horizon, center, left),
    table.hline(stroke: 1pt),
    table.header([*Hyperparameter*], [*Value*], [*Source*]),
    table.hline(stroke: 0.5pt),
    [Optimiser],                    [Adam],                            [`marl.algos` default],
    [Learning rate],                [$5 times 10^(-4)$],               [`lr=5e-4`],
    [Batch size],                   [64],                              [`batch_size=64`],
    [Discount factor $gamma$],      [0.95],                            [`gamma=0.95`],
    [Train interval],               [1 update / 5 env steps],          [`train_interval=(5,"step")`],
    [Gradient-norm clipping],       [10.0],                            [`grad_norm_clipping=10`],
    [$epsilon$ schedule (train)],   [linear $1.0 -> 0.05$, 100k steps], [`EpsilonGreedy.linear(1.0, 0.05, 100_000)`],
    [Evaluation policy],            [greedy ($epsilon = 0$)],          [`ArgMax()`],
    [Q-network architecture],       [`qnetworks.from_env` default],    [marl framework],
    [Mixer (QMIX)],                 [`mixers.QMix.from_env`],          [marl framework],
    [Mixer (VDN)],                  [sum of agent $Q$-values],         [`marl.algos.VDN`],
    [Mixer (IQL)],                  [none],                            [`mixer=None`],
    [Independent heads (IQL, VDN)], [yes],                             [`independent=True`],
    [Independent heads (QMIX)],     [no (shared)],                     [`qnetworks.from_env`],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Hyperparameters used in the learnability experiment (@learnability-experiment) and reused
    unchanged for the data-scaling (@data-scaling-experiment) and curriculum
    (@curriculum-strategy-experiment, @transfer-experiment) experiments. Source values without a
    module prefix are keyword arguments to `run_experiment.py`.
  ],
) <tab-learnability-hyperparams>


== Data-scaling experiment: configuration <appendix-data-scaling>

The data-scaling experiment (@data-scaling-experiment) reuses the learnability task, generator,
and hyperparameters (@appendix-learnability-hyperparams) unchanged, and varies only the
training-pool size. @tab-data-scaling-config lists the full configuration.

#figure(
  table(
    columns: 2,
    stroke: none,
    inset: 8pt,
    align: (left, left),
    table.hline(stroke: 1pt),
    table.header([*Field*], [*Value*]),
    table.hline(stroke: 0.5pt),
    [Grid / agents / lasers],                       [5 × 5 / 2 / 1],
    [Horizon $T_("max")$],                          [10],
    [Generator],                                    [Constructive (cooperative mode)],
    [Training-pool sizes $|cal(D)_("train")|$],     [20, 100, 500 (nested)],
    [Held-out test-pool size $|cal(D)_("test")|$],  [50 (fixed across all conditions)],
    [Training-pool seed],                           [20260618],
    [Test-pool seed],                               [20260619],
    [Environment steps per run],                    [300,000],
    [Algorithms],                                   [IQL, VDN, QMIX],
    [Training seeds],                               [$cal(S) = {0, 1, ..., 19}$],
    [Runs per pool size],                           [60 (3 algorithms × 20 seeds)],
    table.hline(stroke: 1pt),
  ),
  caption: [Configuration of the data-scaling experiment (@data-scaling-experiment).],
) <tab-data-scaling-config>

The three training pools are nested prefixes of a single seeded stream (seed 20260618): the
20-level pool is exactly the learnability training pool of @appendix-learnability-train, the
100-level pool contains it, and the 500-level pool contains both. The 50-level held-out test
pool (seed 20260619) is a superset of the 20-level learnability test pool of
@appendix-learnability-test. Per-level renderings of the 20-level pool therefore already appear
in @fig-pool-learnability-train and @fig-pool-learnability-test; the additional levels in the
100- and 500-level pools are further independent draws from the same constructive cooperative
generator, representative samples of which are shown in
@appendix-gallery-constructive-cooperative. They are not reproduced individually here.

The per-pool-size learning curves below mirror @fig-learnability-curves: each panel pair shows the
train- and test-pool success rate against environment steps for IQL, VDN, and QMIX, with $95%$
confidence bands over the seeds. Read together, they make the effect of @data-scaling-experiment
visible step by step: as the training pool grows from 20 to 100 to 500 levels, the test curves
(right panel of each figure) climb toward the training curves (left panel), i.e. the
generalisation gap closes.

#figure(
  image("../../results/datascale_5x5_2a_1L_n20/figures/learning_curves.pdf", width: 100%),
  caption: [
    Data scaling with $|cal(D)_("train")| = 20$ levels: mean train- and test-pool success rate
    versus environment steps, per algorithm, with $95%$ confidence bands over the seeds. The
    test curves plateau far below the training curves (large gap).
  ],
) <fig-datascale-curves-20>

#figure(
  image("../../results/datascale_5x5_2a_1L_n100/figures/learning_curves.pdf", width: 100%),
  caption: [
    Data scaling with $|cal(D)_("train")| = 100$ levels: the training curves drop and the test
    curves rise relative to the 20-level case, narrowing the gap.
  ],
) <fig-datascale-curves-100>

#figure(
  image("../../results/datascale_5x5_2a_1L_n500/figures/learning_curves.pdf", width: 100%),
  caption: [
    Data scaling with $|cal(D)_("train")| = 500$ levels: the train and test curves nearly coincide,
    and the agent generalises to held-out levels about as well as it fits the training pool.
  ],
) <fig-datascale-curves-500>


== Curriculum-strategy experiment: configuration and per-cell results <appendix-curriculum-strategy-detail>

The curriculum-strategy experiment (@curriculum-strategy-experiment) compares four budget-matched
scheduling conditions on a $6 times 6$ / 2-agent / 1-laser cooperative target reachable by the
direct baseline. @tab-curriculum-strategy-config gives the full configuration and
@tab-curriculum-strategy-perchart the per-(condition, algorithm) final success rates behind the
pooled summary of @tab-curriculum-strategy.

#figure(
  table(
    columns: 2,
    stroke: none,
    inset: 8pt,
    align: (left, left),
    table.hline(stroke: 1pt),
    table.header([*Field*], [*Value*]),
    table.hline(stroke: 0.5pt),
    [Difficulty ladder],          [$4 times 4$/0L (random, $T_("max")=8$) $arrow.r$ $5 times 5$/1L (cooperative, $T_("max")=10$) $arrow.r$ $6 times 6$/1L target (cooperative, $T_("max")=12$)],
    [Agents],                     [2 (fixed across stages; smaller observations zero-padded)],
    [Train pool per stage],        [100 certified levels],
    [Held-out target pool],       [50 levels],
    [Conditions],                 [direct, forward $(50,150,200) times 10^3$, reverse (same per-stage budgets, reversed), mixed (uniform stage per episode)],
    [Total budget per run],       [400,000 environment steps],
    [Algorithms],                 [IQL, VDN, QMIX],
    [Seeds],                      [$cal(S) = {0, 1, ..., 7}$ (eight per condition and algorithm)],
    [Exploration],                [$epsilon$ reset to $1.0$ at each stage boundary, decayed to $0.05$ over $30%$ of that stage's budget],
    [Evaluation],                 [greedy, on the $6 times 6$ target; 50 episodes every 10,000 steps and 200 episodes at the end],
    table.hline(stroke: 1pt),
  ),
  caption: [Configuration of the curriculum-strategy experiment (@curriculum-strategy-experiment).],
) <tab-curriculum-strategy-config>

#figure(
  table(
    columns: 5,
    stroke: none,
    inset: 6pt,
    align: (left, center, center, center, center),
    table.hline(stroke: 1pt),
    table.header(
      [*Condition*], [*Algorithm*], [*$n$*],
      [*Train mean $plus.minus$ CI95*], [*Test mean $plus.minus$ CI95*],
    ),
    table.hline(stroke: 0.5pt),
    [direct],  [IQL],  [8], [$0.30 plus.minus 0.06$], [$0.13 plus.minus 0.03$],
    [direct],  [VDN],  [8], [$0.43 plus.minus 0.08$], [$0.16 plus.minus 0.04$],
    [direct],  [QMIX], [8], [$0.50 plus.minus 0.05$], [$0.22 plus.minus 0.05$],
    [forward], [IQL],  [8], [$0.22 plus.minus 0.04$], [$0.08 plus.minus 0.03$],
    [forward], [VDN],  [8], [$0.49 plus.minus 0.06$], [$0.17 plus.minus 0.06$],
    [forward], [QMIX], [8], [$0.47 plus.minus 0.07$], [$0.20 plus.minus 0.06$],
    [mixed],   [IQL],  [8], [$0.19 plus.minus 0.06$], [$0.12 plus.minus 0.05$],
    [mixed],   [VDN],  [8], [$0.51 plus.minus 0.08$], [$0.29 plus.minus 0.08$],
    [mixed],   [QMIX], [8], [$0.47 plus.minus 0.08$], [$0.27 plus.minus 0.05$],
    [reverse], [IQL],  [8], [$0.06 plus.minus 0.03$], [$0.03 plus.minus 0.02$],
    [reverse], [VDN],  [8], [$0.12 plus.minus 0.04$], [$0.09 plus.minus 0.04$],
    [reverse], [QMIX], [8], [$0.12 plus.minus 0.04$], [$0.09 plus.minus 0.06$],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Final greedy success rate per (condition, algorithm) on the $6 times 6$ / 2-agent / 1-laser
    target, each aggregated over eight seeds. Means with $95%$ confidence intervals
    ($plus.minus t_(7,0.025) sigma / sqrt(8)$, $t_(7,0.025) approx 2.365$). Source:
    `results/curriculum_strategy/runs/`.
  ],
) <tab-curriculum-strategy-perchart>

=== Generated training pools

Each stage is SAT-generated once from the master seed `RNG_SEED = 20260521`; the per-stage training
pool uses the derived seed $20260521 + 100 times "stage"$ and the held-out target pool the same
expression $+ 1$, so every draw is reproducible and the target's train and eval pools never
coincide. Unspecified wall budgets fall back to the generator default $floor("grid area" \/ 10)$.
@tab-cs-pools lists the per-stage parameters; @fig-cs-pool-s1, @fig-cs-pool-s2, and
@fig-cs-pool-s3 show sixteen representative training levels from each stage.

#figure(
  table(
    columns: 9,
    stroke: none,
    inset: (x: 5pt, y: 4pt),
    align: horizon,
    table.hline(stroke: 1pt),
    table.header(
      [*Stage*], [*Grid*], [*Agents*], [*Lasers*], [*$T_("max")$*], [*Walls*],
      [*Generator*], [*Train*], [*Eval*],
    ),
    table.hline(stroke: 0.5pt),
    [S1], [4×4], [2], [0], [8],  [1], [Random (solv.)],       [100], [0],
    [S2], [5×5], [2], [1], [10], [2], [Constructive (coop.)], [100], [0],
    [S3], [6×6], [2], [1], [12], [3], [Constructive (coop.)], [100], [50],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Per-stage generation parameters for the curriculum-strategy pools
    (@curriculum-strategy-experiment). Source: `src/experiments/curriculum_strategy/configs.py`;
    pools rendered by `src/scripts/render_curriculum_strategy_pools.py`.
  ],
) <tab-cs-pools>

#figure(
  pool_grid("../../results/curriculum_strategy/levels/stage_1_4x4_2a_0L_random/train/images", 16, cols: 4),
  caption: [Sixteen S1 training levels: $4 times 4$, 2 agents, 0 lasers (navigation warm-up).],
) <fig-cs-pool-s1>

#figure(
  pool_grid("../../results/curriculum_strategy/levels/stage_2_5x5_2a_1L_cooperative/train/images", 16, cols: 4),
  caption: [Sixteen S2 training levels: $5 times 5$, 2 agents, 1 laser (asymmetric cooperation).],
) <fig-cs-pool-s2>

#figure(
  pool_grid("../../results/curriculum_strategy/levels/stage_3_6x6_2a_1L_cooperative/train/images", 16, cols: 4),
  caption: [Sixteen S3 (target) training levels: $6 times 6$, 2 agents, 1 laser (asymmetric cooperation).],
) <fig-cs-pool-s3>


== Curriculum-transfer experiments: configurations and results <appendix-transfer-detail>

This appendix collects the configurations and per-run results behind the three stages of
@transfer-experiment: the frontier probe, the two-laser curriculum, and the Level-6 transfer.
Across all three, held-out success on the mutually-cooperative target is uniformly zero; the
tables below give the supporting numbers and the exact stage geometries.

=== Frontier probe and diagnostic checks

Direct training from scratch on a fixed $6 times 6$ / 2-agent / 2-laser *mutual* target
($T_("max") = 18$, constructive cooperative generator constrained to the `fully_coupled` profile,
a 20-level training pool and a 20-level held-out pool), 600,000 steps, three seeds per algorithm.
The profile filter is `fully_coupled` rather than `mutual` because, for two agents, the reciprocal
mutual-cooperation pattern is a strongly connected component spanning the whole agent set and is
therefore labelled `fully_coupled` (@sec-ordering-structure); the `mutual` label is reachable only
from three agents upward.
@tab-frontier-probe reports the final greedy success rates: every algorithm reaches a small
nonzero *training* success and exactly zero *held-out* success. Sixteen of the training levels are
shown in @fig-frontier-pool.

#figure(
  table(
    columns: 4,
    stroke: none,
    inset: 6pt,
    align: (left, center, center, center),
    table.hline(stroke: 1pt),
    table.header([*Algorithm*], [*$n$*], [*Train (mean)*], [*Test (mean)*]),
    table.hline(stroke: 0.5pt),
    [IQL],  [3], [$0.09$], [$0.00$],
    [VDN],  [3], [$0.06$], [$0.00$],
    [QMIX], [3], [$0.08$], [$0.00$],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Frontier probe: final greedy success on the $6 times 6$ / 2-agent / 2-laser mutual target,
    direct training from scratch. Source: `results/learnability_6x6_2L/runs/`.
  ],
) <tab-frontier-probe>

#figure(
  pool_grid("../../results/learnability_6x6_2L/levels_png/train", 16, cols: 4),
  caption: [
    Sixteen of the twenty frontier-probe training levels: $6 times 6$, 2 agents, 2 lasers,
    `fully_coupled` cooperation profile. Source:
    `results/learnability_6x6_2L/levels_png/train`.
  ],
) <fig-frontier-pool>

Two diagnostic checks rule out a budget shortfall rather than a learnability wall. An *overfit
gate* trains a single algorithm (QMIX) on one fixed mutual level for 600,000 steps (removing the
need to generalise entirely) and still plateaus below $0.12$ training success with zero held-out
success. A *budget-bump gate* extends the budget to $1{,}500{,}000$ steps (VDN, 100-level pool):
success stays flat, peaking early (around $0.10$) and then decaying to zero rather than climbing.
Finally, shrinking the grid to $5 times 5$ / 2-laser (VDN, 200,000 steps) yields $0.00$ on both
train and test pools: two lasers drive success to zero independently of grid size.

=== Two-laser curriculum

The four scheduling conditions of @curriculum-strategy-experiment, on a fixed $6 times 6$ grid
with a zero-, one-, then two-laser ladder to the mutual two-laser target, budget-matched at
600,000 steps. Owing to the cost of the runs and the uniformly zero outcome, coverage is partial:
*direct* was run with VDN (six seeds) and QMIX (three seeds); *forward*, *reverse*, and *mixed*
with VDN (three seeds each). @tab-2laser-curriculum reports the final held-out success.

#figure(
  table(
    columns: 4,
    stroke: none,
    inset: 6pt,
    align: (left, left, center, center),
    table.hline(stroke: 1pt),
    table.header([*Condition*], [*Algorithms (seeds)*], [*Held-out test (mean)*], [*Train (mean)*]),
    table.hline(stroke: 0.5pt),
    [direct],  [VDN (6), QMIX (3)], [$0.00$], [$0.08$],
    [forward], [VDN (3)],           [$0.00$], [$0.05$],
    [mixed],   [VDN (3)],           [$0.01$], [$0.01$],
    [reverse], [VDN (3)],           [$0.00$], [$0.00$],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Two-laser curriculum: final greedy success on the $6 times 6$ / 2-agent / 2-laser mutual
    target per scheduling condition. Source: `results/curriculum_strategy_2L/runs/`.
  ],
) <tab-2laser-curriculum>

The fixed-grid ladder is SAT-generated once from `RNG_SEED = 20260523` (per-stage seed
$20260523 + 100 times "stage"$, $+ 1$ for the held-out target pool). Only the two-laser target
stage (S3) is constrained to the `fully_coupled` cooperation profile; the lower stages accept any
solvable (S1) or cooperative (S2) level. @tab-cs2l-pools lists the per-stage parameters and
@fig-cs2l-pool-s1, @fig-cs2l-pool-s2, and @fig-cs2l-pool-s3 show sixteen representative training
levels from each stage.

#figure(
  table(
    columns: 10,
    stroke: none,
    inset: (x: 5pt, y: 4pt),
    align: horizon,
    table.hline(stroke: 1pt),
    table.header(
      [*Stage*], [*Grid*], [*Agents*], [*Lasers*], [*$T_("max")$*], [*Walls*],
      [*Generator*], [*Profile*], [*Train*], [*Eval*],
    ),
    table.hline(stroke: 0.5pt),
    [S1], [6×6], [2], [0], [12], [3], [Random (solv.)],       [n/a],             [100], [0],
    [S2], [6×6], [2], [1], [14], [3], [Constructive (coop.)], [any],           [100], [0],
    [S3], [6×6], [2], [2], [18], [3], [Constructive (coop.)], [`fully_coupled`], [100], [50],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Per-stage generation parameters for the two-laser curriculum pools (@transfer-experiment).
    Source: `src/experiments/curriculum_strategy_2L/configs.py`; pools rendered by
    `src/scripts/render_curriculum_strategy_2L_pools.py`.
  ],
) <tab-cs2l-pools>

#figure(
  pool_grid("../../results/curriculum_strategy_2L/levels/stage_1_6x6_2a_0L_random/train/images", 16, cols: 4),
  caption: [Sixteen S1 training levels: $6 times 6$, 2 agents, 0 lasers (navigation warm-up).],
) <fig-cs2l-pool-s1>

#figure(
  pool_grid("../../results/curriculum_strategy_2L/levels/stage_2_6x6_2a_1L_cooperative/train/images", 16, cols: 4),
  caption: [Sixteen S2 training levels: $6 times 6$, 2 agents, 1 laser (asymmetric cooperation).],
) <fig-cs2l-pool-s2>

#figure(
  pool_grid("../../results/curriculum_strategy_2L/levels/stage_3_6x6_2a_2L_cooperative/train/images", 16, cols: 4),
  caption: [
    Sixteen S3 (target) training levels: $6 times 6$, 2 agents, 2 lasers, `fully_coupled` profile
    (the mutual two-laser target).
  ],
) <fig-cs2l-pool-s3>

=== Level-6 transfer

A four-stage curriculum of generated levels growing in geometry and cooperation, four agents
throughout, with the gem reward set to zero in every environment so that the reward structure is
consistent between the gem-free generated levels and the gem-bearing Level 6. @tab-level6-stages
gives the stage ladder and @tab-level6-results the per-condition outcomes. Every condition,
including the full curriculum at two million steps, scores zero on Level 6 *and* on the
in-distribution held-out generated pool; mean Level-6 return stays negative throughout. The stage
pools are SAT-generated from master seed `RNG_SEED = 20260514`, and the runs were produced against
`marl` commit `23c4d233`. The stage pools themselves were not retained on disk; representative
levels for the four stage generators at comparable grid sizes appear in
@appendix-gallery-constrained-random (stage 1), @appendix-gallery-constructive-cooperative
(stages 2–3), and @appendix-gallery-level6 (stage 4, the $12 times 13$ Level-6 footprint).

#figure(
  table(
    columns: 4,
    stroke: none,
    inset: 6pt,
    align: (center, center, center, left),
    table.hline(stroke: 1pt),
    table.header([*Stage*], [*Grid*], [*Lasers*], [*Generator*]),
    table.hline(stroke: 0.5pt),
    [1], [$6 times 6$],   [1], [Random (solvable)],
    [2], [$8 times 8$],   [2], [Constructive (cooperative)],
    [3], [$10 times 10$], [3], [Constructive (cooperative)],
    [4], [$12 times 13$], [3], [Level-6-Style],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Level-6 transfer curriculum stages (condition CURR). Four agents throughout. Source:
    `src/experiments/curriculum/configs.py`.
  ],
) <tab-level6-stages>

#figure(
  table(
    columns: 5,
    stroke: none,
    inset: 6pt,
    align: (left, left, center, center, center),
    table.hline(stroke: 1pt),
    table.header(
      [*Condition*], [*Description*], [*Steps*],
      [*SR Level 6*], [*SR generated pool*],
    ),
    table.hline(stroke: 0.5pt),
    [B1],   [Hardest stage only],          [750k],      [$0.00$], [$0.00$],
    [B2],   [Anti-curriculum (hard→easy)], [750k–2M],   [$0.00$], [$0.00$],
    [B3],   [Direct on Level 6],           [750k],      [$0.00$], [$0.00$],
    [CURR], [Four-stage curriculum],       [up to 2M],  [$0.00$], [$0.00$],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Level-6 transfer: greedy success rate (200 episodes) on the hand-crafted Level 6 and on the
    in-distribution held-out generated pool, per condition. Runs use QMIX and VDN with one to four
    seeds per condition. Mean Level-6 return is negative for all trained conditions (agents accrue
    step penalties without exiting). Source: `results/curriculum_experiment/runs/`.
  ],
) <tab-level6-results>


= Detailed experimental results

== SAT encoding: per-family clause counts <appendix-sat-clauses>

The figures of @experiments report total CNF size for the four benchmark levels under the two
movement formulations. @tab-sat-clauses gives the per-constraint-family decomposition behind
those totals.

#figure(
  table(
    columns: 6,
    stroke: none,
    inset: 6pt,
    align: (left, center, right, right, right, right),
    table.hline(stroke: 1pt),
    table.header(
      [*Level*], [*Method*],
      [*Initialisation*], [*Movement*], [*Laser*], [*Total*],
    ),
    table.hline(stroke: 0.5pt),
    [3×3],     [local],  [23],     [537],     [225],    [785],
    [3×3],     [global], [23],     [505],     [225],    [753],
    [5×5],     [local],  [87],     [4 233],   [1 884],  [6 204],
    [5×5],     [global], [87],     [6 243],   [1 884],  [8 214],
    [8×8],     [local],  [304],    [54 076],  [23 136], [77 516],
    [8×8],     [global], [304],    [143 296], [23 136], [166 736],
    [Level 6], [local],  [690],    [174 592], [77 682], [252 964],
    [Level 6], [global], [690],    [1 089 268], [77 682], [1 167 640],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Clause counts per constraint family for the two SAT movement formulations on the four
    benchmark levels. Source: `results/sat_encoding/benchmark_results.json`.
  ],
) <tab-sat-clauses>


== SAT encoding: generation and solve durations <appendix-sat-times>

@tab-sat-times reports the median CNF generation and SAT solve durations for each
(level, method) pair over the 100 timing runs of the benchmark protocol described in
@benchmarking; the interquartile range follows in parentheses. We report medians rather than means
because the per-run generation duration is heavy-tailed (occasional warm-up and garbage-collection
pauses inflate the mean), as the boxplots of @experiments make visible.

#figure(
  table(
    columns: 5,
    stroke: none,
    inset: 6pt,
    align: (left, center, right, right, right),
    table.hline(stroke: 1pt),
    table.header(
      [*Level*], [*Method*],
      [*Generation (ms)*], [*Solve (ms)*], [*Total (ms)*],
    ),
    table.hline(stroke: 0.5pt),
    [3×3],     [local],  [0.16 (0.16–0.17)],   [0.010 (0.010–0.011)], [0.17],
    [3×3],     [global], [0.13 (0.12–0.14)],   [0.012 (0.011–0.015)], [0.14],
    [5×5],     [local],  [1.26 (1.23–1.47)],   [0.062 (0.060–0.065)], [1.32],
    [5×5],     [global], [1.25 (1.20–1.45)],   [0.122 (0.120–0.127)], [1.38],
    [8×8],     [local],  [16 (15–63)],         [3.69 (3.64–3.79)],    [20.0],
    [8×8],     [global], [75 (26–78)],         [48 (48–49)],          [123],
    [Level 6], [local],  [111 (60–114)],       [4.6 (4.3–5.0)],       [115],
    [Level 6], [global], [466 (457–485)],      [38 (37–40)],          [505],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Median CNF generation, SAT solve, and total durations (milliseconds) per level and movement
    formulation over 100 timing runs, with the interquartile range in parentheses. Source:
    `results/sat_encoding/benchmark_results.json`.
  ],
) <tab-sat-times>


== Generator rejection: detailed numbers <appendix-rejection-detail>

The figures of @generator-rejection-rates report per-generator rejection rates and mean
attempts. @tab-rejection-detail gives the full numbers behind those plots, including the
number of successful trials, the number of failed trials (per-trial budget exhausted), and the
mean number of attempts per accepted level.

#figure(
  table(
    columns: 6,
    stroke: none,
    inset: 6pt,
    align: (left, center, right, right, right, right),
    table.hline(stroke: 1pt),
    table.header(
      [*Generator*], [*Grid*],
      [*Success*], [*Fail*], [*Mean attempts*], [*Rejection (%)*],
    ),
    table.hline(stroke: 0.5pt),
    [Constrained Random (solvable)],   [3×3], [200], [0],  [3.2],   [68.8],
    [Constrained Random (solvable)],   [5×5], [200], [0],  [7.6],   [86.9],
    [Constrained Random (solvable)],   [8×8], [20],  [0],  [6.5],   [84.5],
    [Constrained Random (cooperative)],[3×3], [200], [0],  [74.8],  [98.7],
    [Constrained Random (cooperative)],[5×5], [200], [0],  [77.5],  [98.7],
    [Constrained Random (cooperative)],[8×8], [12],  [8],  [14.8],  [93.3],
    [Constructive (solvable)],         [3×3], [200], [0],  [1.00],  [0.0],
    [Constructive (solvable)],         [5×5], [200], [0],  [1.11],  [10.3],
    [Constructive (solvable)],         [8×8], [20],  [0],  [1.20],  [16.7],
    [Constructive (cooperative)],      [3×3], [200], [0],  [1.00],  [0.0],
    [Constructive (cooperative)],      [5×5], [200], [0],  [1.06],  [5.7],
    [Constructive (cooperative)],      [8×8], [19],  [1],  [1.00],  [0.0],
    [Level-6-Style],                   [3×3], [200], [0],  [74.8],  [98.7],
    [Level-6-Style],                   [5×5], [200], [0],  [5.7],   [82.5],
    [Level-6-Style],                   [8×8], [20],  [0],  [4.1],   [75.3],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Detailed rejection-benchmark numbers per generator setting and grid size. "Success" is
    the number of successful trials and "Fail" the number of trials that exhausted their
    per-trial budget (500 attempts for the small grids; 100 attempts or 30 seconds for the
    $8 times 8$ grid). Mean attempts and rejection rate are computed over the successful
    trials only. The $8 times 8$ Constrained Random cooperative row is the most expensive
    setting, with 8 of 20 trials exhausting the time budget; its mean attempts is therefore an
    optimistic estimate over the trials that completed. That configuration also intermittently
    crashes the SAT solver's native extension, so each attempt is run in an isolated worker
    subprocess that discards and resamples the offending candidate. Source:
    `results/rejection_benchmark/benchmark_results.json`.
  ],
) <tab-rejection-detail>


== Cooperation profile distribution: detailed counts <appendix-profile-detail>

The figure of @profile-distribution shows the cooperation-profile breakdown of accepted
cooperative levels for three generator settings and two grid sizes. @tab-profile-detail gives
the raw counts.

#figure(
  table(
    columns: 8,
    stroke: none,
    inset: 6pt,
    align: (left, center, right, right, right, right, right, right),
    table.hline(stroke: 1pt),
    table.header(
      [*Generator*], [*Grid*],
      [*$n$*], [*asym.*], [*mutual*], [*chain*], [*distr.*], [*full*],
    ),
    table.hline(stroke: 0.5pt),
    [Constrained Random (cooperative)], [5×5], [100], [100], [0],  [0], [0], [0],
    [Constrained Random (cooperative)], [8×8], [50],  [46],  [0],  [1], [3], [0],
    [Constructive (cooperative)],       [5×5], [100], [100], [0],  [0], [0], [0],
    [Constructive (cooperative)],       [8×8], [50],  [2],   [46], [0], [2], [0],
    [Level-6-Style],                    [5×5], [100], [100], [0],  [0], [0], [0],
    [Level-6-Style],                    [8×8], [50],  [13],  [34], [0], [3], [0],
    table.hline(stroke: 1pt),
  ),
  caption: [
    Raw profile-count breakdown per generator and grid size. The columns *asym.*, *mutual*,
    *chain*, *distr.*, *full* correspond to the five cooperation-profile labels classified by
    the analyser of @cooperation-profiles. The 5×5 configuration uses 2 agents and 1 laser;
    the 8×8 configuration uses 3 agents and 2 lasers. Source:
    `results/profile_benchmark/benchmark_results.json`.
  ],
) <tab-profile-detail>


== Learnability: per-seed final success rates <appendix-learnability-detail>

@tab-learnability-perseed lists the final greedy success rate of every (algorithm, seed) cell
in the learnability experiment of @learnability-experiment. Each row is one seed, giving the
train- and test-pool success rate for IQL, VDN, and QMIX. "Train" is the success rate on the
20-level training pool and "Test" on the 20-level held-out pool, each estimated from 200 greedy
evaluation episodes.

#let _runs = json("../../results/learnability_5x5/aggregated.json")

#figure(
  table(
    columns: 7,
    stroke: none,
    inset: (x: 7pt, y: 4pt),
    align: (left, center, center, center, center, center, center),
    table.hline(stroke: 1pt),
    table.header(
      table.cell(rowspan: 2)[*Seed*],
      table.cell(colspan: 2)[*IQL*], table.cell(colspan: 2)[*VDN*], table.cell(colspan: 2)[*QMIX*],
      [*Train*], [*Test*], [*Train*], [*Test*], [*Train*], [*Test*],
    ),
    table.hline(stroke: 0.5pt),
    ..(range(20).map(s => {
      let f = a => _runs.find(r => r.algorithm == a and r.seed == s)
      let r2 = x => str(calc.round(x, digits: 2))
      let iql = f("IQL"); let vdn = f("VDN"); let qmix = f("QMIX")
      (
        str(s),
        r2(iql.train_success), r2(iql.test_success),
        r2(vdn.train_success), r2(vdn.test_success),
        r2(qmix.train_success), r2(qmix.test_success),
      )
    }).flatten()),
    table.hline(stroke: 1pt),
  ),
  caption: [
    Per-(algorithm, seed) final greedy success rates from the learnability experiment of
    @learnability-experiment, one seed per row with the train- and test-pool success rate for each
    algorithm (20 seeds × 3 algorithms). Source: `results/learnability_5x5/aggregated.json`,
    produced by `src/scripts/aggregate_learnability_results.py`.
  ],
) <tab-learnability-perseed>


= Generated level pools

== Learnability: training pool <appendix-learnability-train>

Cooperative pool used as $cal(D)_("train")$ for @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: none,
    inset: 8pt,
    align: (left, left),
    table.hline(stroke: 1pt),
    table.header([*Field*], [*Value*]),
    table.hline(stroke: 0.5pt),
    [Pool path],          [`results/learnability_5x5/levels/5x5_2a_1L_cooperative/train`],
    [Grid],               [5 × 5],
    [Agents],             [2],
    [Lasers],             [1],
    [$T_("max")$],        [10],
    [Generator],          [Constructive (cooperative mode)],
    [Pool seed],          [20260618],
    [Number of levels],   [20],
    table.hline(stroke: 1pt),
  ),
  caption: [Parameters of the learnability training pool.],
)

#figure(
  pool_grid("../../results/learnability_5x5/levels/5x5_2a_1L_cooperative/train/images", 20),
  caption: [All 20 levels of the learnability training pool, in pool order.],
) <fig-pool-learnability-train>


== Learnability: test pool <appendix-learnability-test>

Held-out cooperative pool used as $cal(D)_("test")$ for @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: none,
    inset: 8pt,
    align: (left, left),
    table.hline(stroke: 1pt),
    table.header([*Field*], [*Value*]),
    table.hline(stroke: 0.5pt),
    [Pool path],          [`results/learnability_5x5/levels/5x5_2a_1L_cooperative/test`],
    [Grid],               [5 × 5],
    [Agents],             [2],
    [Lasers],             [1],
    [$T_("max")$],        [10],
    [Generator],          [Constructive (cooperative mode)],
    [Pool seed],          [20260619],
    [Number of levels],   [20],
    table.hline(stroke: 1pt),
  ),
  caption: [Parameters of the learnability test pool.],
)

#figure(
  pool_grid("../../results/learnability_5x5/levels/5x5_2a_1L_cooperative/test/images", 20),
  caption: [All 20 levels of the learnability test pool, in pool order.],
) <fig-pool-learnability-test>


= Generator gallery

== Generator gallery: base random generator <appendix-gallery-random>

Pure random sampling with *no* geometric validation: the generator places agents, exits, walls,
and laser sources uniformly at random and accepts any layout the SAT oracle certifies as
solvable, regardless of laser geometry. Every level shown here is therefore solvable; the
contrast with the Constrained Random generator of the next section is one of geometric *quality*,
not of solvability.

The characteristic artefact is visible throughout the pools below: most levels contain a laser
source that emits *no active beam*, because the source points immediately off the grid or sits
flush against a wall or edge. Such a source is inert (it behaves like an ordinary wall tile
rather than a laser), so the level presents none of the beam-crossing structure the laser was
meant to introduce. Exits and agent starts may likewise fall on beam tiles (the LLE engine
silently relocates an agent start that would be killed on spawn). These are exactly the
degeneracies that the geometric filters of the Constrained Random generator
(@appendix-gallery-constrained-random) are designed to reject. The same grid, agent, laser, and
wall parameters are used here as in that section, so the two galleries can be read side by side.
Pools are generated by `src/scripts/generate_appendix_galleries.py`.

=== Base random: 3×3, 2 agents, 1 laser

#let _g01 = json("../../results/appendix_galleries/01_random_3x3_2a_1L/params.json")
#figure(gallery_params(_g01), caption: [Parameters and seed for the Base Random 3×3 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/01_random_3x3_2a_1L/images", 16, cols: 4),
  caption: [16 Base Random 3×3 (2 agents, 1 laser) levels, no geometric validation.],
)

=== Base random: 5×5, 3 agents, 2 lasers

#let _g02 = json("../../results/appendix_galleries/02_random_5x5_3a_2L/params.json")
#figure(gallery_params(_g02), caption: [Parameters and seed for the Base Random 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/02_random_5x5_3a_2L/images", 16, cols: 4),
  caption: [16 Base Random 5×5 (3 agents, 2 lasers) levels, no geometric validation.],
)

=== Base random: 7×7, 4 agents, 2 lasers

#let _g03 = json("../../results/appendix_galleries/03_random_7x7_4a_2L/params.json")
#figure(gallery_params(_g03), caption: [Parameters and seed for the Base Random 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/03_random_7x7_4a_2L/images", 16, cols: 4),
  caption: [16 Base Random 7×7 (4 agents, 2 lasers) levels, no geometric validation.],
)


== Generator gallery: constrained random generator <appendix-gallery-constrained-random>

Random sampling plus geometric filters (no laser pointing immediately out of bounds, no
zero-length beam, no exit on an unavoidable beam segment, etc.). Compared with the Base Random
generator of @appendix-gallery-random (which uses the identical grid, agent, laser, and wall
parameters but no geometric pre-filter), these filters remove the cosmetically degenerate layouts
(inert laser sources that emit no beam, exits stranded on beam tiles) so that accepted levels
actually exhibit the beam-crossing structure the experiments rely on. Pools are generated by
`src/scripts/generate_appendix_galleries.py`.

=== Constrained random: 3×3, 2 agents, 1 laser

#let _g04 = json("../../results/appendix_galleries/04_constrained_random_3x3_2a_1L/params.json")
#figure(gallery_params(_g04), caption: [Parameters and seed for the Constrained Random 3×3 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/04_constrained_random_3x3_2a_1L/images", 16, cols: 4),
  caption: [16 Constrained Random 3×3 (2 agents, 1 laser) levels.],
)

=== Constrained random: 5×5, 3 agents, 2 lasers

#let _g05 = json("../../results/appendix_galleries/05_constrained_random_5x5_3a_2L/params.json")
#figure(gallery_params(_g05), caption: [Parameters and seed for the Constrained Random 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/05_constrained_random_5x5_3a_2L/images", 16, cols: 4),
  caption: [16 Constrained Random 5×5 (3 agents, 2 lasers) levels.],
)

=== Constrained random: 7×7, 4 agents, 2 lasers

#let _g06 = json("../../results/appendix_galleries/06_constrained_random_7x7_4a_2L/params.json")
#figure(gallery_params(_g06), caption: [Parameters and seed for the Constrained Random 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/06_constrained_random_7x7_4a_2L/images", 16, cols: 4),
  caption: [16 Constrained Random 7×7 (4 agents, 2 lasers) levels.],
)


== Generator gallery: constructive generator (solvable) <appendix-gallery-constructive-solvable>

Lane-based construction (one disjoint lane per agent) followed by random wall placement on
the remaining cells. Cooperation is not required at generation time; only solvability is
certified by the SAT oracle.

=== Constructive solvable: 5×5, 3 agents, 1 laser

#let _g07 = json("../../results/appendix_galleries/07_constructive_5x5_3a_1L/params.json")
#figure(gallery_params(_g07), caption: [Parameters and seed for the Constructive Solvable 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/07_constructive_5x5_3a_1L/images", 16, cols: 4),
  caption: [16 Constructive Solvable 5×5 (3 agents, 1 laser) levels.],
)

=== Constructive solvable: 7×7, 4 agents, 2 lasers

#let _g08 = json("../../results/appendix_galleries/08_constructive_7x7_4a_2L/params.json")
#figure(gallery_params(_g08), caption: [Parameters and seed for the Constructive Solvable 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/08_constructive_7x7_4a_2L/images", 16, cols: 4),
  caption: [16 Constructive Solvable 7×7 (4 agents, 2 lasers) levels.],
)

=== Constructive solvable: 9×9, 4 agents, 3 lasers

#let _g09 = json("../../results/appendix_galleries/09_constructive_9x9_4a_3L/params.json")
#figure(gallery_params(_g09), caption: [Parameters and seed for the Constructive Solvable 9×9 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/09_constructive_9x9_4a_3L/images", 16, cols: 4),
  caption: [16 Constructive Solvable 9×9 (4 agents, 3 lasers) levels.],
)


== Generator gallery: constructive generator (cooperative) <appendix-gallery-constructive-cooperative>

Lane-based construction with planted same-colour structural lasers, certified to satisfy the
binary cooperation criterion of #fref(<thm-5-1>, [Theorem 5.1]). No profile filter is applied;
the gallery shows what the generator produces when any cooperation profile is admissible.

=== Constructive cooperative: 5×5, 2 agents, 1 laser

#let _g10 = json("../../results/appendix_galleries/10_cooperative_5x5_2a_1L/params.json")
#figure(gallery_params(_g10, profile: "cooperative"), caption: [Parameters and seed for the Constructive Cooperative 5×5 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/10_cooperative_5x5_2a_1L/images", 16, cols: 4),
  caption: [16 Constructive Cooperative 5×5 (2 agents, 1 laser) levels.],
)

=== Constructive cooperative: 7×7, 3 agents, 2 lasers

#let _g11 = json("../../results/appendix_galleries/11_cooperative_7x7_3a_2L/params.json")
#figure(gallery_params(_g11, profile: "cooperative"), caption: [Parameters and seed for the Constructive Cooperative 7×7 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/11_cooperative_7x7_3a_2L/images", 16, cols: 4),
  caption: [16 Constructive Cooperative 7×7 (3 agents, 2 lasers) levels.],
)

=== Constructive cooperative: 9×9, 4 agents, 3 lasers

#let _g12 = json("../../results/appendix_galleries/12_cooperative_9x9_4a_3L/params.json")
#figure(gallery_params(_g12, profile: "cooperative"), caption: [Parameters and seed for the Constructive Cooperative 9×9 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/12_cooperative_9x9_4a_3L/images", 16, cols: 4),
  caption: [16 Constructive Cooperative 9×9 (4 agents, 3 lasers) levels.],
)


== Generator gallery: constructive cooperative with profile filter <appendix-gallery-constructive-profile>

Same Constructive Cooperative generator as the previous section, but with an explicit profile
filter so accepted levels match a single label (e.g. *mutual* or *distributed*).

=== Constructive cooperative: 8×8, 3 agents, 2 lasers, profile = `mutual`

#let _g13 = json("../../results/appendix_galleries/13_cooperative_mutual_8x8_3a_2L/params.json")
#figure(gallery_params(_g13, profile: "mutual"), caption: [Parameters and seed for the profile-filtered (mutual) 8×8 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/13_cooperative_mutual_8x8_3a_2L/images", 16, cols: 4),
  caption: [16 profile-filtered (mutual) 8×8 (3 agents, 2 lasers) levels.],
)

=== Constructive cooperative: 10×10, 4 agents, 3 lasers, profile = `distributed`

#let _g14 = json("../../results/appendix_galleries/14_cooperative_distributed_10x10_4a_3L/params.json")
#figure(gallery_params(_g14, profile: "distributed"), caption: [Parameters and seed for the profile-filtered (distributed) 10×10 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/14_cooperative_distributed_10x10_4a_3L/images", 16, cols: 4),
  caption: [16 profile-filtered (distributed) 10×10 (4 agents, 3 lasers) levels.],
)


== Generator gallery: Level-6-style generator <appendix-gallery-level6>

Clustered starts and exits on opposing sides of the grid with a corridor of lasers in between,
inspired by the hand-crafted LLE Level 6.

=== Level-6-style: 8×8, 4 agents, 2 lasers

#let _g15 = json("../../results/appendix_galleries/15_level6_style_8x8_4a_2L/params.json")
#figure(gallery_params(_g15), caption: [Parameters and seed for the Level-6-Style 8×8 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/15_level6_style_8x8_4a_2L/images", 16, cols: 4),
  caption: [16 Level-6-Style 8×8 (4 agents, 2 lasers) levels.],
)

=== Level-6-style: 10×10, 4 agents, 3 lasers

#let _g16 = json("../../results/appendix_galleries/16_level6_style_10x10_4a_3L/params.json")
#figure(gallery_params(_g16), caption: [Parameters and seed for the Level-6-Style 10×10 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/16_level6_style_10x10_4a_3L/images", 16, cols: 4),
  caption: [16 Level-6-Style 10×10 (4 agents, 3 lasers) levels.],
)

=== Level-6-style: 12×13, 4 agents, 3 lasers (Level 6 footprint)

#let _g17 = json("../../results/appendix_galleries/17_level6_style_12x13_4a_3L/params.json")
#figure(gallery_params(_g17), caption: [Parameters and seed for the Level-6-Style 12×13 gallery pool.])
#figure(
  pool_grid("../../results/appendix_galleries/17_level6_style_12x13_4a_3L/images", 16, cols: 4),
  caption: [16 Level-6-Style 12×13 (4 agents, 3 lasers) levels, the same footprint as the hand-crafted LLE Level 6.],
)


= Solver solutions for the default levels <appendix-solved-levels>

The bounded-horizon SAT solver of @sat-reduction certifies a level as solvable by exhibiting an
explicit joint plan. The filmstrips below replay that plan for each of the six default LLE levels.
Each frame is the world rendered at a timestep $t$, sampled evenly across the solution horizon, and
the final frame shows every agent standing on an exit. A static document cannot animate the plans,
so these sampled frames are the portable substitute.

#figure(
  image("../../results/solved_levels/level_1_filmstrip.pdf", width: 100%),
  caption: [LLE Level 1 solved within $T_("max") = 10$ steps.],
) <fig-solved-level-1>

#figure(
  image("../../results/solved_levels/level_2_filmstrip.pdf", width: 100%),
  caption: [LLE Level 2 solved within $T_("max") = 10$ steps.],
) <fig-solved-level-2>

#figure(
  image("../../results/solved_levels/level_3_filmstrip.pdf", width: 100%),
  caption: [LLE Level 3 solved within $T_("max") = 10$ steps.],
) <fig-solved-level-3>

#figure(
  image("../../results/solved_levels/level_4_filmstrip.pdf", width: 100%),
  caption: [LLE Level 4 solved within $T_("max") = 10$ steps.],
) <fig-solved-level-4>

#figure(
  image("../../results/solved_levels/level_5_filmstrip.pdf", width: 100%),
  caption: [LLE Level 5 solved within $T_("max") = 19$ steps.],
) <fig-solved-level-5>

#figure(
  image("../../results/solved_levels/level_6_filmstrip.pdf", width: 100%),
  caption: [LLE Level 6 solved within $T_("max") = 21$ steps; the four agents descend through the laser corridors and reach the exit block together.],
) <fig-solved-level-6>



