#!/usr/bin/env bash
# Container entrypoint:
# 1. set PYTHONPATH so master_thesis modules import (no pip install
#    needed for the in-repo packages),
# 2. install marl in editable mode if not already present (the only
#    runtime install left; lle + the project deps are baked into the
#    image at build time),
# 3. exec the user's command (default: interactive bash).

set -e

# Make experiment code importable without an explicit master_thesis
# install. Set this first so `import generators` succeeds and the
# rest of the entrypoint can rely on it.
export PYTHONPATH="/workspace/master_thesis/src:${PYTHONPATH:-}"
export MARL_VENV="$(which python)"

# lle is baked into the image (PyPI wheel installed at build time).
# This block only triggers when the user explicitly mounts a source
# checkout at /workspace/lle and the baked wheel was not yet imported
# (e.g., the user is testing a custom lle branch).
if [ -d /workspace/lle ] && [ -f /workspace/lle/pyproject.toml ]; then
    if ! python -c "import lle" 2>/dev/null; then
        echo "[entrypoint] Building lle from source (mounted) ..."
        cd /workspace/lle && maturin develop --release --quiet && cd -
    fi
fi

# marl is not on PyPI - install editable from the mounted source.
# This is the only runtime install left (~5-10 s) because pip's user
# site-packages at /home/$USER/.local is in the container's writable
# layer, which is discarded by `docker run --rm`.
if [ -d /workspace/marl ] && [ -f /workspace/marl/pyproject.toml ]; then
    if ! python -c "import marl" 2>/dev/null; then
        echo "[entrypoint] Installing marl (editable, mounted) ..."
        pip install --user --quiet -e /workspace/marl
    fi
else
    echo "[entrypoint] WARNING: /workspace/marl not found - mount it as a volume." >&2
fi

# master_thesis: importable via PYTHONPATH set above, no pip install.

exec "$@"
