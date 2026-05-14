# Setup on a New Machine

What to do on a fresh machine (e.g. your laptop) before you can run the curriculum-transfer experiments. ~10 minutes if everything goes smoothly.

> **Important:** the master_thesis repo is on GitHub, but the **`marl` and `lle` repos are NOT included in this repo** — they live as siblings on disk. You must clone them separately.

---

## 0. Prerequisites

- Python **3.13** installed and on PATH (`python --version` should report 3.13.x).
- `git` installed.
- `uv` installed: `pip install uv` (Python package manager used by `marl`).
- ~5 GB free disk space (mostly for PyTorch + the marl venv).

---

## 1. Pick your projects directory

You'll need master_thesis, marl, and lle as **sibling directories**. On the desktop they live at `C:\Users\hugoc\Projects\` — on your laptop, anywhere works as long as they're siblings. Examples below use `$PROJECTS` as a placeholder; pick a real path:

```powershell
$PROJECTS = "C:\Users\<your-user>\Projects"   # adjust to your laptop user
mkdir $PROJECTS -Force
cd $PROJECTS
```

---

## 2. Clone the three repos as siblings

```powershell
# master_thesis (this repo) — already cloned if you just pulled
git clone https://github.com/hugocharels/master_thesis.git

# marl (the MARL framework — NOT in master_thesis)
git clone --branch dev https://github.com/yamoling/marl.git

# lle (the Laser Learning Environment — already a dep of marl, but
# we sometimes want a local clone for inspection. Skip if marl's
# bundled lle is enough — most users won't need this clone.)
git clone https://github.com/yamoling/lle.git
```

Verify the layout:

```powershell
ls $PROJECTS
# Should show: lle, marl, master_thesis (and whatever else you have)
```

---

## 3. Verify marl's commit matches the desktop's pinned version

Check the SHA recorded by Phase 0 of the experiment:

```powershell
cd $PROJECTS\master_thesis
$pinned = Get-Content results\curriculum_experiment\marl_commit.txt
$actual = git -C $PROJECTS\marl rev-parse HEAD
if ($pinned -eq $actual) { Write-Host "✅ marl commit matches" } else { Write-Host "⚠️  marl commit differs: pinned=$pinned actual=$actual" }
```

If they differ, check out the pinned SHA:

```powershell
git -C $PROJECTS\marl checkout $pinned
```

(You can leave it on `dev` if you don't mind drift, but for reproducibility match the pinned SHA.)

---

## 4. Install marl's dependencies

```powershell
cd $PROJECTS\marl
uv sync
```

This creates `$PROJECTS\marl\.venv\` with marl + lle + PyTorch + everything else.

Then add `python-sat` (needed by the thesis generators):

```powershell
& $PROJECTS\marl\.venv\Scripts\pip.exe install python-sat
```

---

## 5. Verify the curriculum suite works

```powershell
cd $PROJECTS\master_thesis
$PY = "$PROJECTS\marl\.venv\Scripts\python.exe"

# Quick import check
& $PY -c "import marl, lle; print('marl from:', marl.__file__); print('lle from:', lle.__file__)"

# Full curriculum test suite
& $PY -m pytest src/tests/experiments/curriculum/ -v -m "not slow"
```

Expected: **84 passed, 3 skipped, 2 deselected**. The 3 skipped are the pool-loaders (waiting on pre-flight); the 2 deselected are slow smoke tests.

If you see different numbers or import errors, stop and debug before proceeding.

---

## 6. Generate level pools (if not yet generated)

The level pools are produced by a one-shot script with a pinned seed. They live at `results/curriculum_experiment/levels/`. **If the desktop has already generated and committed them**, just `git pull` will give them to you. **If not**, run on whichever machine first:

```powershell
& $PY src\experiments\curriculum\_preflight_generate_pools.py
```

(~5–30 min depending on stage 1's rejection rate.)

Then commit + push so the other machine pulls them:

```powershell
git add results\curriculum_experiment\levels
git commit -m "📦 Pinned curriculum level pools (seed 20260514)"
git push
```

---

## 7. You're ready

From here on, follow `docs/superpowers/notes/how-to-run-experiments.md` from Step 2 (smoke test) onward.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'marl'` | You're using system python. Use `& $PROJECTS\marl\.venv\Scripts\python.exe` instead, or activate the venv. |
| `ModuleNotFoundError: No module named 'pysat'` | `& $PROJECTS\marl\.venv\Scripts\pip.exe install python-sat` |
| Tests fail with weird `Space` import errors | Stale `marlenv` in the venv. `uv sync` again from inside `$PROJECTS\marl`. |
| `uv: command not found` | `pip install uv` |
| AMD GPU detected but PyTorch hangs/crashes | PyTorch on Windows + AMD = doesn't work. Force CPU: `$env:CUDA_VISIBLE_DEVICES = ""` before launching. |
| Path with spaces in `$PROJECTS` | Quote it: `& "$PROJECTS\marl\.venv\Scripts\python.exe"` |

---

## Recap of what's where

- **GitHub** (this repo): all the experiment code, configs, plots, design docs, operator manual, level pools (once generated and committed).
- **NOT on GitHub** (clone separately on each machine): `marl` repo, `lle` repo, the marl venv (per-machine, not synced).
- **Per-machine state**: `$PROJECTS\marl\.venv\` and any `results/curriculum_experiment_smoke/` test outputs you make. Don't commit these.
