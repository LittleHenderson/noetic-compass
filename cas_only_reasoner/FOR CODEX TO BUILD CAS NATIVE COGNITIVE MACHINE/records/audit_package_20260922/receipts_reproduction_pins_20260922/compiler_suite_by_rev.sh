#!/usr/bin/env bash
# Run the five-file compiler suite at several revisions, each from a clean `git archive` export of the three
# folders the suite reads (noetic-compass-scaffold/noetic-compass, offline-cas, dist). Implementation and tests
# come from the SAME revision here; the revision is the pin.
set -u
REPO="$1"; OUT="$2"; shift 2
PY=/c/Python314/python.exe
mkdir -p "$OUT/tmp"
export TEMP="$OUT/tmp" TMP="$OUT/tmp" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONIOENCODING=utf-8
for REV in "$@"; do
  D="$OUT/rev_$REV"
  rm -rf "$D"; mkdir -p "$D"
  git -C "$REPO" archive "$REV" -- noetic-compass-scaffold/noetic-compass offline-cas dist | tar -x -C "$D"
  FILES=""
  for f in tests/test_notation_compiler.py tests/test_notation_compiler_nesting_and_defects.py \
           tests/test_notation_compiler_continuation.py tests/test_offline_help_text_canon.py tests/test_full_demo_program.py; do
    [ -f "$D/noetic-compass-scaffold/noetic-compass/$f" ] && FILES="$FILES $f"
  done
  ( cd "$D/noetic-compass-scaffold/noetic-compass" && \
    $PY -B -m pytest --noconftest -o addopts= $FILES -q -p no:cacheprovider --junitxml="$OUT/compiler_suite_$REV.xml" 2>&1 \
      | tail -1 | tr -d '\r' > "$OUT/compiler_suite_$REV.txt" )
  echo "$REV files:[$FILES ] -> $(cat "$OUT/compiler_suite_$REV.txt")"
done
