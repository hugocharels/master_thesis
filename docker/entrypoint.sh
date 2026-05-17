#!/usr/bin/env bash
# Container entrypoint:
# - put marl's pre-built venv (/opt/marl/.venv) on PATH so `python`
#   resolves to it and finds marl + all its uv-locked deps,
# - set PYTHONPATH so master_thesis modules import directly from the
#   mounted /workspace/master_thesis/src (no install needed),
# - exec the user's command (default: interactive bash).
#
# No runtime pip / uv install: everything is baked into the image at
# build time (see docker/Dockerfile). To refresh marl, rebuild the
# image with `docker build --no-cache`.

set -e

export PATH="/opt/marl/.venv/bin:${PATH}"
export PYTHONPATH="/workspace/master_thesis/src:${PYTHONPATH:-}"
export MARL_VENV="/opt/marl/.venv/bin/python"
export VIRTUAL_ENV="/opt/marl/.venv"

exec "$@"
