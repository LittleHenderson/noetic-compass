#!/usr/bin/env bash
set -euo pipefail

ATTEMPT_ROOT=/workspace/cas-jlcv1-official-a8969eb7-cfbe1680
BUNDLE=/workspace/cas-jlcv1-implementation-a8969eb7.bundle
MANIFEST=/workspace/cas-jlcv1-implementation-manifest-a8969eb7.json
INPUTS=/workspace/cas-jacobian-v1-bootstrap/01_FROZEN_INPUTS
EXPECTED_COMMIT=a8969eb71c6d3e5c43d7ee2b7c7d4aa90dd70fc0
EXPECTED_TREE=cce2d477bb0f423ee6a2669ee680eaac7b999322
EXPECTED_BUNDLE_SHA=0db2c2f6deb3bf797af2b9a42b84714236f66cce48e6c74b769ccbb63c101fff
EXPECTED_MANIFEST_SHA=5561105d014d0bd3a943fc9d498ebc6f657b2e1024018ff95af06f244a9974fa

test ! -e "$ATTEMPT_ROOT"
test "$(sha256sum "$BUNDLE" | awk '{print $1}')" = "$EXPECTED_BUNDLE_SHA"
test "$(sha256sum "$MANIFEST" | awk '{print $1}')" = "$EXPECTED_MANIFEST_SHA"

mkdir -p \
  "$ATTEMPT_ROOT/control" \
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
test -z "$(git -C "$ATTEMPT_ROOT/repo" status --porcelain)"

cp "$BUNDLE" "$ATTEMPT_ROOT/control/jacobian_lens_canary_v1_implementation.bundle"
cp "$MANIFEST" "$ATTEMPT_ROOT/control/jacobian_lens_canary_v1_implementation_manifest.json"

cp "$INPUTS/model/pythia_160m_model_manifest_v1.json" "$ATTEMPT_ROOT/frozen/model/"
cp "$INPUTS/model/pythia_160m_model_manifest_v1.json.publication.json" "$ATTEMPT_ROOT/frozen/model/"
cp "$INPUTS/source/jspace_source_snapshot_v1.json" "$ATTEMPT_ROOT/frozen/source/"
cp "$INPUTS/source/acquisition_v2/jspace_provider_metadata.json" "$ATTEMPT_ROOT/frozen/source/"
cp "$INPUTS/source/acquisition_v2/jspace_source_attestation.json" "$ATTEMPT_ROOT/frozen/source/"
cp "$INPUTS/source/acquisition_v2/jspace_source_snapshot_v1.json.verified.publication.json" "$ATTEMPT_ROOT/frozen/source/"
cp "$INPUTS/tokens_v2/jspace_wikitext_blocks_v1.json" "$ATTEMPT_ROOT/frozen/tokens/"
cp "$INPUTS/tokens_v2/jspace_wikitext_blocks_v1.json.publication.json" "$ATTEMPT_ROOT/frozen/tokens/"

test -z "$(find "$ATTEMPT_ROOT/output" -mindepth 1 -print -quit)"
find "$ATTEMPT_ROOT/frozen" -type f -printf '%P\n' | sort
printf 'attempt_root=%s\ncommit=%s\ntree=%s\n' "$ATTEMPT_ROOT" "$EXPECTED_COMMIT" "$EXPECTED_TREE"
