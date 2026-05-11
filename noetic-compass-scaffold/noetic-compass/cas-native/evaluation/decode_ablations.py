"""Decode-time ablations — diagnostic infra piece 4.

Per user 2026-05-11 (Stage 7 v7.1b post-mortem). Same checkpoint, four
(plus optional fifth) decode strategies, compare canary damage scores
side-by-side.

Modes:
  - "full"           : the production decode path (lm_logits.argmax with
                       phrase-bias mixed in via the decoder's gate)
  - "lm_only"        : zero out the phrase-bias contribution from the
                       decoder; decode purely from the lm_head
  - "copy_disabled"  : prevent any decoded token id from being one that
                       the simplex collator would classify as a typed
                       slot (DOMAIN_LETTER, DRIVE_LETTER, REGISTER_LETTER,
                       OMEGA). Token-level mask, not a hard decoder
                       rewire — the model still produces p_copy but we
                       suppress emission of those identifiers.
  - "phrase_bias_disabled"
                     : decoder's phrase_bias_alpha is temporarily set
                       to 0 during decode. Tests whether the soft
                       simplex-conditioned phrase bias is itself the
                       cause of the lm_head's entropy collapse.
  - "hard_full"      : Candidate C 2026-05-11. Same as "full" but with
                       hard typed-fiber emission enabled — at
                       hard_typed_emission_slots positions (default
                       STAGE_VAR only) with copy.max ≥ threshold AND
                       source-token-type match, emit src_ids[p_copy.argmax]
                       instead of lm_logits.argmax. Conditionally
                       included by the caller (requires
                       hard_typed_emission=True).

This is the SAME checkpoint, no retraining. The cost is N records ×
M strategies × max_new_tokens forward passes. With max_new_tokens=128,
11 records, 4 strategies = ~5600 model calls. ~3 minutes on A6000.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Optional

import torch
from torch import nn

from cas_native.evaluation.sample_decoder import greedy_decode


ABLATION_MODES = ("full", "lm_only", "copy_disabled", "phrase_bias_disabled")
# Modes recognised by run_decode_ablations_one in addition to ABLATION_MODES.
# "hard_full" is conditionally added by callers when hard_typed_emission=True.
EXTENDED_ABLATION_MODES = ABLATION_MODES + ("hard_full",)


@contextmanager
def _phrase_bias_disabled(decoder: nn.Module):
    """Context manager that temporarily zeros decoder.phrase_bias_alpha."""
    if not hasattr(decoder, "phrase_bias_alpha"):
        yield
        return
    saved = decoder.phrase_bias_alpha.data.clone()
    try:
        with torch.no_grad():
            decoder.phrase_bias_alpha.data.fill_(0.0)
        yield
    finally:
        with torch.no_grad():
            decoder.phrase_bias_alpha.data.copy_(saved)


def _build_copy_id_mask(tokenizer: Any) -> set[int]:
    """Return token-ids whose decoded string looks like a typed-slot
    identifier (DOMAIN_LETTER, DRIVE_LETTER, REGISTER_LETTER, OMEGA).

    Used by the ``copy_disabled`` ablation to mask those ids in lm_logits
    before argmax — so the model can't emit them at all.
    """
    from cas_native.training.datasets.simplex_collator import (
        classify_source_token, SLOT_CONNECTIVE,
    )
    masked: set[int] = set()
    # Scan vocab via token_ids_to_tokens if available.
    if not hasattr(tokenizer, "id2word"):
        return masked
    for tok_id, tok_str in tokenizer.id2word.items():
        if classify_source_token(tok_str) != SLOT_CONNECTIVE:
            masked.add(int(tok_id))
    return masked


def _decode_with_lm_logits_mask(
    model: nn.Module,
    record: dict[str, Any],
    collator: Any,
    tokenizer: Any,
    *,
    masked_token_ids: set[int],
    device: torch.device,
    max_new_tokens: int,
) -> dict[str, Any]:
    """Greedy decode with an additional logits mask applied each step.

    Mirrors greedy_decode but suppresses ``masked_token_ids`` from lm_logits
    by setting them to -inf before argmax. Used for ``copy_disabled`` mode.
    """
    bos = int(tokenizer.BOS_ID)
    eos = int(tokenizer.EOS_ID)
    batch = collator([record], device=device)
    if batch is None:
        return {"text": "", "token_ids": [], "n_tokens_generated": 0,
                "hit_eos": False, "slot_type_trace": [], "error": "no_batch"}

    dec_input = torch.tensor([[bos]], dtype=torch.long, device=device)
    generated: list[int] = []
    slot_trace: list[int] = []
    hit_eos = False
    mask_idx = torch.tensor(sorted(masked_token_ids), dtype=torch.long, device=device) \
        if masked_token_ids else None

    model.eval()
    with torch.no_grad():
        for _ in range(max_new_tokens):
            forward_batch = dict(batch)
            forward_batch["lm_decoder_input_ids"] = dec_input
            forward_batch.pop("typed_slot_positions", None)
            forward_batch.pop("typed_slot_source", None)
            out = model(forward_batch)
            last_logits = out["lm_logits"][0, -1, :].clone()
            if mask_idx is not None:
                last_logits[mask_idx] = float("-inf")
            next_id = int(last_logits.argmax().item())
            slot_trace.append(int(out["slot_type_logits"][0, -1, :].argmax().item()))
            if next_id == eos:
                hit_eos = True
                break
            generated.append(next_id)
            dec_input = torch.cat(
                [dec_input, torch.tensor([[next_id]], dtype=torch.long, device=device)],
                dim=1,
            )

    text = tokenizer.decode(generated, skip_special=True) if generated else ""
    return {
        "text": text,
        "token_ids": generated,
        "n_tokens_generated": len(generated),
        "hit_eos": hit_eos,
        "slot_type_trace": slot_trace,
    }


def run_decode_ablations_one(
    model: nn.Module,
    record: dict[str, Any],
    collator: Any,
    tokenizer: Any,
    *,
    device: torch.device,
    max_new_tokens: int = 128,
    modes: tuple[str, ...] = ABLATION_MODES,
    hard_typed_emission: bool = False,
    copy_confidence_threshold: float = 0.5,
    hard_typed_emission_slots: Optional[Iterable[int]] = None,
) -> dict[str, dict[str, Any]]:
    """Run the decode ablations on ONE record. Returns dict keyed by mode.

    Candidate C 2026-05-11: when ``hard_full`` appears in ``modes``, this
    method runs ``greedy_decode`` with ``hard_typed_emission=True`` plus
    the caller-supplied copy threshold + slot scope. The other four modes
    are unaffected by these flags (they remain pure baseline / ablation
    controls so the comparison stays interpretable).
    """
    out: dict[str, dict[str, Any]] = {}
    # Decoder reference for phrase_bias_disabled
    decoder = getattr(model, "decoder", None)

    for mode in modes:
        if mode == "full":
            out[mode] = greedy_decode(
                model, record, collator, tokenizer,
                device=device, max_new_tokens=max_new_tokens,
            )
        elif mode == "hard_full":
            # Candidate C: same decode path as "full" but with hard
            # typed-fiber emission active. Compared side-by-side against
            # "full" this isolates the effect of hard routing alone.
            out[mode] = greedy_decode(
                model, record, collator, tokenizer,
                device=device, max_new_tokens=max_new_tokens,
                hard_typed_emission=True,
                copy_confidence_threshold=copy_confidence_threshold,
                hard_typed_emission_slots=hard_typed_emission_slots,
            )
        elif mode == "phrase_bias_disabled":
            if decoder is None:
                out[mode] = {"error": "model has no .decoder attribute"}
                continue
            with _phrase_bias_disabled(decoder):
                out[mode] = greedy_decode(
                    model, record, collator, tokenizer,
                    device=device, max_new_tokens=max_new_tokens,
                )
        elif mode == "copy_disabled":
            masked = _build_copy_id_mask(tokenizer)
            out[mode] = _decode_with_lm_logits_mask(
                model, record, collator, tokenizer,
                masked_token_ids=masked,
                device=device, max_new_tokens=max_new_tokens,
            )
            out[mode]["n_masked_token_ids"] = len(masked)
        elif mode == "lm_only":
            # "LM only" = phrase_bias disabled AND copy-eligible ids masked.
            # Pure lm_head decode without phrase-bias mix or copy-identifier
            # emission. Tests whether the bare LM produces coherent prose.
            if decoder is None:
                out[mode] = {"error": "model has no .decoder attribute"}
                continue
            masked = _build_copy_id_mask(tokenizer)
            with _phrase_bias_disabled(decoder):
                out[mode] = _decode_with_lm_logits_mask(
                    model, record, collator, tokenizer,
                    masked_token_ids=masked,
                    device=device, max_new_tokens=max_new_tokens,
                )
            out[mode]["n_masked_token_ids"] = len(masked)
        else:
            out[mode] = {"error": f"unknown mode {mode!r}"}
    return out


def run_decode_ablations_pack(
    model: nn.Module,
    canary_records: list[dict[str, Any]],
    collator: Any,
    tokenizer: Any,
    *,
    device: torch.device,
    max_new_tokens: int = 128,
    modes: tuple[str, ...] = ABLATION_MODES,
    hard_typed_emission: bool = False,
    copy_confidence_threshold: float = 0.5,
    hard_typed_emission_slots: Optional[Iterable[int]] = None,
) -> dict[str, Any]:
    """Run the 4 ablations across the full canary pack.

    Returns dict with per-mode pack damage verdicts + per-record samples.
    """
    from cas_native.evaluation.damage_detector import (
        analyze_sample, aggregate_pack_verdict,
    )

    was_training = model.training
    try:
        per_record_results: list[dict[str, Any]] = []
        per_mode_damage: dict[str, list[Any]] = {m: [] for m in modes}
        for rec in canary_records:
            mode_outputs = run_decode_ablations_one(
                model, rec, collator, tokenizer,
                device=device, max_new_tokens=max_new_tokens, modes=modes,
                hard_typed_emission=hard_typed_emission,
                copy_confidence_threshold=copy_confidence_threshold,
                hard_typed_emission_slots=hard_typed_emission_slots,
            )
            rec_entry = {
                "id": rec.get("id"),
                "category": rec.get("v1mix_grammar_category_or_error_class"),
                "task": rec.get("v1mix_task_type"),
                "cas_expression": rec.get("cas_expression"),
                "target_text": rec.get("reply_text") or rec.get("reply", ""),
                "modes": {},
            }
            for mode in modes:
                gen_text = mode_outputs[mode].get("text", "")
                damage = analyze_sample(gen_text, rec_entry["target_text"])
                mode_entry: dict[str, Any] = {
                    "generated_text": gen_text,
                    "n_tokens_generated": mode_outputs[mode].get("n_tokens_generated", 0),
                    "hit_eos": mode_outputs[mode].get("hit_eos", False),
                    "damage_verdict": damage.verdict,
                    "damage_severity": damage.severity_score,
                    "damage_signatures": damage.signatures,
                }
                # Surface slot-trace + route-counts when present (always
                # for hard_full; only when hard mode is on for "full").
                slot_trace = mode_outputs[mode].get("slot_type_trace")
                if slot_trace is not None:
                    mode_entry["slot_type_trace"] = list(slot_trace)[:40]
                route_counts = mode_outputs[mode].get(
                    "emission_route_counts"
                )
                if route_counts is not None:
                    mode_entry["emission_route_counts"] = route_counts
                rec_entry["modes"][mode] = mode_entry
                per_mode_damage[mode].append(damage)
            per_record_results.append(rec_entry)
    finally:
        if was_training:
            model.train()

    summary: dict[str, dict[str, Any]] = {}
    for mode in modes:
        summary[mode] = aggregate_pack_verdict(per_mode_damage[mode])
        # Sum route counts across records for this mode (only meaningful
        # for "hard_full"; harmless for other modes — their records
        # don't carry emission_route_counts so the totals stay zero).
        total_lm = 0
        total_copy = 0
        for rec in per_record_results:
            mode_block = rec["modes"].get(mode, {})
            counts = mode_block.get("emission_route_counts")
            if counts is not None:
                total_lm += int(counts.get("lm", 0))
                total_copy += int(counts.get("copy", 0))
        if total_lm + total_copy > 0:
            summary[mode]["emission_routes_pack"] = {
                "lm_emissions": total_lm,
                "copy_emissions": total_copy,
                "copy_fraction": (
                    total_copy / max(total_lm + total_copy, 1)
                ),
            }

    return {
        "modes": list(modes),
        "summary_by_mode": summary,
        "per_record": per_record_results,
    }
