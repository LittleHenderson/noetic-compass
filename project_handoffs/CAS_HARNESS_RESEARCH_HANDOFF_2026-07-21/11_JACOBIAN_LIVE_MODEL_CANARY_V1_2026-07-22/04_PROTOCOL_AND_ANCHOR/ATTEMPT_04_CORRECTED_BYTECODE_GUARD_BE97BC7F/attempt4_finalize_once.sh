#!/usr/bin/env bash
set -euo pipefail
umask 077

PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
ATTEMPT=/workspace/cas-jlcv1-official-be97bc7f-4108653e
WORKER="$ATTEMPT/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
CONTROL="$ATTEMPT/control"
OUTPUT="$ATTEMPT/output"
RUNLOG="$ATTEMPT/runlog"
OPERATOR="$ATTEMPT/operator"
RUN_ID=jlcv1-rfc3161-4108653e11369d812517e7f5d3ab44c10aa860df3131ac2f8636a14db654c0fc
PRODUCER_RECEIPT="$OUTPUT/jacobian_lens_canary_v1_execution_receipt.json"
PRODUCER_MARKER="$OUTPUT/jacobian_lens_canary_v1_execution_receipt.json.publication.json"
POST_CAPTURE="$CONTROL/jacobian_lens_canary_v1_post_run_capture.json"

test -f "$OPERATOR/launch_started.json"
test -f "$OPERATOR/launch_finished.json"
test -f "$RUNLOG/wrapper_exit_code.txt"
test ! -e "$OPERATOR/finalization_status.json"
test ! -e "$POST_CAPTURE"
test -z "$(pgrep -af 'run_jacobian_lens_canary_v1_seccomp|run_jacobian_lens_canary_v1.py|jacobian_lens_canary_v1.py' || true)"

set -o noclobber
exec 3> "$RUNLOG/post_environment_capture.stdout.log"
exec 4> "$RUNLOG/post_environment_capture.stderr.log"
set +o noclobber
set +e
RUNPOD_POD_ID=zp2s9pscgncn0b \
CAS_PRODUCTION_POD_INSTANCE_ID_SHA256=a1c042b39d028c45b06ed41636090c1098249dc351c51e90dd1fa13e3a3cd0a0 \
"$PY" -I -B "$WORKER/scripts/capture_jacobian_lens_environment_v1.py" \
  --output-directory "$ATTEMPT/environment_post" \
  --phase POST \
  --run-id "$RUN_ID" \
  --expected-provider-instance-id-sha256 6a06b1fb7c93f8abfdb9d625b81088897ce8992e86e5ed4f26a72f19af7704ed \
  --container-image-reference runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04 \
  --network-guard-plan-receipt-sha256 7ff398b4a06451190f1f6d37ea7798e815065b6377247b1a7f9a6dd000ef4b98 \
  --expected-host-identity-sha256 d88f4a806ead491d5c140d54615b6595c926b8e67c476a60a95d566ee732e03c \
  --expected-cuda-driver-version 580.126.09 \
  --compare-pre "$ATTEMPT/environment_pre/pre.environment.json" \
  --comparison-output "$ATTEMPT/environment_post/environment_comparison.json" >&3 2>&4
POST_ENV_EXIT_CODE=$?
set -e
exec 3>&-
exec 4>&-

POST_RUN_EXIT_CODE=-1
CLASSIFICATION=UNFINALIZED_INTERRUPTION
if test "$POST_ENV_EXIT_CODE" = "0" && test -f "$PRODUCER_RECEIPT" && test -f "$PRODUCER_MARKER"; then
  set -o noclobber
  exec 3> "$RUNLOG/post_run_capture.stdout.log"
  exec 4> "$RUNLOG/post_run_capture.stderr.log"
  set +o noclobber
  set +e
  "$PY" -I -B "$WORKER/scripts/prepare_jacobian_lens_canary_v1.py" post-run-capture \
    --protocol "$CONTROL/jacobian_lens_canary_v1_protocol.json" \
    --controller-capture "$CONTROL/jacobian_lens_canary_v1_provider_controller_capture.json" \
    --producer-receipt "$PRODUCER_RECEIPT" \
    --producer-marker "$PRODUCER_MARKER" \
    --environment-post-directory "$ATTEMPT/environment_post" \
    --captured-unix-ms "$(date +%s%3N)" \
    --output "$POST_CAPTURE" >&3 2>&4
  POST_RUN_EXIT_CODE=$?
  set -e
  exec 3>&-
  exec 4>&-
  if test "$POST_RUN_EXIT_CODE" = "0" && test -f "$POST_CAPTURE"; then
    CLASSIFICATION=READY_FOR_INDEPENDENT_RECEIVER
  else
    CLASSIFICATION=POST_RUN_CAPTURE_FAILED_CLOSED
  fi
elif test "$POST_ENV_EXIT_CODE" != "0"; then
  CLASSIFICATION=POST_ENVIRONMENT_CAPTURE_FAILED_CLOSED
fi

FINISHED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
FINISHED_UNIX_MS=$(date +%s%3N)
WRAPPER_EXIT_CODE=$(tr -d '[:space:]' < "$RUNLOG/wrapper_exit_code.txt")
PRODUCER_RECEIPT_PRESENT=false
PRODUCER_MARKER_PRESENT=false
POST_CAPTURE_PRESENT=false
test -f "$PRODUCER_RECEIPT" && PRODUCER_RECEIPT_PRESENT=true
test -f "$PRODUCER_MARKER" && PRODUCER_MARKER_PRESENT=true
test -f "$POST_CAPTURE" && POST_CAPTURE_PRESENT=true
set -o noclobber
printf '{"classification":"%s","finished_at_utc":"%s","finished_unix_ms":%s,"post_environment_capture_exit_code":%s,"post_run_capture_exit_code":%s,"post_run_capture_present":%s,"producer_marker_present":%s,"producer_receipt_present":%s,"run_id":"%s","wrapper_exit_code":%s}\n' \
  "$CLASSIFICATION" "$FINISHED_AT_UTC" "$FINISHED_UNIX_MS" "$POST_ENV_EXIT_CODE" "$POST_RUN_EXIT_CODE" "$POST_CAPTURE_PRESENT" "$PRODUCER_MARKER_PRESENT" "$PRODUCER_RECEIPT_PRESENT" "$RUN_ID" "$WRAPPER_EXIT_CODE" > "$OPERATOR/finalization_status.json"
set +o noclobber
chmod 0444 "$OPERATOR/finalization_status.json" "$RUNLOG/post_environment_capture.stdout.log" "$RUNLOG/post_environment_capture.stderr.log"
test ! -e "$RUNLOG/post_run_capture.stdout.log" || chmod 0444 "$RUNLOG/post_run_capture.stdout.log"
test ! -e "$RUNLOG/post_run_capture.stderr.log" || chmod 0444 "$RUNLOG/post_run_capture.stderr.log"
sync
printf '%s\n' "$CLASSIFICATION"
