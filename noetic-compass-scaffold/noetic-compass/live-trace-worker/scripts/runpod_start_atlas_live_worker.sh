#!/usr/bin/env bash
set -u

# RunPod repair/start script for the Atlas live worker.
#
# Why this exists:
# - The RunPod template starts /start.sh as PID 1, not systemd.
# - Long-running Python from /workspace can hang if the FUSE mount stalls.
# - The worker should run from /root, while source can still be synced from
#   /workspace on pod boot.
#
# Intended install:
#   cp scripts/runpod_start_atlas_live_worker.sh /root/start-atlas-live-worker.sh
#   chmod +x /root/start-atlas-live-worker.sh
#
# The companion runpod_pre_start.sh calls this script from /pre_start.sh.

PORT="${ATLAS_LIVE_WORKER_PORT:-8080}"
RUN_DIR="${ATLAS_LIVE_RUN_DIR:-/root/atlas-live-worker-run}"
VENV_DIR="${ATLAS_LIVE_VENV_DIR:-/root/atlas-live-worker-venv}"
LOG_FILE="${RUN_DIR}/worker.log"
BOOT_LOG="${RUN_DIR}/boot.log"
SOURCE_DIR="${ATLAS_LIVE_SOURCE_DIR:-/workspace/atlas-live-worker-current}"
FALLBACK_SOURCE_DIR="${ATLAS_LIVE_FALLBACK_SOURCE_DIR:-/workspace/atlas-live-worker-6e688b1}"

mkdir -p "${RUN_DIR}"
touch "${BOOT_LOG}"

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${BOOT_LOG}"
}

realmode_ok() {
  curl -fsS "http://127.0.0.1:${PORT}/health/realmode" 2>/dev/null | grep -q 'REAL_PYTHIA_WEIGHTS_LOADED'
}

if realmode_ok; then
  log "Atlas live worker already healthy on port ${PORT}."
  exit 0
fi

if [ -d "${SOURCE_DIR}/app" ]; then
  log "Syncing worker source from ${SOURCE_DIR} to ${RUN_DIR}."
  rsync -a --delete "${SOURCE_DIR}/app" "${RUN_DIR}/"
  [ -f "${SOURCE_DIR}/requirements.txt" ] && cp "${SOURCE_DIR}/requirements.txt" "${RUN_DIR}/requirements.txt"
elif [ -d "${FALLBACK_SOURCE_DIR}/app" ]; then
  log "Syncing worker source from fallback ${FALLBACK_SOURCE_DIR} to ${RUN_DIR}."
  rsync -a --delete "${FALLBACK_SOURCE_DIR}/app" "${RUN_DIR}/"
  [ -f "${FALLBACK_SOURCE_DIR}/requirements.txt" ] && cp "${FALLBACK_SOURCE_DIR}/requirements.txt" "${RUN_DIR}/requirements.txt"
elif [ -d "${RUN_DIR}/app" ]; then
  log "Using existing worker source in ${RUN_DIR}."
else
  log "ERROR: no Atlas worker source found."
  exit 0
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  log "Creating venv at ${VENV_DIR} with system CUDA/PyTorch packages."
  python3 -m venv --system-site-packages "${VENV_DIR}"
fi

if ! "${VENV_DIR}/bin/python" -c 'import fastapi, uvicorn, torch, transformers' >/dev/null 2>&1; then
  log "Installing live worker requirements."
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >>"${BOOT_LOG}" 2>&1
  "${VENV_DIR}/bin/python" -m pip install -r "${RUN_DIR}/requirements.txt" >>"${BOOT_LOG}" 2>&1
fi

EXISTING_PID="$(ss -ltnp 2>/dev/null | awk -v port=":${PORT}" '$4 ~ port {print $NF}' | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -1)"
if [ -n "${EXISTING_PID}" ]; then
  log "Stopping unhealthy listener PID ${EXISTING_PID} on port ${PORT}."
  kill "${EXISTING_PID}" 2>/dev/null || true
  sleep 2
fi

log "Starting Atlas live worker from ${RUN_DIR} on port ${PORT}; fake mode forced off."
cd "${RUN_DIR}" || exit 0
LIVE_TRACE_USE_FAKE=0 PYTHONUNBUFFERED=1 setsid "${VENV_DIR}/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" >>"${LOG_FILE}" 2>&1 &
WORKER_PID="$!"
log "Started Atlas worker PID ${WORKER_PID}."

for _ in $(seq 1 90); do
  if realmode_ok; then
    log "Atlas live worker verified with REAL_PYTHIA_WEIGHTS_LOADED."
    exit 0
  fi
  sleep 2
done

log "WARNING: Atlas live worker did not verify realmode within 180 seconds. Check ${LOG_FILE}."
tail -80 "${LOG_FILE}" >>"${BOOT_LOG}" 2>/dev/null || true
exit 0
