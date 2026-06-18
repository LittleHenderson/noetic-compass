"""Lane A runner: capture W0 for a prompt bank, then evaluate pre-speech gates.

REQUIRES a loaded HF model + a labeled comply/refuse prompt bank — i.e. a GPU run
on the pod. It does NOT run as a local unit test. It wires the apparatus:
W0PreSpeechCapture -> per-prompt W0 vectors -> npz -> the existing
evaluate_behavior_v6_matched_prespeech evaluator (which holds the frozen gates).

Claim boundary: a PASS here only makes pre-speech detection license-ELIGIBLE for
this model/layer/protocol; it does not by itself flip any claim. See
docs/working/w0_prespeech_v5_prereg_20260618.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="HF model id, e.g. Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--prompt-bank", required=True, type=Path, help="JSON prompt bank with comply/refuse labels")
    parser.add_argument("--output-dataset", required=True, type=Path)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    try:
        import numpy as np
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        print(f"[lane-a] missing GPU deps: {exc}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(SCRIPT_DIR.parent))
    from app.runtime.w0_capture import W0PreSpeechCapture, validate_windows

    rows = json.loads(args.prompt_bank.read_text(encoding="utf-8"))
    rows = rows.get("scenarios", rows) if isinstance(rows, dict) else rows

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, output_hidden_states=True).to(args.device).eval()
    cap = W0PreSpeechCapture(model)

    feats, labels, payloads, prompts, sids = [], [], [], [], []
    w1_check = None
    for i, row in enumerate(rows):
        prompt = str(row["prompt"])
        inputs = tok(prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            out = model(**inputs)
        w0 = cap.get_w0_list()
        if w1_check is None:
            # one-shot temporal sanity using the next hidden layer as a proxy for W1 drift
            hs = out.hidden_states
            w1_check = validate_windows(w0, hs[1][0, -1, :].float().tolist())
        feats.append(w0)
        labels.append(str(row.get("prompt_injection_status") or row.get("label") or row.get("behavior")))
        payloads.append(str(row.get("payload_class") or "unknown"))
        prompts.append(prompt)
        sids.append(str(row.get("id") or row.get("scenario_id") or f"row_{i}"))
    cap.remove()

    np.savez_compressed(
        args.output_dataset,
        features=np.asarray(feats, dtype=np.float32)[:, None, :],  # [n, 1-layer, hidden]
        layers=np.asarray([0], dtype=np.int64),
        prompts=np.asarray(prompts, dtype=object),
        scenario_ids=np.asarray(sids, dtype=object),
        labels_prompt_injection_status=np.asarray(labels, dtype=object),
        labels_payload_class=np.asarray(payloads, dtype=object),
    )
    print(json.dumps({
        "status": "W0_CAPTURED",
        "rows": len(feats),
        "temporal_check": w1_check,
        "next": "run evaluate_behavior_v6_matched_prespeech.py on the npz; ALL gates must pass.",
        "claim": "OPEN / NOT LICENSED until gates pass.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
