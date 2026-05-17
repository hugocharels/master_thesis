# Custom image for the master_thesis experiments.
#
# Why uv and not pip?
#   marl (https://github.com/yamoling/marl) declares git-sourced
#   dependencies (smac, smacv2, pysc2) via [tool.uv.sources] in its
#   pyproject.toml. pip ignores that section and either resolves the
#   wrong package from PyPI (the unrelated "smac" Bayesian-optimisation
#   tool) or no package at all. The result is that marlenv.adapters.SMAC
#   is missing and `from marl import algos` fails at import time. uv
#   honours [tool.uv.sources] and reads uv.lock, so we get the exact
#   dep tree the laptop has.
#
# Why bake marl into the image rather than installing at entrypoint?
#   marl's dep tree is large (fastapi, jupyterlab, neptune, pysc2, smac,
#   torch, ...). Building it inside `docker run --rm` makes every
#   container start cost minutes. Baking it at image build time means
#   the cost is paid once and cached forever in Docker's layer cache.
#
# Why python:3.12-slim and not 3.13?
#   The cluster has GTX 1080 Ti (compute capability sm_61, Pascal).
#   PyTorch dropped Pascal kernels in 2.4+. The last torch release
#   with sm_61 support is 2.3.1, which is only published for Python
#   3.8 - 3.12 (no cp313 wheels). So we pin Python to 3.12. Both
#   marl (requires-python = ">=3.12,<4") and master_thesis are
#   compatible with 3.12.
FROM python:3.12-slim

ARG USER_NAME=user
ARG USER_ID=1000
ARG GROUP_ID=1000

# Pin marl to a specific branch so the build is reproducible. Override
# with `docker build --build-arg MARL_BRANCH=...` or `--no-cache` to
# refresh.
ARG MARL_BRANCH=dev

# System packages:
#   git, curl, ca-certificates  - cloning, downloads
#   build-essential, pkg-config, libssl-dev  - native ext builds (sumtree, etc.)
#   tmux, procps, less          - shell ergonomics inside an interactive container
#   libsdl2-*, libxcb1, libgl1, libegl1, libx11-6, libxext6, libxrender1, libsm6,
#   libice6, libxkbcommon0      - LLE links against SDL2 at import time (even when
#                                 not rendering), which transitively requires X11
#                                 client libs; matplotlib's Agg backend doesn't
#                                 need these but `import lle` does.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates \
        build-essential pkg-config libssl-dev \
        tmux procps less \
        libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-ttf-2.0-0 \
        libxcb1 libx11-6 libxext6 libxrender1 libsm6 libice6 \
        libxkbcommon0 libgl1 libegl1 \
    && rm -rf /var/lib/apt/lists/*

# Create the non-root user matching the host's UID/GID. The conditional
# groupadd / useradd lets us reuse a UID/GID that already exists in the
# base image (e.g. UID 1000 maps to an existing default user on some
# bases).
RUN groupadd -g ${GROUP_ID} ${USER_NAME} 2>/dev/null || true \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash ${USER_NAME} 2>/dev/null || true

# Install uv system-wide.
RUN pip install --no-cache-dir uv

# Clone marl from yamoling/marl@${MARL_BRANCH} and create the project
# venv at /opt/marl/.venv. uv resolves the dep tree from marl's
# pyproject.toml (no --frozen because yamoling/marl does not commit
# uv.lock to the repo). `--extra modern-gpu` pulls the modern PyTorch
# dep group; the resulting torch is the CPU wheel from PyPI, which we
# override with the CUDA wheel in the next layer.
RUN git clone --branch ${MARL_BRANCH} https://github.com/yamoling/marl.git /opt/marl \
    && cd /opt/marl && uv sync --extra modern-gpu

# Replace the CPU torch wheel pulled by `uv sync` with a CUDA-enabled
# wheel that includes Pascal (sm_61) kernels. The ULB workstation
# has GTX 1080 Ti cards (compute capability 6.1); PyTorch 2.4+ cu121
# wheels are built only for sm_75 and newer and would fail at runtime
# with `CUDA error: no kernel image is available for execution on the
# device`. Torch 2.3.1 with the cu118 wheel still ships sm_61
# kernels and runs on the cluster's driver 580 (driver supports any
# CUDA <=13).
#
# `uv pip` is used because uv-created venvs do not ship a `pip`
# binary by default.
RUN uv pip install --no-cache-dir --python /opt/marl/.venv/bin/python \
        --reinstall --index-url https://download.pytorch.org/whl/cu118 \
        "torch==2.3.1"

# Master-thesis-specific deps not in marl's pyproject. matplotlib,
# pytest, ruff, laser-learning-environment are already in marl's venv.
RUN uv pip install --no-cache-dir --python /opt/marl/.venv/bin/python \
        python-sat ruff

# /opt/marl is owned by root (since the build runs as root) but the
# default umask (022) makes its files world-readable and dirs world-
# traversable, so the non-root user at runtime can use the venv.
# We do NOT `chmod -R` here: chmod on overlayfs triggers a copy-up
# per inode, which for a multi-GB venv with 100K+ files takes 15+
# minutes even when no permission bits change.

# Mount point for the host's projects directory. docker/run.sh mounts
# ~/projects here so /workspace/master_thesis appears inside.
USER ${USER_NAME}
WORKDIR /workspace

# Copy the entrypoint to a user-agnostic system path (ENTRYPOINT in
# exec-form does not expand ${USER_NAME}).
USER root
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER ${USER_NAME}

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
