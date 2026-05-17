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

# Named Docker volume for the in-container user-site
# (/home/$USER/.local). Persisting this across `docker run --rm`
# means the entrypoint's editable `pip install -e /workspace/marl`
# only runs once per host instead of every time. Docker copies the
# image's /home/$USER/.local into the volume on first creation, so
# the baked-in packages (torch, lle, ...) remain visible.
#
# Override with LOCAL_VOLUME=name to use a different volume (e.g. to
# refresh after a Dockerfile rebuild that changed the baked deps:
# `docker volume rm master_thesis_${USER}_userlocal` before running).
LOCAL_VOLUME="${LOCAL_VOLUME:-master_thesis_${USER}_userlocal}"

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
        # docker's --gpus flag accepts a comma-separated device list, but
        # the value must be passed as `"device=0,1,2"` with literal double
        # quotes around the value (the quotes go to docker, NOT consumed
        # by the shell). Using an array preserves the literal quotes when
        # the array is expanded with "${GPU_ARGS[@]}".
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
    -v "$LOCAL_VOLUME:/home/$USER/.local" \
    -v "$PROJECTS_DIR:/workspace" \
    -w /workspace/master_thesis \
    master_thesis:"$USER" \
    "$@"
