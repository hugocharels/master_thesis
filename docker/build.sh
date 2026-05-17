#!/usr/bin/env bash
# Build the master_thesis Docker image, tagged with your username and
# stamped with your host UID/GID so files written to mounted volumes
# are owned by you, not by root.
#
# Run this once after cloning the repo. Re-run after editing the
# Dockerfile or entrypoint.sh; you do NOT need to re-run after editing
# Python code, because the source is mounted at runtime.

set -e

cd "$(dirname "$0")"

docker build \
    --build-arg USER_NAME="$USER" \
    --build-arg USER_ID="$(id -u)" \
    --build-arg GROUP_ID="$(id -g)" \
    --build-arg MARL_BRANCH="${MARL_BRANCH:-dev}" \
    -t master_thesis:"$USER" \
    .

echo
echo "Built image: master_thesis:$USER"
echo "Run it with: bash docker/run.sh"
