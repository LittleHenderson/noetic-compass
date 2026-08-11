#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT=/workspace/cas-tks-anchor-diagnostic-20260721
REPO="$ROOT/source/repo"
SOURCE="$ROOT/source/operational_canary"
PY="$ROOT/venv/bin/python"
OUT="$ROOT/artifacts/canary-8prompt-2layer"
LOG="$ROOT/logs/tks_definition_anchor_canary.log"
PREFLIGHT="$ROOT/receipts/pythia_160m_hook_preflight.json"
PREFLIGHT_LOG="$ROOT/logs/pythia_160m_hook_preflight.log"
ARCHIVE="$ROOT/source/cas-tks-anchor-diagnostic-20260721-da00bd94.zip"

[[ -x "$PY" ]]
[[ -d "$REPO" ]]
[[ -d "$SOURCE" ]]
[[ ! -e "$OUT" ]]
[[ ! -e "$LOG" ]]

export HF_HOME="$ROOT/hf_cache"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export PYTHONHASHSEED=20260721
export CUDA_VISIBLE_DEVICES=0

COMMON=(
  --repository-root "$REPO"
  --canary-source-dir "$SOURCE"
  --preflight-receipt "$PREFLIGHT"
  --preflight-log "$PREFLIGHT_LOG"
  --source-archive "$ARCHIVE"
)

"$PY" "$SOURCE/build_verified_canary_bundle.py" \
  --mode validate-preflight "${COMMON[@]}"

"$PY" "$SOURCE/run_tks_definition_anchor_canary.py" \
  --repository-root "$REPO" \
  --output-dir "$OUT" \
  2>&1 | tee "$LOG"

"$PY" "$SOURCE/build_verified_canary_bundle.py" \
  --mode build "${COMMON[@]}" \
  --canary-output-dir "$OUT" \
  --canary-log "$LOG"
