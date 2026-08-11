#!/usr/bin/env bash
set -euo pipefail

ARCHIVE_ROOT=/workspace/cas-jlcv1-attempt3-offpod-archives-cfbe1680
AUDIT_ROOT=/workspace/cas-jlcv1-attempt3-readonly-audit-cfbe1680

test -d /workspace/cas-jlcv1-official-a8969eb7-cfbe1680
test -d /workspace/cas-jlcv1-dependency-bundle-a8969eb7
test -d /workspace/cas-model-a8969eb7
test -d "$AUDIT_ROOT"
test ! -e "$ARCHIVE_ROOT"

umask 077
mkdir -p "$ARCHIVE_ROOT"

tar -C /workspace -cpf "$ARCHIVE_ROOT/official_attempt.tar" cas-jlcv1-official-a8969eb7-cfbe1680
tar -C /workspace -cpf "$ARCHIVE_ROOT/dependency_bundle.tar" cas-jlcv1-dependency-bundle-a8969eb7
tar -C /workspace -cpf "$ARCHIVE_ROOT/model_snapshot.tar" cas-model-a8969eb7

tar -tf "$ARCHIVE_ROOT/official_attempt.tar" > "$AUDIT_ROOT/official_attempt_archive_paths.txt"
tar -tf "$ARCHIVE_ROOT/dependency_bundle.tar" > "$AUDIT_ROOT/dependency_bundle_archive_paths.txt"
tar -tf "$ARCHIVE_ROOT/model_snapshot.tar" > "$AUDIT_ROOT/model_snapshot_archive_paths.txt"

sha256sum "$ARCHIVE_ROOT"/*.tar | LC_ALL=C sort -k 2 > "$AUDIT_ROOT/recovery_archive_sha256.txt"
stat -c '%s\t%n' "$ARCHIVE_ROOT"/*.tar | LC_ALL=C sort -k 2 > "$AUDIT_ROOT/recovery_archive_sizes.txt"

printf 'RECOVERY_ARCHIVES_COMPLETE\n'
