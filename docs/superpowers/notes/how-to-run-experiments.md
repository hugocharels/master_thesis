# How to Run the Curriculum-Transfer Experiments

This is the operator's manual for the experiment infrastructure built across Phases 0–8.1. The CODE is finished and committed; this document describes what YOU run, in what order, on what hardware, with rough wall-clock estimates.

**Design doc:** `docs/superpowers/specs/2026-05-14-transfer-curriculum-experiments-design.md`
**Implementation plan:** `docs/superpowers/plans/2026-05-14-transfer-curriculum-experiments.md`
**marl API reference:** `docs/superpowers/notes/marl-api.md`

---

## Prerequisites (do once)

```powershell
# 1. The marl repo is cloned at ../marl on dev branch (Phase 0)
# Verify:
git -C C:\Users\hugoc\Projects\marl rev-parse HEAD
# Should print the SHA recorded in:
Get-Content results\curriculum_experiment\marl_commit.txt

# 2. The marl venv is the python you must use everywhere:
$PY = "C:\Users\hugoc\Projects\marl\.venv\Scripts\python.exe"

# 3. Verify the curriculum suite is green (no slow tests):
& $PY -m pytest src/tests/experiments/curriculum/ -v -m "not slow"
# Expect: 70 passed, 3 skipped (the pool-loaders skip until pre-flight runs)
```

If `python-sat` is missing (signals: `ModuleNotFoundError: pysat`), reinstall it:
```powershell
& C:\Users\hugoc\Projects\marl\.venv\Scripts\pip.exe install python-sat
```

---

## Step 1 — Pre-flight: generate level pools (run ONCE, ~5–30 min)

This produces 200 train levels + 50 stage-4 eval levels under `results/curriculum_experiment/levels/`. Pinned seed `RNG_SEED=20260514`.

```powershell
& $PY src\experiments\curriculum\_preflight_generate_pools.py
```

**Verify:**
```powershell
& $PY -c "from pathlib import Path; from experiments.curriculum.pool_generator import load_pool, pool_path; from experiments.curriculum.configs import CURRICULUM_STAGES; [print(s.stage_id, len(load_pool(pool_path(Path('results/curriculum_experiment'), s, 'train')))) for s in CURRICULUM_STAGES]"
# Expect: "1 50", "2 50", "3 50", "4 50"
```

**If stage 1 fails to reach 50 levels** (4 agents in 6×6/1L is geometrically tight): edit `src/experiments/curriculum/configs.py`, change stage 1 from `(height=6, width=6)` to `(7, 7)`, and re-run pre-flight. Document the change in your thesis appendix.

**Commit the data:**
```powershell
git add results\curriculum_experiment\levels
git commit -m "📦 Pinned curriculum level pools (seed 20260514)"
```

---

## Step 2 — Smoke test (verify one short run works, ~5–10 min)

Tiny B3 IQL run, 5000 steps, throwaway output. If this completes, the marl wiring is healthy.

```powershell
& $PY -m experiments.curriculum.run_experiment `
    --condition B3 --algo IQL --seed 0 --steps 5000 `
    --out-dir results\curriculum_experiment_smoke
```

**Verify:**
```powershell
Get-Content results\curriculum_experiment_smoke\runs\B3_IQL_seed0\final_results.json
Get-Content results\curriculum_experiment_smoke\runs\B3_IQL_seed0\level6_eval.csv
```

If both files exist and the JSON contains `success_rate_level6` (probably `0.0` at 5k steps — that's fine; we're checking the pipeline, not learning), the smoke is green. **Delete `results/curriculum_experiment_smoke/` afterwards** — don't pollute your real output dir.

The runner also writes `checkpoints/step_*` subfolders every 100k env steps; for a 5k smoke you'll see no checkpoints (the cadence hasn't fired). To exercise the resume path manually, kill a longer run and re-launch it with the same `--condition / --algo / --seed / --out-dir` — see "Resuming an interrupted run" below.

If you want a longer end-to-end smoke that actually exercises the curriculum scheduler (~30–60 min):
```powershell
& $PY -m experiments.curriculum.run_experiment `
    --condition CURR --algo QMIX --seed 0 --steps 200000 `
    --out-dir results\curriculum_experiment_smoke
```
Verify `stage_progress.csv` shows at least one stage transition.

---

## Resuming an interrupted run

Each run dir contains `checkpoints/step_<10-digit-step>/` subfolders written every **100k env steps** (a single 1.5M-step run produces ~15 checkpoints, of which only the **2 latest are kept** — older ones are pruned automatically). Each checkpoint stores:

- `trainer/` — full trainer weights via marl's `trainer.save()`.
- `scheduler.json` — `StageScheduler.state_dict()` (CURR only).
- `progress.json` — `{step, episode, wall_clock_seconds}` cursor.

**Disk usage:** ~150–500MB per run for the 2 retained checkpoints (depends on Q-network / mixer size; QMix > VDN ≈ IQL).

**To resume**: just re-launch the *exact same command* (same `--condition`, `--algo`, `--seed`, `--out-dir`):

```powershell
& $PY -m experiments.curriculum.run_experiment `
    --condition CURR --algo QMIX --seed 0 --steps 1500000
```

The runner detects `checkpoints/step_*` automatically, loads the latest one, prints `Resuming from step <N>, episode <M>, stage <S>` to stderr, truncates `level6_eval.csv` and `stage_progress.csv` to rows with `step <= checkpoint_step` (so no duplicate / inconsistent rows), and continues training. `final_results.json` is only written on clean completion of the full step budget.

**Edge cases / gotchas:**

- **Same `--seed` is required.** Resume uses the trainer/optimizer/replay weights from disk, but the runner re-seeds Python/numpy/torch from `--seed` at startup. Changing the seed only affects fresh streams (e.g. eval RNG); the *trained* state still comes from the checkpoint. Result: a mismatched seed produces a hybrid run that is non-reproducible — **don't do it**.
- **Changing `--steps` mid-resume**: increasing it just keeps training longer (the eval / checkpoint cadences continue from where they left off); decreasing it below the checkpointed step value will exit immediately at the top of the loop and write `final_results.json` from the resumed state.
- **Changing `--condition` or `--algo`**: the run dir name changes (`{condition}_{algo}_seed{N}`), so a different sub-tree is created and there's no resume — you start fresh under the new dir.
- **Corrupt / partial checkpoint** (e.g. killed mid-`trainer.save`): the runner logs a `warning: failed to load checkpoint ...` to stderr and starts from scratch. The retained N=2 policy means at least one earlier checkpoint usually survives; if you're unlucky, delete `checkpoints/<step_dir>/` manually and re-launch.
- **Wiping a run**: to start over, delete the entire run dir (`results/curriculum_experiment/runs/<condition>_<algo>_seed<N>/`). Just removing `final_results.json` is not enough — the checkpoints will trigger a resume.

---

## Step 3 — Pilot launch (8 runs, ~8–12h wall-clock)

4 conditions × 2 seeds × QMIX × 750k steps. The launch script below queues 4 in parallel (3 on the Ryzen 7 7700 CPU + 1 on the RTX 3060 Laptop GPU).

Save this as `scripts\launch_pilot.ps1`:

```powershell
$PY = "C:\Users\hugoc\Projects\marl\.venv\Scripts\python.exe"
$conditions = @("B1", "B2", "B3", "CURR")
$seeds = @(0, 1)
$jobs = @()
foreach ($c in $conditions) {
  foreach ($s in $seeds) {
    Write-Host "Launching ${c}_QMIX_seed${s}"
    $jobs += Start-Process -PassThru -WindowStyle Minimized $PY -ArgumentList @(
      "-m", "experiments.curriculum.run_experiment",
      "--condition", $c, "--algo", "QMIX", "--seed", $s, "--steps", "750000"
    )
    if ($jobs.Count -ge 4) {
      Wait-Process -Id $jobs[0].Id
      $jobs = $jobs[1..($jobs.Count - 1)]
    }
  }
}
$jobs | ForEach-Object { Wait-Process -Id $_.Id }
Write-Host "Pilot done."
```

```powershell
.\scripts\launch_pilot.ps1
```

**Monitor periodically:**
```powershell
Get-ChildItem results\curriculum_experiment\runs -Directory | ForEach-Object {
  $csv = Join-Path $_.FullName "level6_eval.csv"
  if (Test-Path $csv) { Write-Host "$($_.Name): $((Get-Content $csv | Select-Object -Last 1))" }
}
```

**Commit when done:**
```powershell
git add results\curriculum_experiment\runs
git commit -m "📊 Pilot results (QMIX × 4 conditions × 2 seeds × 750k)"
```

---

## Step 4 — Pilot review (your decision)

Tabulate the 8 final results:
```powershell
Get-ChildItem results\curriculum_experiment\runs -Directory | ForEach-Object {
  $f = Join-Path $_.FullName "final_results.json"
  if (Test-Path $f) {
    $j = Get-Content $f | ConvertFrom-Json
    Write-Host "$($_.Name): success_rate_level6=$($j.success_rate_level6)"
  }
}
```

Decision rules (from spec § 9):
- **GO** if any CURR seed shows Level-6 success > 0% AND B3's success rate ≤ CURR's. Curriculum signal is alive — proceed to Step 5.
- **INVESTIGATE** if all conditions show 0% success. Likely under-trained. Re-run pilot at 1M steps before scaling.
- **PIVOT** if B3 already cracks Level 6 (>50% success). The "5-year failure" premise is wrong; reconsider the headline before scaling.

Write a one-paragraph decision to `results/curriculum_experiment/pilot_decision.md` and commit:
```powershell
git add results\curriculum_experiment\pilot_decision.md
git commit -m "📝 Pilot review and go/no-go decision"
```

---

## Step 5 — Full Exp 2 follow-up (12 runs, ~30–40h wall-clock)

4 conditions × 3 added seeds (2,3,4) × QMIX × 1.5M steps.

Save as `scripts\launch_followup.ps1`:
```powershell
$PY = "C:\Users\hugoc\Projects\marl\.venv\Scripts\python.exe"
$conditions = @("B1", "B2", "B3", "CURR")
$seeds = @(2, 3, 4)
$jobs = @()
foreach ($c in $conditions) {
  foreach ($s in $seeds) {
    $jobs += Start-Process -PassThru -WindowStyle Minimized $PY -ArgumentList @(
      "-m", "experiments.curriculum.run_experiment",
      "--condition", $c, "--algo", "QMIX", "--seed", $s, "--steps", "1500000"
    )
    if ($jobs.Count -ge 4) { Wait-Process -Id $jobs[0].Id; $jobs = $jobs[1..($jobs.Count - 1)] }
  }
}
$jobs | ForEach-Object { Wait-Process -Id $_.Id }
```

```powershell
.\scripts\launch_followup.ps1
git add results\curriculum_experiment\runs
git commit -m "📊 Exp 2 follow-up results (QMIX × 4 conditions × 3 seeds × 1.5M)"
```

---

## Step 6 — Exp 1 extras (10 runs, ~25–35h wall-clock)

VDN × 5 + IQL × 5 on stage-4 pool only. (The QMIX × 5 from Step 5's `B1_QMIX_seed*` runs already cover Exp 1's QMIX entry — no extra runs needed.)

Save as `scripts\launch_exp1.ps1`:
```powershell
$PY = "C:\Users\hugoc\Projects\marl\.venv\Scripts\python.exe"
$algos = @("VDN", "IQL")
$seeds = @(0, 1, 2, 3, 4)
$jobs = @()
foreach ($a in $algos) {
  foreach ($s in $seeds) {
    $jobs += Start-Process -PassThru -WindowStyle Minimized $PY -ArgumentList @(
      "-m", "experiments.curriculum.run_experiment",
      "--condition", "B1", "--algo", $a, "--seed", $s, "--steps", "1500000"
    )
    if ($jobs.Count -ge 4) { Wait-Process -Id $jobs[0].Id; $jobs = $jobs[1..($jobs.Count - 1)] }
  }
}
$jobs | ForEach-Object { Wait-Process -Id $_.Id }
```

```powershell
.\scripts\launch_exp1.ps1
git add results\curriculum_experiment\runs
git commit -m "📊 Exp 1 results (VDN + IQL × 5 seeds × stage-4 pool × 1.5M)"
```

---

## Step 7 — Generate plots

```powershell
& $PY -m experiments.curriculum.plot_results
```

Produces 4 PDFs under `results/curriculum_experiment/figures/`:
- `learning_curves_level6.pdf` — Level-6 success vs training step, one line per condition (QMIX, 5 seeds, std band)
- `stage_progression.pdf` — CURR stage transitions per seed
- `final_success_rates.pdf` — bar chart, B3/B1/B2/CURR final success on Level 6
- `exp1_learnability.pdf` — bar chart, IQL/VDN/QMIX final success on held-out generated pool

```powershell
git add results\curriculum_experiment\figures
git commit -m "📊 Final figures for curriculum-transfer experiments"
```

---

## Step 8 — Thesis writeup

Update `thesis/chapters/experiments.typ` § "Transfer to Human-Designed Levels" (`<transfer-experiment>`). The placeholder at lines ~344–354 reads `_This section will be completed once the training experiments are run._` — replace with:

- **Protocol** subsection: cite the spec (conditions, step budget, eval protocol, seeds).
- **Results** subsection: embed the 4 PDFs from Step 7 with `image()` calls; add a summary table with mean ± std final success rates.
- **Interpretation** subsection (~400 words): explain what each baseline tells you, the curriculum effect, limitations.

Build to verify:
```powershell
cd thesis
typst compile main.typ
cd ..
```

```powershell
git add thesis\chapters\experiments.typ thesis\main.pdf
git commit -m "📝 Transfer-experiment results and interpretation"
```

---

## Caveats / things I'm flagging

1. **B2's `t_max=21` for all episodes**, even though stages 1–3 used smaller `t_max` during pool generation (12, 16, 18). This is conservative — a longer time limit can only help the agent finish, not artificially block it. If you want strict per-stage `t_max` for B2, you'd need to thread the source stage's `t_max` alongside each world (small refactor in `_load_pools_for_condition` + the baseline training loop). Not blocking; flag in the appendix if a reviewer asks.

2. **`trainer.randomize()` is called once at startup** (legitimate marl pattern), then NOT called again. The custom CURR runner mirrors `simple_run`'s episode loop minus the `randomize()`. So weights persist across all 4 stages — exactly what RQ4 requires.

3. **Replay buffer reuse across stages** (CURR): the buffer is shared throughout the run. This means stage 4 sees a buffer that contains stage 1, 2, 3 transitions too. If you want a clean buffer per stage, add an explicit reset to the runner. Not done by default because it would discard relevant cooperation experience.

4. **`gem_reward = 0` everywhere.** Generated levels have no gems; Level 6 does. Setting gem reward to 0 keeps reward distributions consistent across train/eval. Gems remain physically present on Level 6 (no level modification). All conditions agree on this.

5. **3 pool-loading tests skip until you run pre-flight** (`test_load_pools_b1/b2/curr_returns_*_if_present`). This is intentional — they can't run without on-disk data. They will all turn green after Step 1.

6. **Hardware: AMD GPU is unusable.** Only RTX 3060 Laptop GPU + Ryzen 7 7700 CPU contribute. Expect 4 parallel slots (3 CPU + 1 GPU). RX7800XT on Windows = no PyTorch path that works; ignore it.

7. **All 30 runs ≈ 2–4 days of wall-clock** with 4 parallel slots and conservative per-run estimates (~3–5h each). Build slack into your 2-week deadline; reserve days 12–14 for plots + thesis prose.

---

## Summary of what was built (commits)

| Commit | What |
|---|---|
| `fd2560b` | marl API investigation notes |
| `e2d7467` | LLE-marl env adapter with `gem_reward=0` |
| `33fd166` | Curriculum stage configs + level pool generator |
| `91a98b2` | Curriculum stage scheduler (PoolSampler + StageScheduler) |
| `0ea9233` | `run_experiment.py` CLI |
| `b16496f` | Plotting module |

**70 tests passing**, 3 deferred to post-pre-flight, 1 slow smoke test deferred to user.
