# Gate 1B execution container -- FROZEN RECIPE (GATE 1A.2 section 4).
# The image is NOT built in Gate 1A.2 (no container build is authorized); the
# CONTAINER_PREP approval authorizes the build, and the resolved image digest +
# pip-freeze digest are then bound into the EXECUTION approval. No job body is
# inserted at build time: the campaign driver committed in this repository IS
# the only entry point.
FROM python:3.11-slim

# REQUIRED for torch.use_deterministic_algorithms(True) with cuBLAS GEMMs on
# CUDA >= 10.2 (audit fix): must be set in the ENVIRONMENT before the process
# starts, else the first CUDA matmul raises. Deterministic training depends on it.
ENV CUBLAS_WORKSPACE_CONFIG=:4096:8

# system deps: git for commit verification on-instance
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /campaign
COPY infra/requirements.lock /campaign/requirements.lock
RUN pip install --no-cache-dir -r /campaign/requirements.lock \
    && pip freeze > /campaign/PIP_FREEZE_RESOLVED.txt

# the repository is cloned by bootstrap.sh at the exact approved commit and
# verified (commit, manifests, byte tests) BEFORE anything else runs
COPY infra/bootstrap.sh /campaign/bootstrap.sh
RUN chmod +x /campaign/bootstrap.sh

ENTRYPOINT ["/campaign/bootstrap.sh"]
