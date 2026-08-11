#!/usr/bin/env bash
set -euo pipefail

PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
ATTEMPT=/workspace/cas-jlcv1-official-be97bc7f-4108653e
DEP="$ATTEMPT/dependency"
CONTROL="$ATTEMPT/control"
PRE="$ATTEMPT/environment_pre"
REPO="$ATTEMPT/repo"
APP="$REPO/noetic-compass-scaffold/noetic-compass"
WORKER="$APP/live-trace-worker"

EXPECTED_COMMIT=be97bc7f76d1e9f5e501702660678d4af3081f5e
EXPECTED_TREE=4eb382528e8a4cee81a1c043f65bf0dcfa369ccf
EXPECTED_HOST=d88f4a806ead491d5c140d54615b6595c926b8e67c476a60a95d566ee732e03c
EXPECTED_BOOT=8d6f65214f4ce130d8d342532a65ee41b4a8555fcd102502f6acb3840bbce7aa
EXPECTED_MACHINE=aed9946c7ac389c687b73bd918790d99da1303140bc502277f8d7c016975a486
EXPECTED_GPU_UUID=GPU-5a2301c0-941c-a946-0ea2-f90016d4750f
EXPECTED_DRIVER=580.126.09
EXPECTED_GPU_BYTES=48305799168
EXPECTED_DEPENDENCY_MANIFEST=10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00
EXPECTED_DEPENDENCY_LOCK=deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b
EXPECTED_PLAN=7ff398b4a06451190f1f6d37ea7798e815065b6377247b1a7f9a6dd000ef4b98
EXPECTED_RUNNER=ce16acc6a576cccee2dc13700e09af779570ec0319d6064c109e385020acc70c
EXPECTED_PRE=176d7c0f25a101f939e7835704c79d310258bf1aad62014b8f96eff7a2fea48e
EXPECTED_PRE_CRITICAL=70fab6ca8f7e788427e27224d5abc3eaed98191156fdab8344fd98a15808ea6a
EXPECTED_PRE_DISTS=9897f8e720bde862a02fc640f804aa34733196b1d4c76f7b2945928d4eefab8f
EXPECTED_PRE_SMI=13bd23809031b05ca97ead9c8255511523c8b9c072310cf22eb1d1bccb50b433
EXPECTED_PRE_LAYOUT=0c7e68bc13aee0e3ad4e604ed05eddba63810c16b05be7307e13aa608af90914

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
verify_file "$PRE/pre.environment.json" 3683 "$EXPECTED_PRE"
verify_file "$PRE/pre.critical_runtime_files.json" 3336110 "$EXPECTED_PRE_CRITICAL"
verify_file "$PRE/pre.installed_distributions.json" 50708 "$EXPECTED_PRE_DISTS"
verify_file "$PRE/pre.nvidia_smi.txt" 109 "$EXPECTED_PRE_SMI"
verify_file "$PRE/pre.runtime_layout.json" 33982 "$EXPECTED_PRE_LAYOUT"

verify_file "$CONTROL/jacobian_lens_canary_v1_protocol.json" 8141 823577ef0b10ae73076259de80ecf97e66bd29f5fde7682dd72752ede60ab780
verify_file "$CONTROL/jacobian_lens_canary_v1_anchor_request.tsq" 104 fa887272d01f436d37569f6d13b719f5392539dda897da870606c8845be11829
verify_file "$CONTROL/jacobian_lens_canary_v1_anchor_response.tsr" 6033 08c2a34b3ea398bb1d64c9dd6fb6ae580becd9ba713d36652bae2a54f4e3f4f9
verify_file "$CONTROL/jacobian_lens_canary_v1_anchor_receipt.json" 5597 577c9bb94b87e395444c2f9a1c65a500a4aae85878970db8deddf6e37387bc65
verify_file "$CONTROL/jacobian_lens_canary_v1_launch_configuration.json" 7062 a8c9f45bcbfca9b2460dd6b3b04a253e441b9375e56e64b5fc3b0bad1eeb2445

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
