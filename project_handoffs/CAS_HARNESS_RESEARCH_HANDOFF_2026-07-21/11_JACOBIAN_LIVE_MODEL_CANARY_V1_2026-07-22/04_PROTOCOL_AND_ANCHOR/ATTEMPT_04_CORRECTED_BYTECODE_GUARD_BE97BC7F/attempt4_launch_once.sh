#!/usr/bin/env bash
set -euo pipefail
umask 077

PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
ATTEMPT=/workspace/cas-jlcv1-official-be97bc7f-4108653e
WORKER="$ATTEMPT/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
CONTROL="$ATTEMPT/control"
OPERATOR="$ATTEMPT/operator"
RUNLOG="$ATTEMPT/runlog"
STAGING=/workspace/cas-jlcv1-attempt4-post-anchor-staging-fa887272
GUARD="$OPERATOR/attempt4_post_anchor_prelaunch_guard.sh"
EXPECTED_GUARD_SHA256=4b1f0f2ccde3ee7b226aa3a165b38719fe4dd3bac8bfcecb0429c5cb872d49a7
EXPECTED_LIBSECCOMP_SHA256=d60148325d84cab666b226676c5009a61eea24f3902598829fe714da87ef3587
RUN_ID=jlcv1-rfc3161-4108653e11369d812517e7f5d3ab44c10aa860df3131ac2f8636a14db654c0fc

test "$(sha256sum "$GUARD" | awk '{print $1}')" = "$EXPECTED_GUARD_SHA256"
test ! -e "$OPERATOR/launch_started.json"
test ! -e "$OPERATOR/launch_finished.json"

GUARD_TMP="$STAGING/prelaunch_guard_output.txt"
test ! -e "$GUARD_TMP"
set -o noclobber
bash "$GUARD" > "$GUARD_TMP"
set +o noclobber
grep -Fxq 'post_anchor_prelaunch_guard=PASS' "$GUARD_TMP"
ln "$GUARD_TMP" "$RUNLOG/prelaunch_guard.txt"
chmod 0444 "$GUARD_TMP" "$RUNLOG/prelaunch_guard.txt"

STARTED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
STARTED_UNIX_MS=$(date +%s%3N)
set -o noclobber
printf '{"attempt_identity":"ATTEMPT_04_CORRECTED_BYTECODE_GUARD_BE97BC7F","launch_config_sha256":"a8c9f45bcbfca9b2460dd6b3b04a253e441b9375e56e64b5fc3b0bad1eeb2445","run_id":"%s","started_at_utc":"%s","started_unix_ms":%s,"wrapper_invocation_count":1}\n' \
  "$RUN_ID" "$STARTED_AT_UTC" "$STARTED_UNIX_MS" > "$OPERATOR/launch_started.json"
exec 3> "$RUNLOG/wrapper.stdout.log"
exec 4> "$RUNLOG/wrapper.stderr.log"
set +o noclobber

set +e
RUNPOD_POD_ID=zp2s9pscgncn0b \
CAS_PRODUCTION_POD_INSTANCE_ID_SHA256=a1c042b39d028c45b06ed41636090c1098249dc351c51e90dd1fa13e3a3cd0a0 \
"$PY" -I -B \
  "$WORKER/scripts/run_jacobian_lens_canary_v1_seccomp.py" \
  --launch-config "$CONTROL/jacobian_lens_canary_v1_launch_configuration.json" \
  --expected-libseccomp-sha256 "$EXPECTED_LIBSECCOMP_SHA256" >&3 2>&4
WRAPPER_EXIT_CODE=$?
set -e
exec 3>&-
exec 4>&-

FINISHED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
FINISHED_UNIX_MS=$(date +%s%3N)
STDOUT_SHA256=$(sha256sum "$RUNLOG/wrapper.stdout.log" | awk '{print $1}')
STDERR_SHA256=$(sha256sum "$RUNLOG/wrapper.stderr.log" | awk '{print $1}')
set -o noclobber
printf '%s\n' "$WRAPPER_EXIT_CODE" > "$RUNLOG/wrapper_exit_code.txt"
printf '{"attempt_identity":"ATTEMPT_04_CORRECTED_BYTECODE_GUARD_BE97BC7F","finished_at_utc":"%s","finished_unix_ms":%s,"run_id":"%s","stderr_sha256":"%s","stdout_sha256":"%s","wrapper_exit_code":%s,"wrapper_invocation_count":1}\n' \
  "$FINISHED_AT_UTC" "$FINISHED_UNIX_MS" "$RUN_ID" "$STDERR_SHA256" "$STDOUT_SHA256" "$WRAPPER_EXIT_CODE" > "$OPERATOR/launch_finished.json"
set +o noclobber
chmod 0444 "$OPERATOR/launch_started.json" "$OPERATOR/launch_finished.json" "$RUNLOG/prelaunch_guard.txt" "$RUNLOG/wrapper.stdout.log" "$RUNLOG/wrapper.stderr.log" "$RUNLOG/wrapper_exit_code.txt"
sync
exit "$WRAPPER_EXIT_CODE"
