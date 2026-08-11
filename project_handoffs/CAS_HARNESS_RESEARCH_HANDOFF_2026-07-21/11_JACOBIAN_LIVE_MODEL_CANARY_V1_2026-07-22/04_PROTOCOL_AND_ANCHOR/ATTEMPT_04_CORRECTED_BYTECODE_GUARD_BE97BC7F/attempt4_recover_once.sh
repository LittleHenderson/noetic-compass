#!/usr/bin/env bash
set -euo pipefail
umask 077
export LC_ALL=C

WORKSPACE=/workspace
ATTEMPT_NAME=cas-jlcv1-official-be97bc7f-4108653e
MODEL_NAME=cas-model-a8969eb7
STAGING_NAME=cas-jlcv1-attempt4-post-anchor-staging-fa887272
ATTEMPT="$WORKSPACE/$ATTEMPT_NAME"
RECOVERY="$WORKSPACE/cas-jlcv1-attempt4-recovery-be97bc7f-4108653e"
ARCHIVE="$RECOVERY/attempt4_complete_evidence.tar"
FILE_INVENTORY="$RECOVERY/attempt4_complete_file_inventory.sha256"
SYMLINK_INVENTORY="$RECOVERY/attempt4_complete_symlink_inventory.txt"
DIRECTORY_INVENTORY="$RECOVERY/attempt4_complete_directory_inventory.txt"

test ! -e "$RECOVERY"
test -f "$ATTEMPT/operator/finalization_status.json"
test "$(sha256sum "$ATTEMPT/operator/finalization_status.json" | awk '{print $1}')" = c34e6a43b1d21a07b4bbfa28264ceb842af38cda895e3e52e481d58c50e926f2
test "$(sha256sum "$ATTEMPT/output/jacobian_lens_canary_v1_execution_receipt.json" | awk '{print $1}')" = c57005f90fadabaf9de84edb852f33e0c492599379e8d62755264cc0ab8fe732
test "$(sha256sum "$ATTEMPT/output/jacobian_lens_canary_v1_execution_receipt.json.publication.json" | awk '{print $1}')" = 18edc256a48ae167932e902104be725a229f33453a0f4d70b53d4bfe343f4322
test "$(sha256sum "$ATTEMPT/control/jacobian_lens_canary_v1_post_run_capture.json" | awk '{print $1}')" = 56026b134a644fff844aa301122cb281d5ea0deed0265c2fb66004b8c78f39f0
test -z "$(pgrep -af 'attempt4_finalize_once|capture_jacobian_lens_environment_v1|prepare_jacobian_lens_canary_v1|run_jacobian_lens_canary_v1_seccomp|run_jacobian_lens_canary_v1.py|jacobian_lens_canary_v1.py' || true)"
test "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d '[:space:]')" = 0
test "$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d '[:space:]')" = 0
test "$(find "$WORKSPACE/$MODEL_NAME" -maxdepth 1 -type f | wc -l | tr -d '[:space:]')" = 5

sync
mkdir -m 0700 "$RECOVERY"
(
  cd "$WORKSPACE"
  find "$ATTEMPT_NAME" "$MODEL_NAME" "$STAGING_NAME" -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$FILE_INVENTORY"
(
  cd "$WORKSPACE"
  find "$ATTEMPT_NAME" "$MODEL_NAME" "$STAGING_NAME" -type l -printf '%p|%l\n' | sort
) > "$SYMLINK_INVENTORY"
(
  cd "$WORKSPACE"
  find "$ATTEMPT_NAME" "$MODEL_NAME" "$STAGING_NAME" -type d -printf '%p\n' | sort
) > "$DIRECTORY_INVENTORY"

tar -C "$WORKSPACE" -cf "$ARCHIVE" "$ATTEMPT_NAME" "$MODEL_NAME" "$STAGING_NAME"
ARCHIVE_SHA256=$(sha256sum "$ARCHIVE" | awk '{print $1}')
ARCHIVE_BYTES=$(stat -c '%s' "$ARCHIVE")
FILE_INVENTORY_SHA256=$(sha256sum "$FILE_INVENTORY" | awk '{print $1}')
SYMLINK_INVENTORY_SHA256=$(sha256sum "$SYMLINK_INVENTORY" | awk '{print $1}')
DIRECTORY_INVENTORY_SHA256=$(sha256sum "$DIRECTORY_INVENTORY" | awk '{print $1}')
FILE_COUNT=$(wc -l < "$FILE_INVENTORY" | tr -d '[:space:]')
SYMLINK_COUNT=$(wc -l < "$SYMLINK_INVENTORY" | tr -d '[:space:]')
DIRECTORY_COUNT=$(wc -l < "$DIRECTORY_INVENTORY" | tr -d '[:space:]')
CAPTURED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
CAPTURED_UNIX_MS=$(date +%s%3N)
set -o noclobber
printf '{"archive_bytes":%s,"archive_sha256":"%s","captured_at_utc":"%s","captured_unix_ms":%s,"directory_count":%s,"directory_inventory_sha256":"%s","file_count":%s,"file_inventory_sha256":"%s","finalization_status_sha256":"c34e6a43b1d21a07b4bbfa28264ceb842af38cda895e3e52e481d58c50e926f2","model_root":"%s","official_attempt_root":"%s","recovery_status":"REMOTE_CREATE_ONCE_ARCHIVE_COMPLETE","staging_root":"%s","symlink_count":%s,"symlink_inventory_sha256":"%s"}\n' \
  "$ARCHIVE_BYTES" "$ARCHIVE_SHA256" "$CAPTURED_AT_UTC" "$CAPTURED_UNIX_MS" "$DIRECTORY_COUNT" "$DIRECTORY_INVENTORY_SHA256" "$FILE_COUNT" "$FILE_INVENTORY_SHA256" "$WORKSPACE/$MODEL_NAME" "$ATTEMPT" "$WORKSPACE/$STAGING_NAME" "$SYMLINK_COUNT" "$SYMLINK_INVENTORY_SHA256" > "$RECOVERY/recovery_complete.json"
set +o noclobber
chmod 0444 "$ARCHIVE" "$FILE_INVENTORY" "$SYMLINK_INVENTORY" "$DIRECTORY_INVENTORY" "$RECOVERY/recovery_complete.json"
sync
printf 'remote_recovery=PASS\n'
cat "$RECOVERY/recovery_complete.json"
