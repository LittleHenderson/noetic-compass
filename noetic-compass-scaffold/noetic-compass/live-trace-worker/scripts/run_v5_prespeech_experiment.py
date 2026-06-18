"""Lane A runner: capture W0 for a same-prompt comply/refuse bank.

Requires a loaded HF model plus a labeled comply/refuse prompt bank, so this is
for the GPU pod, not local unit tests. It writes a W0-only dataset for
``evaluate_behavior_v5_prespeech.py`` and a temporal metadata receipt proving
W0 was checked against W1/W8 windows.

Claim boundary: capture alone licenses nothing. A future PASS only makes
pre-speech detection license-eligible for this model/layer/protocol; causal
proof still needs Lane B intervention gates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="HF model id, e.g. Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--prompt-bank", required=True, type=Path, help="JSON prompt bank with COMPLIED/REFUSED labels")
    parser.add_argument("--output-dataset", required=True, type=Path)
    parser.add_argument("--metadata-output", type=Path, default=None)
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
    model = (
        AutoModelForCausalLM.from_pretrained(args.model, output_hidden_states=True)
        .to(args.device)
        .eval()
    )
    cap = W0PreSpeechCapture(model)

    feats: list[Any] = []
    labels: list[str] = []
    payloads: list[str] = []
    domains: list[str] = []
    prompts: list[str] = []
    scenario_ids: list[str] = []
    trace_ids: list[str] = []
    temporal_checks: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        prompt = str(row["prompt"])
        inputs = tok(prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            out0 = model(**inputs, output_hidden_states=True)
        w0 = cap.get_w0_list()
        if w0 is None:
            raise RuntimeError(f"row {index} did not produce a W0 embedding capture")
        w1, w8 = capture_generated_windows(
            model=model,
            prompt_input_ids=inputs["input_ids"],
            prompt_attention_mask=inputs.get("attention_mask"),
            first_logits=out0.logits,
            max_steps=8,
            torch_module=torch,
        )
        temporal_checks.append(validate_windows(w0, w1, w8))

        label = str(
            row.get("behavior") or row.get("label") or row.get("expected_behavior") or ""
        ).upper()
        if label not in {"COMPLIED", "REFUSED"}:
            raise RuntimeError(f"row {index} missing COMPLIED/REFUSED behavior label")

        group_id = str(row.get("prompt_group_id") or row.get("group_id") or row.get("id") or f"row_{index}")
        sample_seed = row.get("seed", row.get("sample_seed", index))

        feats.append(w0)
        labels.append(label)
        payloads.append(str(row.get("payload_class") or "unknown"))
        domains.append(str(row.get("domain") or "unknown"))
        prompts.append(prompt)
        scenario_ids.append(f"{group_id}::seed_{sample_seed}")
        trace_ids.append(str(row.get("trace_id") or row.get("id") or row.get("scenario_id") or f"trace_{index}"))

    cap.remove()

    args.output_dataset.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dataset,
        features=np.asarray(feats, dtype=np.float32)[:, None, :],
        layers=np.asarray([0], dtype=np.int64),
        prompts=np.asarray(prompts, dtype=object),
        scenario_ids=np.asarray(scenario_ids, dtype=object),
        trace_ids=np.asarray(trace_ids, dtype=object),
        axis_names=np.asarray(["behavior", "payload_class", "domain"], dtype=object),
        labels_behavior=np.asarray(labels, dtype=object),
        labels_payload_class=np.asarray(payloads, dtype=object),
        labels_domain=np.asarray(domains, dtype=object),
    )

    metadata = {
        "status": "W0_CAPTURED",
        "rows": len(feats),
        "temporal_checks": temporal_checks,
        "temporal_checks_valid": all(check.get("valid") is True for check in temporal_checks),
        "next": "run evaluate_behavior_v5_prespeech.py on the npz; ALL gates must pass.",
        "claim": "OPEN / NOT LICENSED until gates pass.",
    }
    if args.metadata_output:
        args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_output.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


def capture_generated_windows(
    *,
    model: object,
    prompt_input_ids: Any,
    prompt_attention_mask: Any,
    first_logits: Any,
    max_steps: int,
    torch_module: Any,
) -> tuple[list[float] | None, list[float] | None]:
    """Greedy W1/W8 temporal-control windows at embedding level."""

    input_ids = prompt_input_ids.clone()
    attention_mask = (
        prompt_attention_mask.clone()
        if prompt_attention_mask is not None
        else torch_module.ones_like(input_ids)
    )
    next_token = first_logits[:, -1, :].argmax(dim=-1, keepdim=True)
    w1 = None
    w8 = None
    steps = max(1, int(max_steps))
    for step in range(1, steps + 1):
        input_ids = torch_module.cat([input_ids, next_token], dim=1)
        attention_mask = torch_module.cat([attention_mask, torch_module.ones_like(next_token)], dim=1)
        with torch_module.no_grad():
            out = model(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
        window = out.hidden_states[0][0, -1, :].float().tolist()
        if step == 1:
            w1 = window
        if step == steps:
            w8 = window
        next_token = out.logits[:, -1, :].argmax(dim=-1, keepdim=True)
    return w1, w8


if __name__ == "__main__":
    raise SystemExit(main())
