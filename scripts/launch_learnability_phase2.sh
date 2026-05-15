#!/usr/bin/env bash
# Launch all 60 learnability Phase 2 runs (3 algos x 20 seeds x 200k steps)
# Runs 3 jobs in parallel.

set -e

PY="C:/Users/hugo/Documents/marl/.venv/Scripts/python.exe"
export PYTHONPATH=src
STEPS=200000
MAX_PARALLEL=3

ALGOS=("IQL" "VDN" "QMIX")
SEEDS=$(seq 0 19)

pids=()
count=0
total=60

for algo in "${ALGOS[@]}"; do
  for seed in $SEEDS; do
    count=$((count + 1))
    echo "[${count}/${total}] Launching ${algo}_seed${seed}..."
    cmd //c "$PY" -m experiments.learnability.run_experiment \
      --phase 2 --algo "$algo" --seed "$seed" --steps "$STEPS" &
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

echo "All ${total} runs complete."
