# Atlas live-trace worker — real Pythia-160M on a RunPod GPU.
#
# The final OS and Python sources are independently digest-pinned. The complete
# CUDA 12.6 Torch closure is installed from the hash-bound unified lock, so the
# image does not inherit the current PyTorch base's vulnerable build toolchain
# or the NVIDIA cuDNN base's mismatched duplicate GPU libraries.
#
# This candidate bakes the HF + FastAPI stack, pre-pulls pythia-160m, and
# serves app.main:app on ${PORT:-8080}. Its production profile refuses to
# start without CUDA, the worker token, and a read-only root filesystem.
# Demo behavior remains available only through explicit LIVE_TRACE_DEMO_MODE=1
# outside that production profile. Gate 5 remains OPEN / HELD.

FROM python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af AS python-runtime

FROM ubuntu:24.04@sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467

LABEL org.opencontainers.image.title="atlas-live-trace-worker" \
      org.opencontainers.image.description="Private FastAPI worker: Pythia-160M + probe pipeline, SSE trace stream, behind the noetic-compass-api proxy." \
      org.opencontainers.image.source="https://github.com/LittleHenderson/noetic-compass" \
      org.opencontainers.image.base.name="ubuntu:24.04" \
      org.opencontainers.image.base.digest="sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467" \
      org.opencontainers.image.python.digest="sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af" \
      org.opencontainers.image.ubuntu.snapshot="20260805T000000Z" \
      org.opencontainers.image.run.readonly-rootfs="required" \
      org.opencontainers.image.run.tmpfs="/tmp:rw,noexec,nosuid,nodev,size=64m" \
      org.opencontainers.image.run.auth="ATLAS_LIVE_WORKER_TOKEN required"

# Bootstrap the timestamp-pinned Ubuntu snapshot with the CA bundle from the
# immutable Python stage, then install only Python's shared runtime libraries.
# Package dependency selection is frozen by the snapshot timestamp.
COPY --from=python-runtime /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
RUN sed -i \
      's|http://archive.ubuntu.com/ubuntu/|https://snapshot.ubuntu.com/ubuntu/20260805T000000Z/|; s|http://security.ubuntu.com/ubuntu/|https://snapshot.ubuntu.com/ubuntu/20260805T000000Z/|' \
      /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates=20260601~24.04.1 \
      libreadline8t64=8.2-4build1 \
      libsqlite3-0=3.45.1-1ubuntu2.7 \
      netbase=6.4 \
      tzdata=2026c-0ubuntu0.24.04.1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=python-runtime /usr/local /usr/local

# The official Python stage includes optional native extensions whose Debian
# libraries are intentionally absent from the smaller Ubuntu runtime. These
# features are not used by the worker, so remove the three extensions rather
# than retain unresolved shared objects or add an unrelated GUI/NIS surface.
RUN rm -f \
      /usr/local/lib/python3.12/lib-dynload/_gdbm*.so \
      /usr/local/lib/python3.12/lib-dynload/_tkinter*.so \
      /usr/local/lib/python3.12/lib-dynload/nis*.so \
    && missing="$(find /usr/local/lib/python3.12/lib-dynload -type f -name '*.so' \
      -exec ldd '{}' \; 2>/dev/null | grep 'not found' || true)" \
    && test -z "$missing" \
    && python -c "import bz2,ctypes,lzma,readline,sqlite3,ssl"

WORKDIR /worker

# Pin the Hugging Face cache to the image-owned location. The production
# loader rejects HF_HOME redirection and a writable cache; a separate mutable
# network-volume cache is not admitted by this candidate.
ENV HF_HOME=/worker/.cache/huggingface \
    PYTHIA_160M_REVISION=50f5173d932e8e61f858120bcb800b97af589f46 \
    ATLAS_WORKER_PROFILE=production \
    ATLAS_WORKER_REQUIRE_READ_ONLY_ROOTFS=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install the flattened, hash-bound Python 3.12 application/Torch/CUDA lock
# without dependency traversal. The direct cu126 wheel URL and every transitive
# wheel hash are checked before the environment contract is verified.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --require-hashes \
      --only-binary=:all: --no-deps -r requirements.txt \
    && python -m pip check

# No package installer is needed by the serving process. Remove pip plus the
# standard library's bundled ensurepip bootstrap wheel after dependency checks.
RUN python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.12/ensurepip \
    && test ! -e /usr/local/bin/pip \
    && test ! -e /usr/local/bin/pip3 \
    && python -c "import importlib.util; assert importlib.util.find_spec('ensurepip') is None"

# The admitted worker is a single-GPU eager-attention service. Remove optional
# cluster/RDMA transport plugins whose MPI, UCX, PMIx, libfabric, or InfiniBand
# hosts are outside that boundary instead of shipping unresolved native code.
RUN rm -f \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_bootstrap_mpi.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_bootstrap_pmix.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_bootstrap_shmem.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_transport_ibgda.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_transport_ibdevx.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_transport_libfabric.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/nvshmem/lib/nvshmem_transport_ucx.so.3 \
      /usr/local/lib/python3.12/site-packages/nvidia/cufile/lib/libcufile_rdma.so.1

COPY app ./app

# Acquisition is the only online model step. Hash verification occurs before
# Transformers parses the files. After the offline CPU canary, freeze all code,
# lock, and model-cache bytes as root-owned read-only content, then drop root.
# This is still not a hosted-GPU receipt or Gate 5 closure.
RUN groupadd --gid 10001 atlas-worker \
    && useradd --uid 10001 --gid 10001 --no-create-home \
      --shell /usr/sbin/nologin atlas-worker
RUN python -m app.runtime.container_preflight --scope fetch
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1
RUN python -m app.runtime.container_preflight --scope all
RUN chown -R 0:0 /worker \
    && find /worker -type d -exec chmod 0555 '{}' + \
    && find /worker -type f -exec chmod 0444 '{}' +
ARG SOURCE_COMMIT=UNBOUND
RUN test "${#SOURCE_COMMIT}" -eq 40 \
    && case "$SOURCE_COMMIT" in *[!0-9a-f]*) exit 1 ;; *) exit 0 ;; esac
LABEL org.opencontainers.image.revision="${SOURCE_COMMIT}" \
      org.opencontainers.image.version="gate5-candidate-v0.2"
USER 10001:10001
RUN test ! -w /worker/app \
    && test ! -w /worker/requirements.txt \
    && test ! -w /worker/.cache/huggingface

# Document the served port for the RunPod HTTP proxy / reverse proxies.
EXPOSE 8080

# Liveness is deliberately minimal and unauthenticated. Production readiness
# is established by fail-closed startup plus the authenticated /health/realmode
# proof surface; a failed model/CUDA load exits instead of serving demo data.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,urllib.request,sys; \
  url='http://127.0.0.1:%s/health' % os.environ.get('PORT','8080'); \
  sys.exit(0 if urllib.request.urlopen(url, timeout=4).status==200 else 1)" || exit 1

# Single uvicorn worker — concurrency comes from async event streams, not OS
# processes. Two workers on the same GPU would race for forward hooks.
# ${PORT:-8080} so an empty/unset PORT still binds the canonical default.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
