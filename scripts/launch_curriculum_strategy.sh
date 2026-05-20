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
#   # Pin to GPU 2 only, 3 concurrent (3 on that one GPU):
#   GPUS="2" MAX_PARALLEL=3 bash scripts/launch_curriculum_strategy.sh
#
#   # GPUs 0 and 1, 3 per GPU (=6 concurrent), round-robined across them:
#   GPUS="0 1" MAX_PARALLEL=6 bash scripts/launch_curriculum_strategy.sh
#
#   # One condition only, fewer seeds, shorter budget:
#   CONDITIONS="forward direct" SEEDS="$(seq 0 9)" STEPS=300000 \
#     bash scripts/launch_curriculum_strategy.sh
#
# Knobs (all optional env vars):
#   GPUS          which physical GPU ids to use, space-separated (e.g. "2" or
#                 "0 1 3"). Unset = auto-detect all. Empty ("") = CPU.
#   MAX_PARALLEL  TOTAL concurrent training processes (3 per GPU -> set to
#                 3 * number-of-GPUs-in-GPUS).
#   CONDITIONS / ALGOS / SEEDS / STEPS  the sweep dimensions and budget.
#   MARL_VENV     python interpreter (override on the Linux cluster).

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

# Build the list of physical GPU ids to round-robin training across.
#   GPUS unset   -> auto-detect every GPU nvidia-smi reports
#   GPUS="0 1"   -> use exactly those ids
#   GPUS=""      -> no GPU (CPU)
if [ -z "${GPUS+x}" ]; then
  _ndet=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)
  GPU_LIST=()
  for ((i = 0; i < _ndet; i++)); do GPU_LIST+=("$i"); done
else
  read -ra GPU_LIST <<< "$GPUS"
fi
NGPU=${#GPU_LIST[@]}
echo "GPUs: ${GPU_LIST[*]:-none (CPU)} | MAX_PARALLEL=$MAX_PARALLEL | STEPS=$STEPS"

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
      [ "$NGPU" -gt 0 ] && gpu_index=${GPU_LIST[$(( launched % NGPU ))]}
      launched=$((launched + 1))

      echo "[${count}/${total}] Launching ${cond}_${algo}_seed${seed}${gpu_index:+ on physical GPU $gpu_index}"
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
