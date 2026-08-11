#!/usr/bin/env bash
set -u

ROOT=/workspace/cas-jlcv1-official-f72b89cd-dd55bc73
OPERATOR="$ROOT/operator"
CHECK="$OPERATOR/attempt5_live_continuity_check.sh"
OUTPUT="$OPERATOR/LIVE_CONTINUITY_CHECK_V2.txt"
STDERR="$OPERATOR/LIVE_CONTINUITY_CHECK_V2.stderr.txt"
EXIT_RECORD="$OPERATOR/LIVE_CONTINUITY_CHECK_V2.exit"

for target in "$OUTPUT" "$STDERR" "$EXIT_RECORD"; do
  if [[ -e "$target" || -L "$target" ]]; then
    echo "Refusing to overwrite continuity-v2 evidence: $target" >&2
    exit 2
  fi
done

set +e
"$CHECK" > "$OUTPUT.tmp" 2> "$STDERR.tmp"
rc=$?
set -e
mv "$OUTPUT.tmp" "$OUTPUT"
mv "$STDERR.tmp" "$STDERR"
printf '%s\n' "$rc" > "$EXIT_RECORD.tmp"
mv "$EXIT_RECORD.tmp" "$EXIT_RECORD"
exit "$rc"
