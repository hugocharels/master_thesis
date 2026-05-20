#!/usr/bin/env bash
# Launch the curriculum-strategy comparison: CONDITIONS x ALGOS x SEEDS,
# every cell trained for the SAME total env-step budget (STEPS). Only the
# allocation across the difficulty ladder differs by condition.
#
# Everything is parameterised via environment variables -- one command,
# no editing. Already-finished cells (final_results.json present) are
# skipped, so re-running resumes an interrupted sweep.
#
# Examples:
#   # Full sweep: 4 conditions x 3 algos x 20 seeds = 240 runs, 3 at a time:
#   bash scripts/launch_curriculum_strategy.sh
#
#   # Pilot gate: VDN x 4 conditions x 1 seed:
#   ALGOS="VDN" SEEDS="0" bash scripts/launch_curriculum_strategy.sh
#
#   # 3 processes per GPU across 2 GPUs (=6 concurrent):
#   MAX_PARALLEL=6 bash scripts/launch_curriculum_strategy.sh
#
#   # One condition only, fewer seeds, shorter budget:
#   CONDITIONS="forward direct" SEEDS="$(seq 0 9)" STEPS=300000 \
#     bash scripts/launch_curriculum_strategy.sh

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src
OUT_DIR="results/curriculum_strategy"

STEPS="${STEPS:-600000}"
# MAX_PARALLEL is the TOTAL number of concurrent training processes. To run
# 3 per GPU, set it to 3 * (number of GPUs). Default 3 = 3 on a single GPU.
MAX_PARALLEL="${MAX_PARALLEL:-3}"
CONDITIONS="${CONDITIONS:-direct forward reverse mixed}"
ALGOS="${ALGOS:-IQL VDN QMIX}"
SEEDS="${SEEDS:-$(seq 0 19)}"   # 20 seeds for a publishable result

# Round-robin training subprocesses across visible GPUs.
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)

# Pre-flight: SAT-generate the rung pools once if they are not present.
if [ ! -d "$OUT_DIR/levels/stage_3_7x7_2a_2L_cooperative/eval" ]; then
  echo "Generating rung pools (one-off pre-flight)..."
  "$PY" -m experiments.curriculum_strategy._preflight
fi

pids=()
count=0
launched=0
skipped=0
total=$(( $(echo $CONDITIONS | wc -w) * $(echo $ALGOS | wc -w) * $(echo $SEEDS | wc -w) ))

for cond in $CONDITIONS; do
  for algo in $ALGOS; do
    for seed in $SEEDS; do
      count=$((count + 1))
      run_dir="$OUT_DIR/runs/${cond}_${algo}_seed${seed}"

      if [ -f "$run_dir/final_results.json" ]; then
        skipped=$((skipped + 1))
        echo "[${count}/${total}] SKIP ${cond}_${algo}_seed${seed} (already done)"
        continue
      fi

      gpu_index=""
      [ "$NUM_GPUS" -gt 0 ] && gpu_index=$(( launched % NUM_GPUS ))
      launched=$((launched + 1))

      echo "[${count}/${total}] Launching ${cond}_${algo}_seed${seed}${gpu_index:+ on cuda:$gpu_index}"
      CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.curriculum_strategy.run_experiment \
        --condition "$cond" --algo "$algo" --seed "$seed" --steps "$STEPS" &
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

echo "Done. Skipped ${skipped}, ran $((total - skipped)). Now: python -m experiments.curriculum_strategy.plot_results"
