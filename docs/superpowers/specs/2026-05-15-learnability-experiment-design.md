# Learnability Experiment Design

## Purpose

Establish that MARL agents can learn to solve procedurally generated cooperative levels before testing transfer to human-designed levels. This is the missing link between "the generator produces certified levels" and "those levels are useful for training".

## Experimental Setup

### Phase 1 (this spec)

- Grid: 6x6, 2 agents, 1 laser
- Generator: `cooperative` (requires cooperation)
- t_max: 10
- 20 train levels + 20 test levels (disjoint, pinned seed)
- Algorithms: IQL, VDN, QMIX
- 20 seeds per algo = 60 runs total
- 200k env steps per run
- Eval every 10k steps on both train and test pools (50 episodes each)
- Final eval: 200 episodes on both pools
- gem_reward: 0.0 (no shaping)

### Phase 2 (future, if Phase 1 shows learning)

- Grid: 8x8, 3 agents, 2 lasers
- Same protocol, possibly longer step budget

## Module Structure

```
src/experiments/learnability/
  __init__.py
  configs.py              — grid config, algo list, step budget, eval cadence
  pool_generator.py       — generate/save/load level pools as .txt files
  run_experiment.py       — train on train pool, eval on train+test, write CSVs
  plot_results.py         — learning curves + final bar chart
  _preflight.py           — one-shot script to generate the 20+20 level pools
```

Results layout:
```
results/learnability/
  levels/
    6x6_2a_1L_cooperative/
      train/
        level_000.txt     — raw world string
        level_001.txt
        ...
      test/
        level_000.txt
        ...
  runs/
    IQL_seed0/
      train_eval.csv      — step,success_rate,mean_return
      test_eval.csv       — step,success_rate,mean_return
      final_results.json
    IQL_seed1/
    ...
    QMIX_seed19/
  figures/
    learning_curves.pdf
    final_bar_chart.pdf
```

## configs.py

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class GridConfig:
    height: int
    width: int
    n_agents: int
    n_lasers: int
    t_max: int
    generator_name: str

PHASE1_GRID = GridConfig(
    height=6, width=6, n_agents=2, n_lasers=1,
    t_max=10, generator_name="cooperative",
)

RNG_SEED: int = 20260515
TRAIN_POOL_SIZE: int = 20
TEST_POOL_SIZE: int = 20

ALGORITHMS: tuple[str, ...] = ("IQL", "VDN", "QMIX")
TOTAL_STEPS: int = 200_000
EVAL_FREQUENCY_STEPS: int = 10_000
EVAL_EPISODES: int = 50
FINAL_EVAL_EPISODES: int = 200
```

## pool_generator.py

- Levels stored as `.txt` files containing the raw `world.world_string`
- `save_pool(worlds, directory)` -> writes `level_000.txt`, `level_001.txt`, ...
- `load_pool(directory)` -> reads `.txt` files, returns `list[World]`
- `build_pool(config, seed, n_levels)` -> generates `n_levels` cooperative levels
- Pool directory: `results/learnability/levels/{h}x{w}_{n_agents}a_{n_lasers}L_{generator}/{train,test}/`

## run_experiment.py

CLI:
```
python -m experiments.learnability.run_experiment \
    --algo QMIX --seed 0 [--steps 200000] [--out-dir results/learnability]
```

Training loop:
1. Load train and test pools from disk
2. Build trainer (same hyperparams as curriculum experiment)
3. Loop: sample world from train pool, run one training episode
4. Every 10k steps: eval on train pool (50 eps) + eval on test pool (50 eps), write both CSVs
5. At end: final eval (200 eps each), write final_results.json

Output per run (`{algo}_seed{N}/`):
- `train_eval.csv`: columns `step,success_rate,mean_return`
- `test_eval.csv`: columns `step,success_rate,mean_return`
- `final_results.json`:
  ```json
  {
    "algo": "QMIX",
    "seed": 0,
    "total_steps_trained": 200000,
    "success_rate_train": 0.85,
    "success_rate_train_std": 0.12,
    "mean_return_train": 0.72,
    "success_rate_test": 0.60,
    "success_rate_test_std": 0.15,
    "mean_return_test": 0.48
  }
  ```

No checkpointing (runs are ~5 min each at this grid size).

## plot_results.py

Two figures:

1. **Learning curves** (`learning_curves.pdf`): 1x2 subplots (train / test). Each subplot has one line per algo (mean over 20 seeds, shaded +/- 1 std). X = training steps, Y = success rate.

2. **Final bar chart** (`final_bar_chart.pdf`): grouped bars, one group per algo, two bars per group (train / test). Error bars = seed std.

## Reuse from curriculum experiment

Imported directly (not copied):
- `experiments.curriculum.lle_marl_env.ThesisLLEConfig` — env adapter
- `generators.registry.GENERATOR_REGISTRY` — generator lookup

Adapted (similar logic, simplified):
- Trainer construction — same hyperparams, no condition dispatch
- Episode primitives — same `_train_one_episode`, `_greedy_eval_episode` patterns
- Eval function — same structure, called twice per cadence (train + test)

## Differences from curriculum experiment

| Aspect | Curriculum | Learnability |
|--------|-----------|-------------|
| Conditions | B1/B2/B3/CURR | None (single training pool) |
| Stages | 4 stages with advancement | None |
| Eval target | Level 6 (hand-crafted) | Train pool + test pool (generated) |
| Level format | `.json` wrapper | `.txt` (raw world string) |
| Checkpointing | Yes (100k cadence) | No (runs are short) |
| Step budget | 750k-1.5M | 200k |
