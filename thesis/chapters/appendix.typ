#import "../macros.typ": fref

#heading(numbering: none)[Appendix]

// Helper: zero-pad an integer to three digits ("0", "12", "123" -> "000", "012", "123").
#let _pad3(i) = {
  let s = str(i)
  if s.len() == 1 { "00" + s }
  else if s.len() == 2 { "0" + s }
  else { s }
}

// Helper: build a #grid of every ``level_NNN.png`` under ``dir`` for indices
// 0..n-1. Used in every pool-inventory section below.
#let pool_grid(dir, n, cols: 5) = grid(
  columns: cols,
  gutter: 4pt,
  ..range(n).map(i => image(dir + "/level_" + _pad3(i) + ".png", width: 100%))
)


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


== Learnability and Curriculum Hyperparameters <appendix-learnability-hyperparams>

The learnability experiment (@learnability-experiment) and the curriculum-transfer experiment
(@transfer-experiment) share the same trainer construction in
`src/experiments/learnability/run_experiment.py` and
`src/experiments/curriculum/run_experiment.py`. The hyperparameters listed in
@tab-learnability-hyperparams are identical across the three algorithms (IQL, VDN, QMIX) of
the learnability experiment, as well as across the four conditions (B1, B2, B3, CURR) of the
curriculum-transfer experiment.

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
    [Q-network architecture],                     [marl `qnetworks.from_env` default], [TODO: confirm exact RNN topology in marl],
    [Mixer (QMIX)],                               [`mixers.QMix.from_env`],     [`run_experiment.py`],
    [Mixer (VDN)],                                [sum of agent $Q$-values],    [`marl.algos.VDN` implicit mixer],
    [Mixer (IQL)],                                [none],                       [`run_experiment.py` (`mixer=None`)],
    [Independent $Q$-network heads (IQL, VDN)],   [yes],                        [`qnetworks.from_env(..., independent=True)`],
    [Independent $Q$-network heads (QMIX)],       [no (shared)],                [`qnetworks.from_env(...)` default],
    [Replay buffer size],                         [marl default],               [TODO: confirm in marl source],
    [Target network update interval],             [marl default],               [TODO: confirm in marl source],
  ),
  caption: [
    Hyperparameters used in both the learnability experiment
    (@learnability-experiment) and the curriculum-transfer experiment (@transfer-experiment).
  ],
) <tab-learnability-hyperparams>


== Level Pool Inventory <appendix-pool-inventory>

The remaining sections of the appendix document every level pool used in the experiments. For
each pool we report the generator parameters, the per-pool diversity statistics produced by
`scripts/audit_level_pools.py`, the cooperation criterion of @cooperation-detection, the
cooperation-profile breakdown produced by the analyzer of @generators, and the renderings of
every individual level. Diversity columns are defined as follows:

- `uniq walls / agents / lasers` — number of distinct wall masks, agent-start tuples,
  and laser-source sets across the pool (out of $n$ levels).
- `ham norm` — mean pairwise symmetric-difference size on wall masks, normalised by grid-cell
  count.
- `cooperative` — number of levels for which the binary criterion of #fref(<thm-5-1>, [Theorem 5.1]) holds
  (standard SAT and strict UNSAT). Reported as $n/n$ when every level passes.
- `profile` — distribution across the cooperation-profile families described in @generators
  (or N/A when the pool is non-cooperative by construction).


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
    [Generator],          [`cooperative` (registry key; `constructive_cooperative` in @generators)],
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
    [Generator],          [`cooperative`],
    [Pool seed],          [20260618],
    [Number of levels],   [20],
  ),
  caption: [Parameters of the learnability test pool.],
)

#figure(
  pool_grid("../../results/learnability_5x5/levels/5x5_2a_1L_cooperative/test/images", 20),
  caption: [All 20 levels of the learnability test pool, in pool order.],
) <fig-pool-learnability-test>
