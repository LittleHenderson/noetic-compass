#!/usr/bin/env bash
# Open the SSH tunnel the API uses to reach the private Atlas live-trace worker.
#
# The Pythia-160M worker stays private on the GPU pod (only port 22 is exposed),
# so the API reaches it over a forwarded local port instead of a public URL:
#
#     browser -> noetic-compass-api -> 127.0.0.1:LOCAL_PORT --ssh--> pod:8080
#
# After this tunnel is up, set ATLAS_LIVE_WORKER_URL to the local end and start
# the API. Hosted open-weight audits (EleutherAI/pythia-160m) then run live.
#
# Usage:
#   ./open_atlas_live_tunnel.sh
#   POD_HOST=1.2.3.4 POD_PORT=22055 ./open_atlas_live_tunnel.sh
#
# Pod connection details default to the current pod but are overridable, since
# RunPod reassigns host/port when a pod is recreated.

set -euo pipefail

POD_HOST="${POD_HOST:-194.68.245.85}"
POD_PORT="${POD_PORT:-22055}"
POD_USER="${POD_USER:-root}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
LOCAL_PORT="${LOCAL_PORT:-18080}"
REMOTE_PORT="${REMOTE_PORT:-8080}"

echo "Opening tunnel: 127.0.0.1:${LOCAL_PORT} -> ${POD_USER}@${POD_HOST}:${POD_PORT} -> 127.0.0.1:${REMOTE_PORT}"
echo "Then set in the API environment / .env:"
echo "    ATLAS_LIVE_WORKER_URL=http://127.0.0.1:${LOCAL_PORT}"
echo "Verify with:"
echo "    curl -s http://127.0.0.1:${LOCAL_PORT}/health/realmode"
echo "Press Ctrl-C to close the tunnel."
echo

# Keepalive flags so a transient drop does not silently kill the forward
# mid-audit (we hit 'Connection reset by peer' without these).
exec ssh -N \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=4 \
  -o TCPKeepAlive=yes \
  -o ExitOnForwardFailure=yes \
  -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
  -p "${POD_PORT}" \
  -i "${SSH_KEY}" \
  "${POD_USER}@${POD_HOST}"
