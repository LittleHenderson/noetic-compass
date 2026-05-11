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
    # v6 (2026-05-11): real v1c tokenizer + stratified v1c corpus.
    p.add_argument("--tokenizer-path", type=str, default="",
                   help="Path to v1c tokenizer.json. When set, --vocab-size-override is ignored.")
    p.add_argument("--english-bpe-path", type=str, default="",
                   help="Optional path to english_bpe.json for composed tokenizer.")
    p.add_argument("--data-path", type=str, default="",
                   help="Path to v1c training JSONL. When set, stratifies a sample by "
                        "v1mix_grammar_category_or_error_class instead of using synthetic.")
    p.add_argument("--stratify-categories", type=str,
                   default="rpm_chain,recipe,fractal,meta_logic,cross_register_omega,state_literal,binary_composition",
                   help="Comma-separated categories to stratify across (v6 requirement).")
    p.add_argument("--records-per-category", type=int, default=3)
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
            synthetic_records, copy_bearing_records,
            compute_losses, compute_grad_norm,
            DEFAULT_LOSS_WEIGHTS,
        )

        torch.manual_seed(args.seed)

        # v6 (2026-05-11): use real v1c VALIDTOK tokenizer + stratified
        # v1c corpus when --tokenizer-path and --data-path are set; fall
        # back to v5 copy-bearing fixture + synthetic-vocab tokenizer.
        use_real_tokenizer = bool(args.tokenizer_path)
        use_real_corpus = bool(args.data_path)

        # ---- Records ------------------------------------------------------
        record_categories: list[str] = []
        if use_real_corpus:
            from cas_native.training.train_simplex_mvp import (
                load_jsonl_records, stratified_sample,
            )
            wanted_cats = [c.strip() for c in args.stratify_categories.split(",") if c.strip()]
            all_records = load_jsonl_records(args.data_path, limit=None)
            # Filter to wanted categories, then take ``records_per_category`` from each
            by_cat: dict[str, list[dict]] = {c: [] for c in wanted_cats}
            for rec in all_records:
                cat = rec.get("v1mix_grammar_category_or_error_class", "unk")
                if cat in by_cat and len(by_cat[cat]) < args.records_per_category:
                    by_cat[cat].append(rec)
            records = []
            for c in wanted_cats:
                for rec in by_cat[c]:
                    records.append(rec)
                    record_categories.append(c)
            if not records:
                raise RuntimeError(
                    f"no records loaded from {args.data_path} matching {wanted_cats}"
                )
        else:
            records = copy_bearing_records(args.batch_size)
            record_categories = ["synthetic_copy"] * len(records)

        # ---- Tokenizer ----------------------------------------------------
        if use_real_tokenizer:
            tokenizer = HybridCASTokenizer.load(args.tokenizer_path)
            if args.english_bpe_path:
                tokenizer = tokenizer.with_english_bpe(args.english_bpe_path)
        else:
            tokenizer = HybridCASTokenizer.from_records(records, freeze=True)
        tokenizer_vocab_size = int(tokenizer.vocab_size)
        # When the real v1c tokenizer is loaded, use ITS vocab size for the
        # model embedding/lm_head — override is for synthetic-tokenizer
        # runs that need to budget-test against the v1c size. Avoid mixing.
        if use_real_tokenizer:
            vocab_size = tokenizer_vocab_size
        else:
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
        # Stage 6 v5: parts now contains a __copy_metrics__ sub-dict that
        # holds NaN-valued telemetry when no valid copy slots exist. NaN
        # in TELEMETRY is allowed (means "not measured"); NaN in actual
        # LOSS values is fail. Filter the sub-dict and check losses only.
        loss_keys = (
            "loss_total", "loss_lm", "loss_fr",
            "loss_slot_type", "loss_copy", "loss_phrase_bias_aux",
        )
        all_finite_forward = bool(torch.isfinite(total).item())
        for k in loss_keys:
            v = parts.get(k)
            if isinstance(v, torch.Tensor):
                all_finite_forward = all_finite_forward and bool(torch.isfinite(v).item())
        report["checks"]["6_no_nan_inf"] = {
            "pass": all_finite_forward,
            "loss_total": float(parts["loss_total"].item()) if all_finite_forward else None,
            "per_part": {
                k: float(parts[k].item())
                for k in loss_keys
                if k in parts and isinstance(parts[k], torch.Tensor)
            },
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
        actual_B = out["source_hidden"].shape[0]
        shape_pass = (
            out["source_hidden"].shape == (actual_B, L_src, args.d_model)
            and out["simplex_trajectory"].shape == (actual_B, L_src, NUM_COGNITIVE_STATES)
            and out["simplex_final"].shape == (actual_B, NUM_COGNITIVE_STATES)
            and out["slot_type_logits"].shape == (actual_B, L_out, NUM_SLOT_TYPES)
            and out["p_copy"].shape == (actual_B, L_out, L_src)
        )
        report["checks"]["2_shape_contracts_at_d384"] = {
            "pass": shape_pass,
            "shapes": shape_checks,
            "expected": {
                "source_hidden": [actual_B, L_src, args.d_model],
                "simplex_trajectory": [actual_B, L_src, NUM_COGNITIVE_STATES],
                "simplex_final": [actual_B, NUM_COGNITIVE_STATES],
                "slot_type_logits": [actual_B, L_out, NUM_SLOT_TYPES],
                "p_copy": [actual_B, L_out, L_src],
            },
            "actual_batch_size": actual_B,
            "args_batch_size": args.batch_size,
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

        # ----- Section 10: explicit live/placeholder labeling (user requirement) -----
        # Stage 6 v5 (2026-05-11): L_copy is now LIVE for the four single-
        # token-mappable slot types (DOMAIN_LETTER / DRIVE_LETTER /
        # REGISTER_LETTER / OMEGA). copy_bearing_records() fixture ensures
        # the reply text contains literal copies of source-side typed
        # identifiers so the collator emits typed_slot_source != -1 and
        # the pointer-copy gradient path is exercised.
        #
        # L_phrase_bias_aux REMAINS PLACEHOLDER per user 2026-05-11: the
        # phrase-bias target table needs corpus-aligned labels, which is
        # corpus-alignment-heavy work that risks expanding the MVP scope
        # before the Stage 7 feasibility gate. Explicitly non-gating.
        loss_copy_value = float(parts["loss_copy"].item())
        copy_metrics = parts.get("__copy_metrics__", {})
        copy_valid_count = int(copy_metrics.get(
            "copy_valid_count", torch.tensor(0.0)
        ).item()) if "copy_valid_count" in copy_metrics else 0
        copy_loss_live_val = float(copy_metrics.get(
            "copy_loss_live", torch.tensor(float("nan"))
        ).item()) if "copy_loss_live" in copy_metrics else float("nan")
        copy_argmax_acc_val = float(copy_metrics.get(
            "copy_argmax_acc", torch.tensor(float("nan"))
        ).item()) if "copy_argmax_acc" in copy_metrics else float("nan")
        copy_entropy_val = float(copy_metrics.get(
            "copy_entropy_valid_mean", torch.tensor(float("nan"))
        ).item()) if "copy_entropy_valid_mean" in copy_metrics else float("nan")

        l_copy_is_live = (
            copy_valid_count > 0
            and not (copy_loss_live_val != copy_loss_live_val)  # not NaN
            and copy_loss_live_val > 0.0
        )
        report["loss_status"] = {
            "L_LM": {
                "value": float(parts["loss_lm"].item()),
                "status": "LIVE",
                "live_signal": True,
            },
            "L_FR": {
                "value": float(parts["loss_fr"].item()),
                "status": "LIVE",
                "live_signal": True,
            },
            "L_slot_type": {
                "value": float(parts["loss_slot_type"].item()),
                "status": "LIVE",
                "live_signal": True,
            },
            "L_copy": {
                "value": loss_copy_value,
                "status": (
                    "LIVE (Stage 6 v5: DOMAIN/DRIVE/REGISTER/OMEGA single-token slots)"
                    if l_copy_is_live else
                    "PLACEHOLDER — no valid copy slots derived this batch"
                ),
                "live_signal": l_copy_is_live,
                "copy_valid_count": copy_valid_count,
                "copy_loss_live": copy_loss_live_val,
                "copy_argmax_acc": copy_argmax_acc_val,
                "copy_entropy_valid_mean": copy_entropy_val,
            },
            "L_phrase_bias_aux": {
                "value": float(parts["loss_phrase_bias_aux"].item()),
                "status": (
                    "PLACEHOLDER (deferred per user 2026-05-11 — corpus-alignment-"
                    "heavy work, explicitly non-gating in Stage 7)"
                ),
                "live_signal": False,
                "wired_for_stage": "deferred",
            },
            "summary": (
                "4-of-5 live (LM + FR + slot_type + copy); phrase_bias_aux "
                "remains placeholder and is NON-GATING for Stage 7."
                if l_copy_is_live else
                "3-of-5 live (LM + FR + slot_type only); L_copy did not fire "
                "this batch — Stage 7 launch NOT authorized."
            ),
        }
        # Backward-compat field for v4 readers
        report["placeholders"] = {
            "L_copy": report["loss_status"]["L_copy"],
            "L_phrase_bias_aux": report["loss_status"]["L_phrase_bias_aux"],
            "warning": report["loss_status"]["summary"],
        }

        # New gate: L_copy must be live (4-of-5 live) for Stage 6 PASS
        report["checks"]["10_l_copy_live"] = {
            "pass": l_copy_is_live,
            "copy_valid_count": copy_valid_count,
            "copy_loss_live": copy_loss_live_val,
            "copy_argmax_acc": copy_argmax_acc_val,
            "note": (
                "L_copy LIVE — typed_slot_source emits valid copy targets "
                "and L_copy gradient flows back through p_copy."
                if l_copy_is_live else
                "L_copy did NOT fire — collator emitted no typed_slot_source. "
                "Check that the smoke pack contains reply tokens that match "
                "source-side typed identifiers (DOMAIN/DRIVE/REGISTER/OMEGA)."
            ),
        }

        # v6 (2026-05-11): per-category breakdown when real corpus is in
        # use. Surfaces (a) how often copy fires per category and (b)
        # which slot types (DOMAIN/DRIVE/REGISTER/OMEGA) appear in each
        # category's source. The user-named gate: "copy slots are not
        # only Ω/register easy cases."
        if record_categories:
            from cas_native.training.datasets.simplex_collator import (
                SLOT_DOMAIN_LETTER, SLOT_DRIVE_LETTER,
                SLOT_REGISTER_LETTER, SLOT_OMEGA,
            )
            type_name = {
                SLOT_DOMAIN_LETTER: "DOMAIN_LETTER",
                SLOT_DRIVE_LETTER: "DRIVE_LETTER",
                SLOT_REGISTER_LETTER: "REGISTER_LETTER",
                SLOT_OMEGA: "OMEGA",
            }
            typed_slot_source_t = batch.get("typed_slot_source")
            src_token_type_t = batch.get("src_token_type")
            per_cat: dict[str, dict] = {}
            for b, cat in enumerate(record_categories):
                if cat not in per_cat:
                    per_cat[cat] = {
                        "records": 0,
                        "copy_valid_count": 0,
                        "src_slot_histogram": {},
                        "cas_samples": [],
                    }
                per_cat[cat]["records"] += 1
                # Copy targets
                if typed_slot_source_t is not None:
                    nvalid = int((typed_slot_source_t[b] >= 0).sum().item())
                    per_cat[cat]["copy_valid_count"] += nvalid
                # Source-side typed slot histogram
                if src_token_type_t is not None:
                    src_types = src_token_type_t[b].tolist()
                    for t in src_types:
                        if t > 0:  # not CONNECTIVE
                            tname = type_name.get(int(t), f"slot_{int(t)}")
                            per_cat[cat]["src_slot_histogram"][tname] = (
                                per_cat[cat]["src_slot_histogram"].get(tname, 0) + 1
                            )
                if len(per_cat[cat]["cas_samples"]) < 2:
                    rec = records[b]
                    per_cat[cat]["cas_samples"].append({
                        "cas": rec.get("cas_expression", "")[:80],
                        "reply": rec.get("reply_text", rec.get("reply", ""))[:120],
                    })

            # Aggregate slot-type fire surface
            all_slot_types_fired: set[str] = set()
            for c, info in per_cat.items():
                for stype in info["src_slot_histogram"]:
                    all_slot_types_fired.add(stype)

            report["v6_per_category_breakdown"] = per_cat
            report["v6_slot_types_observed"] = sorted(all_slot_types_fired)
            report["v6_uses_real_v1c_tokenizer"] = use_real_tokenizer
            report["v6_uses_real_v1c_corpus"] = use_real_corpus
            report["v6_deferred_slot_types_note"] = (
                "STAGE_VAR, COEFFICIENT, FRACTAL_K_LITERAL remain deferred "
                "(multi-token or context-aware). Stage 7 must not penalise "
                "their absence. If v6 shows copy supervision misses "
                "rpm/fractal rows, extend those derivations before Stage 7."
            )
            # Surface the per-category copy rate as a check (not pass/fail,
            # informational). The user's caveat: "if v6 shows copy
            # supervision mostly misses rpm/fractal rows, extend those
            # derivations before Stage 7."
            cats_with_zero = [
                c for c, info in per_cat.items()
                if info["copy_valid_count"] == 0
            ]
            report["v6_categories_with_zero_copy"] = cats_with_zero

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
