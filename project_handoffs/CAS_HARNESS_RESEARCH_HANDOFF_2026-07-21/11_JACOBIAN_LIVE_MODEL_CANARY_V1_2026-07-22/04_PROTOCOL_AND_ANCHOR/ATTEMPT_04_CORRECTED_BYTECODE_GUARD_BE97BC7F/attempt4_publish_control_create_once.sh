#!/usr/bin/env bash
set -euo pipefail
umask 077

ATTEMPT=/workspace/cas-jlcv1-official-be97bc7f-4108653e
CONTROL="$ATTEMPT/control"
OPERATOR="$ATTEMPT/operator"
STAGING=/workspace/cas-jlcv1-attempt4-post-anchor-staging-fa887272

verify_file() {
  local path=$1
  local expected_size=$2
  local expected_sha=$3
  test -f "$path"
  test "$(stat -c '%s' "$path")" = "$expected_size"
  test "$(sha256sum "$path" | awk '{print $1}')" = "$expected_sha"
}

verify_file "$STAGING/jacobian_lens_canary_v1_protocol.json" 8141 823577ef0b10ae73076259de80ecf97e66bd29f5fde7682dd72752ede60ab780
verify_file "$STAGING/jacobian_lens_canary_v1_anchor_request.tsq" 104 fa887272d01f436d37569f6d13b719f5392539dda897da870606c8845be11829
verify_file "$STAGING/jacobian_lens_canary_v1_anchor_response.tsr" 6033 08c2a34b3ea398bb1d64c9dd6fb6ae580becd9ba713d36652bae2a54f4e3f4f9
verify_file "$STAGING/jacobian_lens_canary_v1_anchor_receipt.json" 5597 577c9bb94b87e395444c2f9a1c65a500a4aae85878970db8deddf6e37387bc65
verify_file "$STAGING/jacobian_lens_canary_v1_launch_configuration.json" 7062 a8c9f45bcbfca9b2460dd6b3b04a253e441b9375e56e64b5fc3b0bad1eeb2445
verify_file "$STAGING/attempt4_post_anchor_prelaunch_guard.sh" 6299 4b1f0f2ccde3ee7b226aa3a165b38719fe4dd3bac8bfcecb0429c5cb872d49a7
verify_file "$STAGING/attempt4_launch_once.sh" 3063 c135df3727d67e98fbaa917771c3a6ab1558447aa9fa4c496bf219d8f6bf618d
verify_file "$STAGING/attempt4_finalize_once.sh" 4595 fa6fb47f0ea3156907dc53f1de3119b9f3dc58d2105819d9b9f66f1ec6eb0d95

for name in \
  jacobian_lens_canary_v1_protocol.json \
  jacobian_lens_canary_v1_anchor_request.tsq \
  jacobian_lens_canary_v1_anchor_response.tsr \
  jacobian_lens_canary_v1_anchor_receipt.json \
  jacobian_lens_canary_v1_launch_configuration.json; do
  test ! -e "$CONTROL/$name"
done
test ! -e "$OPERATOR"
for directory in "$ATTEMPT/output" "$ATTEMPT/runlog" "$ATTEMPT/environment_post"; do
  test -z "$(find "$directory" -mindepth 1 -print -quit)"
done
test -z "$(pgrep -af 'run_jacobian_lens_canary_v1_seccomp|run_jacobian_lens_canary_v1.py|jacobian_lens_canary_v1.py' || true)"

mkdir -m 0700 "$OPERATOR"
for name in \
  jacobian_lens_canary_v1_protocol.json \
  jacobian_lens_canary_v1_anchor_request.tsq \
  jacobian_lens_canary_v1_anchor_response.tsr \
  jacobian_lens_canary_v1_anchor_receipt.json \
  jacobian_lens_canary_v1_launch_configuration.json; do
  ln "$STAGING/$name" "$CONTROL/$name"
done
for name in \
  attempt4_publish_control_create_once.sh \
  attempt4_post_anchor_prelaunch_guard.sh \
  attempt4_launch_once.sh \
  attempt4_finalize_once.sh; do
  ln "$STAGING/$name" "$OPERATOR/$name"
done
chmod 0444 \
  "$CONTROL/jacobian_lens_canary_v1_protocol.json" \
  "$CONTROL/jacobian_lens_canary_v1_anchor_request.tsq" \
  "$CONTROL/jacobian_lens_canary_v1_anchor_response.tsr" \
  "$CONTROL/jacobian_lens_canary_v1_anchor_receipt.json" \
  "$CONTROL/jacobian_lens_canary_v1_launch_configuration.json" \
  "$OPERATOR/attempt4_publish_control_create_once.sh" \
  "$OPERATOR/attempt4_post_anchor_prelaunch_guard.sh" \
  "$OPERATOR/attempt4_launch_once.sh" \
  "$OPERATOR/attempt4_finalize_once.sh"

PUBLISHER_SHA256=$(sha256sum "$OPERATOR/attempt4_publish_control_create_once.sh" | awk '{print $1}')
PUBLISHED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
PUBLISHED_UNIX_MS=$(date +%s%3N)
set -o noclobber
printf '{"anchor_receipt_sha256":"577c9bb94b87e395444c2f9a1c65a500a4aae85878970db8deddf6e37387bc65","anchor_response_sha256":"08c2a34b3ea398bb1d64c9dd6fb6ae580becd9ba713d36652bae2a54f4e3f4f9","control_publication":"CREATE_ONCE_HARD_LINKED","finalizer_sha256":"fa6fb47f0ea3156907dc53f1de3119b9f3dc58d2105819d9b9f66f1ec6eb0d95","guard_sha256":"4b1f0f2ccde3ee7b226aa3a165b38719fe4dd3bac8bfcecb0429c5cb872d49a7","launch_config_sha256":"a8c9f45bcbfca9b2460dd6b3b04a253e441b9375e56e64b5fc3b0bad1eeb2445","launcher_sha256":"c135df3727d67e98fbaa917771c3a6ab1558447aa9fa4c496bf219d8f6bf618d","protocol_sha256":"823577ef0b10ae73076259de80ecf97e66bd29f5fde7682dd72752ede60ab780","published_at_utc":"%s","published_unix_ms":%s,"publisher_sha256":"%s","query_sha256":"fa887272d01f436d37569f6d13b719f5392539dda897da870606c8845be11829"}\n' \
  "$PUBLISHED_AT_UTC" "$PUBLISHED_UNIX_MS" "$PUBLISHER_SHA256" > "$OPERATOR/control_publication_receipt.json"
set +o noclobber
chmod 0444 "$OPERATOR/control_publication_receipt.json"
sync
printf 'control_publication=PASS\n'
printf 'publisher_sha256=%s\n' "$PUBLISHER_SHA256"
printf 'publication_receipt_sha256=%s\n' "$(sha256sum "$OPERATOR/control_publication_receipt.json" | awk '{print $1}')"
