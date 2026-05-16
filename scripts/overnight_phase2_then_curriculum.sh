#!/usr/bin/env bash
# Overnight script: finish Phase 2 learnability → curriculum pilot
# Run from project root: bash scripts/overnight_phase2_then_curriculum.sh

set -e

PY="C:/Users/hugo/Documents/marl/.venv/Scripts/python.exe"
export PYTHONPATH=src
MAX_PARALLEL=5

echo "=== Step 1: Wait for Phase 2 learnability to finish ==="
while true; do
  count=$(ls results/learnability_phase2/runs/*/final_results.json 2>/dev/null | wc -l)
  echo "$(date +%H:%M:%S) - Phase 2: $count/60 done"
  if [ "$count" -ge 60 ]; then
    echo "Phase 2 learnability complete!"
    break
  fi
  sleep 120
done

echo ""
echo "=== Step 2: Generate Phase 2 plots ==="
cmd //c "$PY" -c "from pathlib import Path; from experiments.learnability.plot_results import generate_all_figures; generate_all_figures(Path('results/learnability_phase2/runs'), Path('results/learnability_phase2/figures'))"
echo "Phase 2 plots generated."

echo ""
echo "=== Step 3: Commit Phase 2 results ==="
git add results/learnability_phase2/
git commit -m "📊 Phase 2 learnability: all 60 runs complete (8x8, 3 agents, 2 lasers)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" || echo "(nothing to commit)"

echo ""
echo "=== Step 4: Curriculum smoke test ==="
cmd //c "$PY" -m experiments.curriculum.run_experiment \
  --condition B3 --algo IQL --seed 0 --steps 5000 \
  --out-dir results/curriculum_experiment_smoke

if [ -f "results/curriculum_experiment_smoke/runs/B3_IQL_seed0/final_results.json" ]; then
  echo "Smoke test PASSED"
  rm -rf results/curriculum_experiment_smoke
else
  echo "ERROR: Smoke test failed! Stopping."
  exit 1
fi

echo ""
echo "=== Step 5: Launch curriculum pilot (8 runs) ==="
echo "4 conditions x 2 seeds x QMIX x 750k steps, $MAX_PARALLEL parallel"

CONDITIONS=("B1" "B2" "B3" "CURR")
SEEDS=(0 1)
STEPS=750000

pids=()
count=0
total=8

for cond in "${CONDITIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    count=$((count + 1))
    run_dir="results/curriculum_experiment/runs/${cond}_QMIX_seed${seed}"

    if [ -f "$run_dir/final_results.json" ]; then
      echo "[${count}/${total}] SKIP ${cond}_QMIX_seed${seed} (already done)"
      continue
    fi

    echo "[${count}/${total}] Launching ${cond}_QMIX_seed${seed}..."
    cmd //c "$PY" -m experiments.curriculum.run_experiment \
      --condition "$cond" --algo QMIX --seed "$seed" --steps "$STEPS" &
    pids+=($!)

    if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
      wait "${pids[0]}"
      pids=("${pids[@]:1}")
    fi
  done
done

for pid in "${pids[@]}"; do
  wait "$pid"
done

echo ""
echo "=== Step 6: Commit curriculum pilot results ==="
git add results/curriculum_experiment/runs/
git commit -m "📊 Curriculum pilot: QMIX × 4 conditions × 2 seeds × 750k steps

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" || echo "(nothing to commit)"

echo ""
echo "=== ALL DONE ==="
echo "Phase 2 learnability + curriculum pilot complete."
echo "Check results/curriculum_experiment/runs/*/final_results.json for pilot results."
