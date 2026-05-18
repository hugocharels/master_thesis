#!/usr/bin/env bash
# Launch the curriculum-learnability pilot: 3-stage curriculum ending
# at 8x8/3a/2L, evaluated on the same test pool as the learnability
# experiment. Same budget (200k steps), so direct comparison is fair.
#
# Pilot: 3 algos x 4 seeds = 12 cells. Bump SEEDS / ALGOS for a full
# sweep once the pilot confirms the curriculum works.

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src
OUT_DIR="results/curriculum_learnability"
STEPS=200000
MAX_PARALLEL=${MAX_PARALLEL:-5}

# Round-robin training subprocesses across visible GPUs.
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)

ALGOS=("IQL" "VDN" "QMIX")
SEEDS=$(seq 0 3)          # 4 seeds for the pilot

# Pre-flight: generate the stage-1 / stage-2 training pools if not
# already present. Stage 3 reuses the learnability pool.
"$PY" -m experiments.curriculum_learnability._preflight

pids=()
count=0
launched=0
skipped=0
total=$((${#ALGOS[@]} * 4))

for algo in "${ALGOS[@]}"; do
  for seed in $SEEDS; do
    count=$((count + 1))
    run_dir="$OUT_DIR/runs/${algo}_seed${seed}"

    if [ -f "$run_dir/final_results.json" ]; then
      skipped=$((skipped + 1))
      echo "[${count}/${total}] SKIP ${algo}_seed${seed} (already done)"
      continue
    fi

    gpu_index=""
    [ "$NUM_GPUS" -gt 0 ] && gpu_index=$(( launched % NUM_GPUS ))
    launched=$((launched + 1))

    echo "[${count}/${total}] Launching ${algo}_seed${seed}${gpu_index:+ on cuda:$gpu_index}"
    CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.curriculum_learnability.run_experiment \
      --algo "$algo" --seed "$seed" --steps "$STEPS" &
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

echo "Done. Skipped ${skipped}, ran $((total - skipped))."
