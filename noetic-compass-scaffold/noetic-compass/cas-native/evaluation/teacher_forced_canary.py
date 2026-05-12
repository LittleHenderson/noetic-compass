"""Teacher-forced canary evaluator — diagnostic infra piece 2.

Per user 2026-05-11 (Stage 7 v7.1b post-mortem). DECISIVE H1 test.

Runs each canary record through the model in teacher-forced mode (decoder
sees the ground-truth reply prefix at every step) and reports per-record:

  - loss_lm           — cross-entropy at TF positions
  - loss_slot_type    — slot_type CE
  - loss_copy         — pointer-copy loss when valid slots fire
  - copy_valid_count  — number of typed slots fired
  - target_len        — target reply length in tokens
  - argmax_text       — what lm_logits.argmax produces at TF time
  - canonical_stage_vars_in_argmax — count of canonical
                                     ``stage[ADWP]\\d+_\\d+_\\d{4}`` matches
                                     in the argmax decoded text
  - tf_repeated_phrase_loop — repeat detector signature for argmax text

The decisive interpretation:
  - TF loss low + argmax text clean → exposure bias confirmed (H1).
    The model knows the right tokens when shown the truth prefix; greedy
    decode is what derails it. Stage 7-bis should try scheduled sampling.
  - TF loss low BUT argmax text already degenerate → architecture issue.
    The model can't even reproduce the training distribution given the
    truth prefix; something is structurally wrong with the head/loss mix.
  - TF loss high → model isn't fitting the data, regardless of decode.
    Indicates training failed somewhere we can't see on scalar gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import torch
from torch import nn
import torch.nn.functional as F


# Bounded canonical stage_var identifier regex.
# Body width was \d{4} (Stage 6 era when only 4-digit bodies existed in
# training). 2026-05-12 broader B3 eval pack intentionally includes 3-,
# 4-, and 5-digit bodies to stress identifier shape variety, so the
# matcher must accept all three. Widened to \d{3,5}. Backward-compatible
# (any 4-digit body the original regex matched still matches).
_CANONICAL_STAGE_VAR_RE = re.compile(r"\bstage[ADWP]\d+_\d+_\d{3,5}\b")


@dataclass
class TfCanaryResult:
    record_id: str
    category: str
    task: str
    cas_expression: str
    target_text: str
    target_len_tokens: int
    loss_lm: float
    loss_slot_type: float
    loss_copy: float
    copy_valid_count: int
    argmax_text: str
    argmax_top1_acc: float       # fraction of TF positions where argmax matches target
    canonical_stage_vars_in_target: int
    canonical_stage_vars_in_argmax: int
    argmax_repeat_loop_found: bool
    argmax_repeat_loop_count: int


def _has_phrase_loop(text: str, min_n: int = 1, max_n: int = 6, min_consec: int = 3) -> tuple[bool, int]:
    """Mirror of damage_detector._has_consecutive_repeats but stateless."""
    tokens = text.split()
    if len(tokens) < min_n * min_consec:
        return False, 0
    for n in range(min_n, max_n + 1):
        for i in range(len(tokens) - n * min_consec + 1):
            base = tokens[i:i + n]
            count = 1
            j = i + n
            while j + n <= len(tokens) and tokens[j:j + n] == base:
                count += 1
                j += n
            if count >= min_consec:
                return True, count
    return False, 0


def teacher_forced_record(
    model: nn.Module,
    record: dict[str, Any],
    collator: Any,
    tokenizer: Any,
    *,
    device: torch.device,
) -> TfCanaryResult:
    """Run one record through the model in teacher-forced mode."""
    model.eval()
    batch = collator([record], device=device)
    if batch is None:
        return TfCanaryResult(
            record_id=str(record.get("id", "")),
            category=str(record.get("v1mix_grammar_category_or_error_class", "")),
            task=str(record.get("v1mix_task_type", "")),
            cas_expression=str(record.get("cas_expression", "")),
            target_text=str(record.get("reply_text", "")),
            target_len_tokens=0,
            loss_lm=float("nan"),
            loss_slot_type=float("nan"),
            loss_copy=float("nan"),
            copy_valid_count=0,
            argmax_text="",
            argmax_top1_acc=float("nan"),
            canonical_stage_vars_in_target=0,
            canonical_stage_vars_in_argmax=0,
            argmax_repeat_loop_found=False,
            argmax_repeat_loop_count=0,
        )

    with torch.no_grad():
        out = model(batch)
        lm_logits = out["lm_logits"]                      # (1, L_out, V)
        slot_logits = out.get("slot_type_logits")
        p_copy = out.get("p_copy")

        targets = batch["lm_targets"]                     # (1, L_out)
        loss_mask = batch.get("loss_mask")
        if loss_mask is None:
            loss_mask = (targets != -100).to(dtype=torch.float32)

        # LM cross-entropy (TF positions only)
        flat_logits = lm_logits.reshape(-1, lm_logits.shape[-1])
        flat_targets = targets.reshape(-1)
        lm_per_tok = F.cross_entropy(
            flat_logits, flat_targets.clamp_min(0), reduction="none"
        ).view_as(loss_mask) * loss_mask
        denom = loss_mask.sum().clamp_min(1.0)
        loss_lm = float((lm_per_tok.sum() / denom).item())

        # Slot type CE
        if "typed_slot_positions" in batch and slot_logits is not None:
            slot_target = batch["typed_slot_positions"].argmax(dim=-1)
            slot_flat = slot_logits.reshape(-1, slot_logits.shape[-1])
            loss_slot_type = float(F.cross_entropy(
                slot_flat, slot_target.reshape(-1), reduction="mean"
            ).item())
        else:
            loss_slot_type = float("nan")

        # Copy loss + valid count
        copy_valid_count = 0
        loss_copy_val = float("nan")
        if "typed_slot_source" in batch and p_copy is not None:
            copy_target = batch["typed_slot_source"].to(dtype=torch.long)
            valid = (copy_target >= 0)
            copy_valid_count = int(valid.sum().item())
            if copy_valid_count > 0:
                B, L_out, L_src = p_copy.shape
                safe_idx = copy_target.clamp(min=0, max=L_src - 1).unsqueeze(-1)
                chosen = p_copy.gather(-1, safe_idx).squeeze(-1).clamp_min(1e-9)
                copy_log = -torch.log(chosen)
                denom_c = valid.to(dtype=torch.float32).sum().clamp_min(1.0)
                loss_copy_val = float((
                    copy_log * valid.to(dtype=copy_log.dtype)
                ).sum().item() / float(denom_c.item()))

        # Top-1 argmax decode under TF
        argmax_ids = lm_logits.argmax(dim=-1)             # (1, L_out)
        # Match against target where loss_mask is active
        match = (argmax_ids == targets) & loss_mask.bool()
        top1_acc = float(match.sum().item()) / float(denom.item())

        # Decode argmax to text (skip EOS/PAD/BOS via tokenizer.decode)
        argmax_tokens = argmax_ids[0].cpu().tolist()
        # Trim at first EOS if present
        eos_id = int(getattr(tokenizer, "EOS_ID", -1))
        if eos_id in argmax_tokens:
            argmax_tokens = argmax_tokens[: argmax_tokens.index(eos_id)]
        argmax_text = tokenizer.decode(argmax_tokens, skip_special=True) \
            if hasattr(tokenizer, "decode") else ""

    target_text = str(record.get("reply_text") or record.get("reply", ""))
    target_len = int(loss_mask.sum().item())

    canonical_target = len(_CANONICAL_STAGE_VAR_RE.findall(target_text))
    canonical_argmax = len(_CANONICAL_STAGE_VAR_RE.findall(argmax_text))
    loop_found, loop_count = _has_phrase_loop(argmax_text)

    return TfCanaryResult(
        record_id=str(record.get("id", "")),
        category=str(record.get("v1mix_grammar_category_or_error_class", "")),
        task=str(record.get("v1mix_task_type", "")),
        cas_expression=str(record.get("cas_expression", "")),
        target_text=target_text,
        target_len_tokens=target_len,
        loss_lm=loss_lm,
        loss_slot_type=loss_slot_type,
        loss_copy=loss_copy_val,
        copy_valid_count=copy_valid_count,
        argmax_text=argmax_text,
        argmax_top1_acc=top1_acc,
        canonical_stage_vars_in_target=canonical_target,
        canonical_stage_vars_in_argmax=canonical_argmax,
        argmax_repeat_loop_found=loop_found,
        argmax_repeat_loop_count=loop_count,
    )


def teacher_forced_canary_pack(
    model: nn.Module,
    canary_records: list[dict[str, Any]],
    collator: Any,
    tokenizer: Any,
    *,
    device: torch.device,
) -> dict[str, Any]:
    """Run TF eval on the canary pack. Returns per-record results + summary."""
    was_training = model.training
    try:
        per_record = [
            teacher_forced_record(model, rec, collator, tokenizer, device=device)
            for rec in canary_records
        ]
    finally:
        if was_training:
            model.train()

    if not per_record:
        return {"n": 0, "summary": {}, "per_record": []}

    # Summary aggregates
    n = len(per_record)
    mean_lm = sum(r.loss_lm for r in per_record) / n
    mean_top1 = sum(r.argmax_top1_acc for r in per_record) / n
    loops = sum(1 for r in per_record if r.argmax_repeat_loop_found)
    canon_target_total = sum(r.canonical_stage_vars_in_target for r in per_record)
    canon_argmax_total = sum(r.canonical_stage_vars_in_argmax for r in per_record)
    valid_copy_records = [r for r in per_record if r.copy_valid_count > 0]
    mean_copy_loss = (
        sum(r.loss_copy for r in valid_copy_records) / len(valid_copy_records)
        if valid_copy_records else float("nan")
    )

    return {
        "n": n,
        "summary": {
            "mean_loss_lm": mean_lm,
            "mean_argmax_top1_acc": mean_top1,
            "n_records_with_argmax_loop": loops,
            "canonical_stage_vars_in_targets": canon_target_total,
            "canonical_stage_vars_in_argmax": canon_argmax_total,
            "canonical_recovery_rate": (
                canon_argmax_total / canon_target_total
                if canon_target_total > 0 else float("nan")
            ),
            "mean_loss_copy_at_valid": mean_copy_loss,
            "records_with_valid_copy": len(valid_copy_records),
        },
        "per_record": [
            {
                "id": r.record_id,
                "category": r.category,
                "task": r.task,
                "cas_expression": r.cas_expression,
                "target_text": r.target_text,
                "target_len_tokens": r.target_len_tokens,
                "loss_lm": r.loss_lm,
                "loss_slot_type": r.loss_slot_type,
                "loss_copy": r.loss_copy,
                "copy_valid_count": r.copy_valid_count,
                "argmax_text": r.argmax_text,
                "argmax_top1_acc": r.argmax_top1_acc,
                "canonical_stage_vars_in_target": r.canonical_stage_vars_in_target,
                "canonical_stage_vars_in_argmax": r.canonical_stage_vars_in_argmax,
                "argmax_repeat_loop_found": r.argmax_repeat_loop_found,
                "argmax_repeat_loop_count": r.argmax_repeat_loop_count,
            }
            for r in per_record
        ],
    }
