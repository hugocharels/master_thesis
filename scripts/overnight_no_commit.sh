#!/usr/bin/env bash
# Overnight: wait for Phase 2 → plots → curriculum pilot (NO commits)
set -e

PY="C:/Users/hugo/Documents/marl/.venv/Scripts/python.exe"
export PYTHONPATH=src
MAX_PARALLEL=5

echo "=== Waiting for Phase 2 learnability ==="
while true; do
  count=$(ls results/learnability_phase2/runs/*/final_results.json 2>/dev/null | wc -l)
  echo "$(date +%H:%M:%S) - Phase 2: $count/60 done"
  if [ "$count" -ge 60 ]; then break; fi
  sleep 120
done

echo "=== Generating Phase 2 plots ==="
cmd //c "$PY" -c "from pathlib import Path; from experiments.learnability.plot_results import generate_all_figures; generate_all_figures(Path('results/learnability_phase2/runs'), Path('results/learnability_phase2/figures'))"

echo "=== Curriculum smoke test ==="
cmd //c "$PY" -m experiments.curriculum.run_experiment \
  --condition B3 --algo IQL --seed 0 --steps 5000 \
  --out-dir results/curriculum_experiment_smoke

if [ -f "results/curriculum_experiment_smoke/runs/B3_IQL_seed0/final_results.json" ]; then
  echo "Smoke PASSED"
  rm -rf results/curriculum_experiment_smoke
else
  echo "Smoke FAILED"; exit 1
fi

echo "=== Launching curriculum pilot (8 runs) ==="
CONDITIONS=("B1" "B2" "B3" "CURR")
SEEDS=(0 1)
pids=()
count=0
for cond in "${CONDITIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    count=$((count + 1))
    run_dir="results/curriculum_experiment/runs/${cond}_QMIX_seed${seed}"
    if [ -f "$run_dir/final_results.json" ]; then
      echo "[${count}/8] SKIP ${cond}_QMIX_seed${seed}"; continue
    fi
    echo "[${count}/8] Launching ${cond}_QMIX_seed${seed}..."
    cmd //c "$PY" -m experiments.curriculum.run_experiment \
      --condition "$cond" --algo QMIX --seed "$seed" --steps 750000 &
    pids+=($!)
    if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
      wait "${pids[0]}"; pids=("${pids[@]:1}")
    fi
  done
done
for pid in "${pids[@]}"; do wait "$pid"; done

echo "=== ALL DONE (no commits made) ==="
