#!/usr/bin/env bash
set -euo pipefail
umask 077

ATTEMPT_ROOT=/workspace/cas-jlcv1-official-be97bc7f-4108653e
BUNDLE=/workspace/cas-jlcv1-implementation-be97bc7f.bundle
MANIFEST=/workspace/cas-jlcv1-implementation-manifest-be97bc7f.json
DEPENDENCY_SOURCE=/workspace/cas-jlcv1-dependency-bundle-be97bc7f
INPUTS=/workspace/cas-jacobian-v1-bootstrap/01_FROZEN_INPUTS
EXPECTED_COMMIT=be97bc7f76d1e9f5e501702660678d4af3081f5e
EXPECTED_TREE=4eb382528e8a4cee81a1c043f65bf0dcfa369ccf
EXPECTED_BUNDLE_SHA=3ddf60a6f24c204489a70c62465efed3ccd421baa7739bffa923d26821512b67
EXPECTED_MANIFEST_SHA=bbaaa973372cd95c3c99472a31664ab2add699cf1d844a5b2ab28a763dd04ffb

test ! -e "$ATTEMPT_ROOT"
test "$(sha256sum "$BUNDLE" | awk '{print $1}')" = "$EXPECTED_BUNDLE_SHA"
test "$(sha256sum "$MANIFEST" | awk '{print $1}')" = "$EXPECTED_MANIFEST_SHA"

mkdir -p \
  "$ATTEMPT_ROOT/control" \
  "$ATTEMPT_ROOT/dependency" \
  "$ATTEMPT_ROOT/environment_pre" \
  "$ATTEMPT_ROOT/environment_post" \
  "$ATTEMPT_ROOT/frozen/model" \
  "$ATTEMPT_ROOT/frozen/source" \
  "$ATTEMPT_ROOT/frozen/tokens" \
  "$ATTEMPT_ROOT/output" \
  "$ATTEMPT_ROOT/runlog"

git clone --quiet "$BUNDLE" "$ATTEMPT_ROOT/repo"
git -C "$ATTEMPT_ROOT/repo" checkout --quiet --detach "$EXPECTED_COMMIT"
test "$(git -C "$ATTEMPT_ROOT/repo" rev-parse HEAD)" = "$EXPECTED_COMMIT"
test "$(git -C "$ATTEMPT_ROOT/repo" rev-parse 'HEAD^{tree}')" = "$EXPECTED_TREE"
test -z "$(git -C "$ATTEMPT_ROOT/repo" status --porcelain=v1 --untracked-files=all)"

cp -- "$BUNDLE" "$ATTEMPT_ROOT/control/jacobian_lens_canary_v1_implementation.bundle"
cp -- "$MANIFEST" "$ATTEMPT_ROOT/control/jacobian_lens_canary_v1_implementation_manifest.json"

DEPENDENCY_FILES=(
  LICENSE
  jlens/__init__.py
  jlens/_logging.py
  jlens/data/README.md
  jlens/data/blackmail.json
  jlens/data/slice_vis.html
  jlens/examples.py
  jlens/fitting.py
  jlens/hf.py
  jlens/hooks.py
  jlens/lens.py
  jlens/protocol.py
  jlens/vis.py
  pyproject.toml
  uv.lock
)
for relative_path in "${DEPENDENCY_FILES[@]}"; do
  test -f "$DEPENDENCY_SOURCE/$relative_path"
  test ! -L "$DEPENDENCY_SOURCE/$relative_path"
  mkdir -p "$(dirname "$ATTEMPT_ROOT/dependency/$relative_path")"
  cp -- "$DEPENDENCY_SOURCE/$relative_path" "$ATTEMPT_ROOT/dependency/$relative_path"
done
test "$(find "$ATTEMPT_ROOT/dependency" -type f | wc -l)" -eq 15
test -z "$(find "$ATTEMPT_ROOT/dependency" -type l -print -quit)"
test -z "$(find "$ATTEMPT_ROOT/dependency" -type f \( -name '*.pyc' -o -path '*/__pycache__/*' \) -print -quit)"

cp -- "$INPUTS/model/pythia_160m_model_manifest_v1.json" "$ATTEMPT_ROOT/frozen/model/"
cp -- "$INPUTS/model/pythia_160m_model_manifest_v1.json.publication.json" "$ATTEMPT_ROOT/frozen/model/"
cp -- "$INPUTS/source/jspace_source_snapshot_v1.json" "$ATTEMPT_ROOT/frozen/source/"
cp -- "$INPUTS/source/acquisition_v2/jspace_provider_metadata.json" "$ATTEMPT_ROOT/frozen/source/"
cp -- "$INPUTS/source/acquisition_v2/jspace_source_attestation.json" "$ATTEMPT_ROOT/frozen/source/"
cp -- "$INPUTS/source/acquisition_v2/jspace_source_snapshot_v1.json.verified.publication.json" "$ATTEMPT_ROOT/frozen/source/"
cp -- "$INPUTS/tokens_v2/jspace_wikitext_blocks_v1.json" "$ATTEMPT_ROOT/frozen/tokens/"
cp -- "$INPUTS/tokens_v2/jspace_wikitext_blocks_v1.json.publication.json" "$ATTEMPT_ROOT/frozen/tokens/"

test "$(sha256sum "$ATTEMPT_ROOT/frozen/model/pythia_160m_model_manifest_v1.json" | awk '{print $1}')" = e78edf3255f59a69c03659585da04e6a6ca624c707b1567556180873fd54be17
test "$(sha256sum "$ATTEMPT_ROOT/frozen/model/pythia_160m_model_manifest_v1.json.publication.json" | awk '{print $1}')" = 7207dd18ce0a77d49f443007677527dc486d4317318e187a4f96ea11f88f10df
test "$(sha256sum "$ATTEMPT_ROOT/frozen/source/jspace_source_snapshot_v1.json" | awk '{print $1}')" = 624f9c31208343ca9ea514d1abbd1c8d7a7af953ecd71337ce07e8390189886b
test "$(sha256sum "$ATTEMPT_ROOT/frozen/source/jspace_provider_metadata.json" | awk '{print $1}')" = 8a16fab2fd7b1a268a42759cbde5c0162571e4a4166ac975fe69bbf8a96e39ca
test "$(sha256sum "$ATTEMPT_ROOT/frozen/source/jspace_source_attestation.json" | awk '{print $1}')" = 6a133cae284710669f5a46acb9a990c0c200f64a9213a0a2271555001c031755
test "$(sha256sum "$ATTEMPT_ROOT/frozen/source/jspace_source_snapshot_v1.json.verified.publication.json" | awk '{print $1}')" = 8e214cc1c8a6869a7fc8b6707693d2f26b80110d20ee979dc13f45f20f641cce
test "$(sha256sum "$ATTEMPT_ROOT/frozen/tokens/jspace_wikitext_blocks_v1.json" | awk '{print $1}')" = 9cf4549abfaf6b8e44bce8a2578428d27b45f3e207a32f0472b2f53adeb54b28
test "$(sha256sum "$ATTEMPT_ROOT/frozen/tokens/jspace_wikitext_blocks_v1.json.publication.json" | awk '{print $1}')" = a953a9f3180391f21bfbb4763c47cba8d9df5669e7b3637a650823c4217d1c5f

test -z "$(find "$ATTEMPT_ROOT/environment_pre" -mindepth 1 -print -quit)"
test -z "$(find "$ATTEMPT_ROOT/environment_post" -mindepth 1 -print -quit)"
test -z "$(find "$ATTEMPT_ROOT/output" -mindepth 1 -print -quit)"
test -z "$(find "$ATTEMPT_ROOT/runlog" -mindepth 1 -print -quit)"
test "$(find "$ATTEMPT_ROOT/frozen" -type f | wc -l)" -eq 8

printf 'attempt_root=%s\ncommit=%s\ntree=%s\ndependency_files=15\nstatic_publications=8\n' \
  "$ATTEMPT_ROOT" "$EXPECTED_COMMIT" "$EXPECTED_TREE"
