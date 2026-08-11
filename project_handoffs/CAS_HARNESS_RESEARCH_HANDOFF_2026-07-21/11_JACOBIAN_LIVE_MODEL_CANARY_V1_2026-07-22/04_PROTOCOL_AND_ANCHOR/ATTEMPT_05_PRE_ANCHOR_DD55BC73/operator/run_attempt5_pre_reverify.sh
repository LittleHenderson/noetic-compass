#!/usr/bin/env bash
set -u

ROOT=/workspace/cas-jlcv1-official-f72b89cd-dd55bc73
PYTHON=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
SCRIPT="$ROOT/operator/verify_attempt5_pre.py"
OUTPUT="$ROOT/operator/PRE_INDEPENDENT_REVERIFY.json"
EXIT_RECORD="$ROOT/operator/PRE_INDEPENDENT_REVERIFY.exit"

if [ -e "$OUTPUT" ] || [ -e "$EXIT_RECORD" ]; then
  echo "Refusing to overwrite PRE independent re-verification evidence" >&2
  exit 2
fi

set +e
"$PYTHON" -I -B "$SCRIPT" > "$OUTPUT.tmp" 2>&1
rc=$?
set -e
mv "$OUTPUT.tmp" "$OUTPUT"
printf '%s\n' "$rc" > "$EXIT_RECORD.tmp"
mv "$EXIT_RECORD.tmp" "$EXIT_RECORD"
exit "$rc"
