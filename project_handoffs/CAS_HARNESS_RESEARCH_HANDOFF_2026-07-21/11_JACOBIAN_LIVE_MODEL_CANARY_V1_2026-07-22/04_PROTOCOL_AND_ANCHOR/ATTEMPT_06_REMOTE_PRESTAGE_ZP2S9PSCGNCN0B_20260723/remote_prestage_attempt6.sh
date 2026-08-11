#!/usr/bin/env bash
# Attempt 6 non-model remote prestage — JACOBIAN_LENS_CANARY_V1.
# Mirrors the Attempt 5 prestage checks at the repaired commit 29551624.
# Creates NO nonce, run ID, PRE, protocol, query, anchor, launch config;
# performs NO TSA transmission and NO model/CUDA execution.
set -euo pipefail

ROOT=/workspace/cas-jlcv1-attempt6-prestage-29551624-20260723
UP="$ROOT/upload"
REPO="$ROOT/repo"
APPROOT="$REPO/noetic-compass-scaffold/noetic-compass"
WORKER="$APPROOT/live-trace-worker"
MODEL=/workspace/cas-model-a8969eb7
PY=/usr/bin/python3.11

EXPECTED_COMMIT=29551624f4de0eec61c4035e364203be55d6c08a
EXPECTED_TREE=0d70f8e8e8d9dfd9f36ed88ade731ab466935be6
EXPECTED_PARENT=f72b89cd2ec574400ffe69ad7bd1540791fb73c3
EXPECTED_BUNDLE_SHA=821dbc2dfad076dd8261768963f63d4cadd7726d2f6b635574ef0401f315088d
EXPECTED_BUNDLE_BYTES=36557255
EXPECTED_MANIFEST_SHA=abaee8b11af0c8d57969bfab19a28914e074dc9ae5eb6c1536a141edee53385d
EXPECTED_MANIFEST_BYTES=5689
EXPECTED_DEP_TAR_SHA=ed16af7ae5a1ac8d61c6d3e83cf946a8cb3669c10f0f679fb2351965d5922bb8
EXPECTED_DEP_TAR_BYTES=706560
EXPECTED_DEP_MANIFEST=10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00
EXPECTED_DEP_LOCK=deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b
EXPECTED_BOOT=8d6f65214f4ce130d8d342532a65ee41b4a8555fcd102502f6acb3840bbce7aa
EXPECTED_MACHINE=aed9946c7ac389c687b73bd918790d99da1303140bc502277f8d7c016975a486
EXPECTED_GPU_UUID=GPU-b7638993-cc34-ac95-7fc8-5002ce894e00
MIN_GPU_BYTES=24000000000

say() { printf '== %s\n' "$*"; }
fail() { printf 'PRESTAGE_FAIL: %s\n' "$*" >&2; exit 2; }

sha() { sha256sum "$1" | cut -d ' ' -f 1; }
bytes() { stat -c '%s' "$1"; }

expect_file() {
  local path=$1 want_bytes=$2 want_sha=$3 label=$4
  [[ -f "$path" && ! -L "$path" ]] || fail "$label missing or non-regular"
  [[ "$(bytes "$path")" == "$want_bytes" ]] || fail "$label byte count differs"
  [[ "$(sha "$path")" == "$want_sha" ]] || fail "$label sha256 differs"
  say "$label OK ($want_bytes bytes, $want_sha)"
}

say "host identity"
hostname
[[ "$(sha /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT" ]] || fail "boot id differs"
[[ "$(sha /etc/machine-id)" == "$EXPECTED_MACHINE" ]] || fail "machine id differs"
say "boot+machine identity OK"
GPU_LINE=$(nvidia-smi --query-gpu=uuid,memory.total,driver_version --format=csv,noheader)
echo "gpu: $GPU_LINE"
[[ "$GPU_LINE" == "$EXPECTED_GPU_UUID"* ]] || fail "GPU UUID differs"
GPU_MIB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | tr -d ' ')
GPU_BYTES=$((GPU_MIB * 1024 * 1024))
echo "gpu_total_memory_bytes=$GPU_BYTES"
[[ "$GPU_BYTES" -ge "$MIN_GPU_BYTES" ]] || fail "GPU capacity below gate"
say "capacity gate OK"
grep -E '^CapEff' /proc/self/status
say "tool identities"
for tool in /usr/bin/git /usr/bin/openssl "$PY"; do
  printf '%s sha256=%s bytes=%s\n' "$tool" "$(sha "$tool")" "$(bytes "$tool")"
done
git --version; openssl version; "$PY" --version

say "uploaded inputs"
expect_file "$UP/jacobian_lens_canary_v1_implementation.bundle" "$EXPECTED_BUNDLE_BYTES" "$EXPECTED_BUNDLE_SHA" "implementation bundle"
expect_file "$UP/jacobian_lens_canary_v1_implementation_manifest.json" "$EXPECTED_MANIFEST_BYTES" "$EXPECTED_MANIFEST_SHA" "implementation manifest"

say "frozen input publications rehash"
declare -A FROZEN=(
  [pythia_160m_model_manifest_v1.json]=e78edf3255f59a69c03659585da04e6a6ca624c707b1567556180873fd54be17
  [pythia_160m_model_manifest_v1.json.publication.json]=7207dd18ce0a77d49f443007677527dc486d4317318e187a4f96ea11f88f10df
  [jspace_provider_metadata.json]=8a16fab2fd7b1a268a42759cbde5c0162571e4a4166ac975fe69bbf8a96e39ca
  [jspace_source_attestation.json]=6a133cae284710669f5a46acb9a990c0c200f64a9213a0a2271555001c031755
  [jspace_source_snapshot_v1.json]=624f9c31208343ca9ea514d1abbd1c8d7a7af953ecd71337ce07e8390189886b
  [jspace_source_snapshot_v1.json.verified.publication.json]=8e214cc1c8a6869a7fc8b6707693d2f26b80110d20ee979dc13f45f20f641cce
  [jspace_wikitext_blocks_v1.json]=9cf4549abfaf6b8e44bce8a2578428d27b45f3e207a32f0472b2f53adeb54b28
  [jspace_wikitext_blocks_v1.json.publication.json]=a953a9f3180391f21bfbb4763c47cba8d9df5669e7b3637a650823c4217d1c5f
)
for name in "${!FROZEN[@]}"; do
  [[ "$(sha "$UP/frozen_inputs/$name")" == "${FROZEN[$name]}" ]] || fail "frozen input differs: $name"
done
say "8 frozen input publications OK"

say "clearing prior derived outputs for a clean deterministic pass"
rm -rf "$REPO" "$ROOT/dependency" "$ROOT/remote_manifest.json"

say "bundle reconstruction"
rm -rf "$ROOT/.bundlecheck"
git init -q "$ROOT/.bundlecheck"
git -C "$ROOT/.bundlecheck" bundle verify "$UP/jacobian_lens_canary_v1_implementation.bundle"
rm -rf "$ROOT/.bundlecheck"
HEADS=$(git bundle list-heads "$UP/jacobian_lens_canary_v1_implementation.bundle" | wc -l)
[[ "$HEADS" == "1" ]] || fail "bundle head count is $HEADS"
git clone --no-local "$UP/jacobian_lens_canary_v1_implementation.bundle" "$REPO" 2>&1 | tail -1 || true
git -C "$REPO" config core.autocrlf false
git -C "$REPO" config core.eol lf
git -C "$REPO" checkout --detach "$EXPECTED_COMMIT" 2>&1 | tail -1
git -C "$REPO" fsck --full --strict --no-reflogs
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || fail "commit differs"
[[ "$(git -C "$REPO" rev-parse 'HEAD^{tree}')" == "$EXPECTED_TREE" ]] || fail "tree differs"
[[ "$(git -C "$REPO" rev-parse 'HEAD^1')" == "$EXPECTED_PARENT" ]] || fail "parent differs"
[[ -z "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)" ]] || fail "repository not clean"
say "repository reconstruction OK ($EXPECTED_COMMIT)"

say "remote implementation manifest reconstruction"
cd "$WORKER"
"$PY" -B scripts/prepare_jacobian_lens_canary_v1.py implementation-manifest \
  --repository-root "$APPROOT" \
  --code-commit "$EXPECTED_COMMIT" \
  --output "$ROOT/remote_manifest.json"
REMOTE_MANIFEST_SHA=$(sha "$ROOT/remote_manifest.json")
REMOTE_MANIFEST_BYTES=$(bytes "$ROOT/remote_manifest.json")
echo "remote manifest: $REMOTE_MANIFEST_BYTES bytes, $REMOTE_MANIFEST_SHA"
[[ "$REMOTE_MANIFEST_SHA" == "$EXPECTED_MANIFEST_SHA" ]] || fail "remote manifest sha differs"
cmp "$ROOT/remote_manifest.json" "$UP/jacobian_lens_canary_v1_implementation_manifest.json" || fail "remote manifest bytes differ"
say "remote manifest byte-identical OK"

say "dependency archive verification"
expect_file "$UP/dependency_bundle.tar" "$EXPECTED_DEP_TAR_BYTES" "$EXPECTED_DEP_TAR_SHA" "dependency archive"
mkdir "$ROOT/dependency"
tar -xf "$UP/dependency_bundle.tar" -C "$ROOT/dependency"
"$PY" -I -B - <<PYEOF
import sys
from pathlib import Path
sys.path.insert(0, "$WORKER")
from research.jacobian_lens_dependency_bundle import verify_dependency_bundle
verified = verify_dependency_bundle(Path("$ROOT/dependency/cas-jlcv1-dependency-bundle-a8969eb7"))
assert verified.file_count == 15, verified.file_count
assert verified.file_manifest_sha256 == "$EXPECTED_DEP_MANIFEST", verified.file_manifest_sha256
assert verified.uv_lock_sha256 == "$EXPECTED_DEP_LOCK", verified.uv_lock_sha256
print("dependency bundle OK:", verified.file_count, "files,", verified.upstream_commit)
PYEOF
PYC_COUNT=$(find "$ROOT/dependency" "$WORKER" -name '*.pyc' 2>/dev/null | wc -l)
[[ "$PYC_COUNT" == "0" ]] || fail "pyc files present: $PYC_COUNT"
say "dependency OK, zero pyc"

say "model snapshot rehash (no model load)"
declare -A MODEL_FILES=(
  [config.json]=76eb275107220e450d31258f792a2efcbee109d8b62ae0088260057dec06362f
  [model.safetensors]=29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270
  [special_tokens_map.json]=6f50ab5a5a509a1c309d6171f339b196a900dc9c99ad0408ff23bb615fdae7ad
  [tokenizer.json]=c24618a1b3e6a38167beff1c72cffd126c3a66254347304b50547d12c5f25624
  [tokenizer_config.json]=70e38394e494931c6f773ba41e19460dd4436526b852207367f04341b4066d3f
)
MODEL_COUNT=$(find "$MODEL" -type f | wc -l)
[[ "$MODEL_COUNT" == "5" ]] || fail "model snapshot file count is $MODEL_COUNT"
for name in "${!MODEL_FILES[@]}"; do
  [[ "$(sha "$MODEL/$name")" == "${MODEL_FILES[$name]}" ]] || fail "model file differs: $name"
done
say "model snapshot 5/5 hashes OK"

say "OpenSSL empty-config and stdin checks"
EMPTY_CONF=$(mktemp); printf '\n' > "$EMPTY_CONF"
OPENSSL_CONF="$EMPTY_CONF" openssl version >/dev/null || fail "empty-config openssl failed"
ROOT_CERT="$WORKER/research_protocols/DigiCertTrustedRootG4.crt.pem"
if [[ ! -f "$ROOT_CERT" ]]; then
  ROOT_CERT=$(find "$WORKER" -name 'DigiCert*G4*.pem' | head -1)
fi
[[ -n "$ROOT_CERT" && -f "$ROOT_CERT" ]] || fail "root certificate not found in checkout"
FP=$(OPENSSL_CONF="$EMPTY_CONF" openssl x509 -noout -fingerprint -sha256 < "$ROOT_CERT")
FP_HEX=$(printf '%s' "$FP" | cut -d= -f2 | tr -d ':' | tr 'A-F' 'a-f')
echo "root fingerprint: $FP_HEX"
[[ "$FP_HEX" == "552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988" ]] || fail "root fingerprint differs: $FP"
say "openssl x509 PEM-on-stdin (no -in -) OK"

say "CRLF normalization contract checks on pod OpenSSL (LF platform)"
"$PY" -I -B - <<'PYEOF'
import importlib.util
import subprocess
import sys
from pathlib import Path

worker = Path("/workspace/cas-jlcv1-attempt6-prestage-29551624-20260723/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker")
sys.path.insert(0, str(worker))
spec = importlib.util.spec_from_file_location(
    "recv", worker / "scripts" / "verify_jacobian_lens_canary_v1_independent.py"
)
recv = importlib.util.module_from_spec(spec)
sys.modules["recv"] = recv
spec.loader.exec_module(recv)

query = subprocess.run(
    ["/usr/bin/openssl", "ts", "-query", "-digest", "34" * 32, "-sha256", "-text"],
    capture_output=True,
)
assert query.returncode == 0, query.stderr
assert b"\r" not in query.stdout, "pod OpenSSL unexpectedly emitted CR"
lf_text = recv._normalized_openssl_text(query.stdout, label="RFC3161 query text")
assert recv._extract_imprint(lf_text, label="query") == "34" * 32
crlf = lf_text.replace("\n", "\r\n").encode()
assert recv._normalized_openssl_text(crlf, label="RFC3161 query text") == lf_text
try:
    recv._normalized_openssl_text(b"Verification: OK\r", label="x")
    raise SystemExit("bare CR unexpectedly accepted")
except recv.VerificationError:
    pass

helper_spec = importlib.util.spec_from_file_location(
    "helper", worker / "scripts" / "run_cjt_ohm_statistical_validation.py"
)
helper = importlib.util.module_from_spec(helper_spec)
sys.modules["helper"] = helper
helper_spec.loader.exec_module(helper)
assert helper._normalize_openssl_human_text("A\r\nB\n", label="x") == "A\nB\n"
try:
    helper._normalize_openssl_human_text("A\rB\n", label="x")
    raise SystemExit("helper bare CR unexpectedly accepted")
except helper.StatisticalRunnerError:
    pass
print("CRLF contract checks OK on pod (receiver + helper, real openssl output)")
PYEOF

say "runner bound-OpenSSL real-binary checks (sealed memfd, Linux)"
"$PY" -B - <<'PYEOF'
import hashlib
import shutil
import sys
from pathlib import Path

worker = Path("/workspace/cas-jlcv1-attempt6-prestage-29551624-20260723/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker")
sys.path.insert(0, str(worker))
from research import jacobian_lens_canary_runner as runner

executable = Path(shutil.which("openssl")).resolve()
expected = runner.sha256_stable_file(executable)[1]
result = runner._run_bound_openssl(
    [str(executable), "ts", "-query", "-digest", "00" * 32, "-sha256", "-text"],
    executable=executable,
    expected_sha256=expected,
)
assert result.returncode == 0, result.stderr
text = runner._decode_bound_openssl_text(result.stdout, label="prestage ts query")
assert "Hash Algorithm: sha256" in text and "Message data:" in text
assert "\r" not in text
print("bound OpenSSL sealed-memfd + normalized decode OK")
PYEOF

say "wrapper fail-closed enforcement"
set +e
PLAIN_OUT=$("$PY" "$WORKER/scripts/run_jacobian_lens_canary_v1.py" 2>&1)
PLAIN_RC=$?
ISO_OUT=$("$PY" -I "$WORKER/scripts/run_jacobian_lens_canary_v1.py" 2>&1)
ISO_RC=$?
set -e
echo "wrapper plain rc=$PLAIN_RC: $(echo "$PLAIN_OUT" | head -1)"
echo "wrapper -I-only rc=$ISO_RC: $(echo "$ISO_OUT" | head -1)"
[[ "$PLAIN_RC" == "2" ]] || fail "wrapper without -I/-B did not fail closed with rc 2"
echo "$PLAIN_OUT" | grep -q 'isolated mode (-I)' || fail "wrapper missing required -I message"
[[ "$ISO_RC" == "2" ]] || fail "wrapper with -I but no -B did not fail closed with rc 2"
echo "$ISO_OUT" | grep -q 'bytecode writes disabled (-B)' || fail "wrapper missing required -B message"
say "wrapper fails closed without -I (rc 2) and without -B (rc 2) OK"

say "final GPU compute application count"
APPS=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -c . || true)
echo "compute_application_count=$APPS"
[[ "$APPS" == "0" ]] || fail "compute applications present"

say "attempt identity boundary"
for missing in nonce run_id environment_pre protocol query response anchor launch; do
  found=$(find "$ROOT" -maxdepth 2 -name "*${missing}*" 2>/dev/null | grep -v upload | grep -v repo || true)
  [[ -z "$found" ]] || fail "unexpected identity artifact: $found"
done
echo "no nonce/run-id/PRE/protocol/query/response/anchor/launch artifacts under prestage root"

say "ATTEMPT6_REMOTE_PRESTAGE_PASS"
