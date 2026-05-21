# Next steps — experiments to run

_Status (2026-05-21): the curriculum experiment was retargeted. The 8x8/2L pilot
proved two-laser (mutual) cooperation is a hard wall for value-decomposition MARL
(all conditions 0). We pivoted to a reachable **base** result: target **6x6/2a/1L**,
ladder 4x4/0L -> 5x5/1L -> 6x6/1L, 400k budget, per-stage epsilon. Seed 0 (all 3
algos) is done and shows a CL signal (VDN forward test 0.32 vs direct 0.16; reverse
worst everywhere). Now: run to **20 seeds** and aggregate._

All cluster runs go through `bash docker/run.sh -- ...` (it picks the GPUs and the right
python). Set `GPU_DEVICES` to the GPUs you grabbed and `MAX_PARALLEL = 3 x #GPUs`.
**`git pull` on the cluster first.**

---

## 1. Curriculum base (6x6/1L) — run seeds 1..19 (to reach 20 total)

Seed 0 is already done and committed; the launcher skips finished cells
(`final_results.json` present), so **do NOT** `rm -rf runs/` this time — just run the
new seeds. Pools are already generated (preflight will be a no-op).

```bash
ALGOS="IQL VDN QMIX" SEEDS="$(seq 1 19)" GPU_DEVICES="0,1,2,3,4,5,6,7" MAX_PARALLEL=24 \
  bash docker/run.sh -- bash scripts/launch_curriculum_strategy.sh
```
- 19 seeds x 4 conditions x 3 algos = **228 runs**, 400k steps each (~10 waves on 8 GPUs).
- 4 conditions = `direct` (baseline), `forward` (curriculum), `reverse`, `mixed`.

**After it finishes:**
```bash
git add results/curriculum_strategy && git commit -m "new results: curriculum 6x6 to 20 seeds" && git push
```
-> tell Claude to pull, regenerate the figures, and read the result. The plots already
scale to any seed count:
```bash
PYTHONPATH=src <marl-venv-python> -m experiments.curriculum_strategy.plot_results
```
(writes `final_success.pdf`, `test_curves_pooled.pdf`, `test_curves_by_algo.pdf` and a
mean +- CI95 table). The base result = does **forward/mixed beat direct on held-out
6x6 test** with CIs, across the 20 seeds (and `reverse` should stay worst).

---

## 2. Data scaling — remaining seeds (5..19, to reach 20)  [secondary]

Seeds 0-4 are done; the thesis section is written with provisional 5-seed numbers.
Nested pools are reused, finished cells are skipped.

```bash
SEEDS="$(seq 5 19)" GPU_DEVICES="0,1,2,3,4,5,6,7" MAX_PARALLEL=24 \
  bash docker/run.sh -- bash scripts/data_scaling_sweep.sh
```
- 15 seeds x 3 sizes (20/100/500) x 3 algos = **135 runs**, 300k steps each.

**After it finishes:**
```bash
git add results/datascale_* && git commit -m "new results: data-scaling 20 seeds" && git push
```
-> tell Claude to re-run `experiments.learnability.plot_data_scaling` and update the
thesis table/figure to the final 20-seed numbers.

---

## Later (not built yet) — CL where direct fails

The base proves CL helps on a reachable target. The follow-up experiment points CL at
the hard regime the 8x8 pilot exposed: the **two-laser / mutual-cooperation wall**
(direct = 0 everywhere), bigger grids, or the LLE Level-6 transfer. Design TBD.

---

## Reminders
- **GPU check:** the runner prints `Using device: cuda`; `nvidia-smi` should show your PIDs
  on GPUs at >0 % util. High CPU is normal (LLE env is CPU-bound). If GPU 0 % and all cores
  maxed, docker lost the GPU link -> `docker kill` the container and relaunch.
- **Don't** `rm -rf results/curriculum_strategy/runs` for step 1 (it would wipe seed 0).
  Only clear runs/ when you intentionally want a fresh start (e.g. after a config change).
- Don't set `MAX_PARALLEL` above the number of free CPU cores.
- Kill only your container: `docker kill $(docker ps -q --filter ancestor=master_thesis:$USER)`.
