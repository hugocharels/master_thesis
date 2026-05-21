#!/usr/bin/env bash
# Data-scaling experiment (DIRECT training): fix the task, vary the number of
# TRAINING levels, hold the test set fixed, measure held-out TEST success.
#
# Tests whether more generator-produced levels fixes the overfitting exposed by
# the learnability sweep (train ~0.63 but test ~0.20 on 5x5; test ~0 beyond).
# If test climbs toward train as #levels grows, that is the generator's payoff:
# unlimited diverse solvable levels -> generalization.
#
# Train pools of size 20/100/500 share the same RNG seed, so they are NESTED
# (the 100-pool's first 20 == the 20-pool); the test pool uses a different seed
# and a FIXED size, so it is identical across all conditions -> a clean
# controlled comparison.
#
# Cluster (inside the container):
#   GPU_DEVICES="0,1,2,3,4,5,6,7" MAX_PARALLEL=24 \
#     bash docker/run.sh -- bash scripts/data_scaling_sweep.sh
#
# Knobs (env vars):
#   H W AGENTS L T   the fixed task                 (default 5 5 2 1 10)
#   TRAIN_SIZES      training-pool sizes to sweep   (default "20 100 500")
#   TEST_SIZE        held-out test pool size        (default 50)
#   ALGOS / SEEDS / STEPS / MAX_PARALLEL / GPUS     as in the other launchers

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src

H="${H:-5}"; W="${W:-5}"; AGENTS="${AGENTS:-2}"; L="${L:-1}"; T="${T:-10}"
TEST_SIZE="${TEST_SIZE:-50}"
TRAIN_SIZES="${TRAIN_SIZES:-20 100 500}"
ALGOS="${ALGOS:-IQL VDN QMIX}"
SEEDS="${SEEDS:-0 1 2 3 4}"
STEPS="${STEPS:-300000}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
TRAIN_SIZES="${TRAIN_SIZES//,/ }"; ALGOS="${ALGOS//,/ }"; SEEDS="${SEEDS//,/ }"

if [ -z "${GPUS+x}" ]; then
  _ndet=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)
  GPU_LIST=(); for ((i = 0; i < _ndet; i++)); do GPU_LIST+=("$i"); done
else
  read -ra GPU_LIST <<< "$GPUS"
fi
NGPU=${#GPU_LIST[@]}
echo "task=${H}x${W}/${AGENTS}a/${L}L | TRAIN_SIZES=$TRAIN_SIZES | TEST_SIZE=$TEST_SIZE | STEPS=$STEPS | GPUs=${GPU_LIST[*]:-CPU} | MAX_PARALLEL=$MAX_PARALLEL"

pids=()
launched=0

for N in $TRAIN_SIZES; do
  OUT="results/datascale_${H}x${W}_${AGENTS}a_${L}L_n${N}"
  if [ ! -d "$OUT/levels" ]; then
    "$PY" -m experiments.learnability._preflight \
      --height "$H" --width "$W" --agents "$AGENTS" --lasers "$L" --t-max "$T" \
      --train-pool-size "$N" --test-pool-size "$TEST_SIZE" --out-dir "$OUT"
  fi
  for algo in $ALGOS; do
    for s in $SEEDS; do
      run_dir="$OUT/runs/${algo}_seed${s}"
      if [ -f "$run_dir/final_results.json" ]; then
        echo "SKIP n=$N $algo seed=$s (done)"; continue
      fi
      gpu=""
      [ "$NGPU" -gt 0 ] && gpu=${GPU_LIST[$(( launched % NGPU ))]}
      launched=$((launched + 1))
      echo "Launch n=$N $algo seed=$s${gpu:+ on GPU $gpu}"
      CUDA_VISIBLE_DEVICES="$gpu" "$PY" -m experiments.learnability.run_experiment \
        --algo "$algo" --seed "$s" --height "$H" --width "$W" --agents "$AGENTS" \
        --lasers "$L" --t-max "$T" --steps "$STEPS" --out-dir "$OUT" &
      pids+=($!)
      if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
        wait "${pids[0]}"; pids=("${pids[@]:1}")
      fi
    done
  done
done

for pid in "${pids[@]}"; do wait "$pid"; done
echo "Data-scaling sweep done. Compare success_rate_test across results/datascale_*_n*/runs/*/final_results.json"
