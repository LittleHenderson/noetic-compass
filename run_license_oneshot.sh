#!/usr/bin/env bash
# One-shot closed-book KWIK license test on a FRESH GPU pod.
#
# Hard-won rules baked in (this is what burned the last pod):
#   * NEVER install a quantizer (gptqmodel / autoawq / torchao) — that churns torch and
#     poisons the op registry. Use bf16 only.
#   * NEVER reinstall torch/torchvision. Use the pod's pre-matched torch.
#   * REMOVE torchvision/torchaudio so transformers skips them cleanly (text models don't
#     need them; a mismatched torchvision is what threw `operator torchvision::nms`).
#
# Usage:
#   bash run_license_oneshot.sh Qwen/Qwen2.5-32B-Instruct 6000 auto      # 32B bf16, multi-GPU
#   bash run_license_oneshot.sh Qwen/Qwen2.5-72B-Instruct 6000 auto      # 72B bf16 (needs >=145GB disk)
set -uo pipefail
MODEL="${1:-Qwen/Qwen2.5-32B-Instruct}"; N="${2:-6000}"; DM="${3:-auto}"
cd /root

echo "=== [1/5] clean deps (no quantizer; remove torchvision/torchaudio) ==="
pip uninstall -y torchvision torchaudio gptqmodel autoawq torchao 2>/dev/null || true
pip install -q "transformers>=5.0,<6" accelerate datasets scikit-learn || { echo "PIP_FAIL"; exit 1; }

echo "=== [2/5] smoke: Qwen2 class import + tiny model load ==="
python3 -c 'from transformers.models.qwen2 import Qwen2ForCausalLM; import torch; print("import ok, torch", torch.__version__, "cuda", torch.cuda.is_available(), "ngpu", torch.cuda.device_count())' || { echo "IMPORT_FAIL"; exit 1; }

echo "=== [3/5] capture ($MODEL, N=$N, device_map=$DM) ==="
python3 -u closedbook_kwik_capture.py --model-id "$MODEL" --device-map "$DM" --n "$N" \
  --out /root/kwik_lic.npz --gen-out /root/kwik_lic_gens.jsonl || { echo "CAPTURE_FAIL"; exit 1; }

echo "=== [4/5] raw gate (floor/margin/residual/held-out) ==="
python3 -u lic_eval_fast.py /root/kwik_lic.npz --out=/root/lic_report_raw.json 2>&1 | tail -8

echo "=== [5/5] text-orthogonal gate (clean labels + residual-blind probe) ==="
python3 -u lic_eval_ortho.py /root/kwik_lic.npz /root/kwik_lic_gens.jsonl --out=/root/lic_report_ortho.json 2>&1 | tail -8

echo "=== DONE.  reports: /root/lic_report_raw.json  /root/lic_report_ortho.json ==="
echo "If deterministic gates PASS in either, run the permutation:"
echo "  python3 -u lic_eval_ortho.py /root/kwik_lic.npz /root/kwik_lic_gens.jsonl --perm --out=/root/lic_report_ortho_perm.json"
