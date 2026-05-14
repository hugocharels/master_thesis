# marl API Investigation Notes

Source: clone of `https://github.com/yamoling/marl.git` (branch `dev`, commit
`23c4d233e7ce213b49870c2be1e34bf77040eca4`) at `C:\Users\hugoc\Projects\marl`.

This document captures everything Phase 1-4 implementer agents need to write the
curriculum-transfer experiment without re-reading marl. Snippets quote the live
source faithfully; line numbers are stable for this commit.

---

## 0. Repo layout (relevant subset)

```
marl/
  pyproject.toml                # requires-python = ">=3.12,<4"; deps include lle, marlenv, torch
  examples/
    train_example.py            # Canonical "how to train QMix / VDN on LLE" example
    intrinsic_motivation.py     # DQN + RND + VDN-mixer example
    plot_results.py
  src/marl/
    __init__.py                 # exports Experiment, EnvConfig, Trainer, Agent, ...
    algos/                      # Trainers: DQN, VDN, QMix, PPO, MAVEN, ...
      dqn.py                    # DQN[M: (Mixer | None)]; IQL = DQN(mixer=None)
      vdn.py                    # VDN(DQN[mixers.VDN]) - mixer defaults to mixers.VDN()
      qmix.py                   # QMix(DQN[mixers.QMix]) - caller passes mixers.QMix.from_env(env)
      intrinsic_reward/         # RND, ICM, ...
    env/
      env_config.py             # EnvConfig (abstract), LLEConfig, SMACConfig, PickleEnvConfig
      __init__.py               # re-exports EnvConfig, LLEConfig, ...
      wrappers/                 # PreventActions wrapper
    models/
      experiment.py             # Experiment dataclass and .run(...)
      run.py                    # Run dataclass (per-seed)
      trainer.py                # Trainer base
      replay_memory.py          # TransitionMemory, EpisodeMemory, PrioritizedMemory, ...
      agent.py                  # Agent base
    nn/
      mixers/                   # VDN, QMix mixers (mixers.VDN, mixers.QMix)
      model_bank/qnetworks/     # QMLP, QCNN, QRNN, QCRNN, IndependentCNN
        __init__.py             # qnetworks.from_env(env, ...) factory
    policy/                     # EpsilonGreedy, ArgMax
    runners/
      simple_runner.py          # simple_run(run, quiet, render_tests, device)
      sequential_runner.py      # sequential_run(...)
      parallel_runner.py        # parallel_run(...)
    logging/
      __init__.py               # LoggerType = Literal["tensorboard","csv","wandb","neptune","sqlite"]
      csv_logger.py             # CSVLogger
      tensorboard.py            # TBLogger
```

WebFetch had earlier suggested algos lived under `marl.training`; **they do not**.
The actual namespace is `marl.algos`. There is no `marl.training` module.

---

## 1. Env adapter contract

### 1.1 Base class

`marl.EnvConfig` (defined at `src/marl/env/env_config.py:18`) is the abstract base
that all environment adapters subclass. It is a `@dataclass` parameterised by the
environment type `E: MARLEnv` (where `MARLEnv` comes from `marlenv`, the maintainer's
sister library).

Required override (one method):

```python
@abstractmethod
def make_base_env(self) -> E: ...
```

The base class then wraps the returned env in a `marlenv.Builder` to add common
options (time limit, agent id, last action, MAVEN noise padding) inside `make()`,
which is automatically called from `__post_init__` and stored in `self.env`.

Common keyword-only fields (all defaulted, on the base class):

| field | type | default | meaning |
|---|---|---|---|
| `agent_id` | `bool` | `True` | Append one-hot agent id to obs. |
| `time_limit` | `int \| None` | `None` | Truncation horizon (steps). |
| `last_action` | `bool` | `False` | Append previous action to obs. |
| `maven_noise_size` | `int \| None` | `None` | Pad MAVEN noise extras. |

The base class exposes useful properties (also forwarded from the underlying env):
`name`, `n_agents`, `n_actions`, `observation_shape`, `observation_size`,
`state_shape`, `state_size`, `extras_shape`, `extras_size`, `extras_meanings`,
`n_objectives`, `reward_space`, `action_space`.

### 1.2 LLE adapter (the one to mirror / extend)

`marl.env.LLEConfig` (`src/marl/env/env_config.py:148`) is the adapter for the
Laser Learning Environment. Skeleton:

```python
@dataclass
class LLEConfig(EnvConfig[lle.LLE]):
    level_or_path: Literal[1, 2, 3, 4, 5, 6] | str   # int -> predefined level; str -> path to .toml
    _: KW_ONLY
    obs_type: LLEObsType = "layered"                  # layered | flattened | partial3x3 | partial5x5 | partial7x7 | state | image | perspective
    state_type: LLEObsType = "state"
    pbrs: bool = False                                # potential-based reward shaping
    time_limit: int | None = -1                       # if <= 0, set to width * height // 2

    def make_base_env(self):
        match self.level_or_path:
            case int(level):
                lle_builder = lle.level(level)
            case str(path):
                lle_builder = lle.from_file(path)
        builder = lle_builder.obs_type(self.obs_type).state_type(self.state_type)
        if self.pbrs:
            ...  # builder.pbrs(reward_value=1.0, gamma=1.0, lasers_to_reward=...)
        return builder.build()
```

Important: `LLEConfig` only accepts a hard-coded LLE level (1..6) or a `.toml`
path. To use **arbitrary in-memory `lle.World` objects** (such as the levels
generated by this thesis' `Level6StyleGenerator`), the implementer should
**subclass `EnvConfig[lle.LLE]`** and override `make_base_env()` to call the
thesis' `world_builder` and then `lle.env.Builder(world).obs_type(...).build()`.
A clean approach is to serialise the generated `World` to a TOML string and
pass that string as a dataclass field, so the config remains JSON-serialisable
through marl's `Serializable` mixin:

```python
from dataclasses import dataclass, field
import lle
from marl.env import EnvConfig

@dataclass
class ThesisLLEConfig(EnvConfig[lle.LLE]):
    world_toml: str          # serialized .toml form of the generated World
    obs_type: str = "layered"
    state_type: str = "state"
    time_limit: int | None = -1

    def __post_init__(self):
        if self.time_limit is not None and self.time_limit <= -1:
            env = self.make_base_env()
            self.time_limit = env.width * env.height // 2
        super().__post_init__()

    def make_base_env(self):
        return (
            lle.from_str(self.world_toml)
            .obs_type(self.obs_type)
            .state_type(self.state_type)
            .build()
        )
```

(There is also a `PickleEnvConfig` in marl that serialises an arbitrary
pre-built env to disk, but it is brittle across version changes and an opaque
blob — the maintainer recommends bespoke `EnvConfig` subclasses for projects
under active development. The thesis should use the TOML approach above.)

### 1.3 Underlying env contract (`lle.LLE` extends `marlenv.DiscreteMARLEnv`)

From `lle/python/lle/env/env.py`:

* `reset(*, seed: int | None = None) -> tuple[Observation, State]`
* `step(action: array[int, n_agents]) -> Step` where `Step` has
  `obs`, `state`, `reward`, `done`, `info={"gems_collected", "exit_rate"}`.
* `available_actions() -> bool[n_agents, n_actions]`.
* `seed(seed_value: int)`.
* `n_agents`, `n_actions`, `observation_shape`, `state_shape`, `reward_space`,
  `extras_shape`, `extras_meanings`.
* The action space is `DiscreteSpace.action(Action.cardinality(), [...]).repeat(n_agents)`,
  i.e. each agent picks from `Action.variants()` (NORTH, EAST, SOUTH, WEST, STAY,
  LASER) - 5 or 6 actions depending on LLE version.
* Observations come in several formats; the canonical one for CNN-based
  Q-networks is `"layered"` (3-D tensor `(C, H, W)`), and for MLP it is
  `"flattened"` (1-D vector). Layer ordering is documented in
  `lle/python/lle/observations.py`.
* Team size is exposed as `env.n_agents` (and proxied through
  `env_config.n_agents`).

### 1.4 Reward shape

LLE returns a numpy array reward whose shape is `self.reward_space.shape`.
Default strategy is `SingleObjective`, which produces `np.array([reward],
dtype=np.float32)` - i.e. a length-1 vector. With `MultiObjective` (selectable
via the Builder's `.multi_objective()`) it returns 4 scalars `[gem, exit, death,
done]`.

---

## 2. Algorithms

All trainers live in `marl.algos` and inherit from `marl.models.Trainer`.
**IQL is just `DQN(mixer=None)`** (the README confirms this).

### 2.1 DQN base (file: `src/marl/algos/dqn.py`)

```python
@dataclass(unsafe_hash=True)
class DQN[M: (Mixer | None)](Trainer):
    qnetwork: QNetwork                               # positional, required
    _: KW_ONLY
    memory_size: int | Literal["auto"] = "auto"      # auto = 50_000 (transition) or 5_000 (episode)
    mixer: M = None                                  # IQL when None
    train_policy: Policy = EpsilonGreedy.constant(0.1)
    lr: float = 1e-4
    batch_size: int = 64
    double_qlearning: bool = True
    test_policy: Policy = ArgMax()
    target_updater: TargetParametersUpdater = SoftUpdate(1e-2)
    optimiser_type: Literal["adam", "rmsprop"] = "adam"
    vbe: VBE | None = None
```

Inherited from `Trainer`:

```python
gamma: float = 0.99
ir_module: IRModule | None = None
grad_norm_clipping: float | None = None
train_interval: tuple[int, Literal["step", "episode"]] = (5, "step")   # update every 5 env steps
```

`__post_init__` automatically picks `EpisodeMemory` for recurrent Q-nets
(`qnetwork.is_recurrent`) and `TransitionMemory` otherwise. `memory_size="auto"`
maps to `5_000` episodes / `50_000` transitions. The `target_updater` defaults
to a Polyak soft update with tau = 0.01.

### 2.2 VDN (`src/marl/algos/vdn.py`)

```python
@dataclass(unsafe_hash=True)
class VDN(DQN[mixers.VDN]):
    _: KW_ONLY
    mixer: mixers.VDN = field(default_factory=mixers.VDN)
```

Trivial subclass - VDN mixer is auto-constructed (no env-specific args).

### 2.3 QMix (`src/marl/algos/qmix.py`)

```python
@dataclass
class QMix(DQN[mixers.QMix]):
    def __post_init__(self):
        return super().__post_init__()
```

Caller must supply `mixer=mixers.QMix.from_env(env)` explicitly (no default).

### 2.4 Constructing a trainer (canonical example, from `examples/train_example.py`)

```python
from marl import Experiment, algos
from marl.env import LLEConfig
from marl.models import TransitionMemory
from marl.nn import mixers
from marl.nn.model_bank import qnetworks
from marl.policy import EpsilonGreedy

env = LLEConfig(6, obs_type="layered")

# QMix
trainer = algos.QMix(
    qnetworks.from_env(env),
    TransitionMemory(50_000),                       # passes through to DQN.memory_size implicitly via __post_init__? NO - see note
    mixer=mixers.QMix.from_env(env),
)

# VDN (a real example with explicit hyperparams)
trainer = algos.VDN(
    qnetworks.from_env(env, independent=True),
    TransitionMemory(50_000),
    train_policy=EpsilonGreedy.linear(1, 0.05, 100_000),
    gamma=0.95,
    train_interval=(5, "step"),
    lr=5e-4,
    batch_size=64,
    optimiser_type="adam",
    grad_norm_clipping=10,
)

# IQL
trainer = algos.DQN(qnetworks.from_env(env, independent=True), mixer=None)
```

**Note on the second positional argument:** the example snippet above passes
`TransitionMemory(50_000)` as a positional argument, but the dataclass
signature does not declare a positional `memory` field. Reading the dataclass
again, only `qnetwork` is positional; `memory_size` is the keyword. The
`examples/train_example.py` lines

```python
algos.QMix(qnetworks.from_env(env), TransitionMemory(50_000), mixer=mixers.QMix.from_env(env))
```

actually pass the memory as the **second positional**, which would be
`memory_size`. Because `memory_size` is typed as `int | "auto"` and accepts a
`TransitionMemory`, it works only because the dataclass replaces `self.memory`
inside `__post_init__` based on `memory_size` resolution. **If the example
fails, instead drop the memory argument** (DQN will allocate a 50k
TransitionMemory by default for non-recurrent nets) **or pass `memory_size=50_000`**
- do not rely on this positional shorthand.

The dev-branch implementation that the implementer should trust is the
dataclass field order (only `qnetwork` is positional). Use keyword args.

### 2.5 Q-network factory (`src/marl/nn/model_bank/qnetworks/__init__.py`)

```python
def from_env(
    env: DiscreteMARLEnv | EnvConfig[DiscreteMARLEnv],
    recurrent: bool = False,
    independent: bool = False,
    duelling: bool = True,
    noisy: bool = False,
) -> QNetwork:
    # registry key = (len(observation_shape), recurrent, independent)
    # (1, False, False) -> QMLP        # "flattened" obs
    # (3, False, False) -> QCNN        # "layered" obs (shared across agents)
    # (3, False, True)  -> IndependentCNN  # "layered", per-agent CNN
    # (1, True, False)  -> QRNN
    # (3, True, False)  -> QCRNN
```

Default for QMLP / QCNN includes duelling=True. `independent=True` is the
recommended choice for IQL and VDN per the example.

QMLP defaults: `hidden_sizes=(256, 128)`, `activation="relu"`.
QCNN defaults: `mlp_sizes=(256, 128)`, `hidden_activation="relu"`,
`independent_mlp=True`.

### 2.6 Mixer factories

```python
from marl.nn import mixers
mixers.VDN()                                          # no args
mixers.QMix.from_env(env, embed_size=64, hypernet_embed_size=64)
```

### 2.7 LLE-specific defaults

There are **no LLE-only hyperparameter defaults** baked into the algos. The only
LLE-aware code is in `LLEConfig` (auto time-limit, PBRS hooks). All RL hypers
are the DQN/Trainer defaults shown above. The example code uses `gamma=0.95`
and `lr=5e-4` for LLE Level 6, but those are explicit, not defaults.

---

## 3. Training entry

### 3.1 High-level: `Experiment.run(...)`

`marl.Experiment` (`src/marl/models/experiment.py:28`) is the canonical entry.
Constructor:

```python
@dataclass
class Experiment[E: MARLEnv, T: Trainer](Serializable):
    env: EnvConfig[E]
    trainer: T
    n_steps: int = 1_000_000                                                 # total step budget
    logdir: str | Literal["auto", "test", "debug"] = "test"
    test_env: EnvConfig[E] | None = None                                     # defaults to self.env
    loggers: Collection[LoggerType] = field(default_factory=lambda: ["csv"]) # csv | tensorboard | wandb | neptune | sqlite
    creation_timestamp: datetime | None = None
```

`logdir="auto"` produces `logs/<trainer.name>-<env.name>`. `logdir="test"` or
`"debug"` overwrites any pre-existing experiment with the same name (useful
during development; otherwise an existing logdir raises `FileExistsError`).

`run(...)` signature:

```python
def run(
    self,
    seeds: int | Collection[int] = 1,                  # int N -> seeds [0..N-1]
    gpu_strategy: Literal["scatter", "group"] = "group",
    save_weights: bool = True,
    save_actions: bool = True,
    n_tests: int = 1,                                  # tests per checkpoint
    test_interval: int = 5000,                         # steps between tests
    *,
    quiet: bool = False,
    device: Literal["cpu", "auto"] | int = "auto",
    render_tests: bool = False,
    n_jobs: int | Literal["auto"] = "auto",            # parallel runs
    disabled_gpus: Collection[int] = (),
):
    ...
    if n_jobs <= 1 or len(runs) <= 1:
        return sequential_run(runs, device, gpu_strategy, quiet, render_tests, disabled_gpus)
    return parallel_run(runs, n_jobs, device, gpu_strategy, render_tests, disabled_gpus, quiet)
```

Minimal usage (single seed, CPU, 5k steps, csv log):

```python
exp = Experiment(env, trainer, logdir="auto", n_steps=5_000, loggers=["csv"])
exp.run(test_interval=500, n_tests=1)
```

For the curriculum experiment specifically: pass `device="cpu"` if no CUDA, or
let `"auto"` pick. For deterministic reruns, pass an explicit `seeds=[s]` list.

### 3.2 Per-run loop: `simple_run` (`src/marl/runners/simple_runner.py`)

This is the function called underneath sequential/parallel. Useful when the
implementer needs more control (e.g., to manually drive a curriculum across
worlds and reuse the same `Trainer`):

```python
def simple_run[E: MARLEnv, T: ArrayLike](
    run: "Run[E, T]", quiet: bool, render_tests: bool, device: torch.device,
):
    """
    - Seed env/test_env/trainer/agent
    - Train until time_step >= run.n_steps, episode by episode
    - Test every run.test_interval steps via _test_and_log
    - Logs training transitions through trainer.update_step and episodes
      through trainer.update_episode
    """
```

The training loop is straightforward (lines 33-41):

```python
while time_step < run.n_steps:
    episode = _train_episode(env, test_env, agent, trainer, time_step, episode_num, ...)
    episode_num += 1
    time_step += len(episode)
    pbar.update(len(episode))
if run.should_test_at(time_step):
    _test_and_log(test_env, agent, time_step, render_tests, quiet, run)
```

For curriculum learning, **the cleanest hook is to construct one `Experiment`
per training stage with shared trainer weights**. To carry weights across
stages, after stage `k` finishes call `trainer.save(checkpoint_dir)` and at the
start of stage `k+1` call `trainer.load(checkpoint_dir)` on a freshly built
trainer (or reuse the same instance - `Trainer.load(directory)` walks
`networks()` and calls `nn.load(directory)` per network).

### 3.3 Checkpoint / save behaviour

* If `save_weights=True` (the default), `_test_and_log` calls
  `run.logger.save_agent(agent, time_step)` before each test, dumping current
  parameters under `logs/<exp>/run-<seed>/test/<step>/`.
* If `save_actions=True`, the test episode actions are also persisted, enabling
  `Experiment.replay_episode(seed, time_step, test_num)` later.
* `Trainer.save(directory)` (in `src/marl/models/trainer.py:79`) iterates over
  every `NN` attribute and writes its weights to `directory`. `Trainer.load`
  is its inverse. Use these to manually checkpoint between curriculum stages.

### 3.4 Logging / metrics

`LoggerType = Literal["tensorboard","csv","wandb","neptune","sqlite"]`.

* **CSV** (default): `run.logger.log_train(metrics, time_step)` / `log_test_episodes(...)`
  write rolled-up rows per episode to `logs/<exp>/run-<seed>/{train,test,training_data}.csv`.
* **TensorBoard**: pass `loggers=["tensorboard"]` (or both: `["csv","tensorboard"]`)
  and view with `tensorboard --logdir logs`.
* Per-step logs are throttled by `train_interval` (default every 5 steps).
* `Experiment.get_results(granularity, aggregate_by)` returns aggregated polars
  dataframes for train, test, and training-data metrics - useful for plotting
  curriculum performance after the fact.

---

## 4. `gem_reward = 0` configuration in LLE

**The bad news:** there is **no first-class `gem_reward` parameter** anywhere in
LLE or in marl. `REWARD_GEM` is a module-level constant in
`lle/python/lle/env/reward_strategy.py`:

```python
REWARD_GEM = 1.0
REWARD_EXIT = 1.0
REWARD_DONE = 1.0
REWARD_DEATH = -1.0


@dataclass
class SingleObjective(RewardStrategy):
    def __init__(self, n_agents: int):
        super().__init__(n_agents, ["reward"])

    def compute_reward(self, events: list[WorldEvent]):
        reward = 0.0
        for event in events:
            match event.event_type:
                case EventType.AGENT_DIED:
                    reward += REWARD_DEATH
                    self.n_deads += 1
                case EventType.GEM_COLLECTED:
                    reward += REWARD_GEM           # <-- module constant, no override hook
                case EventType.AGENT_EXIT:
                    reward += REWARD_EXIT
                    self.n_arrived += 1
        ...
```

The `Builder` pipeline (`lle/python/lle/env/builder.py`) accepts an
`extras_generator`, `walkable_lasers`, `death_strategy`, `multi_objective()`,
`pbrs(...)`, `randomize_lasers()`, etc., **but no per-event reward weights**.

### 4.1 Recommended approach: subclass `SingleObjective`

Define a small reward-strategy override and inject it into the env after the
Builder is done with it. Both `lle.LLE.__init__` and the public `Builder` set
`reward_strategy` as an attribute, so post-build mutation is safe:

```python
# zero_gem_reward.py
from dataclasses import dataclass
from lle.env.reward_strategy import SingleObjective, REWARD_DEATH, REWARD_EXIT, REWARD_DONE
from lle.world import EventType
import numpy as np

@dataclass
class NoGemSingleObjective(SingleObjective):
    """SingleObjective with REWARD_GEM = 0."""

    def compute_reward(self, events):
        reward = 0.0
        for event in events:
            match event.event_type:
                case EventType.AGENT_DIED:
                    reward += REWARD_DEATH
                    self.n_deads += 1
                case EventType.GEM_COLLECTED:
                    pass                       # gem reward = 0
                case EventType.AGENT_EXIT:
                    reward += REWARD_EXIT
                    self.n_arrived += 1
        if self.n_arrived == self.n_agents:
            reward += REWARD_DONE
        return np.array([reward], dtype=np.float32)
```

Then wire it inside the env adapter:

```python
def make_base_env(self):
    env = lle.from_str(self.world_toml).obs_type("layered").build()
    if self.gem_reward == 0:
        env.reward_strategy = NoGemSingleObjective(env.n_agents)
    return env
```

### 4.2 Alternative: monkey-patch the constant

```python
import lle.env.reward_strategy as rs
rs.REWARD_GEM = 0.0
```

This works because `SingleObjective.compute_reward` reads the global at call
time, but it is process-wide and brittle - **prefer the subclass approach.**

### 4.3 Why this matters for the curriculum

The plan calls for a "no-shaping" condition where collecting gems gives no
reward. The exit reward (1.0) and the all-agents-arrived bonus (1.0) remain.
The implementer should expose `gem_reward: float = 1.0` on the env adapter so
the experiment matrix can toggle it. A general implementation would
parametrise `REWARD_GEM` directly:

```python
@dataclass
class WeightedSingleObjective(SingleObjective):
    gem_reward: float = 1.0
    exit_reward: float = REWARD_EXIT
    done_reward: float = REWARD_DONE
    death_reward: float = REWARD_DEATH

    def compute_reward(self, events):
        ...   # mirror SingleObjective, but use self.* constants
```

---

## 5. Installation status

* `git clone --branch dev https://github.com/yamoling/marl.git C:\Users\hugoc\Projects\marl` - **OK**
* `uv sync` (run inside the clone) - **OK**, exit code 0. The marl venv lives
  at `C:\Users\hugoc\Projects\marl\.venv`.
* Verification with the marl venv:

  ```powershell
  & C:\Users\hugoc\Projects\marl\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'C:\Users\hugoc\Projects\marl\src'); import marl; print(marl.__file__)"
  # -> C:\Users\hugoc\Projects\marl\src\marl\__init__.py
  ```

* Verification with the **system** `python3.13` fails: the global site-packages
  has an incompatible `marlenv` (no `Space` symbol). The implementer **must
  run experiments through the marl venv** (`marl/.venv/Scripts/python.exe`) or
  install marl's deps into the master_thesis venv via `uv pip install -e
  C:\Users\hugoc\Projects\marl`. Do not rely on system `python3.13` for the
  curriculum experiment runs.

* Pinned commit: `23c4d233e7ce213b49870c2be1e34bf77040eca4`
  (recorded in `results/curriculum_experiment/marl_commit.txt`).

---

## 6. Suggested pattern for Phase 1 (env adapter)

```python
# src/curriculum/env_adapter.py  (new module in master_thesis)
from dataclasses import dataclass, field
from typing import Literal

import lle
import numpy as np
from lle.env.reward_strategy import SingleObjective, REWARD_DEATH, REWARD_EXIT, REWARD_DONE
from lle.world import EventType
from marl.env import EnvConfig


@dataclass
class WeightedSingleObjective(SingleObjective):
    gem_reward: float = 1.0

    def compute_reward(self, events):
        reward = 0.0
        for event in events:
            match event.event_type:
                case EventType.AGENT_DIED:
                    reward += REWARD_DEATH
                    self.n_deads += 1
                case EventType.GEM_COLLECTED:
                    reward += self.gem_reward
                case EventType.AGENT_EXIT:
                    reward += REWARD_EXIT
                    self.n_arrived += 1
        if self.n_arrived == self.n_agents:
            reward += REWARD_DONE
        return np.array([reward], dtype=np.float32)


@dataclass
class CurriculumLLEConfig(EnvConfig[lle.LLE]):
    world_toml: str
    obs_type: Literal["layered", "flattened"] = "layered"
    state_type: str = "state"
    gem_reward: float = 1.0       # set 0.0 for the "no-shaping" arm
    time_limit: int | None = -1

    def __post_init__(self):
        if self.time_limit is not None and self.time_limit <= -1:
            self.time_limit = self.make_base_env().width * self.make_base_env().height // 2
        super().__post_init__()

    def make_base_env(self):
        env = (
            lle.from_str(self.world_toml)
            .obs_type(self.obs_type)
            .state_type(self.state_type)
            .build()
        )
        env.reward_strategy = WeightedSingleObjective(env.n_agents)
        env.reward_strategy.gem_reward = self.gem_reward
        return env
```

## 7. Suggested pattern for Phase 2 (training a single stage)

```python
from marl import Experiment, algos
from marl.nn import mixers
from marl.nn.model_bank import qnetworks
from marl.policy import EpsilonGreedy

env = CurriculumLLEConfig(world_toml=stage1_toml, gem_reward=0.0)

trainer = algos.QMix(
    qnetworks.from_env(env),
    mixer=mixers.QMix.from_env(env),
    train_policy=EpsilonGreedy.linear(1.0, 0.05, 100_000),
    lr=5e-4,
    batch_size=64,
    gamma=0.95,
    train_interval=(5, "step"),
    grad_norm_clipping=10,
)

exp = Experiment(
    env=env,
    trainer=trainer,
    n_steps=200_000,
    logdir="logs/curriculum/stage1",
    loggers=["csv", "tensorboard"],
)
exp.run(seeds=[0], n_tests=5, test_interval=5_000, device="auto")
```

For the next stage, build a fresh `CurriculumLLEConfig(world_toml=stage2_toml,
...)`, instantiate a new `algos.QMix(...)` with the same architecture, then
`new_trainer.load(Path("logs/curriculum/stage1/run-0/test/200000"))` to warm-start.

---

## 8. Quick reference

| Need | Where |
|---|---|
| Build env from generated `lle.World` | `lle.from_str(toml).obs_type(...).build()` (subclass `EnvConfig`) |
| IQL | `algos.DQN(qnetwork, mixer=None)` |
| VDN | `algos.VDN(qnetwork)` (mixer auto) |
| QMix | `algos.QMix(qnetwork, mixer=mixers.QMix.from_env(env))` |
| Train N steps | `Experiment(env, trainer, n_steps=N).run(seeds=[s])` |
| Save/restore weights between stages | `trainer.save(dir)` / new trainer + `trainer.load(dir)` |
| Disable gem reward | inject custom `RewardStrategy` post-build (see section 4.1) |
| Scale to multiple seeds | `Experiment.run(seeds=N, n_jobs=...)` |
| TensorBoard logs | `loggers=["tensorboard"]`, then `tensorboard --logdir logs` |

---

## 9. Caveats and gotchas

1. **`marl.training` does not exist.** Algos are in `marl.algos`. The
   originally-fetched docs were stale.
2. **Positional memory argument in examples is unreliable.** Always use
   keyword args: `algos.QMix(qnet, mixer=..., memory_size=50_000, ...)`.
3. **`logdir="test"` / `"debug"` will silently delete** any existing experiment
   with that name on construction (`Experiment.__post_init__`). Use a unique
   path for real curriculum runs.
4. **`Experiment` raises `FileExistsError`** on construction if `logdir` is
   neither `test`/`debug`/`tests` and the directory already contains data.
   Implementers must clean up between reruns or use new logdirs per stage.
5. **`gem_reward` is not configurable through any public LLE API.** Subclass
   the reward strategy or monkey-patch the module constant. The thesis adapter
   should expose a real parameter.
6. **System `python3.13` cannot import marl** because of `marlenv` version
   skew in user site-packages. Use the marl venv (`marl/.venv/Scripts/python.exe`)
   or install marl's deps into the project venv.
7. **Trainer dataclasses are `@dataclass(unsafe_hash=True)`**; copy them with
   `copy.deepcopy` rather than reusing the same instance across stages if you
   want a fresh optimiser. Otherwise, reuse the trainer (and its replay buffer)
   across curriculum stages - that is exactly the transfer that the thesis
   wants to study.
8. **Trainer reset between stages.** `trainer.randomize()` re-initialises all
   `NN` parameters; `simple_run` calls it on every run. To keep weights across
   stages, do not let `simple_run` reset them - i.e., bypass `Experiment.run`
   for stage 2+ and drive `simple_run` (or the loop manually) yourself, or
   call `trainer.load(checkpoint_dir)` *inside* the run after `randomize()`.
   The cleanest hook is to wrap `simple_run`, or to write a small custom
   runner that mirrors `simple_run` minus the `randomize()` call.
