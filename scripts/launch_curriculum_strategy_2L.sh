#!/usr/bin/env bash
# Launch the 2-laser curriculum-strategy comparison: CONDITIONS x ALGOS x SEEDS,
# every cell trained for the SAME total env-step budget (STEPS). Only the
# allocation across the fixed-grid 0L->1L->2L ladder differs by condition.
#
# This is the "where direct fails" experiment: the target is the 6x6 / 2-agent /
# 2-laser fully_coupled (mutual) level, on which Phase 0 showed direct reaches a
# nonzero train but ~0 held-out success. Headline = forward vs direct on the
# held-out target (final success OR sample-efficiency).
#
# Sibling of launch_curriculum_strategy.sh; same knobs and docker workflow.
#
# Examples (cluster, via docker):
#   # Pilot: VDN x 4 conditions x 1 seed on physical GPU 2:
#   GPU_DEVICES=2 MAX_PARALLEL=4 ALGOS="VDN" SEEDS="0" \
#     bash docker/run.sh -- bash scripts/launch_curriculum_strategy_2L.sh
#
#   # Full sweep on GPU 2, 3 concurrent:
#   GPU_DEVICES=2 MAX_PARALLEL=3 \
#     bash docker/run.sh -- bash scripts/launch_curriculum_strategy_2L.sh
#
# Examples (direct, no docker -- e.g. local Windows):
#   ALGOS="VDN" SEEDS="0" bash scripts/launch_curriculum_strategy_2L.sh
#
# Knobs (all optional env vars):
#   GPU_DEVICES   (docker/run.sh) physical GPU(s) for the container, e.g. 2 or 2,4.
#   GPUS          (this script, direct mode) physical GPU ids, space-separated.
#                 Unset = auto-detect all exposed. "" = CPU.
#   MAX_PARALLEL  TOTAL concurrent training processes (3 per GPU is a good rule).
#   CONDITIONS / ALGOS / SEEDS / STEPS   the sweep dimensions and budget.
#   MARL_VENV     python interpreter (same convention as the other launch_*.sh).

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src
OUT_DIR="results/curriculum_strategy_2L"

# Empty by default -> do NOT pass --steps, so the runner uses its config default
# (experiments.curriculum_strategy_2L.configs.TOTAL_STEPS, currently 600k).
STEPS="${STEPS:-}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
CONDITIONS="${CONDITIONS:-direct forward reverse mixed}"
ALGOS="${ALGOS:-IQL VDN QMIX}"
SEEDS="${SEEDS:-$(seq 0 19)}"   # 20 seeds for a publishable result

# Tolerate comma-separated lists in addition to the space-separated form.
CONDITIONS="${CONDITIONS//,/ }"
ALGOS="${ALGOS//,/ }"
SEEDS="${SEEDS//,/ }"

# Build the list of physical GPU ids to round-robin training across.
if [ -z "${GPUS+x}" ]; then
  _ndet=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)
  GPU_LIST=()
  for ((i = 0; i < _ndet; i++)); do GPU_LIST+=("$i"); done
else
  read -ra GPU_LIST <<< "$GPUS"
fi
NGPU=${#GPU_LIST[@]}
echo "GPUs: ${GPU_LIST[*]:-none (CPU)} | MAX_PARALLEL=$MAX_PARALLEL | STEPS=${STEPS:-config default (TOTAL_STEPS)}"

# Pre-flight: SAT-generate the rung pools once if they are not present. The guard
# checks the target rung's held-out eval pool (stage 3 = 6x6/2a/2L cooperative).
if [ ! -d "$OUT_DIR/levels/stage_3_6x6_2a_2L_cooperative/eval" ]; then
  echo "Generating rung pools (one-off pre-flight)..."
  "$PY" -m experiments.curriculum_strategy_2L._preflight
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
      CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.curriculum_strategy_2L.run_experiment \
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

echo "Done. Skipped ${skipped}, ran $((total - skipped))."
echo "Now: python -m experiments.curriculum_strategy_2L.plot_results"
