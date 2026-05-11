"""Stage 7 v7.1 greedy decoder for canary sample reads.

Per user 2026-05-11. Generates greedy text from the simplex MVP model for
each canary record, returning decoded strings the damage detector can scan.

Default decoder strategy: lm_logits.argmax only. The model's slot_type /
p_copy heads are loss-side supervisory signals and are NOT consulted for
token selection. Stage 7 is feasibility, not product quality; the
simplest decode suffices.

Candidate C (2026-05-11, opt-in via ``hard_typed_emission=True``): at
positions where the slot_type head predicts a hard-emission-eligible
slot (default ``{SLOT_STAGE_VAR}``), the copy head replaces the lm_head
for that step IF AND ONLY IF (a) p_copy.max ≥ ``copy_confidence_threshold``,
(b) the source position pointed at by p_copy.argmax is unpadded, (c) the
source token is not a PAD/BOS/EOS special, and (d) the source token's
type ID matches the predicted slot type. If any guard fails, the step
falls back to lm_logits.argmax.

For typed-slot output positions (when the slot_type head predicts one of
1..7), an inline trace flag is added to the trace so downstream analysis
can see whether the model is even ATTEMPTING to use the copy mechanism.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

import torch
from torch import nn

# Default hard-emission slot scope per audit 2026-05-11. STAGE_VAR is the
# specific identifier-recovery failure mode (canonical_stage_var_recovery
# 0/4 across the diagnostic baseline). Restricting to STAGE_VAR by default
# keeps the experiment focused; widen via ``hard_typed_emission_slots``.
_SLOT_STAGE_VAR = 2
_DEFAULT_HARD_EMISSION_SLOTS = frozenset({_SLOT_STAGE_VAR})
# Slots that are NEVER hard-emission-eligible regardless of caller config:
# CONNECTIVE (0) and NOETIC_PHRASE (8) always emit via LM.
_HARD_EMISSION_NEVER = frozenset({0, 8})


def greedy_decode(
    model: nn.Module,
    record: dict[str, Any],
    collator: Any,
    tokenizer: Any,
    *,
    device: torch.device,
    max_new_tokens: int = 128,
    trace: bool = False,
    topk: int = 5,
    hard_typed_emission: bool = False,
    copy_confidence_threshold: float = 0.5,
    hard_typed_emission_slots: Optional[Iterable[int]] = None,
) -> dict[str, Any]:
    """Greedy-decode one record. Returns dict with text + token ids + trace.

    Args:
        model:        the SimplexMVP model wrapper (encoder + decoder)
        record:       single canary record dict
        collator:     SimplexCollator (enable_simplex_aux=True)
        tokenizer:    same tokenizer the collator uses
        device:       cuda device
        max_new_tokens: cap on generated tokens before forced EOS
        trace:        when True, log per-token diagnostics for piece 3
                      of the v7.1b post-mortem (top-k probs, lm entropy,
                      slot_type distribution, copy entropy + argmax).
        topk:         k for top-k token logging (only used if trace=True)

    Returns:
        Default (trace=False):
          {
            "text": decoded string,
            "token_ids": [int, ...],
            "n_tokens_generated": int,
            "hit_eos": bool,
            "slot_type_trace": [int, ...]  # per-position predicted slot type
          }
        With trace=True, ADDITIONALLY adds:
          "per_token_trace": [
            {
              "pos": int,
              "chosen_id": int,
              "chosen_token_str": str,
              "lm_top_k": [(id, prob, token_str), ...],
              "lm_entropy": float,         # nats
              "slot_type_argmax": int,
              "slot_type_top_prob": float,
              "slot_type_entropy": float,
              "copy_argmax": int,
              "copy_top_prob": float,
              "copy_entropy": float,
              "ngram_repeat_count": int,   # length of longest immediate repeat
              "ngram_repeat_phrase": str,
              "is_copy_eligible_slot": bool,
            },
            ...
          ]
    """
    model.eval()
    bos = int(tokenizer.BOS_ID)
    eos = int(tokenizer.EOS_ID)

    # Build initial batch from the record (single record)
    batch = collator([record], device=device)
    if batch is None:
        return {
            "text": "",
            "token_ids": [],
            "n_tokens_generated": 0,
            "hit_eos": False,
            "slot_type_trace": [],
            "error": "collator returned None",
        }

    # Start decoder input with [BOS]
    dec_input = torch.tensor([[bos]], dtype=torch.long, device=device)
    generated: list[int] = []
    slot_trace: list[int] = []
    per_token_trace: list[dict[str, Any]] = []  # piece 3 (v7.1b post-mortem)
    hit_eos = False
    # Slot ids whose presence indicates copy-eligible position (used for
    # the per_token_trace ``is_copy_eligible_slot`` flag only; the actual
    # hard-emission slot scope is ``hard_slots`` below, which defaults to
    # STAGE_VAR-only per audit 2026-05-11).
    _COPY_ELIGIBLE_SLOTS = {1, 2, 3, 4, 5, 6, 7}
    # Resolve hard-emission slot scope. Caller-supplied set is filtered
    # against the never-eligible set (CONNECTIVE / NOETIC_PHRASE) so a
    # caller cannot accidentally route LM-only slots to copy.
    if hard_typed_emission_slots is None:
        hard_slots = set(_DEFAULT_HARD_EMISSION_SLOTS)
    else:
        hard_slots = {int(s) for s in hard_typed_emission_slots}
    hard_slots -= _HARD_EMISSION_NEVER
    # Candidate C 2026-05-11: hard-emission routing trace (only populated
    # when hard_typed_emission=True). Each element ∈ {"lm", "copy"}.
    emission_route_trace: list[str] = []
    # Source-side token ids + per-token type tags — needed for hard-copy
    # emission's type-match guard.
    src_ids = batch.get("cas_prefix_ids")
    src_mask = batch.get("cas_prefix_mask")
    src_token_type = batch.get("src_token_type")
    if src_ids is None:
        # No source available; hard-emission cannot fire. Synthesize a
        # single-pad source so the decode loop still runs LM-only.
        src_ids = torch.zeros((1, 1), dtype=torch.long, device=device)
        src_mask = torch.zeros((1, 1), dtype=torch.bool, device=device)
        src_token_type = None

    with torch.no_grad():
        for step_idx in range(max_new_tokens):
            forward_batch = dict(batch)
            forward_batch["lm_decoder_input_ids"] = dec_input
            # v7.1 fix (2026-05-11): typed_slot_positions / typed_slot_source
            # tensors have a fixed L_out from the original collator output
            # (matches the reply length). During greedy decode, dec_input
            # grows token-by-token from length 1 upward, so the decoder's
            # copy_source_indices has the SMALLER L_out_actual and can't
            # be torch.where()'d against the (stale) L_out_collator
            # target_typed_positions. Removing these keys forces the
            # decoder's target_typed_positions branch to skip — copy gating
            # is loss-side anyway and doesn't affect lm_logits.argmax.
            forward_batch.pop("typed_slot_positions", None)
            forward_batch.pop("typed_slot_source", None)
            out = model(forward_batch)
            # Take last position's logits
            last_logits = out["lm_logits"][0, -1, :]  # (V,)
            lm_next_id = int(last_logits.argmax().item())
            slot_argmax = int(out["slot_type_logits"][0, -1, :].argmax().item())
            slot_trace.append(slot_argmax)

            # Candidate C 2026-05-11 (audit-revised): hard typed-fiber
            # emission routing. Decode-time only; training is unchanged.
            # Per audit, hard copy requires ALL of:
            #   - slot_argmax ∈ hard_slots (default {STAGE_VAR} only)
            #   - p_copy.max ≥ copy_confidence_threshold
            #   - the source position p_copy points at is NOT padded
            #   - the source token there is not a PAD/BOS/EOS special
            #   - src_token_type[copy_src_pos] == slot_argmax
            #         (type-match: e.g. STAGE_VAR slot must copy from a
            #         STAGE_VAR source token, not punctuation/connective)
            # Any guard failure → LM fallback.
            # CONNECTIVE (0) and NOETIC_PHRASE (8) are excluded from
            # hard_slots by construction (_HARD_EMISSION_NEVER).
            next_id = lm_next_id
            route = "lm"
            if hard_typed_emission and slot_argmax in hard_slots:
                p_copy_last = out["p_copy"][0, -1, :]  # (L_src,)
                if p_copy_last.numel() > 0:
                    top_copy_prob = float(p_copy_last.max().item())
                    if top_copy_prob >= copy_confidence_threshold:
                        copy_src_pos = int(p_copy_last.argmax().item())
                        # Reject if the source position is padded — no
                        # meaningful token to copy.
                        is_valid_src = True
                        if src_mask is not None and src_mask.numel() > 0:
                            is_valid_src = bool(
                                src_mask[0, copy_src_pos].item()
                            )
                        # Type-match guard: source token must carry the
                        # same slot type the model predicted. Fail closed
                        # if src_token_type is unavailable — without it
                        # we cannot verify the type, so we don't copy.
                        type_matches = False
                        if is_valid_src and src_token_type is not None:
                            src_type_at_pos = int(
                                src_token_type[0, copy_src_pos].item()
                            )
                            type_matches = (src_type_at_pos == slot_argmax)
                        if is_valid_src and type_matches:
                            candidate_id = int(
                                src_ids[0, copy_src_pos].item()
                            )
                            # Reject PAD / BOS / EOS specials as copy
                            # targets — they shouldn't appear mid-decode.
                            specials = {
                                int(getattr(tokenizer, "PAD_ID", -1)),
                                int(getattr(tokenizer, "BOS_ID", -1)),
                                int(getattr(tokenizer, "EOS_ID", -1)),
                            }
                            if candidate_id not in specials:
                                next_id = candidate_id
                                route = "copy"
            emission_route_trace.append(route)

            if trace:
                # Piece 3 per-token diagnostics
                import torch.nn.functional as F
                lm_probs = F.softmax(last_logits, dim=-1)
                lm_entropy = float(
                    -(lm_probs * lm_probs.clamp_min(1e-12).log()).sum().item()
                )
                top_vals, top_idx = lm_probs.topk(min(topk, lm_probs.shape[-1]))
                top_k_entries = []
                for v, i in zip(top_vals.tolist(), top_idx.tolist()):
                    tok_str = ""
                    if hasattr(tokenizer, "decode"):
                        try:
                            tok_str = tokenizer.decode([int(i)], skip_special=False)
                        except Exception:
                            tok_str = ""
                    top_k_entries.append((int(i), float(v), tok_str))
                slot_probs = F.softmax(out["slot_type_logits"][0, -1, :], dim=-1)
                slot_top_prob = float(slot_probs.max().item())
                slot_entropy = float(
                    -(slot_probs * slot_probs.clamp_min(1e-12).log()).sum().item()
                )
                p_copy_last = out["p_copy"][0, -1, :]  # (L_src,)
                copy_argmax = int(p_copy_last.argmax().item())
                copy_top_prob = float(p_copy_last.max().item())
                # Handle nan_to_num'd uniform-zero row from all-PAD source
                if p_copy_last.sum().item() < 1e-9:
                    copy_entropy = float("nan")
                else:
                    copy_entropy = float(
                        -(p_copy_last * p_copy_last.clamp_min(1e-12).log()).sum().item()
                    )
                # Immediate n-gram repeat: longest n such that the last n
                # generated tokens match the n before them.
                ngram_repeat_count = 0
                ngram_repeat_phrase = ""
                if next_id != eos and len(generated) >= 2:
                    candidate = generated + [next_id]
                    for n in range(1, min(6, len(candidate) // 2) + 1):
                        if candidate[-n:] == candidate[-2 * n: -n]:
                            ngram_repeat_count = n
                            phrase_ids = candidate[-n:]
                            if hasattr(tokenizer, "decode"):
                                try:
                                    ngram_repeat_phrase = tokenizer.decode(
                                        phrase_ids, skip_special=False,
                                    )
                                except Exception:
                                    ngram_repeat_phrase = ""
                chosen_str = ""
                if hasattr(tokenizer, "decode"):
                    try:
                        chosen_str = tokenizer.decode([next_id], skip_special=False)
                    except Exception:
                        chosen_str = ""
                per_token_trace.append({
                    "pos": step_idx,
                    "chosen_id": next_id,
                    "chosen_token_str": chosen_str,
                    "lm_top_k": top_k_entries,
                    "lm_entropy": lm_entropy,
                    "slot_type_argmax": slot_argmax,
                    "slot_type_top_prob": slot_top_prob,
                    "slot_type_entropy": slot_entropy,
                    "copy_argmax": copy_argmax,
                    "copy_top_prob": copy_top_prob,
                    "copy_entropy": copy_entropy,
                    "ngram_repeat_count": ngram_repeat_count,
                    "ngram_repeat_phrase": ngram_repeat_phrase,
                    "is_copy_eligible_slot": slot_argmax in _COPY_ELIGIBLE_SLOTS,
                })
            if next_id == eos:
                hit_eos = True
                break
            generated.append(next_id)
            dec_input = torch.cat(
                [dec_input, torch.tensor([[next_id]], dtype=torch.long, device=device)],
                dim=1,
            )

    # Decode generated tokens to string
    text = tokenizer.decode(generated, skip_special=True) if generated else ""
    result = {
        "text": text,
        "token_ids": generated,
        "n_tokens_generated": len(generated),
        "hit_eos": hit_eos,
        "slot_type_trace": slot_trace,
    }
    if hard_typed_emission:
        result["emission_route_trace"] = emission_route_trace
        # Aggregate route stats — surface in canary_history for analysis
        from collections import Counter
        route_counts = Counter(emission_route_trace)
        result["emission_route_counts"] = {
            "lm": int(route_counts.get("lm", 0)),
            "copy": int(route_counts.get("copy", 0)),
        }
    if trace:
        result["per_token_trace"] = per_token_trace
    return result


def decode_canary_pack(
    model: nn.Module,
    canary_records: list[dict[str, Any]],
    collator: Any,
    tokenizer: Any,
    *,
    device: torch.device,
    max_new_tokens: int = 128,
    hard_typed_emission: bool = False,
    copy_confidence_threshold: float = 0.5,
    hard_typed_emission_slots: Optional[Iterable[int]] = None,
) -> list[dict[str, Any]]:
    """Decode every record in the canary pack and return per-record results.

    Restores model.train() after decoding so the caller can resume training
    without missing the toggle.
    """
    was_training = model.training
    results: list[dict[str, Any]] = []
    try:
        for rec in canary_records:
            decode_result = greedy_decode(
                model, rec, collator, tokenizer,
                device=device, max_new_tokens=max_new_tokens,
                hard_typed_emission=hard_typed_emission,
                copy_confidence_threshold=copy_confidence_threshold,
                hard_typed_emission_slots=hard_typed_emission_slots,
            )
            entry = {
                "id": rec.get("id"),
                "category": rec.get("v1mix_grammar_category_or_error_class"),
                "task": rec.get("v1mix_task_type"),
                "cas_expression": rec.get("cas_expression"),
                "target_text": rec.get("reply_text") or rec.get("reply", ""),
                "generated_text": decode_result["text"],
                "n_tokens_generated": decode_result["n_tokens_generated"],
                "hit_eos": decode_result["hit_eos"],
                "slot_type_trace": decode_result["slot_type_trace"][:20],
            }
            if hard_typed_emission:
                entry["emission_route_counts"] = decode_result.get(
                    "emission_route_counts", {"lm": 0, "copy": 0}
                )
                entry["emission_route_trace"] = decode_result.get(
                    "emission_route_trace", []
                )[:40]  # truncate for report size
            results.append(entry)
    finally:
        if was_training:
            model.train()
    return results
