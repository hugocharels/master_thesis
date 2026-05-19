#!/usr/bin/env bash
# Single-seed probe to test whether the current MARL stack learns
# anything above the 5x5 baseline on a 7x7 cooperative pool.
#
# Run via your usual Docker wrapper, e.g.::
#
#     GPU_DEVICES=0 bash docker/run.sh -- bash scripts/launch_learnability_7x7_probe.sh
#
# Add seeds by exporting SEEDS="0 1 2" before the call. Skips runs that
# already have final_results.json so re-running the command is safe.

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src
OUT_DIR="results/learnability_7x7"
STEPS=${STEPS:-200000}
MAX_PARALLEL=${MAX_PARALLEL:-1}

# 7x7 probe geometry: one extra agent and one larger grid side than the
# 5x5 baseline, same horizon-per-cell ratio, same generator.
HEIGHT=7
WIDTH=7
AGENTS=3
LASERS=1
T_MAX=14

# Round-robin training subprocesses across the GPUs exposed to this
# container via `docker run --gpus device=...`. NUM_GPUS=0 -> no env var
# set -> torch falls back to CPU.
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)

ALGOS=(${ALGOS:-QMIX})
SEEDS=${SEEDS:-0}

pids=()
count=0
launched=0
skipped=0
total=0
for algo in "${ALGOS[@]}"; do
  for seed in $SEEDS; do
    total=$((total + 1))
  done
done

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
    CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.learnability.run_experiment \
      --algo "$algo" --seed "$seed" --steps "$STEPS" \
      --height "$HEIGHT" --width "$WIDTH" \
      --agents "$AGENTS" --lasers "$LASERS" --t-max "$T_MAX" \
      --out-dir "$OUT_DIR" &
    pids+=($!)

    # Wait if we've hit the parallel limit
    if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
      wait "${pids[0]}"
      pids=("${pids[@]:1}")
    fi
  done
done

# Wait for remaining
for pid in "${pids[@]}"; do
  wait "$pid"
done

echo "All done. Skipped ${skipped}, ran $((total - skipped))."
