#!/usr/bin/env bash
# Launch the curriculum-strategy comparison: CONDITIONS x ALGOS x SEEDS,
# every cell trained for the SAME total env-step budget (STEPS). Only the
# allocation across the difficulty ladder differs by condition.
#
# Everything is parameterised via environment variables -- one command,
# no editing. Already-finished cells (final_results.json present) are
# skipped, so re-running resumes an interrupted sweep.
#
# ON THE ULB CLUSTER, run this INSIDE the docker container. docker/run.sh
# picks the GPU (GPU_DEVICES) and forwards MAX_PARALLEL/SEEDS/CONDITIONS/
# ALGOS/STEPS into the container; inside, this script auto-detects the
# exposed GPU(s) (leave GPUS unset). The GPUS knob below is only for
# running the venv Python directly (e.g. locally on Windows).
#
# Examples (cluster, via docker -- the usual case):
#   # Pilot: VDN x 4 conditions x 1 seed, all 4 at once on physical GPU 2:
#   GPU_DEVICES=2 MAX_PARALLEL=4 ALGOS="VDN" SEEDS="0" \
#     bash docker/run.sh -- bash scripts/launch_curriculum_strategy.sh
#
#   # Full sweep on GPU 2, 3 concurrent:
#   GPU_DEVICES=2 MAX_PARALLEL=3 \
#     bash docker/run.sh -- bash scripts/launch_curriculum_strategy.sh
#
#   # Two GPUs, 3 each (=6 concurrent):
#   GPU_DEVICES=2,4 MAX_PARALLEL=6 \
#     bash docker/run.sh -- bash scripts/launch_curriculum_strategy.sh
#
# Examples (direct, no docker -- e.g. local Windows):
#   ALGOS="VDN" SEEDS="0" bash scripts/launch_curriculum_strategy.sh
#   GPUS="2" MAX_PARALLEL=3 bash scripts/launch_curriculum_strategy.sh   # pin GPU
#
# Already-finished cells (final_results.json present) are skipped, so
# re-running resumes an interrupted sweep.
#
# Knobs (all optional env vars):
#   GPU_DEVICES   (docker/run.sh) physical GPU(s) for the container, e.g. 2
#                 or 2,4. This is the cluster GPU selector.
#   GPUS          (this script, direct mode only) physical GPU ids to use,
#                 space-separated. Unset = auto-detect all exposed. "" = CPU.
#   MAX_PARALLEL  TOTAL concurrent training processes (3 per GPU -> set to
#                 3 * number-of-GPUs).
#   CONDITIONS / ALGOS / SEEDS / STEPS  the sweep dimensions and budget.
#   MARL_VENV     python interpreter. Same default/convention as the other
#                 launch_*.sh scripts, so it resolves the same way inside the
#                 cluster docker image; override only if your setup differs.

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src
OUT_DIR="results/curriculum_strategy"

# Empty by default -> do NOT pass --steps, so the runner uses its config
# default (experiments.curriculum_strategy.configs.TOTAL_STEPS, currently 200k,
# matching the learnability budget). Set STEPS only to override (e.g. a smoke run).
STEPS="${STEPS:-}"
# MAX_PARALLEL is the TOTAL number of concurrent training processes. To run
# 3 per GPU, set it to 3 * (number of GPUs). Default 3 = 3 on a single GPU.
MAX_PARALLEL="${MAX_PARALLEL:-3}"
CONDITIONS="${CONDITIONS:-direct forward reverse mixed}"
ALGOS="${ALGOS:-IQL VDN QMIX}"
SEEDS="${SEEDS:-$(seq 0 19)}"   # 20 seeds for a publishable result

# Tolerate comma-separated lists (e.g. SEEDS="0,1,2") in addition to the
# space-separated form the for-loops expect.
CONDITIONS="${CONDITIONS//,/ }"
ALGOS="${ALGOS//,/ }"
SEEDS="${SEEDS//,/ }"

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
echo "GPUs: ${GPU_LIST[*]:-none (CPU)} | MAX_PARALLEL=$MAX_PARALLEL | STEPS=${STEPS:-config default (TOTAL_STEPS)}"

# Pre-flight: SAT-generate the rung pools once if they are not present. The
# guard checks the target rung's held-out eval pool (stage 2 = 5x5/2a/1L).
if [ ! -d "$OUT_DIR/levels/stage_2_5x5_2a_1L_cooperative/eval" ]; then
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
        --condition "$cond" --algo "$algo" --seed "$seed" ${STEPS:+--steps $STEPS} &
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
