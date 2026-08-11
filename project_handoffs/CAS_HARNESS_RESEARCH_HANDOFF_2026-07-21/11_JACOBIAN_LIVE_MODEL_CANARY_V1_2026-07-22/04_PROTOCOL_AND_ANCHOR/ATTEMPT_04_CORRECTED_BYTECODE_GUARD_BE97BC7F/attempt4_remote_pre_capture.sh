#!/usr/bin/env bash
set -euo pipefail
umask 077

PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
ATTEMPT=/workspace/cas-jlcv1-official-be97bc7f-4108653e
DEP="$ATTEMPT/dependency"
CONTROL="$ATTEMPT/control"
PRE="$ATTEMPT/environment_pre"
REPO="$ATTEMPT/repo"
APP="$REPO/noetic-compass-scaffold/noetic-compass"
WORKER="$APP/live-trace-worker"
CEREMONY="$WORKER/scripts/prepare_jacobian_lens_canary_v1.py"

RUN_ID=jlcv1-rfc3161-4108653e11369d812517e7f5d3ab44c10aa860df3131ac2f8636a14db654c0fc
RESEARCH_POD_ID=zp2s9pscgncn0b
RESEARCH_HASH=6a06b1fb7c93f8abfdb9d625b81088897ce8992e86e5ed4f26a72f19af7704ed
PRODUCTION_HASH=a1c042b39d028c45b06ed41636090c1098249dc351c51e90dd1fa13e3a3cd0a0
IMAGE_REFERENCE=runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
IMAGE_REFERENCE_HASH=7b71112562b301ec14e7865e6d5839843d7fc97425da5875ac3d310a2f869402
CUDA_DRIVER_VERSION=580.126.09
EXPECTED_DEPENDENCY_MANIFEST=10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00
EXPECTED_DEPENDENCY_LOCK=deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b

test "$(git -C "$REPO" rev-parse HEAD)" = be97bc7f76d1e9f5e501702660678d4af3081f5e
test "$(git -C "$REPO" rev-parse 'HEAD^{tree}')" = 4eb382528e8a4cee81a1c043f65bf0dcfa369ccf
test -z "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)"
test -z "$(find "$PRE" -mindepth 1 -print -quit)"
test -z "$(find "$ATTEMPT/output" -mindepth 1 -print -quit)"
test -z "$(find "$ATTEMPT/runlog" -mindepth 1 -print -quit)"
test -z "$(find "$ATTEMPT/environment_post" -mindepth 1 -print -quit)"

test "$(sha256sum "$CONTROL/jacobian_lens_canary_v1_implementation.bundle" | awk '{print $1}')" = 3ddf60a6f24c204489a70c62465efed3ccd421baa7739bffa923d26821512b67
test "$(sha256sum "$CONTROL/jacobian_lens_canary_v1_implementation_manifest.json" | awk '{print $1}')" = bbaaa973372cd95c3c99472a31664ab2add699cf1d844a5b2ab28a763dd04ffb
test "$(sha256sum "$ATTEMPT/frozen/model/pythia_160m_model_manifest_v1.json" | awk '{print $1}')" = e78edf3255f59a69c03659585da04e6a6ca624c707b1567556180873fd54be17
test "$(sha256sum "$ATTEMPT/frozen/model/pythia_160m_model_manifest_v1.json.publication.json" | awk '{print $1}')" = 7207dd18ce0a77d49f443007677527dc486d4317318e187a4f96ea11f88f10df
test "$(sha256sum "$ATTEMPT/frozen/source/jspace_source_snapshot_v1.json" | awk '{print $1}')" = 624f9c31208343ca9ea514d1abbd1c8d7a7af953ecd71337ce07e8390189886b
test "$(sha256sum "$ATTEMPT/frozen/source/jspace_source_snapshot_v1.json.verified.publication.json" | awk '{print $1}')" = 8e214cc1c8a6869a7fc8b6707693d2f26b80110d20ee979dc13f45f20f641cce
test "$(sha256sum "$ATTEMPT/frozen/source/jspace_source_attestation.json" | awk '{print $1}')" = 6a133cae284710669f5a46acb9a990c0c200f64a9213a0a2271555001c031755
test "$(sha256sum "$ATTEMPT/frozen/source/jspace_provider_metadata.json" | awk '{print $1}')" = 8a16fab2fd7b1a268a42759cbde5c0162571e4a4166ac975fe69bbf8a96e39ca
test "$(sha256sum "$ATTEMPT/frozen/tokens/jspace_wikitext_blocks_v1.json" | awk '{print $1}')" = 9cf4549abfaf6b8e44bce8a2578428d27b45f3e207a32f0472b2f53adeb54b28
test "$(sha256sum "$ATTEMPT/frozen/tokens/jspace_wikitext_blocks_v1.json.publication.json" | awk '{print $1}')" = a953a9f3180391f21bfbb4763c47cba8d9df5669e7b3637a650823c4217d1c5f
test "$(sha256sum /workspace/cas-model-a8969eb7/model.safetensors | awk '{print $1}')" = 29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270

DEPENDENCY_JSON=$("$PY" -I -B -c "import json,sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_dependency_bundle import verify_dependency_bundle; value=verify_dependency_bundle(Path('$DEP')); print(json.dumps({'file_count': value.file_count, 'file_manifest_sha256': value.file_manifest_sha256, 'dependency_lock_sha256': value.uv_lock_sha256}, sort_keys=True, separators=(',', ':')))" )
printf '%s\n' "$DEPENDENCY_JSON"
printf '%s' "$DEPENDENCY_JSON" | grep -Fq "$EXPECTED_DEPENDENCY_MANIFEST"
printf '%s' "$DEPENDENCY_JSON" | grep -Fq "$EXPECTED_DEPENDENCY_LOCK"

"$PY" -I -B "$CEREMONY" implementation-manifest \
  --repository-root "$APP" \
  --code-commit be97bc7f76d1e9f5e501702660678d4af3081f5e \
  --output "$CONTROL/jacobian_lens_canary_v1_implementation_manifest_reconstructed.json"
cmp "$CONTROL/jacobian_lens_canary_v1_implementation_manifest_reconstructed.json" \
  "$CONTROL/jacobian_lens_canary_v1_implementation_manifest.json"

"$PY" -I -B "$CEREMONY" runner-tools \
  --git-executable /usr/bin/git \
  --openssl-executable /usr/bin/openssl \
  --output "$CONTROL/jacobian_lens_canary_v1_runner_tool_binding.json"

set +e
UNSHARE_N_OUTPUT=$(unshare -n true 2>&1)
UNSHARE_N_CODE=$?
UNSHARE_URN_OUTPUT=$(unshare -Urn true 2>&1)
UNSHARE_URN_CODE=$?
set -e
test "$UNSHARE_N_CODE" -ne 0
test "$UNSHARE_URN_CODE" -ne 0
printf '%s' "$UNSHARE_N_OUTPUT" | grep -Fqi 'Operation not permitted'
printf '%s' "$UNSHARE_URN_OUTPUT" | grep -Fqi 'Operation not permitted'

CAP_EFF=$(awk '/^CapEff:/ {print $2}' /proc/self/status)
"$PY" -I -B -c "value=int('$CAP_EFF',16); assert not value & (1 << 12), 'CAP_NET_ADMIN present'; assert not value & (1 << 21), 'CAP_SYS_ADMIN present'; print('cap-net-admin-present=false'); print('cap-sys-admin-present=false')"

HOST_SHA=$("$PY" -I -B -c "import sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_environment_evidence import _HashBudget,_host_evidence; print(_host_evidence({'boot_id': Path('/proc/sys/kernel/random/boot_id'), 'machine_id': Path('/etc/machine-id')}, budget=_HashBudget())['identity_sha256'])")
GPU_BYTES=$("$PY" -I -B -c "import sys; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_environment_evidence import nvml_total_memory_bytes; value=nvml_total_memory_bytes(); assert len(value)==1; print(value[0])")
test "$GPU_BYTES" -ge 24000000000
test "$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | tr -d '[:space:]')" = "$CUDA_DRIVER_VERSION"

"$PY" -I -B "$WORKER/scripts/build_jacobian_lens_network_guard_plan_v1.py" \
  --repository-root "$APP" \
  --output "$CONTROL/jacobian_lens_canary_v1_network_guard_plan.json" \
  --run-id "$RUN_ID" \
  --provider-instance-id-sha256 "$RESEARCH_HASH" \
  --production-pod-instance-id-sha256 "$PRODUCTION_HASH" \
  --container-image-reference "$IMAGE_REFERENCE" \
  --container-image-reference-sha256 "$IMAGE_REFERENCE_HASH" \
  --container-image-reference-source RUNPOD_UI_OPERATOR_OBSERVED_TAG \
  --container-image-immutable-digest-status UNAVAILABLE \
  --implementation-manifest-sha256 bbaaa973372cd95c3c99472a31664ab2add699cf1d844a5b2ab28a763dd04ffb \
  --implementation-git-bundle-sha256 3ddf60a6f24c204489a70c62465efed3ccd421baa7739bffa923d26821512b67 \
  --unshare-n-result EPERM \
  --unshare-urn-result EPERM \
  --cap-net-admin-present false \
  --cap-sys-admin-present false

PLAN_SHA=$(sha256sum "$CONTROL/jacobian_lens_canary_v1_network_guard_plan.json" | awk '{print $1}')

RUNPOD_POD_ID="$RESEARCH_POD_ID" \
"$PY" -I -B "$WORKER/scripts/capture_jacobian_lens_environment_v1.py" \
  --output-directory "$PRE" \
  --phase PRE \
  --run-id "$RUN_ID" \
  --expected-provider-instance-id-sha256 "$RESEARCH_HASH" \
  --container-image-reference "$IMAGE_REFERENCE" \
  --network-guard-plan-receipt-sha256 "$PLAN_SHA" \
  --expected-host-identity-sha256 "$HOST_SHA" \
  --expected-cuda-driver-version "$CUDA_DRIVER_VERSION"

printf 'host_identity_sha256=%s\n' "$HOST_SHA"
printf 'gpu_total_memory_bytes=%s\n' "$GPU_BYTES"
printf 'network_guard_plan_sha256=%s\n' "$PLAN_SHA"
find "$PRE" -maxdepth 1 -type f -printf '%f\n' | sort
