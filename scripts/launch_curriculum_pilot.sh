#!/usr/bin/env bash
# Curriculum-transfer PILOT: 4 conditions x QMIX x 4 seeds x 750k steps.
# 16 cells total. Skips runs that already have final_results.json.
#
# Goal: validate that the scheduler advances correctly, that CURR's
# stage progression behaves, and that B1/B2/B3/CURR are roughly
# distinguishable. With 4 seeds the per-condition SE is small enough
# to read the trend (2 seeds is too noisy).

set -e

# Edit if your venv lives elsewhere.
PY="${MARL_VENV:-C:/Users/hugoc/Projects/marl/.venv/Scripts/python.exe}"
export PYTHONPATH=src

OUT_DIR="results/curriculum_experiment"
STEPS=${STEPS:-750000}    # PILOT_RUN_TOTAL_STEPS in configs.py; override via env
MAX_PARALLEL=${MAX_PARALLEL:-4}

# Round-robin across the GPUs exposed via `docker run --gpus device=...`.
# nvidia-smi -L lists only those (renumbered 0..N-1). NUM_GPUS=0 -> no
# env var set -> torch falls back to CPU.
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l || echo 0)

CONDITIONS=(${CONDITIONS:-B1 B2 B3 CURR})
ALGOS=(${ALGOS:-QMIX})
SEEDS=${SEEDS:-$(seq 0 3)} # 4 seeds for the pilot by default; override via env

# Count seeds explicitly (SEEDS may be a space-separated list)
n_seeds=0
for _s in $SEEDS; do n_seeds=$((n_seeds + 1)); done

pids=()
count=0
launched=0
skipped=0
total=$((${#CONDITIONS[@]} * ${#ALGOS[@]} * n_seeds))

for cond in "${CONDITIONS[@]}"; do
  for algo in "${ALGOS[@]}"; do
    for seed in $SEEDS; do
      count=$((count + 1))
      run_dir="$OUT_DIR/runs/${cond}_${algo}_seed${seed}"

      if [ -f "$run_dir/final_results.json" ]; then
        skipped=$((skipped + 1))
        echo "[${count}/${total}] SKIP ${cond}_${algo}_seed${seed}"
        continue
      fi

      gpu_index=""
      [ "$NUM_GPUS" -gt 0 ] && gpu_index=$(( launched % NUM_GPUS ))
      launched=$((launched + 1))

      echo "[${count}/${total}] Launching ${cond}_${algo}_seed${seed} (${STEPS} steps)${gpu_index:+ on cuda:$gpu_index}"
      CUDA_VISIBLE_DEVICES="$gpu_index" "$PY" -m experiments.curriculum.run_experiment \
        --condition "$cond" --algo "$algo" --seed "$seed" --steps "$STEPS" \
        --out-dir "$OUT_DIR" &
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

echo "Pilot done. Skipped ${skipped}, ran $((total - skipped))."
echo "Aggregate with: PYTHONPATH=src \$PY -m experiments.curriculum.plot_results"
