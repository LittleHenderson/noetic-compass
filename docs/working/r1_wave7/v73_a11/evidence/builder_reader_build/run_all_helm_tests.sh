#!/usr/bin/env bash
# Scratch runner (build of reader v7.3): every test_helm_*.py in the worktree, one process per file, unittest; then the
# four pytest-style files with pytest. Logs go to <log dir>; one summary line per file goes to <log dir>/SUMMARY.txt.
# usage: run_all_helm_tests.sh <worktree> <log dir> <session dir>
set -u
WT="$1"; LOG="$2"; SESS="$3"
mkdir -p "$LOG" "$SESS"
: > "$LOG/SUMMARY.txt"
cd "$WT" || exit 2
for f in test_helm_*.py; do
  m="${f%.py}"
  HELM_SESSION_DIR="$SESS" python -X utf8 -B -m unittest "$m" > "$LOG/unittest_$m.log" 2>&1
  rc=$?
  ran=$(grep -E "^Ran [0-9]+ tests? in" "$LOG/unittest_$m.log" | tail -1)
  res=$(grep -E "^(OK|FAILED|NO TESTS RAN)" "$LOG/unittest_$m.log" | tail -1)
  echo "unittest $m | $ran | $res | rc=$rc" >> "$LOG/SUMMARY.txt"
done
for f in test_helm_agentic_planner.py test_helm_chat_nuance.py test_helm_memory.py test_helm_memory_compact.py; do
  [ -f "$f" ] || { echo "pytest $f | not present" >> "$LOG/SUMMARY.txt"; continue; }
  HELM_SESSION_DIR="$SESS" python -X utf8 -B -m pytest -q -p no:cacheprovider "$f" > "$LOG/pytest_${f%.py}.log" 2>&1
  rc=$?
  last=$(grep -E "(passed|failed|error|skipped|no tests ran)" "$LOG/pytest_${f%.py}.log" | tail -1)
  echo "pytest $f | $last | rc=$rc" >> "$LOG/SUMMARY.txt"
done
cat "$LOG/SUMMARY.txt"
