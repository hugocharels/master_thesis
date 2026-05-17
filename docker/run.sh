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
#     PROJECTS_DIR=/data/hugoc/projects MEM_LIMIT=32g bash docker/run.sh
#     bash docker/run.sh -- bash scripts/launch_curriculum_pilot.sh
#     bash docker/run.sh -- python -m pytest src/tests/

set -e

PROJECTS_DIR="${PROJECTS_DIR:-$HOME/projects}"
MEM_LIMIT="${MEM_LIMIT:-16g}"
SWAP_LIMIT="${SWAP_LIMIT:-20g}"

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

# Use docker (not nvidia-docker) - the trainer is CPU-only, GPU not needed.
docker run --rm -it \
    --memory="$MEM_LIMIT" \
    --memory-swap="$SWAP_LIMIT" \
    -v "$PROJECTS_DIR:/workspace" \
    -w /workspace/master_thesis \
    master_thesis:"$USER" \
    "$@"
