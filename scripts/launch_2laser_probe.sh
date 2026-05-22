#!/usr/bin/env bash
# Phase-0 frontier probe for the 2-laser curriculum experiment.
#
# Question: can `direct` (from-scratch) value-decomposition MARL reach a
# NONZERO success rate on the 6x6 / 2-agent / 2-laser *fully_coupled*
# cooperative target at all? If yes, a curriculum has a signal to amplify
# (proceed to the full strategy sweep); if it is flat 0, it is a wall and we
# apply the rescue knobs (STEP_PENALTY, smaller grid) before spending more.
#
# This reuses the learnability trainer (train-from-scratch == `direct`) and
# sweeps ALGOS x SEEDS at a matched budget. Already-finished cells
# (final_results.json present) are skipped, so re-running resumes a sweep.
#
# The certified level pool is committed under
# results/learnability_6x6_2L/levels/; if it is missing this script
# regenerates it (one-off pre-flight).
#
# Examples (cluster, via docker -- the usual case):
#   # 3 algos x 3 seeds on physical GPU 2, 3 concurrent:
#   GPU_DEVICES=2 MAX_PARALLEL=3 bash docker/run.sh -- bash scripts/launch_2laser_probe.sh
#
#   # Just VDN, 5 seeds, with the per-step reward shaping rescue knob:
#   GPU_DEVICES=2 ALGOS="VDN" SEEDS="0 1 2 3 4" STEP_PENALTY=0.02 \
#     bash docker/run.sh -- bash scripts/launch_2laser_probe.sh
#
# Examples (direct, no docker -- e.g. local Windows):
#   ALGOS="VDN" SEEDS="0" bash scripts/launch_2laser_probe.sh
#
# Knobs (all optional env vars):
#   GPU_DEVICES   (docker/run.sh) physical GPU(s) for the container, e.g. 2 or 2,4.
#   GPUS          (this script, direct mode) physical GPU ids, space-separated.
#                 Unset = auto-detect all exposed. "" = CPU.
#   MAX_PARALLEL  TOTAL concurrent training processes (3 per GPU is a good rule).
#   ALGOS / SEEDS / STEPS   sweep dimensions and per-cell budget.
#   STEP_PENALTY  per-step reward penalty (default 0.0). Set ~0.02 to restore a
#                 learnable gradient if the sparse 2-laser exit reward is never hit.
#   HEIGHT/WIDTH/AGENTS/LASERS/TMAX/PROFILE   target geometry (defaults below).
#                 To probe a smaller target: HEIGHT=5 WIDTH=5 TMAX=14.
#   MARL_VENV     python interpreter (same convention as the other launch_*.sh).

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src

# --- Target config (the fully_coupled 2-laser frontier) ---
HEIGHT="${HEIGHT:-6}"
WIDTH="${WIDTH:-6}"
AGENTS="${AGENTS:-2}"
LASERS="${LASERS:-2}"
TMAX="${TMAX:-18}"
GENERATOR="${GENERATOR:-cooperative}"
PROFILE="${PROFILE:-fully_coupled}"
OUT_DIR="${OUT_DIR:-results/learnability_${HEIGHT}x${WIDTH}_${LASERS}L}"
TRAIN_POOL="${TRAIN_POOL:-20}"
TEST_POOL="${TEST_POOL:-20}"

# --- Sweep / budget ---
STEPS="${STEPS:-600000}"
STEP_PENALTY="${STEP_PENALTY:-0.0}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
ALGOS="${ALGOS:-IQL VDN QMIX}"
SEEDS="${SEEDS:-0 1 2}"

# Tolerate comma-separated lists in addition to space-separated.
ALGOS="${ALGOS//,/ }"
SEEDS="${SEEDS//,/ }"

# --- Build the GPU round-robin list (same pattern as the other launchers) ---
if [ -z "${GPUS+x}" ]; then
  _ndet=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)
  GPU_LIST=()
  for ((i = 0; i < _ndet; i++)); do GPU_LIST+=("$i"); done
else
  read -ra GPU_LIST <<< "$GPUS"
fi
NGPU=${#GPU_LIST[@]}
echo "Target: ${HEIGHT}x${WIDTH}/${AGENTS}a/${LASERS}L ${PROFILE} | OUT_DIR=$OUT_DIR"
echo "GPUs: ${GPU_LIST[*]:-none (CPU)} | MAX_PARALLEL=$MAX_PARALLEL | STEPS=$STEPS | STEP_PENALTY=$STEP_PENALTY"

# --- Pre-flight: SAT-generate the pool once if it is not present ---
POOL_TRAIN_DIR="$OUT_DIR/levels/${HEIGHT}x${WIDTH}_${AGENTS}a_${LASERS}L_${GENERATOR}/train"
if [ ! -d "$POOL_TRAIN_DIR" ]; then
  echo "Generating ${PROFILE} pool (one-off pre-flight)..."
  "$PY" -m experiments.learnability._preflight \
    --height "$HEIGHT" --width "$WIDTH" --agents "$AGENTS" --lasers "$LASERS" \
    --t-max "$TMAX" --generator "$GENERATOR" --profile "$PROFILE" \
    --train-pool-size "$TRAIN_POOL" --test-pool-size "$TEST_POOL" \
    --out-dir "$OUT_DIR"
fi

pids=()
count=0
launched=0
skipped=0
total=$(( $(echo $ALGOS | wc -w) * $(echo $SEEDS | wc -w) ))

for algo in $ALGOS; do
  for seed in $SEEDS; do
    count=$((count + 1))
    run_dir="$OUT_DIR/runs/${algo}_seed${seed}"

    if [ -f "$run_dir/final_results.json" ]; then
      skipped=$((skipped + 1))
      echo "[${count}/${total}] SKIP ${algo}_seed${seed} (already done)"
      continue
    fi

    gpu_index=""
    [ "$NGPU" -gt 0 ] && gpu_index=${GPU_LIST[$(( launched % NGPU ))]}
    launched=$((launched + 1))

    echo "[${count}/${total}] Launching ${algo}_seed${seed}${gpu_index:+ on physical GPU $gpu_index}"
    CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.learnability.run_experiment \
      --algo "$algo" --seed "$seed" --steps "$STEPS" \
      --height "$HEIGHT" --width "$WIDTH" --agents "$AGENTS" --lasers "$LASERS" \
      --t-max "$TMAX" --out-dir "$OUT_DIR" --step-penalty "$STEP_PENALTY" &
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
echo "Inspect: ${OUT_DIR}/runs/*/final_results.json  (watch success_rate_train > 0)"
