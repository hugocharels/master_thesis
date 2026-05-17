#!/usr/bin/env bash
# Launch all 60 learnability runs (3 algos x 20 seeds x 200k steps).
# Skips runs that already have final_results.json.

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src
OUT_DIR="results/learnability"
STEPS=200000
MAX_PARALLEL=5

ALGOS=("IQL" "VDN" "QMIX")
SEEDS=$(seq 0 19)

pids=()
count=0
skipped=0
total=60

for algo in "${ALGOS[@]}"; do
  for seed in $SEEDS; do
    count=$((count + 1))
    run_dir="$OUT_DIR/runs/${algo}_seed${seed}"

    if [ -f "$run_dir/final_results.json" ]; then
      skipped=$((skipped + 1))
      echo "[${count}/${total}] SKIP ${algo}_seed${seed} (already done)"
      continue
    fi

    echo "[${count}/${total}] Launching ${algo}_seed${seed}..."
    "$PY" -m experiments.learnability.run_experiment \
      --algo "$algo" --seed "$seed" --steps "$STEPS" &
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
