#!/usr/bin/env bash
# Learnability difficulty sweep (DIRECT training only) to characterise, per
# level setting:
#   - steps-to-learn / plateau height (the ceiling), from the eval curves;
#   - whether a reward-shaping step_penalty unlocks settings that otherwise
#     get zero learning signal (flat 0).
#
# It trains the learnability runner across a grid of (size, lasers) settings,
# each with and without step_penalty, and writes per-setting eval curves +
# final_results.json. No curriculum here -- this is the diagnostic that grounds
# the curriculum design.
#
# On the ULB cluster, run INSIDE the container (docker/run.sh picks the GPUs):
#   GPU_DEVICES="0,1,2,3,4,5,6,7" MAX_PARALLEL=24 \
#     bash docker/run.sh -- bash scripts/learnability_sweep.sh
#
# Knobs (env vars):
#   CONFIGS      pipe-separated "H W L T_MAX" tokens (grid, lasers, horizon)
#   PENALTIES    space/comma list of step_penalty values   (default "0.0 0.02")
#   SEEDS        space/comma list of seeds                  (default "0 1")
#   ALGO         single algo                                (default VDN)
#   AGENTS       agent count for every setting              (default 2)
#   STEPS        env-steps per run                          (default 400000)
#   MAX_PARALLEL total concurrent runs (3 x #GPUs)          (default 3)
#   GPUS         physical GPU ids (direct mode); unset = auto-detect exposed

set -e

PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src

STEPS="${STEPS:-400000}"
ALGO="${ALGO:-VDN}"
AGENTS="${AGENTS:-2}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
CONFIGS="${CONFIGS:-5 5 1 10|6 6 1 12|7 7 1 14|6 6 2 12|7 7 2 14|8 8 2 16}"
PENALTIES="${PENALTIES:-0.0 0.02}"
SEEDS="${SEEDS:-0 1}"
PENALTIES="${PENALTIES//,/ }"
SEEDS="${SEEDS//,/ }"

# GPU list to round-robin across (same convention as the curriculum launcher).
if [ -z "${GPUS+x}" ]; then
  _ndet=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)
  GPU_LIST=()
  for ((i = 0; i < _ndet; i++)); do GPU_LIST+=("$i"); done
else
  read -ra GPU_LIST <<< "$GPUS"
fi
NGPU=${#GPU_LIST[@]}
echo "GPUs: ${GPU_LIST[*]:-none (CPU)} | MAX_PARALLEL=$MAX_PARALLEL | STEPS=$STEPS | ALGO=$ALGO | AGENTS=$AGENTS"

pids=()
launched=0
IFS='|' read -ra CFG_ARR <<< "$CONFIGS"

for cfg in "${CFG_ARR[@]}"; do
  set -- $cfg; H=$1; W=$2; L=$3; T=$4
  for SP in $PENALTIES; do
    OUT="results/sweep_${H}x${W}_${AGENTS}a_${L}L_sp${SP}"
    # Generate the pool once per (setting, penalty) output dir if missing.
    if [ ! -d "$OUT/levels" ]; then
      "$PY" -m experiments.learnability._preflight \
        --height "$H" --width "$W" --agents "$AGENTS" --lasers "$L" --t-max "$T" --out-dir "$OUT"
    fi
    for s in $SEEDS; do
      run_dir="$OUT/runs/${ALGO}_seed${s}"
      if [ -f "$run_dir/final_results.json" ]; then
        echo "SKIP ${H}x${W}/${AGENTS}a/${L}L sp=$SP seed=$s (done)"
        continue
      fi
      gpu=""
      [ "$NGPU" -gt 0 ] && gpu=${GPU_LIST[$(( launched % NGPU ))]}
      launched=$((launched + 1))
      echo "Launch ${H}x${W}/${AGENTS}a/${L}L sp=$SP seed=$s${gpu:+ on GPU $gpu}"
      CUDA_VISIBLE_DEVICES="$gpu" "$PY" -m experiments.learnability.run_experiment \
        --algo "$ALGO" --seed "$s" --height "$H" --width "$W" --agents "$AGENTS" \
        --lasers "$L" --t-max "$T" --steps "$STEPS" --step-penalty "$SP" --out-dir "$OUT" &
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
echo "Sweep done. Curves in results/sweep_*/runs/${ALGO}_seed*/{train,test}_eval.csv"
