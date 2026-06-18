"""Lane B runner: W0 causal intervention experiment (held-out prompts, 4 conditions).

REQUIRES a loaded HF model + held-out prompts + a frozen refusal direction and α —
i.e. a GPU run on the pod. Generates outputs under no_op/+refusal/-refusal/random;
labels must then be assigned by the cross-family verifier; finally
``verify_causal_gates`` decides CAUSAL_PROOF_LICENSED. No claim flips until all
eight gates pass. See docs/working/w0_prespeech_v5_prereg_20260618.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--heldout-prompts", required=True, type=Path)
    parser.add_argument("--refusal-direction", required=True, type=Path, help=".npy unit-norm W0 direction")
    parser.add_argument("--alpha", required=True, type=float, help="frozen, calibrated intervention gain")
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--output", required=True, type=Path)
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

    prompts = json.loads(args.heldout_prompts.read_text(encoding="utf-8"))
    prompts = [str(p["prompt"]) if isinstance(p, dict) else str(p) for p in (prompts.get("scenarios", prompts) if isinstance(prompts, dict) else prompts)]
    d = torch.tensor(np.load(args.refusal_direction), dtype=torch.float32)

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model).to(args.device).eval()
    hook = CausalInterventionHook(model, d, args.alpha)
    hook.attach()

    conditions = ("no_op", "+refusal", "-refusal", "random")
    results = []
    for pi, prompt in enumerate(prompts):
        for seed in range(args.seeds):
            torch.manual_seed(pi * 1000 + seed)
            for cond in conditions:
                hook.set_condition(cond)
                inputs = tok(prompt, return_tensors="pt").to(args.device)
                with torch.no_grad():
                    gen = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=True, temperature=0.8, top_p=0.95)
                text = tok.decode(gen[0], skip_special_tokens=True)
                results.append({"prompt_idx": pi, "seed": seed, "condition": cond, "output": text, "label": None})
    hook.remove()

    args.output.write_text(json.dumps({
        "status": "OUTPUTS_GENERATED",
        "count": len(results),
        "next": "label outputs with cross-family verifier, then verify_causal_gates(...).",
        "claim": "causal_proof OPEN / NOT LICENSED until all 8 gates pass.",
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"[lane-b] wrote {args.output} ({len(results)} outputs, unlabeled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
