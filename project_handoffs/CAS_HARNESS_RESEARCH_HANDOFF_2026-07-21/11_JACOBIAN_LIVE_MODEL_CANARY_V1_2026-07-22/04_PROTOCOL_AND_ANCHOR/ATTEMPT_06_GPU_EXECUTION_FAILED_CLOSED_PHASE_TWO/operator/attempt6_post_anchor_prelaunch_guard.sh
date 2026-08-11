#!/usr/bin/env bash
set -euo pipefail

PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
ATTEMPT=/workspace/cas-jlcv1-official-29551624-f3e3adad
DEP="$ATTEMPT/dependency"
CONTROL="$ATTEMPT/control"
PRE="$ATTEMPT/environment_pre"
REPO="$ATTEMPT/repo"
APP="$REPO/noetic-compass-scaffold/noetic-compass"
WORKER="$APP/live-trace-worker"

EXPECTED_COMMIT=29551624f4de0eec61c4035e364203be55d6c08a
EXPECTED_TREE=0d70f8e8e8d9dfd9f36ed88ade731ab466935be6
EXPECTED_HOST=d88f4a806ead491d5c140d54615b6595c926b8e67c476a60a95d566ee732e03c
EXPECTED_BOOT=8d6f65214f4ce130d8d342532a65ee41b4a8555fcd102502f6acb3840bbce7aa
EXPECTED_MACHINE=aed9946c7ac389c687b73bd918790d99da1303140bc502277f8d7c016975a486
EXPECTED_GPU_UUID=GPU-b7638993-cc34-ac95-7fc8-5002ce894e00
EXPECTED_DRIVER=580.126.09
EXPECTED_GPU_BYTES=48305799168
EXPECTED_DEPENDENCY_MANIFEST=10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00
EXPECTED_DEPENDENCY_LOCK=deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b
EXPECTED_PLAN=b1d25efd7ca66248931f519bdc1312b1135005e9676ba7f95e2f27c5ce2e0afa
EXPECTED_RUNNER=ce16acc6a576cccee2dc13700e09af779570ec0319d6064c109e385020acc70c
EXPECTED_PRE=73e043701b4151f17ac6cb29a0258e63412f8e4d6d6227c1163d1d96b892e963
EXPECTED_PRE_CRITICAL=51504cf719518054edc040893eb12425179b9a8edb74e03b2b212c99e507f3c0
EXPECTED_PRE_DISTS=0c050e9ff2db88d24f5a9e7940495e2f82c6fb6f693b3fff0ea4bca54abd5e82
EXPECTED_PRE_SMI=9840a3a45b1f38a5a9cb70a96a573a01331313853545536d97620a3ab9fd8b9e
EXPECTED_PRE_LAYOUT=df78ad9b505dea16c106a2ac61a125efac343901c1f274c170c75719e9fe2fc3

verify_file() {
  local path=$1
  local expected_size=$2
  local expected_sha=$3
  test -f "$path"
  test "$(stat -c '%s' "$path")" = "$expected_size"
  test "$(sha256sum "$path" | awk '{print $1}')" = "$expected_sha"
}

test "$(git -C "$REPO" rev-parse HEAD)" = "$EXPECTED_COMMIT"
test "$(git -C "$REPO" rev-parse 'HEAD^{tree}')" = "$EXPECTED_TREE"
test -z "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)"
test -z "$(find "$REPO" -type f -name '*.pyc' -print -quit)"

HOST_SHA=$("$PY" -I -B -c "import sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_environment_evidence import _HashBudget,_host_evidence; print(_host_evidence({'boot_id': Path('/proc/sys/kernel/random/boot_id'), 'machine_id': Path('/etc/machine-id')}, budget=_HashBudget())['identity_sha256'])")
BOOT_SHA=$(sha256sum /proc/sys/kernel/random/boot_id | awk '{print $1}')
MACHINE_SHA=$(sha256sum /etc/machine-id | awk '{print $1}')
test "$HOST_SHA" = "$EXPECTED_HOST"
test "$BOOT_SHA" = "$EXPECTED_BOOT"
test "$MACHINE_SHA" = "$EXPECTED_MACHINE"

GPU_BYTES=$("$PY" -I -B -c "import sys; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_environment_evidence import nvml_total_memory_bytes; value=nvml_total_memory_bytes(); assert len(value)==1; print(value[0])")
GPU_UUID=$(nvidia-smi --query-gpu=uuid --format=csv,noheader,nounits | tr -d '[:space:]')
DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | tr -d '[:space:]')
GPU_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d '[:space:]')
GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d '[:space:]')
test "$GPU_BYTES" = "$EXPECTED_GPU_BYTES"
test "$GPU_UUID" = "$EXPECTED_GPU_UUID"
test "$DRIVER" = "$EXPECTED_DRIVER"
test "$GPU_USED" = "0"
test "$GPU_UTIL" = "0"

DEPENDENCY_JSON=$("$PY" -I -B -c "import json,sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_dependency_bundle import verify_dependency_bundle; value=verify_dependency_bundle(Path('$DEP')); print(json.dumps({'file_count': value.file_count, 'file_manifest_sha256': value.file_manifest_sha256, 'dependency_lock_sha256': value.uv_lock_sha256}, sort_keys=True, separators=(',', ':')))")
printf '%s' "$DEPENDENCY_JSON" | grep -Fq '"file_count":15'
printf '%s' "$DEPENDENCY_JSON" | grep -Fq "$EXPECTED_DEPENDENCY_MANIFEST"
printf '%s' "$DEPENDENCY_JSON" | grep -Fq "$EXPECTED_DEPENDENCY_LOCK"
test -z "$(find "$DEP" -type f -name '*.pyc' -print -quit)"

verify_file "$CONTROL/jacobian_lens_canary_v1_network_guard_plan.json" 7320 "$EXPECTED_PLAN"
verify_file "$CONTROL/jacobian_lens_canary_v1_runner_tool_binding.json" 450 "$EXPECTED_RUNNER"
verify_file "$PRE/pre.environment.json" 3684 "$EXPECTED_PRE"
verify_file "$PRE/pre.critical_runtime_files.json" 3336110 "$EXPECTED_PRE_CRITICAL"
verify_file "$PRE/pre.installed_distributions.json" 165131 "$EXPECTED_PRE_DISTS"
verify_file "$PRE/pre.nvidia_smi.txt" 109 "$EXPECTED_PRE_SMI"
verify_file "$PRE/pre.runtime_layout.json" 34905 "$EXPECTED_PRE_LAYOUT"

verify_file "$CONTROL/jacobian_lens_canary_v1_protocol.json" 8141 013c8b528c50e5cb260a9a642ed3d597304b6d8c3ebdd601a4a1523faf6cdc01
verify_file "$CONTROL/jacobian_lens_canary_v1_anchor_request.tsq" 104 c47ba9d88710deb3861f245252f48247b443e72d9a3c3cf756eddf4069578fc5
verify_file "$CONTROL/jacobian_lens_canary_v1_anchor_response.tsr" 6033 dd944b0f3dc3a87498cb2995fafb2dc258dc94612f064f0271d76878a6f72aa7
verify_file "$CONTROL/jacobian_lens_canary_v1_anchor_receipt.json" 5597 842d65e0fc71cf893064bc0e2a121c2d55edb53fe813f40b3b625847a917be26
verify_file "$CONTROL/jacobian_lens_canary_v1_launch_configuration.json" 7062 3113e05d0a2a8913ce2f4a0838d6d8092c62d966691bf953e31fcad7b4ff257d

for directory in "$ATTEMPT/output" "$ATTEMPT/runlog" "$ATTEMPT/environment_post"; do
  test -d "$directory"
  test -z "$(find "$directory" -mindepth 1 -print -quit)"
done
test ! -e "$ATTEMPT/operator/launch_started.json"
test ! -e "$ATTEMPT/operator/launch_finished.json"
test -z "$(pgrep -af 'run_jacobian_lens_canary_v1_seccomp|run_jacobian_lens_canary_v1.py|jacobian_lens_canary_v1.py' || true)"

printf 'post_anchor_prelaunch_guard=PASS\n'
printf 'checked_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'hostname=%s\n' "$(hostname)"
printf 'host_identity_sha256=%s\n' "$HOST_SHA"
printf 'boot_id_sha256=%s\n' "$BOOT_SHA"
printf 'machine_id_sha256=%s\n' "$MACHINE_SHA"
printf 'gpu_uuid=%s\n' "$GPU_UUID"
printf 'gpu_total_memory_bytes=%s\n' "$GPU_BYTES"
printf 'gpu_memory_used_mib=%s\n' "$GPU_USED"
printf 'gpu_utilization_percent=%s\n' "$GPU_UTIL"
printf 'driver_version=%s\n' "$DRIVER"
printf 'dependency=%s\n' "$DEPENDENCY_JSON"
