"""Lane B runner: W0 causal intervention experiment on held-out prompts.

Requires a loaded HF model, held-out prompts, a frozen refusal direction, and a
frozen intervention gain. It writes JSONL rows compatible with
``analyze_behavior_v5_causal.py`` after labels are filled by a cross-family
verifier.

Claim boundary: generated outputs are not causal proof. Causal proof remains
OPEN / NOT LICENSED until the labeled rows pass all paired-seed gates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--heldout-prompts", required=True, type=Path)
    parser.add_argument("--refusal-direction", required=True, type=Path, help=".npy unit-norm W0 direction")
    parser.add_argument("--alpha", required=True, type=float, help="frozen, calibrated intervention gain")
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--output", required=True, type=Path, help="JSONL output path")
    parser.add_argument("--metadata-output", type=Path, default=None)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    try:
        import numpy as np
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        print(f"[lane-b] missing GPU deps: {exc}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(SCRIPT_DIR.parent))
    from app.runtime.causal_intervention import CausalInterventionHook

    prompt_rows = load_prompt_rows(args.heldout_prompts)
    direction = torch.tensor(np.load(args.refusal_direction), dtype=torch.float32, device=args.device)

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model).to(args.device).eval()
    hook = CausalInterventionHook(model, direction, args.alpha)
    hook.attach()

    conditions = ("no_op", "+refusal", "-refusal", "random")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.output.open("w", encoding="utf-8") as handle:
        for prompt_index, prompt_row in enumerate(prompt_rows):
            prompt_id = str(prompt_row.get("prompt_id") or prompt_row.get("id") or f"prompt_{prompt_index}")
            prompt = str(prompt_row["prompt"])
            for seed in range(args.seeds):
                for condition in conditions:
                    torch.manual_seed(prompt_index * 1000 + seed)
                    hook.set_condition(condition)
                    inputs = tok(prompt, return_tensors="pt").to(args.device)
                    with torch.no_grad():
                        generated = model.generate(
                            **inputs,
                            max_new_tokens=args.max_new_tokens,
                            do_sample=True,
                            temperature=0.8,
                            top_p=0.95,
                        )
                    text = tok.decode(generated[0], skip_special_tokens=True)
                    row = {
                        "prompt_id": prompt_id,
                        "seed": seed,
                        "condition": condition,
                        "label": None,
                        "output": text,
                    }
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                    count += 1
    hook.remove()

    metadata = {
        "status": "OUTPUTS_GENERATED_UNLABELED",
        "count": count,
        "condition_count": len(conditions),
        "seeds_per_prompt": int(args.seeds),
        "next": "label JSONL rows with cross-family verifier, then run analyze_behavior_v5_causal.py.",
        "claim": "causal_proof OPEN / NOT LICENSED until all paired-seed gates pass.",
    }
    if args.metadata_output:
        args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_output.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


def load_prompt_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if isinstance(row, dict):
            if "prompt" not in row:
                raise RuntimeError(f"heldout prompt row {index} missing prompt")
            out.append(row)
        else:
            out.append({"prompt_id": f"prompt_{index}", "prompt": str(row)})
    return out


if __name__ == "__main__":
    raise SystemExit(main())
