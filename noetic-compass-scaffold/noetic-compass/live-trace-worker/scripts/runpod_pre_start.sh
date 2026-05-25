#!/usr/bin/env bash
set +e

# RunPod's /start.sh executes /pre_start.sh if it exists. This wrapper is
# intentionally non-fatal: a worker boot failure must not take SSH access down
# with the container. The health endpoints and API proof route are responsible
# for refusing to claim LIVE real weights when the worker is unavailable.

if [ ! -x /root/start-atlas-live-worker.sh ] && [ -f /workspace/start-atlas-live-worker.sh ]; then
  cp /workspace/start-atlas-live-worker.sh /root/start-atlas-live-worker.sh
  chmod +x /root/start-atlas-live-worker.sh
fi

if [ -x /root/start-atlas-live-worker.sh ]; then
  /root/start-atlas-live-worker.sh
else
  echo "Atlas live worker startup script missing; leaving pod online for SSH repair."
fi

exit 0
