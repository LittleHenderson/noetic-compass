#!/usr/bin/env bash
set -euo pipefail

RECORDS_ROOT=/workspace/cas-jlcv1-attempt3-readonly-audit-cfbe1680
OUTPUT="$RECORDS_ROOT/records_sha256_final_remote.txt"

test -d "$RECORDS_ROOT"
test ! -e "$OUTPUT"

(
  cd "$RECORDS_ROOT"
  find . -maxdepth 1 -type f ! -name records_sha256_final_remote.txt -print0 |
    LC_ALL=C sort -z |
    xargs -0 sha256sum
) > "$OUTPUT"

printf 'FINAL_REMOTE_RECORD_HASHES_COMPLETE\n'
