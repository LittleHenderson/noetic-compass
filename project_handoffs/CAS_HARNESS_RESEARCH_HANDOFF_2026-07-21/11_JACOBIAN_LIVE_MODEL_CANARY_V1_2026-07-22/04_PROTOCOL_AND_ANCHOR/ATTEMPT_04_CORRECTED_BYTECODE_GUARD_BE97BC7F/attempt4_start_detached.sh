#!/usr/bin/env bash
set -euo pipefail
umask 077

STAGING=/workspace/cas-jlcv1-attempt4-post-anchor-staging-fa887272
LAUNCHER=/workspace/cas-jlcv1-official-be97bc7f-4108653e/operator/attempt4_launch_once.sh
STDOUT="$STAGING/launch_orchestrator.stdout.log"
STDERR="$STAGING/launch_orchestrator.stderr.log"
PID_FILE="$STAGING/launch_orchestrator.pid"

test ! -e "$STDOUT"
test ! -e "$STDERR"
test ! -e "$PID_FILE"
set -o noclobber
nohup bash "$LAUNCHER" </dev/null > "$STDOUT" 2> "$STDERR" &
PID=$!
printf '%s\n' "$PID" > "$PID_FILE"
set +o noclobber
printf 'launch_orchestrator_pid=%s\n' "$PID"
