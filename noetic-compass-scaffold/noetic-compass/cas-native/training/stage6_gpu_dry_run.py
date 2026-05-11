"""Stage 6 GPU dry-run — real-model-size 1-step wiring validation.

User-gate per docs/working/simplex_mvp_execution_plan_2026_05_11.md §Stage 6.
Does NOT touch v0 inference path. Does NOT load real corpus. Does NOT
emit training-progress noise. ONLY: instantiate the real-size simplex MVP
model on GPU, run ONE forward+backward+optim step on 4 synthetic records,
validate 8 hard checks, and write a Stage 6 report.

Explicit user requirement (2026-05-11):
  "The dry-run must explicitly surface that L_copy and L_phrase_bias_aux
   are still placeholders. Do not let a successful Stage 6 imply the full
   five-loss system is functionally live."

  → Every report line that mentions L_copy / L_phrase_bias_aux carries a
    PLACEHOLDER tag. The 8 gate checks treat them as "shape-correct but
    not exercised here" — not as failures, but not as wins either.

Gate criteria (the 8 hard checks):
  1. Real-size model instantiates on cuda:0
  2. Tensor shape contracts at d_model=384 (encoder + decoder outputs)
  3. Simplex invariants: (p > 0).all() AND row-sum ≈ 1
  4. Device + dtype contracts: params on cuda:0; simplex_trajectory fp32
     even with bf16/fp16 trunk
  5. Param count within ±2M of build-spec estimate (~48.5M)
  6. No NaN/Inf in any tensor (forward + backward)
  7. Gradient flow on encoder AND decoder (non-zero grad norms)
  8. GPU memory <20 GB peak, wall-clock <10 s

Plus the placeholder surfacing requirement (Sec 9 in report).

NaN at any tensor → exit 1. Output: stage6_report.json in --output-dir.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
import types as _types
from dataclasses import dataclass, asdict
from pathlib import Path

import torch
from torch import nn
import torch.optim as optim


_THIS_FILE = Path(__file__).resolve()
_CAS_NATIVE = _THIS_FILE.parent.parent
_PROJECT_ROOT = _CAS_NATIVE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    _pkg = _types.ModuleType("cas_native")
    _pkg.__file__ = str(_CAS_NATIVE / "__init__.py")
    _pkg.__path__ = [str(_CAS_NATIVE)]
    sys.modules["cas_native"] = _pkg


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 6 GPU dry-run.")
    p.add_argument("--output-dir", required=True, type=str)
    p.add_argument("--device", type=str, default="cuda:0")
    p.add_argument("--d-model", type=int, default=384)
    p.add_argument("--encoder-n-layers", type=int, default=4)
    p.add_argument("--encoder-n-heads", type=int, default=6)
    p.add_argument("--decoder-n-layers", type=int, default=6)
    p.add_argument("--decoder-n-heads", type=int, default=6)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--seed", type=int, default=1729)
    # Memory threshold (GB)
    p.add_argument("--memory-threshold-gb", type=float, default=20.0)
    # Wall-clock threshold (seconds)
    p.add_argument("--wallclock-threshold-sec", type=float, default=10.0)
    # Param count budget (millions); ±2M tolerance per build-spec
    p.add_argument("--param-count-target-m", type=float, default=48.5)
    p.add_argument("--param-count-tolerance-m", type=float, default=2.0)
    # Override vocab size for param-count contract (use v1c VALIDTOK 38685
    # to match build-spec budget). Tokenizer remains synthetic for the
    # actual forward; only the embedding/lm_head shapes change.
    p.add_argument("--vocab-size-override", type=int, default=0)
    return p


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ----- Check 0: cuda available -----
    if not torch.cuda.is_available():
        report = {
            "verdict": "FAIL",
            "halt_reason": "torch.cuda.is_available() is False",
        }
        (out_dir / "stage6_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8",
        )
        print(json.dumps(report), flush=True)
        return 1

    device = torch.device(args.device)
    torch.cuda.set_device(device)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device=device)

    report: dict = {
        "event": "stage6_dry_run",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": vars(args),
        "device_name": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "checks": {},
        "placeholders": {},
    }

    try:
        # ----- Imports + tokenizer + collator -----
        from cas_native.model.simplex_encoder import (
            SimplexEncoder, SimplexEncoderConfig, NUM_COGNITIVE_STATES,
        )
        from cas_native.model.typed_fiber_decoder import (
            TypedFiberDecoder, TypedFiberDecoderConfig, NUM_SLOT_TYPES,
        )
        from cas_native.training.fisher_rao_loss import FisherRaoLoss
        from cas_native.training.datasets.simplex_collator import SimplexCollator
        from cas_native.training.tokenizer import HybridCASTokenizer
        from cas_native.training.train_simplex_mvp import (
            synthetic_records, compute_losses, compute_grad_norm,
            DEFAULT_LOSS_WEIGHTS,
        )

        torch.manual_seed(args.seed)

        # Build synthetic records (no data-file dependency on the pod)
        records = synthetic_records(args.batch_size)
        tokenizer = HybridCASTokenizer.from_records(records, freeze=True)
        tokenizer_vocab_size = int(tokenizer.vocab_size)
        # Embedding/lm_head dimension — use override (e.g. v1c VALIDTOK
        # 38685) for budget-aligned param-count check; tokenizer remains
        # synthetic for the forward pass.
        vocab_size = (
            args.vocab_size_override
            if args.vocab_size_override > 0
            else tokenizer_vocab_size
        )

        # Real-size encoder + decoder
        enc_cfg = SimplexEncoderConfig(
            vocab_size=vocab_size,
            d_model=args.d_model,
            n_heads=args.encoder_n_heads,
            ffn_dim=args.d_model * 4,
            n_layers=args.encoder_n_layers,
        )
        dec_cfg = TypedFiberDecoderConfig(
            vocab_size_english=vocab_size,
            d_model=args.d_model,
            n_heads=args.decoder_n_heads,
            ffn_dim=args.d_model * 4,
            n_layers=args.decoder_n_layers,
        )
        encoder = SimplexEncoder(enc_cfg).to(device)
        decoder = TypedFiberDecoder(dec_cfg).to(device)
        fisher_rao_loss = FisherRaoLoss().to(device)

        n_params_enc = sum(p.numel() for p in encoder.parameters() if p.requires_grad)
        n_params_dec = sum(p.numel() for p in decoder.parameters() if p.requires_grad)
        n_params_total = n_params_enc + n_params_dec

        # ----- Check 1: real-size model instantiates on cuda:0 -----
        all_on_device = all(p.device.type == "cuda" for p in encoder.parameters()) \
                        and all(p.device.type == "cuda" for p in decoder.parameters())
        report["checks"]["1_instantiates_on_gpu"] = {
            "pass": all_on_device,
            "encoder_params": n_params_enc,
            "decoder_params": n_params_dec,
            "total_params": n_params_total,
            "total_params_M": round(n_params_total / 1e6, 3),
        }

        # ----- Check 5 (param count budget) -----
        target_m = args.param_count_target_m
        tol_m = args.param_count_tolerance_m
        actual_m = n_params_total / 1e6
        in_budget = abs(actual_m - target_m) <= tol_m
        report["checks"]["5_param_count_in_budget"] = {
            "pass": in_budget,
            "actual_M": round(actual_m, 3),
            "target_M": target_m,
            "tolerance_M": tol_m,
            "delta_M": round(actual_m - target_m, 3),
            "vocab_size_used_for_model": vocab_size,
            "tokenizer_vocab_size": tokenizer_vocab_size,
            "note": (
                "build-spec estimate ~48.5M assumes vocab_size=38685 (v1c "
                "VALIDTOK tokenizer). Pass --vocab-size-override 38685 to "
                "build the model at the real embedding/lm_head size while "
                "keeping the tokenizer synthetic for the forward pass."
            ),
        }

        # ----- Build collator + batch -----
        collator = SimplexCollator(tokenizer, enable_simplex_aux=True)
        batch = collator(records, device=device)
        if batch is None:
            raise RuntimeError("collator returned None on synthetic records")

        # ----- Forward + backward + optim step -----
        optimizer = optim.Adam(
            list(encoder.parameters()) + list(decoder.parameters()),
            lr=1e-4, weight_decay=1e-4,
        )

        t_step_start = time.time()
        optimizer.zero_grad(set_to_none=True)

        enc_out = encoder(
            batch["cas_prefix_ids"] if batch.get("cas_prefix_ids") is not None
            else torch.zeros((args.batch_size, 1), dtype=torch.long, device=device),
            attention_mask=batch.get("cas_prefix_mask"),
        )
        src_padding_mask = batch.get("cas_prefix_mask")
        if src_padding_mask is None:
            src_padding_mask = torch.zeros(
                (args.batch_size, enc_out["source_hidden"].shape[1]),
                dtype=torch.bool, device=device,
            )

        dec_out = decoder(
            decoder_input_ids=batch["lm_decoder_input_ids"],
            source_hidden=enc_out["source_hidden"],
            simplex_trajectory=enc_out["simplex_trajectory"],
            src_ids=batch["cas_prefix_ids"] if batch.get("cas_prefix_ids") is not None
                    else torch.zeros((args.batch_size, 1), dtype=torch.long, device=device),
            src_token_type=batch.get("src_token_type"),
            src_padding_mask=src_padding_mask,
            target_typed_positions=(
                batch["typed_slot_positions"].argmax(dim=-1)
                if "typed_slot_positions" in batch else None
            ),
        )
        out = {**enc_out, **dec_out}

        total, parts = compute_losses(
            out, batch, fisher_rao_loss=fisher_rao_loss, weights=dict(DEFAULT_LOSS_WEIGHTS),
        )

        # ----- Check 6 (no NaN/Inf in forward) -----
        all_finite_forward = bool(torch.isfinite(total).item())
        for k, v in parts.items():
            if isinstance(v, torch.Tensor):
                all_finite_forward = all_finite_forward and bool(torch.isfinite(v).item())
        report["checks"]["6_no_nan_inf"] = {
            "pass": all_finite_forward,
            "loss_total": float(parts["loss_total"].item()) if all_finite_forward else None,
            "per_part": {k: float(v.item()) if isinstance(v, torch.Tensor) else float(v)
                         for k, v in parts.items()},
        }
        if not all_finite_forward:
            report["halt_reason"] = "NaN/Inf in forward"
            report["verdict"] = "FAIL"
            (out_dir / "stage6_report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8",
            )
            print(json.dumps(report, ensure_ascii=False), flush=True)
            return 1

        # Backward + optim
        total.backward()
        enc_grad_norm = compute_grad_norm(encoder.parameters())
        dec_grad_norm = compute_grad_norm(decoder.parameters())
        torch.nn.utils.clip_grad_norm_(
            list(encoder.parameters()) + list(decoder.parameters()), 1.0,
        )
        optimizer.step()
        torch.cuda.synchronize()
        wall_clock = time.time() - t_step_start

        # ----- Check 2 (tensor shape contracts at d_model=384) -----
        L_src = batch["cas_prefix_ids"].shape[1] if isinstance(batch.get("cas_prefix_ids"), torch.Tensor) else 1
        L_out = batch["lm_targets"].shape[1]
        shape_checks = {
            "source_hidden": list(out["source_hidden"].shape),
            "simplex_trajectory": list(out["simplex_trajectory"].shape),
            "simplex_final": list(out["simplex_final"].shape),
            "lm_logits": list(out["lm_logits"].shape),
            "slot_type_logits": list(out["slot_type_logits"].shape),
            "p_copy": list(out["p_copy"].shape),
        }
        shape_pass = (
            out["source_hidden"].shape == (args.batch_size, L_src, args.d_model)
            and out["simplex_trajectory"].shape == (args.batch_size, L_src, NUM_COGNITIVE_STATES)
            and out["simplex_final"].shape == (args.batch_size, NUM_COGNITIVE_STATES)
            and out["slot_type_logits"].shape == (args.batch_size, L_out, NUM_SLOT_TYPES)
            and out["p_copy"].shape == (args.batch_size, L_out, L_src)
        )
        report["checks"]["2_shape_contracts_at_d384"] = {
            "pass": shape_pass,
            "shapes": shape_checks,
            "expected": {
                "source_hidden": [args.batch_size, L_src, args.d_model],
                "simplex_trajectory": [args.batch_size, L_src, NUM_COGNITIVE_STATES],
                "simplex_final": [args.batch_size, NUM_COGNITIVE_STATES],
                "slot_type_logits": [args.batch_size, L_out, NUM_SLOT_TYPES],
                "p_copy": [args.batch_size, L_out, L_src],
            },
        }

        # ----- Check 3 (simplex invariants at real size) -----
        simplex = out["simplex_trajectory"].detach()
        simplex_pos = bool((simplex > 0).all().item())
        row_sums = simplex.sum(dim=-1)
        row_sum_ok = bool(torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-4))
        report["checks"]["3_simplex_invariants"] = {
            "pass": simplex_pos and row_sum_ok,
            "all_p_gt_zero": simplex_pos,
            "rows_sum_to_one": row_sum_ok,
            "min_p": float(simplex.min().item()),
            "max_row_sum_deviation": float((row_sums - 1.0).abs().max().item()),
        }

        # ----- Check 4 (device + dtype contracts) -----
        params_on_cuda = all(p.device.type == "cuda" for p in encoder.parameters()) \
                         and all(p.device.type == "cuda" for p in decoder.parameters())
        simplex_is_fp32 = simplex.dtype == torch.float32
        report["checks"]["4_device_and_dtype_contracts"] = {
            "pass": params_on_cuda and simplex_is_fp32,
            "all_params_on_cuda": params_on_cuda,
            "simplex_trajectory_dtype": str(simplex.dtype),
            "simplex_is_fp32_per_buildspec": simplex_is_fp32,
            "source_hidden_dtype": str(out["source_hidden"].dtype),
        }

        # ----- Check 7 (gradient flow encoder + decoder) -----
        enc_grad_present = enc_grad_norm > 0
        dec_grad_present = dec_grad_norm > 0
        # Also check: every loss term contributed to SOMETHING — but the
        # placeholder check below handles L_copy / L_phrase_bias_aux.
        grads_all_finite = True
        for p in list(encoder.parameters()) + list(decoder.parameters()):
            if p.grad is not None and not torch.isfinite(p.grad).all().item():
                grads_all_finite = False
                break
        report["checks"]["7_gradients_flow_both_paths"] = {
            "pass": enc_grad_present and dec_grad_present and grads_all_finite,
            "encoder_grad_norm": enc_grad_norm,
            "decoder_grad_norm": dec_grad_norm,
            "all_gradients_finite": grads_all_finite,
        }

        # ----- Check 8 (GPU memory + wall-clock) -----
        peak_mem_bytes = torch.cuda.max_memory_allocated(device=device)
        peak_mem_gb = peak_mem_bytes / (1024 ** 3)
        memory_ok = peak_mem_gb < args.memory_threshold_gb
        wallclock_ok = wall_clock < args.wallclock_threshold_sec
        report["checks"]["8_memory_and_wallclock"] = {
            "pass": memory_ok and wallclock_ok,
            "peak_memory_gb": round(peak_mem_gb, 3),
            "memory_threshold_gb": args.memory_threshold_gb,
            "wall_clock_sec": round(wall_clock, 4),
            "wallclock_threshold_sec": args.wallclock_threshold_sec,
        }

        # ----- Check 9 (train_progress JSON-shape: all required fields would emit) -----
        # We don't actually emit train_progress here, but we verify the
        # raw loss/grad/simplex telemetry plumbing produces every field
        # the Stage 5 emit_train_progress() pulls from.
        with torch.no_grad():
            entropy = -(simplex * simplex.clamp_min(1e-12).log()).sum(dim=-1).mean()
            simplex_entropy_mean = float(entropy.item())
            simplex_min_p = float(simplex.min().item())
        loss_lm = float(parts["loss_lm"].item())
        loss_fr = float(parts["loss_fr"].item())
        fr_lm_ratio = (loss_fr / loss_lm) if loss_lm > 0 else 0.0
        train_progress_fields_present = {
            "loss_total": float(parts["loss_total"].item()),
            "loss_lm": loss_lm,
            "loss_fr": loss_fr,
            "loss_slot_type": float(parts["loss_slot_type"].item()),
            "loss_copy": float(parts["loss_copy"].item()),
            "loss_phrase_bias_aux": float(parts["loss_phrase_bias_aux"].item()),
            "grad_norm_encoder": enc_grad_norm,
            "grad_norm_decoder": dec_grad_norm,
            "simplex_entropy_mean": simplex_entropy_mean,
            "simplex_min_p": simplex_min_p,
            "fr_lm_ratio": fr_lm_ratio,
        }
        report["checks"]["9_train_progress_fields_emit"] = {
            "pass": all(v is not None for v in train_progress_fields_present.values()),
            "fields": train_progress_fields_present,
        }

        # ----- Section 10: explicit placeholder labeling (user requirement) -----
        # L_copy is always 0 here because the Stage 1 collator anchor stub
        # sets typed_slot_source = -1 for every position. The pointer-copy
        # path is wired and shape-correct (verified in Stage 2 tests),
        # but produces no live gradient signal until real anchor
        # derivation lands in Stage 7.
        #
        # L_phrase_bias_aux is always 0 because it is a Stage 1
        # placeholder (`torch.zeros((), requires_grad=False)`); the
        # phrase-bias target table needs corpus-aligned labels, also
        # Stage 7.
        #
        # PASSING Stage 6 does NOT imply the full five-loss system is
        # functionally live. Only LM + FR + slot_type are exercised with
        # real learning signal here.
        report["placeholders"] = {
            "L_copy": {
                "value": float(parts["loss_copy"].item()),
                "status": "PLACEHOLDER — not exercised in Stage 6",
                "why_zero": (
                    "Collator anchor stub (Stage 1) emits typed_slot_source = -1 "
                    "for every output position. Pointer-copy path is shape-correct "
                    "but inactive."
                ),
                "live_signal": False,
                "wired_for_stage": 7,
            },
            "L_phrase_bias_aux": {
                "value": float(parts["loss_phrase_bias_aux"].item()),
                "status": "PLACEHOLDER — Stage 1 zeros placeholder",
                "why_zero": (
                    "Implementation in compute_losses() is a "
                    "torch.zeros((), requires_grad=False) until the phrase-bias "
                    "target table is built and corpus-aligned."
                ),
                "live_signal": False,
                "wired_for_stage": 7,
            },
            "warning": (
                "Stage 6 PASS only validates that LM + FR + slot_type are live "
                "and the model wiring is sound at real size. It does NOT validate "
                "L_copy or L_phrase_bias_aux. Treat the 5-loss assembly as "
                "3-of-5 live until Stage 7."
            ),
        }

        # ----- Final verdict -----
        gate_results = report["checks"]
        overall_pass = all(g.get("pass", False) for g in gate_results.values())
        report["verdict"] = "PASS" if overall_pass else "FAIL"
        report["wall_clock_sec_step"] = round(wall_clock, 4)
        report["peak_memory_gb"] = round(peak_mem_gb, 3)

    except Exception as exc:  # any unexpected exception is a FAIL
        report["verdict"] = "FAIL"
        report["halt_reason"] = f"exception: {type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()

    (out_dir / "stage6_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if report.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
