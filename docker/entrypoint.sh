#!/usr/bin/env bash
# Container entrypoint:
# 1. pip-install the mounted source repos in editable mode (so host-side
#    code edits take effect immediately without rebuilding the image),
# 2. set PYTHONPATH so master_thesis modules import,
# 3. exec the user's command (default: interactive bash).

set -e

# Install lle from source if mounted; otherwise from PyPI.
if [ -d /workspace/lle ] && [ -f /workspace/lle/pyproject.toml ]; then
    if ! python -c "import lle" 2>/dev/null; then
        echo "[entrypoint] Building lle from source (mounted) ..."
        cd /workspace/lle && maturin develop --release --quiet && cd -
    fi
else
    if ! python -c "import lle" 2>/dev/null; then
        echo "[entrypoint] Installing lle from PyPI ..."
        pip install --user --quiet laser-learning-environment
    fi
fi

# Install marl from source (must be mounted - not on PyPI).
if [ -d /workspace/marl ] && [ -f /workspace/marl/pyproject.toml ]; then
    if ! python -c "import marl" 2>/dev/null; then
        echo "[entrypoint] Installing marl (editable, mounted) ..."
        pip install --user --quiet -e /workspace/marl
    fi
else
    echo "[entrypoint] WARNING: /workspace/marl not found - mount it as a volume." >&2
fi

# Install master_thesis from source (must be mounted - not on PyPI).
if [ -d /workspace/master_thesis ] && [ -f /workspace/master_thesis/pyproject.toml ]; then
    if ! python -c "import generators" 2>/dev/null; then
        echo "[entrypoint] Installing master_thesis deps ..."
        pip install --user --quiet -e /workspace/master_thesis
    fi
else
    echo "[entrypoint] WARNING: /workspace/master_thesis not found - mount it as a volume." >&2
fi

# Make experiment code importable without explicit installs.
export PYTHONPATH="/workspace/master_thesis/src:${PYTHONPATH:-}"
export MARL_VENV="$(which python)"

exec "$@"
