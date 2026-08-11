#!/usr/bin/env bash
set -euo pipefail

PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
ATTEMPT=/workspace/cas-jlcv1-official-f72b89cd-dd55bc73
CONTROL="$ATTEMPT/control"
DEP="$ATTEMPT/dependency"
FROZEN="$ATTEMPT/frozen"
PRE="$ATTEMPT/environment_pre"
REPO="$ATTEMPT/repo"
APP="$REPO/noetic-compass-scaffold/noetic-compass"
WORKER="$APP/live-trace-worker"
MODEL=/workspace/cas-model-a8969eb7

EXPECTED_COMMIT=f72b89cd2ec574400ffe69ad7bd1540791fb73c3
EXPECTED_TREE=71c45fd5999b1d3f31636bbae8bd199d166ab2f5
EXPECTED_PARENT=be97bc7f76d1e9f5e501702660678d4af3081f5e
EXPECTED_HOST=d88f4a806ead491d5c140d54615b6595c926b8e67c476a60a95d566ee732e03c
EXPECTED_BOOT=8d6f65214f4ce130d8d342532a65ee41b4a8555fcd102502f6acb3840bbce7aa
EXPECTED_MACHINE=aed9946c7ac389c687b73bd918790d99da1303140bc502277f8d7c016975a486
EXPECTED_GPU_UUID=GPU-b7638993-cc34-ac95-7fc8-5002ce894e00
EXPECTED_DRIVER=580.126.09
EXPECTED_GPU_BYTES=48305799168
EXPECTED_RUN_ID=jlcv1-rfc3161-dd55bc73ab446ccc794d26c2aeaa2eec2b0997d1384db9752e0f7615d804c380
EXPECTED_DEPENDENCY_MANIFEST=10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00
EXPECTED_DEPENDENCY_LOCK=deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b

check_file() {
  local path=$1
  local expected_bytes=$2
  local expected_sha=$3
  if [[ ! -f "$path" || -L "$path" ]]; then
    echo "Missing or non-regular continuity input: $path" >&2
    exit 2
  fi
  local observed_bytes
  local observed_sha
  observed_bytes=$(stat -c '%s' "$path")
  observed_sha=$(sha256sum "$path" | cut -d ' ' -f 1)
  if [[ "$observed_bytes" != "$expected_bytes" || "$observed_sha" != "$expected_sha" ]]; then
    echo "Continuity input differs: $path" >&2
    exit 2
  fi
}

test "$(git -C "$REPO" rev-parse HEAD)" = "$EXPECTED_COMMIT"
test "$(git -C "$REPO" rev-parse 'HEAD^{tree}')" = "$EXPECTED_TREE"
test "$(git -C "$REPO" rev-parse 'HEAD^1')" = "$EXPECTED_PARENT"
test -z "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)"
git -C "$REPO" fsck --full --strict

HOST_SHA=$(
  "$PY" -I -B -c \
    "import sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_environment_evidence import _HashBudget,_host_evidence; print(_host_evidence({'boot_id': Path('/proc/sys/kernel/random/boot_id'), 'machine_id': Path('/etc/machine-id')}, budget=_HashBudget())['identity_sha256'])"
)
BOOT_SHA=$(sha256sum /proc/sys/kernel/random/boot_id | cut -d ' ' -f 1)
MACHINE_SHA=$(sha256sum /etc/machine-id | cut -d ' ' -f 1)
test "$HOST_SHA" = "$EXPECTED_HOST"
test "$BOOT_SHA" = "$EXPECTED_BOOT"
test "$MACHINE_SHA" = "$EXPECTED_MACHINE"

GPU_BYTES=$(
  "$PY" -I -B -c \
    "import sys; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_environment_evidence import nvml_total_memory_bytes; value=nvml_total_memory_bytes(); assert len(value)==1; print(value[0])"
)
GPU_UUID=$(
  nvidia-smi --query-gpu=uuid --format=csv,noheader,nounits | tr -d '[:space:]'
)
DRIVER=$(
  nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits \
    | tr -d '[:space:]'
)
test "$GPU_BYTES" = "$EXPECTED_GPU_BYTES"
test "$GPU_UUID" = "$EXPECTED_GPU_UUID"
test "$DRIVER" = "$EXPECTED_DRIVER"

DEPENDENCY_JSON=$(
  "$PY" -I -B -c \
    "import json,sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_dependency_bundle import verify_dependency_bundle; value=verify_dependency_bundle(Path('$DEP')); print(json.dumps({'file_count': value.file_count, 'file_manifest_sha256': value.file_manifest_sha256, 'dependency_lock_sha256': value.uv_lock_sha256}, sort_keys=True, separators=(',', ':')))"
)
printf '%s' "$DEPENDENCY_JSON" | grep -Fq '"file_count":15'
printf '%s' "$DEPENDENCY_JSON" | grep -Fq "$EXPECTED_DEPENDENCY_MANIFEST"
printf '%s' "$DEPENDENCY_JSON" | grep -Fq "$EXPECTED_DEPENDENCY_LOCK"
test "$(find "$DEP" -type f -name '*.pyc' -print -quit)" = ""

check_file "$CONTROL/jacobian_lens_canary_v1_implementation.bundle" 36549194 360dfc7fab45b780eec2a52b049d9bdb660bc33251fb86dcecd5bc5e8748074b
check_file "$CONTROL/jacobian_lens_canary_v1_implementation_manifest.json" 5689 cb72ea06ef560b12eeeb0ec843aa46b777d16185bc41089339439a489ca51579
check_file "$CONTROL/jacobian_lens_canary_v1_implementation_manifest_reconstructed.json" 5689 cb72ea06ef560b12eeeb0ec843aa46b777d16185bc41089339439a489ca51579
check_file "$CONTROL/jacobian_lens_canary_v1_network_guard_plan.json" 7320 d015aa87c3ee86292e9f1743d0be89fa2604daa0264782b2a518811f4f760f69
check_file "$CONTROL/jacobian_lens_canary_v1_nonce_record.json" 646 701675e54b7a6bb6e4de3e374f1ada87a330e495b830f61b0c62f3a894088aa0
check_file "$CONTROL/jacobian_lens_canary_v1_provider_controller_capture.json" 1248 b0ed2192892b5a9e84ced9b021df7d7620d2dd0f9aaf6fa916276049ffd75dce
check_file "$CONTROL/jacobian_lens_canary_v1_receiver_tool_binding.json" 747 68a318796c9b02ca142cdce227bb273cb5cae5baace3118f790735312410bbf0
check_file "$CONTROL/jacobian_lens_canary_v1_runner_tool_binding.json" 450 ce16acc6a576cccee2dc13700e09af779570ec0319d6064c109e385020acc70c
check_file "$CONTROL/research_pod_id.txt" 15 76eec834b49407219e07801e5e8fa9adeb9b7541ce81a7bde7a515348c63beed
check_file "$CONTROL/production_pod_id.txt" 15 3458d34941f578d5d9d84578534062e3ac9fd30687bb14fda74803d9f0ded58d
check_file "$CONTROL/jacobian_lens_canary_v0_raw.json" 16292 fb302300829889072c68e5fd0f0e9ac1710daa58aab4aae5abc76a8eee360cb1
check_file "$CONTROL/jacobian_lens_canary_v0_canonical.json" 14190 1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5
check_file "$CONTROL/jacobian_lens_canary_v1_protocol.json" 8141 a038e18087a31956339f235a852e59a0fc67bc4088434f502787df68428abf34
check_file "$CONTROL/jacobian_lens_canary_v1_launch_target_paths.json" 2606 ceebdc5a9720bc3c466760bab3c9b378f70c2317293177adf3e9126b35ff9643
check_file "$CONTROL/jacobian_lens_canary_v1_anchor_payload.json" 3858 240d6f2de585c3f098d96b05a02fee4a121b3deb30f0165a28c40a79fe79c991
check_file "$CONTROL/jacobian_lens_canary_v1_anchor_request.tsq" 104 e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846

check_file "$FROZEN/model/pythia_160m_model_manifest_v1.json" 1157 e78edf3255f59a69c03659585da04e6a6ca624c707b1567556180873fd54be17
check_file "$FROZEN/model/pythia_160m_model_manifest_v1.json.publication.json" 405 7207dd18ce0a77d49f443007677527dc486d4317318e187a4f96ea11f88f10df
check_file "$FROZEN/source/jspace_source_snapshot_v1.json" 2152 624f9c31208343ca9ea514d1abbd1c8d7a7af953ecd71337ce07e8390189886b
check_file "$FROZEN/source/jspace_source_snapshot_v1.json.verified.publication.json" 548 8e214cc1c8a6869a7fc8b6707693d2f26b80110d20ee979dc13f45f20f641cce
check_file "$FROZEN/source/jspace_source_attestation.json" 4404 6a133cae284710669f5a46acb9a990c0c200f64a9213a0a2271555001c031755
check_file "$FROZEN/source/jspace_provider_metadata.json" 5894 8a16fab2fd7b1a268a42759cbde5c0162571e4a4166ac975fe69bbf8a96e39ca
check_file "$FROZEN/tokens/jspace_wikitext_blocks_v1.json" 975400 9cf4549abfaf6b8e44bce8a2578428d27b45f3e207a32f0472b2f53adeb54b28
check_file "$FROZEN/tokens/jspace_wikitext_blocks_v1.json.publication.json" 666 a953a9f3180391f21bfbb4763c47cba8d9df5669e7b3637a650823c4217d1c5f

check_file "$PRE/pre.critical_runtime_files.json" 3336110 2484391419db0447f11507266ca080997858ee0d61f2f2290ec40eae83950943
check_file "$PRE/pre.environment.json" 3683 4ecd72100da14ccaa657cdd47ae85e8ba5373b66b6c5a71581aea597435ce097
check_file "$PRE/pre.installed_distributions.json" 50708 7a90d9e7e575349ac24f3ee43dbd3236402a3aa788e179967d4102d838b1e8cb
check_file "$PRE/pre.nvidia_smi.txt" 109 9840a3a45b1f38a5a9cb70a96a573a01331313853545536d97620a3ab9fd8b9e
check_file "$PRE/pre.runtime_layout.json" 33977 1fae9cd0c47fa41cc95d3a3fd874b1dbf213df6187994293d0ece948360890c2

check_file "$MODEL/config.json" 569 76eb275107220e450d31258f792a2efcbee109d8b62ae0088260057dec06362f
check_file "$MODEL/model.safetensors" 374998696 29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270
check_file "$MODEL/special_tokens_map.json" 99 6f50ab5a5a509a1c309d6171f339b196a900dc9c99ad0408ff23bb615fdae7ad
check_file "$MODEL/tokenizer.json" 2113710 c24618a1b3e6a38167beff1c72cffd126c3a66254347304b50547d12c5f25624
check_file "$MODEL/tokenizer_config.json" 396 70e38394e494931c6f773ba41e19460dd4436526b852207367f04341b4066d3f

for directory in "$ATTEMPT/output" "$ATTEMPT/runlog" "$ATTEMPT/environment_post"; do
  test -d "$directory"
  test -z "$(find "$directory" -mindepth 1 -print -quit)"
done
test ! -e "$CONTROL/jacobian_lens_canary_v1_anchor_response.tsr"
test ! -e "$CONTROL/jacobian_lens_canary_v1_anchor_receipt.json"
test ! -e "$CONTROL/jacobian_lens_canary_v1_launch_configuration.json"
test -z "$(
  pgrep -af \
    'run_jacobian_lens_canary_v1_seccomp|run_jacobian_lens_canary_v1.py|jacobian_lens_canary_v1.py' \
    || true
)"

OBSERVED_RUN_ID=$(
  "$PY" -I -B -c \
    "import json; from pathlib import Path; values=[json.loads(Path('$CONTROL/jacobian_lens_canary_v1_nonce_record.json').read_text()), json.loads(Path('$CONTROL/jacobian_lens_canary_v1_protocol.json').read_text()), json.loads(Path('$PRE/pre.environment.json').read_text())]; ids=[values[0]['run_id'], values[1]['execution_boundary']['run_id'], values[2]['run_id']]; assert len(set(ids))==1; print(ids[0])"
)
test "$OBSERVED_RUN_ID" = "$EXPECTED_RUN_ID"

COMPUTE_APPS=$(
  nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits \
    | sed '/^[[:space:]]*$/d' \
    | wc -l
)
test "$COMPUTE_APPS" = "0"

printf 'continuity=PASS\n'
printf 'checked_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'hostname=%s\n' "$(hostname)"
printf 'run_id=%s\n' "$OBSERVED_RUN_ID"
printf 'commit=%s\n' "$EXPECTED_COMMIT"
printf 'tree=%s\n' "$EXPECTED_TREE"
printf 'parent=%s\n' "$EXPECTED_PARENT"
printf 'host_identity_sha256=%s\n' "$HOST_SHA"
printf 'boot_id_sha256=%s\n' "$BOOT_SHA"
printf 'machine_id_sha256=%s\n' "$MACHINE_SHA"
printf 'gpu_uuid=%s\n' "$GPU_UUID"
printf 'gpu_total_memory_bytes=%s\n' "$GPU_BYTES"
printf 'driver_version=%s\n' "$DRIVER"
printf 'dependency=%s\n' "$DEPENDENCY_JSON"
printf 'compute_application_count=%s\n' "$COMPUTE_APPS"
printf 'rfc3161_query_status=UNSENT\n'
printf 'external_tsa_transmission=NONE\n'
printf 'model_or_cuda_execution=NONE\n'
printf 'claim_boundary=SHADOW / NONE / NOT_LICENSED\n'
