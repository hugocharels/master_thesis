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
    [Synthetic 3×3], [3×3], [2], [1], [8],
    [Synthetic 5×5], [5×5], [3], [2], [12],
    [Synthetic 8×8], [8×8], [4], [3], [32],
    [Benchmark Level 6], [varies], [4], [3], [known],
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
@tab-learnability-hyperparams are identical across the three algorithms (IQL, VDN, QMIX) and
across both phases of the learnability experiment, as well as across the four conditions
(B1, B2, B3, CURR) of the curriculum-transfer experiment.

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
- `cooperative` — number of levels for which the binary criterion of Theorem 4.9 holds
  (standard SAT and strict UNSAT). Reported as $n/n$ when every level passes.
- `profile` — distribution across the cooperation-profile families described in @generators
  (or N/A when the pool is non-cooperative by construction).


== Learnability Phase 1 — Training Pool <appendix-learnability-p1>

Cooperative pool used as $cal(D)_("train")$ for Phase 1 of @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/learnability/levels/6x6_2a_1L_cooperative/train`],
    [Grid],               [6 × 6],
    [Agents],             [2],
    [Lasers],             [1],
    [$T_("max")$],        [10],
    [Generator],          [`cooperative` (registry key; `constructive_cooperative` in @generators)],
    [Pool seed],          [20260515],
    [Number of levels],   [20],
    [Unique wall masks],  [20 / 20],
    [Unique agent tuples], [12 / 20],
    [Unique laser sets],  [10 / 20],
    [Mean pairwise wall-Hamming distance (normalised)], [0.154],
    [Cooperative under Theorem 4.9], [20 / 20],
    [Profile distribution], [20 asymmetric],
  ),
  caption: [Parameters and diversity statistics of the Phase 1 training pool.],
)

#figure(
  pool_grid("../../results/learnability/levels/6x6_2a_1L_cooperative/train/images", 20),
  caption: [All 20 levels of the Phase 1 training pool, in pool order.],
) <fig-pool-learnability-p1-train>


== Learnability Phase 1 — Test Pool <appendix-learnability-p1-test>

Held-out cooperative pool used as $cal(D)_("test")$ for Phase 1 of @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/learnability/levels/6x6_2a_1L_cooperative/test`],
    [Grid],               [6 × 6],
    [Agents],             [2],
    [Lasers],             [1],
    [$T_("max")$],        [10],
    [Generator],          [`cooperative`],
    [Pool seed],          [20260516],
    [Number of levels],   [20],
    [Unique wall masks],  [20 / 20],
    [Unique agent tuples], [8 / 20],
    [Unique laser sets],  [12 / 20],
    [Mean pairwise wall-Hamming distance (normalised)], [0.153],
    [Cooperative under Theorem 4.9], [20 / 20],
    [Profile distribution], [20 asymmetric],
  ),
  caption: [Parameters and diversity statistics of the Phase 1 test pool.],
)

#figure(
  pool_grid("../../results/learnability/levels/6x6_2a_1L_cooperative/test/images", 20),
  caption: [All 20 levels of the Phase 1 test pool, in pool order.],
) <fig-pool-learnability-p1-test>


== Learnability Phase 2 — Training Pool <appendix-learnability-p2>

Cooperative pool used as $cal(D)_("train")$ for Phase 2 of @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/learnability_phase2/levels/8x8_3a_2L_cooperative/train`],
    [Grid],               [8 × 8],
    [Agents],             [3],
    [Lasers],             [2],
    [$T_("max")$],        [16],
    [Generator],          [`cooperative`],
    [Pool seed],          [20260615],
    [Number of levels],   [20],
    [Unique wall masks],  [20 / 20],
    [Unique agent tuples], [17 / 20],
    [Unique laser sets],  [20 / 20],
    [Mean pairwise wall-Hamming distance (normalised)], [0.168],
    [Cooperative under Theorem 4.9], [20 / 20],
    [Profile distribution], [17 mutual, 3 asymmetric],
  ),
  caption: [Parameters and diversity statistics of the Phase 2 training pool.],
)

#figure(
  pool_grid("../../results/learnability_phase2/levels/8x8_3a_2L_cooperative/train/images", 20),
  caption: [All 20 levels of the Phase 2 training pool, in pool order.],
) <fig-pool-learnability-p2-train>


== Learnability Phase 2 — Test Pool <appendix-learnability-p2-test>

Held-out cooperative pool used as $cal(D)_("test")$ for Phase 2 of @learnability-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/learnability_phase2/levels/8x8_3a_2L_cooperative/test`],
    [Grid],               [8 × 8],
    [Agents],             [3],
    [Lasers],             [2],
    [$T_("max")$],        [16],
    [Generator],          [`cooperative`],
    [Pool seed],          [20260616],
    [Number of levels],   [20],
    [Unique wall masks],  [20 / 20],
    [Unique agent tuples], [19 / 20],
    [Unique laser sets],  [20 / 20],
    [Mean pairwise wall-Hamming distance (normalised)], [0.169],
    [Cooperative under Theorem 4.9], [20 / 20],
    [Profile distribution], [18 mutual, 1 asymmetric, 1 distributed],
  ),
  caption: [Parameters and diversity statistics of the Phase 2 test pool.],
)

#figure(
  pool_grid("../../results/learnability_phase2/levels/8x8_3a_2L_cooperative/test/images", 20),
  caption: [All 20 levels of the Phase 2 test pool, in pool order.],
) <fig-pool-learnability-p2-test>


== Curriculum Stage 1 — Training Pool <appendix-curriculum-s1>

Navigation-warmup pool with no lasers (cooperation is structurally absent), generated by the
`random` solvable generator. Used as the stage-1 source for the CURR condition and as part of
the B2 union pool of @transfer-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/curriculum_experiment/levels/stage_1_6x6_4a_0L_random/train`],
    [Grid],               [6 × 6],
    [Agents],             [4],
    [Lasers],             [0],
    [$T_("max")$],        [12],
    [Generator],          [`random` (`constrained_random_solvable` in @generators)],
    [Pool seed],          [20260614],
    [Number of levels],   [50],
    [Unique wall masks],  [50 / 50],
    [Unique agent tuples], [50 / 50],
    [Unique laser sets],  [1 / 50 (empty set: no lasers)],
    [Mean pairwise wall-Hamming distance (normalised)], [0.152],
    [Cooperative under Theorem 4.9], [N/A (no lasers)],
    [Profile distribution], [N/A],
  ),
  caption: [Parameters and diversity statistics of the curriculum stage-1 training pool.],
)

#figure(
  pool_grid("../../results/curriculum_experiment/levels/stage_1_6x6_4a_0L_random/train/images", 50, cols: 10),
  caption: [All 50 levels of the curriculum stage-1 training pool, in pool order.],
) <fig-pool-curriculum-s1>


== Curriculum Stage 2 — Training Pool <appendix-curriculum-s2>

Cooperative pool with a single structural laser, used as the stage-2 source for the CURR
condition and as part of the B2 union pool of @transfer-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/curriculum_experiment/levels/stage_2_8x8_4a_1L_cooperative/train`],
    [Grid],               [8 × 8],
    [Agents],             [4],
    [Lasers],             [1],
    [$T_("max")$],        [16],
    [Generator],          [`cooperative`],
    [Pool seed],          [20260714],
    [Number of levels],   [50],
    [Unique wall masks],  [50 / 50],
    [Unique agent tuples], [45 / 50],
    [Unique laser sets],  [29 / 50],
    [Mean pairwise wall-Hamming distance (normalised)], [0.170],
    [Cooperative under Theorem 4.9], [50 / 50],
    [Profile distribution], [50 asymmetric],
  ),
  caption: [Parameters and diversity statistics of the curriculum stage-2 training pool.],
)

#figure(
  pool_grid("../../results/curriculum_experiment/levels/stage_2_8x8_4a_1L_cooperative/train/images", 50, cols: 10),
  caption: [All 50 levels of the curriculum stage-2 training pool, in pool order.],
) <fig-pool-curriculum-s2>


== Curriculum Stage 3 — Training Pool <appendix-curriculum-s3>

Cooperative pool with two distinct-colour structural lasers, used as the stage-3 source for the
CURR condition and as part of the B2 union pool of @transfer-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/curriculum_experiment/levels/stage_3_10x10_4a_2L_cooperative/train`],
    [Grid],               [10 × 10],
    [Agents],             [4],
    [Lasers],             [2],
    [$T_("max")$],        [18],
    [Generator],          [`cooperative`],
    [Pool seed],          [20260814],
    [Number of levels],   [50],
    [Unique wall masks],  [50 / 50],
    [Unique agent tuples], [49 / 50],
    [Unique laser sets],  [48 / 50],
    [Mean pairwise wall-Hamming distance (normalised)], [0.179],
    [Cooperative under Theorem 4.9], [50 / 50],
    [Profile distribution], [49 mutual, 1 distributed],
  ),
  caption: [Parameters and diversity statistics of the curriculum stage-3 training pool.],
)

#figure(
  pool_grid("../../results/curriculum_experiment/levels/stage_3_10x10_4a_2L_cooperative/train/images", 50, cols: 10),
  caption: [All 50 levels of the curriculum stage-3 training pool, in pool order.],
) <fig-pool-curriculum-s3>


== Curriculum Stage 4 — Training Pool <appendix-curriculum-s4>

Cooperative pool generated by the level-6-style generator, used as the stage-4 source for the
CURR condition and as the sole training distribution for the B1 baseline of
@transfer-experiment.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/curriculum_experiment/levels/stage_4_12x13_4a_3L_level6_style/train`],
    [Grid],               [12 × 13],
    [Agents],             [4],
    [Lasers],             [3],
    [$T_("max")$],        [21],
    [Generator],          [`level6_style` (`constructive_level6_style` in @generators)],
    [Pool seed],          [20260914],
    [Number of levels],   [50],
    [Unique wall masks],  [50 / 50],
    [Unique agent tuples], [27 / 50],
    [Unique laser sets],  [45 / 50],
    [Mean pairwise wall-Hamming distance (normalised)], [0.173],
    [Cooperative under Theorem 4.9], [50 / 50],
    [Profile distribution], [39 mutual, 10 asymmetric, 1 distributed],
  ),
  caption: [Parameters and diversity statistics of the curriculum stage-4 training pool.],
)

#figure(
  pool_grid("../../results/curriculum_experiment/levels/stage_4_12x13_4a_3L_level6_style/train/images", 50, cols: 10),
  caption: [All 50 levels of the curriculum stage-4 training pool, in pool order.],
) <fig-pool-curriculum-s4-train>


== Curriculum Stage 4 — Held-out Evaluation Pool <appendix-curriculum-s4-eval>

Held-out evaluation pool used by the B1 baseline of @transfer-experiment as a generated
analogue of the Level 6 target.

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: (left, left),
    table.header([*Field*], [*Value*]),
    [Pool path],          [`results/curriculum_experiment/levels/stage_4_12x13_4a_3L_level6_style/eval`],
    [Grid],               [12 × 13],
    [Agents],             [4],
    [Lasers],             [3],
    [$T_("max")$],        [21],
    [Generator],          [`level6_style`],
    [Pool seed],          [20260915],
    [Number of levels],   [50],
    [Unique wall masks],  [50 / 50],
    [Unique agent tuples], [24 / 50],
    [Unique laser sets],  [37 / 50],
    [Mean pairwise wall-Hamming distance (normalised)], [0.173],
    [Cooperative under Theorem 4.9], [50 / 50],
    [Profile distribution], [39 mutual, 6 asymmetric, 5 distributed],
  ),
  caption: [Parameters and diversity statistics of the curriculum stage-4 held-out evaluation pool.],
)

#figure(
  pool_grid("../../results/curriculum_experiment/levels/stage_4_12x13_4a_3L_level6_style/eval/images", 50, cols: 10),
  caption: [All 50 levels of the curriculum stage-4 evaluation pool, in pool order.],
) <fig-pool-curriculum-s4-eval>
