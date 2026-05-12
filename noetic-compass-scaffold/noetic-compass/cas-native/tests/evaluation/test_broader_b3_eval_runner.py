"""Tests for broader_b3_eval_runner — audit-blocker fixes 2026-05-12.

Specifically verifies:
  - Bounded-regex identifier extraction rejects partial-substring matches.
  - Positional recovery counts an identifier only when it appears at the
    same position in the generated identifier sequence as in the target.
  - Out-of-order recovery is not counted.
  - Truncate-trace opt-out returns full traces.
"""
from __future__ import annotations


def test_bounded_regex_extracts_only_canonical_shape():
    from cas_native.evaluation.broader_b3_eval_runner import (
        extract_identifiers_in_order,
    )
    text = "Let stageA0_4_0049 name a thought, stageD4_4_0049 name something."
    idents = extract_identifiers_in_order(text)
    assert idents == ["stageA0_4_0049", "stageD4_4_0049"]


def test_bounded_regex_supports_3_4_5_digit_bodies():
    from cas_native.evaluation.broader_b3_eval_runner import (
        extract_identifiers_in_order,
    )
    text = "stageA0_6_707 stageD4_4_0049 stageW6_8_19672"
    idents = extract_identifiers_in_order(text)
    assert idents == ["stageA0_6_707", "stageD4_4_0049", "stageW6_8_19672"]


def test_bounded_regex_rejects_partial_substring_match():
    """Audit blocker 2: 'stageA0_4_0049' must NOT be extracted from
    'stageA0_4_004999' (longer identifier embedding it)."""
    from cas_native.evaluation.broader_b3_eval_runner import (
        extract_identifiers_in_order,
    )
    text = "Let stageA0_4_004999 name a thought."
    idents = extract_identifiers_in_order(text)
    # Either the 6-digit body doesn't match \d{3,5} (no match) OR it
    # matches the full 6-digit form (one match). It must NOT match
    # the embedded 4-digit prefix as a separate identifier.
    assert "stageA0_4_0049" not in idents
    # Specifically: the runner's bounded regex caps body at 5 digits, so
    # a 6-digit body falls outside the canonical-shape definition and
    # is NOT extracted. This is the conservative behavior — better to
    # under-count than to falsely credit a malformed identifier.
    assert idents == []


def test_per_record_recovery_positional_exact():
    """Audit blocker 2: positional matching, not substring."""
    from cas_native.evaluation.broader_b3_eval_runner import per_record_recovery
    record = {
        "eval_meta": {
            "canonical_identifiers": ["stageA0_4_0049", "stageD4_4_0049"],
        },
    }
    # Both identifiers at the right positions
    gen = "Let stageA0_4_0049 name a thought, stageD4_4_0049 name something."
    rec = per_record_recovery(record, gen)
    assert rec["applicable"] is True
    assert rec["n_target"] == 2
    assert rec["n_recovered"] == 2
    assert rec["recovery_rate"] == 1.0


def test_per_record_recovery_wrong_position_is_zero():
    """Swapped order: target has [A,D] but gen has [D,A]. Neither matches
    at its own position, so n_recovered must be 0."""
    from cas_native.evaluation.broader_b3_eval_runner import per_record_recovery
    record = {
        "eval_meta": {
            "canonical_identifiers": ["stageA0_4_0049", "stageD4_4_0049"],
        },
    }
    gen = "Let stageD4_4_0049 name a thought, stageA0_4_0049 name something."
    rec = per_record_recovery(record, gen)
    assert rec["n_recovered"] == 0


def test_per_record_recovery_partial_substring_rejected():
    """Audit blocker 2 explicit: a longer identifier must NOT credit a
    canonical target."""
    from cas_native.evaluation.broader_b3_eval_runner import per_record_recovery
    record = {
        "eval_meta": {"canonical_identifiers": ["stageA0_4_0049"]},
    }
    # Generated text contains a longer identifier that embeds the target
    gen = "Let stageA0_4_004999 name a thought."
    rec = per_record_recovery(record, gen)
    assert rec["n_recovered"] == 0


def test_per_record_recovery_more_gen_idents_than_target_ok():
    """If gen has more identifiers than target, only the first
    len(target) positions count."""
    from cas_native.evaluation.broader_b3_eval_runner import per_record_recovery
    record = {
        "eval_meta": {"canonical_identifiers": ["stageA0_4_0049"]},
    }
    gen = "stageA0_4_0049 stageD4_4_0049 stageW6_8_19672"
    rec = per_record_recovery(record, gen)
    assert rec["n_recovered"] == 1
    # The extra identifiers are recorded for diagnostic but don't break
    assert rec["generated_identifiers"] == [
        "stageA0_4_0049", "stageD4_4_0049", "stageW6_8_19672"
    ]


def test_per_record_recovery_non_rpm_is_not_applicable():
    from cas_native.evaluation.broader_b3_eval_runner import per_record_recovery
    record = {"eval_meta": {"canonical_identifiers": []}}
    gen = "Some text without identifiers."
    rec = per_record_recovery(record, gen)
    assert rec["applicable"] is False
    assert rec["n_target"] == 0


def test_decode_canary_pack_truncate_traces_false_returns_full(monkeypatch):
    """Audit blocker 3: truncate_traces=False must return full
    slot_type_trace, not the 20-element slice."""
    import torch
    from cas_native.evaluation.sample_decoder import decode_canary_pack

    class _Tok:
        BOS_ID, EOS_ID, PAD_ID = 1, 2, 0
        def decode(self, ids, skip_special=True):
            return " ".join(str(i) for i in ids)

    class _Coll:
        def __init__(self): self.tokenizer = _Tok()
        def __call__(self, records, device="cpu"):
            L_src = 5
            return {
                "input_ids": torch.zeros((1, 4), dtype=torch.long),
                "attention_mask": torch.ones((1, 4), dtype=torch.bool),
                "cas_prefix_ids": torch.zeros((1, L_src), dtype=torch.long),
                "cas_prefix_mask": torch.ones((1, L_src), dtype=torch.bool),
                "lm_decoder_input_ids": torch.tensor([[1]], dtype=torch.long),
                "lm_targets": torch.zeros((1, 4), dtype=torch.long),
                "loss_mask": torch.ones((1, 4), dtype=torch.float32),
                "typed_slot_positions": torch.zeros((1, 4, 9), dtype=torch.float32),
                "typed_slot_source": torch.full((1, 4), -1, dtype=torch.int16),
                "src_token_type": torch.zeros((1, L_src), dtype=torch.int8),
            }

    class _Model(torch.nn.Module):
        def forward(self, batch):
            L_out = batch["lm_decoder_input_ids"].shape[1]
            L_src = batch["cas_prefix_ids"].shape[1]
            lm = torch.full((1, L_out, 100), -50.0); lm[..., 5] = 50.0
            sl = torch.full((1, L_out, 9), -50.0); sl[..., 0] = 50.0
            return {
                "lm_logits": lm, "slot_type_logits": sl,
                "p_copy": torch.full((1, L_out, L_src), 1.0 / L_src),
                "source_hidden": torch.zeros(1, L_src, 4),
                "simplex_trajectory": torch.ones(1, L_src, 40) / 40.0,
                "simplex_final": torch.ones(1, 40) / 40.0,
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros(1, L_out, 4),
            }

    rec = {"id": "r1",
           "v1mix_grammar_category_or_error_class": "rpm_chain",
           "v1mix_task_type": "test",
           "cas_expression": "x", "reply_text": "y"}

    # Run with max_new_tokens=50 to ensure > 20 positions are produced
    out_trunc = decode_canary_pack(
        _Model(), [rec], _Coll(), _Tok(),
        device=torch.device("cpu"), max_new_tokens=50,
        truncate_traces=True,
    )
    out_full = decode_canary_pack(
        _Model(), [rec], _Coll(), _Tok(),
        device=torch.device("cpu"), max_new_tokens=50,
        truncate_traces=False,
    )
    # Default truncated trace caps at 20
    assert len(out_trunc[0]["slot_type_trace"]) == 20
    # Full trace exceeds 20 (we asked for max_new_tokens=50 and EOS won't
    # fire because mock lm peaks at token id 5, not EOS_ID 2)
    assert len(out_full[0]["slot_type_trace"]) > 20


def test_decode_canary_pack_truncate_traces_hard_emission_routes(monkeypatch):
    """Audit blocker 3 companion: emission_route_trace must also be full
    when truncate_traces=False."""
    import torch
    from cas_native.evaluation.sample_decoder import decode_canary_pack

    class _Tok:
        BOS_ID, EOS_ID, PAD_ID = 1, 2, 0
        def decode(self, ids, skip_special=True):
            return " ".join(str(i) for i in ids)

    class _Coll:
        def __init__(self): self.tokenizer = _Tok()
        def __call__(self, records, device="cpu"):
            L_src = 5
            return {
                "input_ids": torch.zeros((1, 4), dtype=torch.long),
                "attention_mask": torch.ones((1, 4), dtype=torch.bool),
                "cas_prefix_ids": torch.zeros((1, L_src), dtype=torch.long),
                "cas_prefix_mask": torch.ones((1, L_src), dtype=torch.bool),
                "lm_decoder_input_ids": torch.tensor([[1]], dtype=torch.long),
                "lm_targets": torch.zeros((1, 4), dtype=torch.long),
                "loss_mask": torch.ones((1, 4), dtype=torch.float32),
                "typed_slot_positions": torch.zeros((1, 4, 9), dtype=torch.float32),
                "typed_slot_source": torch.full((1, 4), -1, dtype=torch.int16),
                "src_token_type": torch.zeros((1, L_src), dtype=torch.int8),
            }

    class _Model(torch.nn.Module):
        def forward(self, batch):
            L_out = batch["lm_decoder_input_ids"].shape[1]
            L_src = batch["cas_prefix_ids"].shape[1]
            lm = torch.full((1, L_out, 100), -50.0); lm[..., 5] = 50.0
            sl = torch.full((1, L_out, 9), -50.0); sl[..., 0] = 50.0
            return {
                "lm_logits": lm, "slot_type_logits": sl,
                "p_copy": torch.full((1, L_out, L_src), 1.0 / L_src),
                "source_hidden": torch.zeros(1, L_src, 4),
                "simplex_trajectory": torch.ones(1, L_src, 40) / 40.0,
                "simplex_final": torch.ones(1, 40) / 40.0,
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros(1, L_out, 4),
            }

    rec = {"id": "r1",
           "v1mix_grammar_category_or_error_class": "rpm_chain",
           "v1mix_task_type": "test",
           "cas_expression": "x", "reply_text": "y"}

    out_full = decode_canary_pack(
        _Model(), [rec], _Coll(), _Tok(),
        device=torch.device("cpu"), max_new_tokens=50,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
        truncate_traces=False,
    )
    # emission_route_trace must equal n_tokens_generated, not capped at 40
    assert len(out_full[0]["emission_route_trace"]) == out_full[0]["n_tokens_generated"]
    assert len(out_full[0]["emission_route_trace"]) > 40  # confirms > 40-truncation didn't fire


def test_tf_canary_regex_supports_3_5_digit_bodies():
    """Audit blocker 4: TF canonical regex must match 3-, 4-, 5-digit
    bodies (the broader B3 eval pack intentionally varies body width)."""
    from cas_native.evaluation.teacher_forced_canary import (
        _CANONICAL_STAGE_VAR_RE,
    )
    text_3 = "stageA0_6_707"
    text_4 = "stageA0_4_0049"
    text_5 = "stageA0_9_81399"
    assert _CANONICAL_STAGE_VAR_RE.search(text_3) is not None
    assert _CANONICAL_STAGE_VAR_RE.search(text_4) is not None
    assert _CANONICAL_STAGE_VAR_RE.search(text_5) is not None
    # And does NOT match a 6-digit body
    text_6 = "stageA0_4_004999"
    # The 6-digit body should ALSO not be matched as a whole (no \d{6} in
    # pattern); however the regex will greedily match the first 5 digits
    # WITH a word boundary, and the 6th digit breaks that boundary, so
    # no match. Confirm:
    assert _CANONICAL_STAGE_VAR_RE.search(text_6) is None
