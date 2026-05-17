#!/usr/bin/env bash
# Curriculum-transfer FULL sweep: 4 conditions x 3 algos x 5 seeds x 1.5M steps.
# 60 cells total. Skips runs that already have final_results.json.
#
# Do NOT launch this until the pilot has validated the scheduler and
# the four conditions look distinguishable on QMIX. Expect ~50 h per
# cell on a single CPU; plan accordingly.

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src

OUT_DIR="results/curriculum_experiment"
STEPS=1500000             # FULL_RUN_TOTAL_STEPS in configs.py
MAX_PARALLEL=${MAX_PARALLEL:-4}

# Round-robin across the GPUs exposed via `docker run --gpus device=...`.
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)

CONDITIONS=("B1" "B2" "B3" "CURR")
ALGOS=("QMIX" "VDN" "IQL")
SEEDS=$(seq 0 4)          # 5 seeds for the full sweep

pids=()
count=0
launched=0
skipped=0
total=$((${#CONDITIONS[@]} * ${#ALGOS[@]} * 5))

for cond in "${CONDITIONS[@]}"; do
  for algo in "${ALGOS[@]}"; do
    for seed in $SEEDS; do
      count=$((count + 1))
      run_dir="$OUT_DIR/runs/${cond}_${algo}_seed${seed}"

      if [ -f "$run_dir/final_results.json" ]; then
        skipped=$((skipped + 1))
        echo "[${count}/${total}] SKIP ${cond}_${algo}_seed${seed}"
        continue
      fi

      gpu_index=""
      [ "$NUM_GPUS" -gt 0 ] && gpu_index=$(( launched % NUM_GPUS ))
      launched=$((launched + 1))

      echo "[${count}/${total}] Launching ${cond}_${algo}_seed${seed} (${STEPS} steps)${gpu_index:+ on cuda:$gpu_index}"
      CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.curriculum.run_experiment \
        --condition "$cond" --algo "$algo" --seed "$seed" --steps "$STEPS" \
        --out-dir "$OUT_DIR" &
      pids+=($!)

      if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
        wait "${pids[0]}"
        pids=("${pids[@]:1}")
      fi
    done
  done
done

for pid in "${pids[@]}"; do
  wait "$pid"
done

echo "Full sweep done. Skipped ${skipped}, ran $((total - skipped))."
