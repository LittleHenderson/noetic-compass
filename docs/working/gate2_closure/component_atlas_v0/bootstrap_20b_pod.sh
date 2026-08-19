#!/usr/bin/env bash
# Bootstrap a fresh RunPod instance for the GPT-NeoX-20B Component Atlas run.
# Paste-and-run on the new pod. Idempotent: safe to re-run after a disconnect.
#
# Encodes every failure already paid for on pod w0pjqx3ndaxfkg:
#   - venv had NO pip and NO sklearn      -> ensurepip, then install
#   - HF cache is FLAT                    -> HF_HUB_CACHE, not HF_HOME alone
#   - 8 download workers + anon rate limit-> max_workers=3 with retries
#   - nohup died with the SSH session     -> setsid + </dev/null
#   - disk quota hit at 52G               -> checks free space BEFORE downloading
set -u

WS=/workspace
CACHE=$WS/cas-hf-cache
VENV=$WS/atlas-venv
RUN=$WS/cas-atlas-v0
MODEL=EleutherAI/gpt-neox-20b
NEED_GB=60          # 20B (~41G) + blobs + outputs + headroom

echo "=== 0. disk check ==="
mkdir -p "$WS" 2>/dev/null
AVAIL_GB=$(df -BG --output=avail "$WS" 2>/dev/null | tail -1 | tr -dc '0-9')
USED_GB=$(du -sBG "$WS" 2>/dev/null | cut -f1 | tr -dc '0-9')
echo "workspace used=${USED_GB:-?}G  filesystem avail=${AVAIL_GB:-?}G  need>=${NEED_GB}G"
# NOTE: a network FS can report huge avail while a per-pod QUOTA still blocks writes.
# Prove writability at size rather than trusting df.
echo "  probing real writability (1G)..."
if dd if=/dev/zero of="$WS/.quota_probe" bs=1M count=1024 status=none 2>/dev/null; then
  rm -f "$WS/.quota_probe"; echo "  OK: 1G write succeeded"
else
  rm -f "$WS/.quota_probe"; echo "  FATAL: cannot write 1G to $WS -- quota/disk too small. STOP."; exit 1
fi

echo "=== 1. python venv ==="
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV" || { echo "FATAL: venv creation failed"; exit 1; }
fi
VP="$VENV/bin/python"
"$VP" -m ensurepip --upgrade >/dev/null 2>&1
"$VP" -m pip install -q --upgrade pip
echo "  python: $("$VP" --version 2>&1)"

echo "=== 2. deps ==="
"$VP" -m pip install -q torch transformers numpy scikit-learn huggingface_hub accelerate
"$VP" - <<'PY'
import torch, transformers, numpy, sklearn
print(f"  torch {torch.__version__} cuda={torch.cuda.is_available()}")
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    gib = p.total_memory / 1024**3
    print(f"  gpu: {p.name}  {gib:.1f} GiB")
    print(f"  20B fp32 needs 76.6 GiB -> {'FITS' if gib > 80 else 'DOES NOT FIT (use bf16)'}")
    print(f"  20B bf16 needs 38.3 GiB -> {'FITS' if gib > 42 else 'DOES NOT FIT'}")
print(f"  transformers {transformers.__version__}  numpy {numpy.__version__}  sklearn {sklearn.__version__}")
PY

echo "=== 3. cache env ==="
mkdir -p "$CACHE" "$RUN"
export HF_HUB_CACHE="$CACHE"      # authoritative: flat layout, NOT $HF_HOME/hub
export HF_HOME="$CACHE"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DOWNLOAD_TIMEOUT=60
grep -q HF_HUB_CACHE ~/.bashrc 2>/dev/null || cat >> ~/.bashrc <<EOF
export HF_HUB_CACHE=$CACHE
export HF_HOME=$CACHE
export TOKENIZERS_PARALLELISM=false
EOF

echo "=== 4. download $MODEL (detached, retrying) ==="
cat > "$RUN/dl20b.py" <<'PY'
import os, sys, time
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"
from huggingface_hub import snapshot_download
for attempt in range(1, 41):
    try:
        p = snapshot_download("EleutherAI/gpt-neox-20b",
                              allow_patterns=["*.json", "*.txt", "*.safetensors", "tokenizer*"],
                              max_workers=3, etag_timeout=60)
        print("SNAPSHOT_PATH", p, flush=True)
        print("PIN_THIS_COMMIT", os.path.basename(os.path.realpath(p)), flush=True)
        break
    except Exception as e:
        print(f"[retry {attempt}] {type(e).__name__}: {str(e)[:160]}", flush=True)
        time.sleep(min(20, 3 * attempt))
else:
    print("DOWNLOAD_FAILED_AFTER_RETRIES", flush=True); sys.exit(1)
PY
cd "$RUN"
setsid nohup env HF_HUB_CACHE="$CACHE" HF_HOME="$CACHE" "$VP" -u dl20b.py \
    > "$RUN/dl20b.log" 2>&1 < /dev/null &
disown
echo "  started (detached). Progress:"
echo "    du -sh $CACHE/models--EleutherAI--gpt-neox-20b"
echo "    grep -vE 'it/s|Fetching' $RUN/dl20b.log | tail"
echo "  When it finishes, PIN the commit it prints as PIN_THIS_COMMIT."
echo
echo "=== NEXT ==="
echo "  1. wait for SNAPSHOT_PATH / PIN_THIS_COMMIT in $RUN/dl20b.log"
echo "  2. transfer component_atlas_v0.py (see RUNBOOK_POD.md) and verify sha256"
echo "  3. run --preflight FIRST, then the confirmatory pass"
echo "  venv python: $VP"
