# Custom image for the master_thesis experiments.
#
# Why not the official ULB gpu_ubuntu1804:base?
#   It's Python 3.6 + TF 2.3 + CUDA 10.1, much too old for our stack
#   (Python 3.13 + PyTorch). We build on python:3.13-slim and rely on
#   the CUDA-enabled PyTorch wheel (cu121), which ships its own CUDA
#   runtime libraries; only the NVIDIA driver needs to be on the host
#   and exposed to the container via `docker run --gpus all`.
#
# The build follows the ULB pattern (per the GPU workstation guide):
#   - build args for your username / UID / GID so files written into
#     mounted volumes are owned by you, not by root;
#   - non-root container user;
#   - shared-volume mount point at /workspace.
FROM python:3.13-slim

ARG USER_NAME=user
ARG USER_ID=1000
ARG GROUP_ID=1000

# System packages:
#   git, curl, ca-certificates  - cloning, downloads
#   build-essential, pkg-config, libssl-dev  - Rust ext build (lle from source)
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

USER ${USER_NAME}
WORKDIR /home/${USER_NAME}

# Rust toolchain for compiling the lle C/Rust extension on the
# (likely) chance that no Linux wheel is published for Python 3.13.
# Installed in the user's home so it persists with the image without
# needing root.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/home/${USER_NAME}/.cargo/bin:/home/${USER_NAME}/.local/bin:${PATH}"

# Baseline Python deps that we want baked into the image so each
# `docker run` is fast. Heavy ones (laser-learning-environment via PyPI)
# come pre-installed; project-specific editable installs happen at
# entrypoint time on the mounted source.
RUN pip install --no-cache-dir --user --upgrade pip wheel setuptools maturin

# Install CUDA-enabled PyTorch (cu121 wheel). The wheel bundles its own
# CUDA runtime libs, so the image does not need a CUDA toolkit installed
# system-wide. At runtime, `docker run --gpus all` exposes the host's
# NVIDIA driver to the container and torch.cuda.is_available() returns
# True. Installed up front so the entrypoint's `pip install -e marl`
# finds torch already present and does not pull the CPU wheel.
RUN pip install --no-cache-dir --user \
        torch --index-url https://download.pytorch.org/whl/cu121

# Mount point for the host's projects directory. The runtime command
# (see docker/run.sh) mounts ~/projects here, so /workspace/master_thesis
# and /workspace/marl appear inside.
WORKDIR /workspace

# Entrypoint pip-installs the mounted source repos in editable mode then
# execs whatever command the user passed (default: interactive bash).
# Copied to a user-agnostic system path because ENTRYPOINT in exec-form
# does not expand ${USER_NAME}.
USER root
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER ${USER_NAME}

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
