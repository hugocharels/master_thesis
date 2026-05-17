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
# Why python:3.13-slim?
#   marl's pyproject says requires-python = ">=3.12,<4"; 3.13 satisfies.
#   The slim variant keeps the base image small; we add only what we
#   actually need.
FROM python:3.13-slim

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

# Replace the CPU torch wheel pulled by `uv sync` with the CUDA-12.1
# wheel. The cu121 wheel ships its own CUDA runtime libs; only the
# host's NVIDIA driver needs to be exposed via `docker run --gpus ...`.
RUN /opt/marl/.venv/bin/pip install --no-cache-dir --upgrade \
        torch --index-url https://download.pytorch.org/whl/cu121

# Master-thesis-specific deps not in marl's pyproject. matplotlib,
# pytest, ruff, laser-learning-environment are already in marl's venv.
RUN /opt/marl/.venv/bin/pip install --no-cache-dir python-sat ruff

# Make /opt/marl readable (and the .venv binaries executable) by the
# non-root user.
RUN chmod -R a+rX /opt/marl

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
