# Custom image for the master_thesis experiments.
#
# Why not the official ULB gpu_ubuntu1804:base?
#   It's Python 3.6 + TF 2.3 + CUDA 10.1, much too old for our stack
#   (Python 3.13 + PyTorch). Since our trainer is CPU-only
#   (`torch.device("cpu")` is hardcoded in run_experiment.py), we don't
#   need CUDA, so we build on a slim Python 3.13 base instead.
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
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates \
        build-essential pkg-config libssl-dev \
        tmux procps less \
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
# `docker run` is fast. Heavy ones (laser-learning-environment, torch via
# marl) come pre-installed; project-specific editable installs happen at
# entrypoint time on the mounted source.
RUN pip install --no-cache-dir --user --upgrade pip wheel setuptools maturin

# Mount point for the host's projects directory. The runtime command
# (see docker/run.sh) mounts ~/projects here, so /workspace/master_thesis
# and /workspace/marl appear inside.
WORKDIR /workspace

# Entrypoint pip-installs the mounted source repos in editable mode then
# execs whatever command the user passed (default: interactive bash).
COPY --chown=${USER_NAME}:${USER_NAME} entrypoint.sh /home/${USER_NAME}/entrypoint.sh
RUN chmod +x /home/${USER_NAME}/entrypoint.sh

ENTRYPOINT ["/home/user/entrypoint.sh"]
CMD ["bash"]
