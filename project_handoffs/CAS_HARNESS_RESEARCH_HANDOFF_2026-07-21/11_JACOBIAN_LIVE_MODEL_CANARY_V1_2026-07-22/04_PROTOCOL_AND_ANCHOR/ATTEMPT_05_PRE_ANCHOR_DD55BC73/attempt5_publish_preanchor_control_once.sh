#!/usr/bin/env bash
set -euo pipefail

ROOT=/workspace/cas-jlcv1-official-f72b89cd-dd55bc73
STAGING=/workspace/cas-jlcv1-attempt5-publish-dd55bc73
CONTROL="$ROOT/control"

declare -a records=(
  "jacobian_lens_canary_v0_raw.json|16292|fb302300829889072c68e5fd0f0e9ac1710daa58aab4aae5abc76a8eee360cb1"
  "jacobian_lens_canary_v0_canonical.json|14190|1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5"
  "jacobian_lens_canary_v1_protocol.json|8141|a038e18087a31956339f235a852e59a0fc67bc4088434f502787df68428abf34"
  "jacobian_lens_canary_v1_launch_target_paths.json|2606|ceebdc5a9720bc3c466760bab3c9b378f70c2317293177adf3e9126b35ff9643"
  "jacobian_lens_canary_v1_anchor_payload.json|3858|240d6f2de585c3f098d96b05a02fee4a121b3deb30f0165a28c40a79fe79c991"
  "jacobian_lens_canary_v1_anchor_request.tsq|104|e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846"
)

for record in "${records[@]}"; do
  IFS='|' read -r name expected_bytes expected_sha <<<"$record"
  source_path="$STAGING/$name"
  target_path="$CONTROL/$name"
  if [[ ! -f "$source_path" || -L "$source_path" ]]; then
    echo "Invalid staging source: $source_path" >&2
    exit 2
  fi
  if [[ -e "$target_path" || -L "$target_path" ]]; then
    echo "Refusing to overwrite control artifact: $target_path" >&2
    exit 2
  fi
  observed_bytes=$(stat -c '%s' "$source_path")
  observed_sha=$(sha256sum "$source_path" | cut -d ' ' -f 1)
  if [[ "$observed_bytes" != "$expected_bytes" || "$observed_sha" != "$expected_sha" ]]; then
    echo "Staging artifact differs: $name" >&2
    exit 2
  fi
done

for record in "${records[@]}"; do
  IFS='|' read -r name _ _ <<<"$record"
  ln "$STAGING/$name" "$CONTROL/$name"
done

for record in "${records[@]}"; do
  IFS='|' read -r name expected_bytes expected_sha <<<"$record"
  target_path="$CONTROL/$name"
  observed_bytes=$(stat -c '%s' "$target_path")
  observed_sha=$(sha256sum "$target_path" | cut -d ' ' -f 1)
  if [[ "$observed_bytes" != "$expected_bytes" || "$observed_sha" != "$expected_sha" ]]; then
    echo "Published control artifact differs: $name" >&2
    exit 2
  fi
  printf '%s\t%s\t%s\n' "$name" "$observed_bytes" "$observed_sha"
done

echo "PREANCHOR_CONTROL_PUBLICATION_PASS"
echo "NO_EXTERNAL_TRANSMISSION"
echo "NO_MODEL_OR_CUDA_EXECUTION"
echo "SHADOW / NONE / NOT_LICENSED"
