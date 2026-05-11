"""Stage 7 v7.1 greedy decoder for canary sample reads.

Per user 2026-05-11. Generates greedy text from the simplex MVP model for
each canary record, returning decoded strings the damage detector can scan.

Decoder strategy: lm_logits.argmax only. The model's slot_type / p_copy
heads are NOT used for decode-time token selection — they're loss-side
supervisory signals. At 1000 steps the model hasn't been trained long
enough to coordinate them with lm output anyway. Stage 7 is feasibility,
not product quality; the simplest decode suffices.

For typed-slot output positions (when the slot_type head predicts one of
1..7), an inline trace flag is added to the trace so downstream analysis
can see whether the model is even ATTEMPTING to use the copy mechanism.
"""
from __future__ import annotations

from typing import Any, Optional

import torch
from torch import nn


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
    # Slot ids whose presence indicates copy-eligible position
    _COPY_ELIGIBLE_SLOTS = {1, 2, 3, 4, 5, 6, 7}

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
            next_id = int(last_logits.argmax().item())
            slot_argmax = int(out["slot_type_logits"][0, -1, :].argmax().item())
            slot_trace.append(slot_argmax)

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
            )
            results.append({
                "id": rec.get("id"),
                "category": rec.get("v1mix_grammar_category_or_error_class"),
                "task": rec.get("v1mix_task_type"),
                "cas_expression": rec.get("cas_expression"),
                "target_text": rec.get("reply_text") or rec.get("reply", ""),
                "generated_text": decode_result["text"],
                "n_tokens_generated": decode_result["n_tokens_generated"],
                "hit_eos": decode_result["hit_eos"],
                "slot_type_trace": decode_result["slot_type_trace"][:20],  # truncate for report size
            })
    finally:
        if was_training:
            model.train()
    return results
