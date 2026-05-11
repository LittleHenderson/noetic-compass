"""Run the 3 post-replay analyses on the saved final checkpoint.

Per user 2026-05-11 diagnostic decision standard. This script is run
ONCE on the pod after the diagnostic replay finishes; it produces:

  - tf_canary_report.json     (Analysis A — teacher-forced canary eval)
  - per_token_trace.json      (Analysis B — greedy trace on rpm_chain)
  - decode_ablations.json     (Analysis C — 4-mode ablation harness)

All three target the SAME loaded checkpoint. No new training. ~3-5 min
total on A6000.
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import torch


_THIS_FILE = Path(__file__).resolve()
_CAS_NATIVE = _THIS_FILE.parent.parent
_PROJECT_ROOT = _CAS_NATIVE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__file__ = str(_CAS_NATIVE / "__init__.py")
    pkg.__path__ = [str(_CAS_NATIVE)]
    sys.modules["cas_native"] = pkg


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint-path", required=True)
    p.add_argument("--tokenizer-path", required=True)
    p.add_argument("--english-bpe-path", default="")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--canary-max-new-tokens", type=int, default=128)
    args = p.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    from cas_native.training.simplex_checkpoint import load_checkpoint
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.training.tokenizer import HybridCASTokenizer
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    from cas_native.evaluation.stage7_canary_pack import canary_pack
    from cas_native.evaluation.teacher_forced_canary import (
        teacher_forced_canary_pack,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    from cas_native.evaluation.decode_ablations import run_decode_ablations_pack

    print(json.dumps({"event": "analysis_start"}), flush=True)

    # ---- Tokenizer ------------------------------------------------------
    tokenizer = HybridCASTokenizer.load(args.tokenizer_path)
    if args.english_bpe_path:
        tokenizer = tokenizer.with_english_bpe(args.english_bpe_path)
    vocab_size = int(tokenizer.vocab_size)
    print(json.dumps({"event": "tokenizer_loaded", "vocab_size": vocab_size}), flush=True)

    # ---- Model ----------------------------------------------------------
    cfg = SimplexTrainConfig(
        data_path="", output_dir="",
        d_model=384, encoder_n_layers=4, decoder_n_layers=6,
        encoder_n_heads=6, decoder_n_heads=6, batch_size=1,
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
    model = build_simplex_mvp_model(
        cfg, vocab_size=vocab_size, vocab_size_english=vocab_size,
    )
    payload = load_checkpoint(
        args.checkpoint_path, model=model, map_location="cpu",
    )
    model = model.to(device)
    print(json.dumps({
        "event": "checkpoint_loaded",
        "step": payload.get("step"),
        "saved_at_utc": payload.get("saved_at_utc"),
    }), flush=True)

    collator = SimplexCollator(tokenizer, enable_simplex_aux=True)
    pack = canary_pack()
    print(json.dumps({"event": "canary_pack_loaded", "n": len(pack)}), flush=True)

    # ---- Analysis A — Teacher-forced canary eval -----------------------
    print(json.dumps({"event": "analysis_A_start"}), flush=True)
    tf_result = teacher_forced_canary_pack(
        model, pack, collator, tokenizer, device=device,
    )
    (out_dir / "tf_canary_report.json").write_text(
        json.dumps(tf_result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(json.dumps({
        "event": "analysis_A_done",
        "summary": tf_result["summary"],
    }), flush=True)

    # ---- Analysis B — Per-token greedy trace on rpm_chain --------------
    print(json.dumps({"event": "analysis_B_start"}), flush=True)
    rpm_records = [
        r for r in pack
        if r.get("v1mix_grammar_category_or_error_class") == "rpm_chain"
    ]
    traces = []
    for rec in rpm_records:
        result = greedy_decode(
            model, rec, collator, tokenizer,
            device=device, max_new_tokens=args.canary_max_new_tokens,
            trace=True, topk=5,
        )
        traces.append({
            "id": rec.get("id"),
            "category": rec.get("v1mix_grammar_category_or_error_class"),
            "target_text": rec.get("reply_text"),
            "generated_text": result["text"],
            "n_tokens_generated": result["n_tokens_generated"],
            "per_token_trace": result.get("per_token_trace", []),
        })
    (out_dir / "per_token_trace.json").write_text(
        json.dumps(traces, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(json.dumps({
        "event": "analysis_B_done",
        "n_records_traced": len(traces),
    }), flush=True)

    # ---- Analysis C — Decode-time ablations ----------------------------
    print(json.dumps({"event": "analysis_C_start"}), flush=True)
    abl_result = run_decode_ablations_pack(
        model, pack, collator, tokenizer,
        device=device, max_new_tokens=args.canary_max_new_tokens,
    )
    (out_dir / "decode_ablations.json").write_text(
        json.dumps(abl_result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    summary_by_mode = abl_result["summary_by_mode"]
    print(json.dumps({
        "event": "analysis_C_done",
        "summary_by_mode": {
            mode: {"verdict": v["verdict"], "by_verdict": v["by_verdict"]}
            for mode, v in summary_by_mode.items()
        },
    }), flush=True)

    print(json.dumps({"event": "all_analyses_done"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
