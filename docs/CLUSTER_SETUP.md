# ULB GPU Workstation Setup (Docker workflow)

How to set up and run the curriculum-transfer experiments on the
**ULB MLG GPU workstation** (`10.149.16.180` / `ulb-gpu.info.ulb.ac.be`).

> Follows the ULB workflow: zero installs on the host, everything
> runs inside a per-user Docker container. The trainer is CPU-only
> (`torch.device("cpu")` in `run_experiment.py`), so we do NOT need
> a GPU — we use plain `docker` rather than `nvidia-docker` and skip
> the GPU-allocation table in the workstation guide.

## 1 — Connect via SSH

```bash
ssh yourlogin@ulb-gpu.info.ulb.ac.be       # preferred
# or
ssh yourlogin@10.149.16.180                 # IP fallback
```

If off-campus the workstation is unreachable without the **ULB VPN**.
First-time login asks you to confirm the host fingerprint — type `yes`.

Convenience (on your laptop, in `~/.ssh/config`):

```
Host ulb
    HostName ulb-gpu.info.ulb.ac.be
    User yourlogin
    ServerAliveInterval 60
    ServerAliveCountMax 10
```

Then `ssh ulb` is enough. `ServerAliveInterval` keeps the tunnel alive
so a tmux session with 12 h of training inside isn't killed by a
silent connection drop.

## 2 — Clone the two repos on the workstation

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/yamoling/marl.git
git clone https://github.com/hugocharels/master_thesis.git
```

You do **not** need to clone `lle` — the entrypoint installs it from
PyPI inside the container. Clone it too only if you've authored
modifications you want to test (e.g. the cooperative-generator branch):

```bash
git clone https://github.com/yamoling/lle.git    # optional
```

## 3 — Build your Docker image (one-time)

This builds a personal image tagged `master_thesis:$USER`, with your
host UID/GID baked in so files written to mounted volumes end up
owned by you (not by root). Follows the ULB build pattern from the
workstation guide.

```bash
cd ~/projects/master_thesis
bash docker/build.sh
```

First build takes 5–10 minutes (Rust toolchain + Python wheels). The
build args (`USER`, UID, GID) come from your shell environment
automatically.

If `docker build` says `permission denied`, you need to be added to
the `docker` Linux group — message Yann-Aël or Jacopo on the Teams
channel (the workstation guide names them as admins).

## 4 — Launch a container

For an interactive shell:

```bash
bash docker/run.sh
```

You land in `/workspace/master_thesis/` with `python` pointing at
3.13, `PYTHONPATH` set, and `marl` + `lle` already installed. Verify:

```bash
python -m pytest src/tests/ -p no:warnings --ignore=src/tests/experiments -q
# expect: 175 passed
```

For a non-interactive run, append `--` and the command:

```bash
bash docker/run.sh -- bash scripts/launch_curriculum_pilot.sh
bash docker/run.sh -- python -m experiments.curriculum.plot_results
```

Tune memory / swap via env vars (ULB recommends not taking everything):

```bash
MEM_LIMIT=32g SWAP_LIMIT=40g bash docker/run.sh
```

## 5 — Run long jobs inside tmux *outside* the container

There's no batch scheduler on this workstation. The pattern that
survives SSH drops is:

```bash
# OUTSIDE the container, on the host:
tmux new -s curriculum-pilot

# Inside the tmux pane, launch the container with the experiment:
bash docker/run.sh -- bash scripts/launch_curriculum_pilot.sh

# Detach with Ctrl-b d. The container keeps running.
# Reattach later with:  tmux attach -t curriculum-pilot
```

`tmux ls` lists active sessions. Container output goes to the
attached tmux pane; checkpoints + final results land on the host via
the mounted volume.

## 6 — Run the experiments

Each launch script is independent and skips already-done cells, so
you can run them in parallel tmux sessions (one per script).
Recommended order:

### 6a — Curriculum pilot (4 conditions × QMIX × 4 seeds × 750 k steps)

```bash
tmux new -s curr-pilot
bash docker/run.sh -- bash scripts/launch_curriculum_pilot.sh
# Ctrl-b d to detach
```

16 cells; ~5 days at MAX_PARALLEL=4 on this workstation. Checkpoints
every 100 k steps to
`results/curriculum_experiment/runs/{COND}_QMIX_seed{N}/checkpoints/`
so killed cells resume on relaunch.

### 6b — Learnability (8×8 / 3 agents / 2 lasers)

```bash
tmux new -s learn
bash docker/run.sh -- bash scripts/launch_learnability.sh
```

~12 h. Trains IQL / VDN / QMIX × 20 seeds × 200 k steps on the
8×8 cooperative pool.

### 6c — B3-long stretch baseline (optional, valuable)

Test whether direct Level-6 training EVER converges with more budget.
Run only if the pilot suggests B3 hasn't converged at 750 k.

```bash
tmux new -s b3-long
bash docker/run.sh -- bash scripts/launch_b3_long.sh
```

### 6d — Curriculum full sweep (60 cells × 1.5 M steps)

**Only after the pilot validates.** Plan for several days.

```bash
tmux new -s curr-full
bash docker/run.sh -- bash scripts/launch_curriculum_full.sh
```

## 7 — Aggregate results into figures

```bash
bash docker/run.sh -- python -m experiments.curriculum.plot_results
bash docker/run.sh -- python -m experiments.learnability.plot_results
```

PDFs land under `results/{curriculum_experiment,learnability}/figures/`.

## 8 — Pull results back to your laptop

From your laptop:

```bash
rsync -avz --partial ulb:projects/master_thesis/results/ ./results/
```

Then thread the new figures into the thesis (see §10) and recompile
locally:

```bash
typst compile --root . thesis/main.typ
```

## 9 — Re-thread results into the thesis

1. Replace the "To be regenerated" callout in
   `thesis/chapters/experiments.typ <learnability-experiment>` with
   the new figures + per-algorithm mean ± std table.
2. Replace the `// TODO: results` block in
   `thesis/chapters/experiments.typ <transfer-experiment>` with the
   curriculum-pilot (or full-sweep) figures and a per-condition table.

Headline metric is `success_rate_level6` per condition (mean ± 95 %
CI across seeds), read from
`results/curriculum_experiment/runs/*/final_results.json`.

## 10 — Why this Dockerfile and not the official ULB base?

The ULB-supplied `gpu_ubuntu1804:base` image is Python 3.6 +
TensorFlow 2.3 + CUDA 10.1 — way too old for our PyTorch + Python
3.13 stack. Building Python 3.13 on top of that base would be
fighting the image rather than using it.

Our `docker/Dockerfile` instead starts from `python:3.13-slim` (much
smaller, current Python) and adds Rust + system build deps. We keep
the spirit of the ULB convention: per-user image (`master_thesis:$USER`)
built with your UID/GID, shared volume mount at `/workspace`, no
host-level installs.

GPU support is not added — we use plain `docker run`, not
`nvidia-docker`. Justification: `run_experiment.py` hardcodes
`device = torch.device("cpu")` because marl's models are small and
SAT-solver calls dominate the per-step cost; GPU offers no speed-up
for our workload.

## 11 — Troubleshooting

- **`docker build` says `permission denied`** — your user isn't in
  the `docker` group on the workstation. Ask admins to add you (Teams
  channel; admins are Yann-Aël and Jacopo per the workstation guide).
- **`docker run` says port already in use** — only matters if you've
  mapped a port (e.g. Jupyter). Our run.sh doesn't, so this should
  not happen.
- **`maturin develop` fails on lle source build** — first try
  `pip install laser-learning-environment` from PyPI; the wheel may
  exist for Linux/Python 3.13. The entrypoint already prefers PyPI
  when the lle source isn't mounted.
- **`ImportError: cannot import name 'DiscreteActionSpace' from 'marlenv'`**
  — wrong marl version (the system one shadows our editable install).
  Inside the container, run
  `pip install --force-reinstall -e /workspace/marl`.
- **Container loses my work when it exits** — only paths under
  `/workspace` (= host `~/projects`) survive. The mounted volume
  syncs both ways, so editing files on the host with `vim` /
  `nano` / `code` is fine.
- **Out of memory** — reduce `MAX_PARALLEL` in the launch scripts
  (`scripts/launch_*.sh`) from 4 to 2. Also tighten `MEM_LIMIT`
  when launching `docker/run.sh` so you don't starve other users.
- **Run was killed and tmux session disappeared** — your
  `final_results.json` files are still on disk (mounted volume).
  Re-launch the same script; it skips any cell that already has one
  and resumes the rest from the latest 100 k-step checkpoint.
- **Network is dead inside the container** — Docker on the ULB
  workstation usually has bridged networking, so PyPI / GitHub should
  work. If not, build the image once with a working network and the
  PyPI deps will be baked in; only the editable installs (mounted
  sources) need network on subsequent runs.
