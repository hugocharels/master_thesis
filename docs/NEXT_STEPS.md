# Next steps — experiments to run

_Status (2026-05-21): the data-scaling result is confirmed positive (held-out test
0.14 → 0.29 → 0.44 as #train levels 20 → 100 → 500) at 5 seeds; the thesis section is
written with provisional 5-seed numbers. Two things left: (1) finish data-scaling to
20 seeds, (2) run the curriculum (CL) experiment._

All cluster runs go through `bash docker/run.sh -- ...` (it picks the GPUs and the right
python). Set `GPU_DEVICES` to the GPUs you grabbed and `MAX_PARALLEL = 3 × #GPUs`.
**`git pull` on the cluster first** so it has the latest scripts.

---

## 1. Data scaling — remaining seeds (5 → 19, to reach 20 total)

Seeds 0–4 are already done. The script skips finished cells and reuses the existing pools,
so this only runs the new seeds.

```bash
SEEDS="$(seq 5 19)" GPU_DEVICES="0,1,2,3,4,5,6,7" MAX_PARALLEL=24 \
  bash docker/run.sh -- bash scripts/data_scaling_sweep.sh
```
- 15 seeds × 3 sizes (20/100/500) × 3 algos = **135 runs**, 300k steps each (~2 h on 8 GPUs).

**After it finishes:**
```bash
git add results/datascale_* && git commit -m "new results: data-scaling 20 seeds" && git push
```
→ tell Claude: re-run `experiments.learnability.plot_data_scaling` and update the thesis
table/figure to the final 20-seed numbers (the trend is already locked).

---

## 2. Curriculum vs direct on the 8×8 target — the CL result (NOT run yet)

Ladder (2 agents): 4×4/0L → 5×5/1L → 6×6/1L → 7×7/2L → **8×8/2L (target)**, 100 levels/rung,
1M steps total. Conditions: `direct` (baseline), `forward` (curriculum), `reverse`, `mixed`.
Direct's 8×8 baseline is ~0.12 train / 0 test — we want `forward` clearly above that.

**Step 2a — pilot first (gates the full run):**
```bash
ALGOS="VDN" SEEDS="0" GPU_DEVICES="4,5,6,7" MAX_PARALLEL=4 \
  bash docker/run.sh -- bash scripts/launch_curriculum_strategy.sh
```
- 4 conditions × VDN × seed 0 = **4 runs**, 1M each.
- First launch SAT-generates 100 levels/rung incl. 8×8/2L → preflight takes ~10–20 min.
- **Gate:** does `forward` beat `direct` on 8×8?  Check:
  ```bash
  cat results/curriculum_strategy/runs/*_VDN_seed0/final_results.json
  ```

**Step 2b — full run (only if the pilot shows a gap):**
```bash
ALGOS="IQL VDN QMIX" SEEDS="$(seq 0 19)" GPU_DEVICES="0,1,2,3,4,5,6,7" MAX_PARALLEL=24 \
  bash docker/run.sh -- bash scripts/launch_curriculum_strategy.sh
```
- 4 conditions × 3 algos × 20 seeds = **240 runs**, 1M each (big).
- For a faster first look use `SEEDS="$(seq 0 4)"` (5 seeds = 60 runs).

**After it finishes:**
```bash
git add results/curriculum_strategy && git commit -m "new results: curriculum vs direct 8x8" && git push
```
→ tell Claude: plot per-condition success on 8×8 and add the CL section to the thesis.

---

## Reminders
- **GPU check:** the runner prints `Using device: cuda`; `nvidia-smi` should show your PIDs on
  GPUs at >0 % util. High CPU is normal (LLE env is CPU-bound). If GPU 0 % and all cores maxed,
  docker lost the GPU link → `docker kill` the container and relaunch.
- Don't set `MAX_PARALLEL` above the number of free CPU cores.
