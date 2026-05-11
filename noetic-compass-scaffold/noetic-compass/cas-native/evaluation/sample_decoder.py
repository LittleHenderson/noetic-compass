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
) -> dict[str, Any]:
    """Greedy-decode one record. Returns dict with text + token ids + trace.

    Args:
        model:        the SimplexMVP model wrapper (encoder + decoder)
        record:       single canary record dict
        collator:     SimplexCollator (enable_simplex_aux=True)
        tokenizer:    same tokenizer the collator uses
        device:       cuda device
        max_new_tokens: cap on generated tokens before forced EOS

    Returns:
        {
          "text": decoded string,
          "token_ids": [int, ...],
          "n_tokens_generated": int,
          "hit_eos": bool,
          "slot_type_trace": [int, ...]  # per-position predicted slot type
        }
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
    hit_eos = False

    with torch.no_grad():
        for _ in range(max_new_tokens):
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
    return {
        "text": text,
        "token_ids": generated,
        "n_tokens_generated": len(generated),
        "hit_eos": hit_eos,
        "slot_type_trace": slot_trace,
    }


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
