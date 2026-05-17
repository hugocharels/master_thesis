#!/usr/bin/env bash
# B3-LONG stretch baseline: train QMIX directly on hand-crafted Level 6
# with 2x and 3x the default budget (3M and 4.5M env steps).
#
# Purpose: establish whether B3 can EVER succeed on Level 6 given more
# compute, which strengthens or weakens the thesis claim:
#   - B3 still fails at 3M / 4.5M  -> CURR enables what direct training
#                                      cannot. Strongest thesis claim.
#   - B3 succeeds at 3M but not 1.5M -> CURR is faster than direct
#                                      training. Weaker but still useful.
#   - B3 succeeds at 1.5M already   -> No need to run this; B3 isn't the
#                                      bottleneck.
#
# Skips runs that already have final_results.json.

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src

OUT_DIR="results/curriculum_experiment_b3_long"
ALGO="QMIX"
SEEDS=$(seq 0 2)          # 3 seeds, enough to see if it ever converges
STEP_BUDGETS=(3000000 4500000)
MAX_PARALLEL=${MAX_PARALLEL:-2}

# Round-robin across the GPUs exposed via `docker run --gpus device=...`.
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)

pids=()
count=0
launched=0
skipped=0
total=$((${#STEP_BUDGETS[@]} * 3))

for steps in "${STEP_BUDGETS[@]}"; do
  for seed in $SEEDS; do
    count=$((count + 1))
    # Tag the run dir with the step budget so 3M / 4.5M don't collide.
    run_dir="$OUT_DIR/runs/B3_${ALGO}_seed${seed}_steps${steps}"

    if [ -f "$run_dir/final_results.json" ]; then
      skipped=$((skipped + 1))
      echo "[${count}/${total}] SKIP B3_${ALGO}_seed${seed}_steps${steps}"
      continue
    fi

    # The runner derives the run-dir from condition/algo/seed, so we
    # point --out-dir at a tagged subdir per step budget to keep the
    # results separated.
    out_dir_for_run="${OUT_DIR}/budget_${steps}"
    mkdir -p "$out_dir_for_run"

    gpu_index=""
    [ "$NUM_GPUS" -gt 0 ] && gpu_index=$(( launched % NUM_GPUS ))
    launched=$((launched + 1))

    echo "[${count}/${total}] Launching B3_${ALGO}_seed${seed} (${steps} steps)${gpu_index:+ on cuda:$gpu_index}"
    CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.curriculum.run_experiment \
      --condition B3 --algo "$ALGO" --seed "$seed" --steps "$steps" \
      --out-dir "$out_dir_for_run" &
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

echo "B3-long done. Skipped ${skipped}, ran $((total - skipped))."
