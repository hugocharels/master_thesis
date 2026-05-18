#!/usr/bin/env bash
# Launch an interactive container with $PROJECTS_DIR mounted at
# /workspace. Defaults to ~/projects so a layout like:
#
#     ~/projects/marl/
#     ~/projects/master_thesis/
#     ~/projects/lle/             (optional - PyPI install is fine)
#
# becomes visible inside the container as /workspace/{marl,master_thesis,lle}.
#
# Override the defaults via env vars before invocation:
#
#     GPU_DEVICES=5 bash docker/run.sh -- bash scripts/launch_learnability.sh
#     PROJECTS_DIR=/data/hugoc/projects MEM_LIMIT=32g bash docker/run.sh
#     bash docker/run.sh -- python -m pytest src/tests/

set -e

PROJECTS_DIR="${PROJECTS_DIR:-$HOME/projects}"
MEM_LIMIT="${MEM_LIMIT:-16g}"
SWAP_LIMIT="${SWAP_LIMIT:-20g}"

# GPU passthrough. The ULB workstation has 8 GPUs and a per-user
# allocation table (see workstation guide); claiming all GPUs without
# coordination is explicitly discouraged. This script therefore
# REQUIRES the GPU_DEVICES env var on hosts with an NVIDIA driver.
# Accepted values:
#     GPU_DEVICES=5         expose only physical GPU 5
#     GPU_DEVICES=5,6       expose GPUs 5 and 6
#     GPU_DEVICES=all       expose every GPU (discouraged; emergency only)
#     GPU_DEVICES=none      force CPU mode even though a GPU is present
GPU_ARGS=()
if [ -f /proc/driver/nvidia/version ] || [ -e /dev/nvidia0 ]; then
    if [ -z "${GPU_DEVICES:-}" ]; then
        echo "ERROR: an NVIDIA driver is present but GPU_DEVICES is unset." >&2
        echo >&2
        echo "Pick a GPU first. Run 'nvidia-smi' to see which GPUs are free," >&2
        echo "then invoke this script with an explicit assignment:" >&2
        echo "    GPU_DEVICES=5 bash docker/run.sh -- ..." >&2
        echo "    GPU_DEVICES=2,4,7 bash docker/run.sh -- ..." >&2
        echo "Use GPU_DEVICES=none to force CPU mode." >&2
        exit 1
    elif [ "$GPU_DEVICES" = "all" ]; then
        GPU_ARGS=(--gpus all)
    elif [ "$GPU_DEVICES" = "none" ]; then
        GPU_ARGS=()
    else
        # docker's --gpus flag needs the comma-separated device list
        # wrapped in literal double quotes that survive the shell and
        # reach docker as part of the argument value. Without them
        # docker's option parser splits on commas and treats each token
        # as a separate option, producing:
        #   Error: cannot set both Count and DeviceIDs on device request
        # Using a bash array preserves the literal quotes through
        # "${GPU_ARGS[@]}" expansion.
        GPU_ARGS=(--gpus "\"device=$GPU_DEVICES\"")
    fi
fi

if [ ! -d "$PROJECTS_DIR" ]; then
    echo "ERROR: PROJECTS_DIR=$PROJECTS_DIR does not exist." >&2
    echo "Clone the repos first, e.g.:" >&2
    echo "    mkdir -p $PROJECTS_DIR" >&2
    echo "    git clone https://github.com/yamoling/marl.git $PROJECTS_DIR/marl" >&2
    echo "    git clone https://github.com/hugocharels/master_thesis.git $PROJECTS_DIR/master_thesis" >&2
    exit 1
fi

# Drop the literal "--" separator that lets users pass commands without
# them being parsed as run.sh's own flags.
if [ "${1:-}" = "--" ]; then
    shift
fi

# GPU passthrough is enabled when /proc/driver/nvidia/version exists.
# The trainer uses cuda when torch.cuda.is_available(), CPU otherwise.
docker run --rm -it \
    "${GPU_ARGS[@]}" \
    --memory="$MEM_LIMIT" \
    --memory-swap="$SWAP_LIMIT" \
    -v "$PROJECTS_DIR:/workspace" \
    -w /workspace/master_thesis \
    master_thesis:"$USER" \
    "$@"
