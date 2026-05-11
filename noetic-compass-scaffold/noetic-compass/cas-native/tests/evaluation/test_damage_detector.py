"""Tests for the Stage 7 v7.1 damage detector — the 6 Phase-C signatures."""
from __future__ import annotations

import pytest

from cas_native.evaluation.damage_detector import (
    aggregate_pack_verdict,
    analyze_sample,
)


# ---------------------------------------------------------------------------
# 1. Repeated phrase loops
# ---------------------------------------------------------------------------

def test_clean_text_no_repeat():
    r = analyze_sample("This is a normal English sentence that does not repeat.")
    assert r.signatures["repeated_phrase_loop"]["found"] is False


def test_simple_word_repeat_loop():
    r = analyze_sample("the the the the cat sat")
    assert r.signatures["repeated_phrase_loop"]["found"] is True
    assert r.signatures["repeated_phrase_loop"]["count"] >= 3


def test_two_gram_repeat_loop():
    r = analyze_sample("foo bar foo bar foo bar baz")
    assert r.signatures["repeated_phrase_loop"]["found"] is True
    assert r.signatures["repeated_phrase_loop"]["n"] == 2


def test_legit_phrase_not_flagged_as_loop():
    # "the the" is not a real loop because it doesn't repeat 3+ times
    r = analyze_sample("the cat. the dog. the bird.")
    assert r.signatures["repeated_phrase_loop"]["found"] is False


# ---------------------------------------------------------------------------
# 2. Truncation / mid-clause cutoff
# ---------------------------------------------------------------------------

def test_truncation_on_function_word():
    r = analyze_sample("The expression names a foundational thought with")
    assert r.signatures["truncation"]["found"] is True
    assert r.signatures["truncation"]["reason"] == "ends_on_function_word"


def test_truncation_on_comma():
    r = analyze_sample("This expression contains a state literal, a drive,")
    assert r.signatures["truncation"]["found"] is True
    assert r.signatures["truncation"]["reason"] == "ends_on_comma"


def test_no_truncation_with_period():
    r = analyze_sample("This is a complete sentence ending in a period.")
    assert r.signatures["truncation"]["found"] is False


# ---------------------------------------------------------------------------
# 3. Stage variable corruption
# ---------------------------------------------------------------------------

def test_canonical_stage_var_clean():
    r = analyze_sample("Let stageA0_5_0296 name a foundational thought.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is False
    assert sig["canonical_count"] >= 1


def test_stage_var_double_underscore():
    r = analyze_sample("Let stageA0__5_0296 name something.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is True
    assert sig["double_underscore"]


def test_stage_var_missing_letter():
    r = analyze_sample("Let stage_5_0296 name something.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is True
    assert sig["no_letter"]


def test_stage_var_bad_digits():
    # 6+ trailing digits = malformed
    r = analyze_sample("Let stageD3_3_0233333 name something.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is True
    assert sig["bad_digits"]


# ---------------------------------------------------------------------------
# 4. Hard notation leak
# ---------------------------------------------------------------------------

def test_notation_leak_caret_in_prose():
    r = analyze_sample("The expression is ^P which is a foundational realm idea ^0.")
    sig = r.signatures["notation_leak"]
    assert sig["found"] is True


def test_notation_leak_pipe_letter():
    r = analyze_sample("Register is |T and applies to the cognitive arena.")
    sig = r.signatures["notation_leak"]
    assert sig["found"] is True


def test_no_notation_leak_in_plain_english():
    r = analyze_sample("The expression describes a cognitive state in the foundational realm.")
    sig = r.signatures["notation_leak"]
    assert sig["found"] is False


# ---------------------------------------------------------------------------
# 5. Generic prose collapse
# ---------------------------------------------------------------------------

def test_generic_collapse_short_output():
    r = analyze_sample(
        "This expression is valid.",
        target_text="A long expected reply with many specifics about the meaning of the expression that spans several clauses.",
    )
    sig = r.signatures["generic_collapse"]
    assert sig["found"] is True
    assert sig["is_too_short"] is True


def test_generic_collapse_generic_phrase():
    r = analyze_sample(
        "This expression is valid and means something specific.",
        target_text="The expression denotes a binary composition of two cognitive states.",
    )
    sig = r.signatures["generic_collapse"]
    assert sig["found"] is True


def test_no_generic_collapse_with_specific_content():
    r = analyze_sample(
        "The expression denotes a binary composition of cognitive states integrated together.",
        target_text="The expression denotes a binary composition of cognitive states integrated together.",
    )
    sig = r.signatures["generic_collapse"]
    assert sig["found"] is False


# ---------------------------------------------------------------------------
# 6. ABeing-style token boundary corruption
# ---------------------------------------------------------------------------

def test_abeing_style_fusion():
    r = analyze_sample("ABeing aThought aFeeling all merge inThe mind.")
    sig = r.signatures["camel_fusion"]
    assert sig["found"] is True
    assert sig["count"] >= 3


def test_single_camel_word_not_flagged():
    # iPhone-style legit camelcase shouldn't trip the gate by itself
    r = analyze_sample("The model trained on iPhone data for one example.")
    sig = r.signatures["camel_fusion"]
    # found may be True (count==1) but not severe; verdict shouldn't escalate
    assert sig["count"] <= 1


# ---------------------------------------------------------------------------
# Verdict bands
# ---------------------------------------------------------------------------

def test_clean_sample_clean_verdict():
    r = analyze_sample(
        "A thought in cognitive thinking, driven by a need for connection.",
        target_text="A thought in cognitive thinking, driven by a need for connection.",
    )
    assert r.verdict == "clean"


def test_severe_repeat_loop_kills():
    text = "the the the the the the the the the"
    r = analyze_sample(text)
    assert r.verdict == "kill"


def test_stage_var_corruption_kills():
    text = "Let stageA0__5_0296 name a thought, and stage_5_0296 name a feeling."
    r = analyze_sample(text)
    assert r.verdict == "kill"


def test_mild_truncation_warns_not_kills():
    r = analyze_sample(
        "This is a normal sentence that ends in a hanging the",
        target_text="A target reply about the cognitive state.",
    )
    # Truncation alone shouldn't kill (it's 0.5 severity)
    assert r.verdict in ("clean", "warn")


# ---------------------------------------------------------------------------
# Pack-level aggregation
# ---------------------------------------------------------------------------

def test_pack_verdict_one_kill_kills_pack():
    reports = [
        analyze_sample("This is a normal sentence.", target_text="This is a normal sentence."),
        analyze_sample("Let stageA0__5_0296 cause stage_5_0296 corruption everywhere here."),
    ]
    p = aggregate_pack_verdict(reports)
    assert p["verdict"] == "kill"


def test_pack_verdict_all_clean_is_clean():
    reports = [
        analyze_sample("A normal reply about cognitive states.", target_text="A normal reply about cognitive states."),
        analyze_sample("A second normal reply describing operations.", target_text="A second normal reply describing operations."),
    ]
    p = aggregate_pack_verdict(reports)
    assert p["verdict"] == "clean"


def test_pack_verdict_no_samples():
    p = aggregate_pack_verdict([])
    assert p["verdict"] == "no_samples"


# ---------------------------------------------------------------------------
# v7.1 regression test (post-mortem of canary shape-mismatch crash 2026-05-11):
# greedy decode must not pass typed_slot_positions / typed_slot_source into
# the model — those tensors have the collator's L_out_max (matches reply),
# while dec_input grows from length 1 upward during sampling. The decoder's
# torch.where against target_typed_positions then sees mismatched shapes.
# ---------------------------------------------------------------------------

import torch
import sys


def test_greedy_decode_does_not_crash_on_shape_mismatch():
    """Reproduces the v7.1 canary crash: a batch with typed_slot_positions
    of length L_out=44 must NOT crash when greedy decode runs the model
    with dec_input of length 1, 2, 3, ... The fix is to pop the typed_*
    keys before forward."""
    # Mock model + tokenizer + collator that don't need real torch infra
    class _MockTok:
        BOS_ID = 1
        EOS_ID = 2
        PAD_ID = 0

        def decode(self, ids, skip_special=True):
            return " ".join(str(i) for i in ids)

    class _MockCollator:
        def __init__(self):
            self.tokenizer = _MockTok()

        def __call__(self, records, device="cpu"):
            # Return a fixed batch that mimics what the v1c collator would
            # produce: typed_slot_positions has length 44 from the original
            # reply tokenization.
            B, L_src, L_out = 1, 5, 44
            return {
                "input_ids": torch.zeros((B, 8), dtype=torch.long, device=device),
                "attention_mask": torch.ones((B, 8), dtype=torch.bool, device=device),
                "cas_prefix_ids": torch.zeros((B, L_src), dtype=torch.long, device=device),
                "cas_prefix_mask": torch.ones((B, L_src), dtype=torch.bool, device=device),
                "lm_decoder_input_ids": torch.tensor([[1, 0, 0]], dtype=torch.long, device=device),
                "lm_targets": torch.zeros((B, L_out), dtype=torch.long, device=device),
                "loss_mask": torch.ones((B, L_out), dtype=torch.float32, device=device),
                "typed_slot_positions": torch.zeros((B, L_out, 9), dtype=torch.float32, device=device),
                "typed_slot_source": torch.full((B, L_out), -1, dtype=torch.int16, device=device),
                "src_token_type": torch.zeros((B, L_src), dtype=torch.int8, device=device),
            }

    # Spy on the model to capture what's passed in
    captured_batches: list[dict] = []

    class _MockModel(torch.nn.Module):
        def forward(self, batch):
            captured_batches.append(batch)
            L_out = batch["lm_decoder_input_ids"].shape[1]
            return {
                "lm_logits": torch.zeros((1, L_out, 10)),
                "slot_type_logits": torch.zeros((1, L_out, 9)),
                "source_hidden": torch.zeros((1, 5, 4)),
                "simplex_trajectory": torch.ones((1, 5, 40)) / 40.0,
                "simplex_final": torch.ones((1, 40)) / 40.0,
                "p_copy": torch.zeros((1, L_out, 5)),
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros((1, L_out, 4)),
            }

    # Patch the module load path so cas_native.evaluation.sample_decoder
    # imports cleanly without conftest. Since conftest already wires it,
    # we just import.
    from cas_native.evaluation.sample_decoder import greedy_decode

    rec = {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"}
    tok = _MockTok()
    collator = _MockCollator()
    model = _MockModel()
    result = greedy_decode(
        model, rec, collator, tok, device=torch.device("cpu"), max_new_tokens=3,
    )
    # The load-bearing assertions:
    assert "error" not in result, f"greedy_decode errored: {result.get('error')}"
    assert captured_batches, "model was never called"
    for b in captured_batches:
        # The fix: typed_slot_positions and typed_slot_source must be
        # absent in the forward batch (popped by greedy_decode).
        assert "typed_slot_positions" not in b, (
            "greedy_decode passed typed_slot_positions to model — "
            "this causes shape-mismatch crash in decoder torch.where "
            "when L_out_collator != L_out_dec_input."
        )
        assert "typed_slot_source" not in b, (
            "greedy_decode passed typed_slot_source to model — "
            "potentially shape-mismatched against dec_input."
        )


# ---------------------------------------------------------------------------
# Diagnostic infra piece 3 — per-token greedy trace (2026-05-11)
# ---------------------------------------------------------------------------

def test_greedy_decode_trace_off_by_default():
    """Default invocations of greedy_decode must NOT include per_token_trace."""
    class _MockTok:
        BOS_ID = 1
        EOS_ID = 2
        PAD_ID = 0
        def decode(self, ids, skip_special=True):
            return " ".join(str(i) for i in ids)

    class _MockCollator:
        def __init__(self):
            self.tokenizer = _MockTok()
        def __call__(self, records, device="cpu"):
            return {
                "input_ids": torch.zeros((1, 4), dtype=torch.long),
                "attention_mask": torch.ones((1, 4), dtype=torch.bool),
                "cas_prefix_ids": torch.zeros((1, 3), dtype=torch.long),
                "cas_prefix_mask": torch.ones((1, 3), dtype=torch.bool),
                "lm_decoder_input_ids": torch.tensor([[1]], dtype=torch.long),
                "lm_targets": torch.zeros((1, 4), dtype=torch.long),
                "loss_mask": torch.ones((1, 4), dtype=torch.float32),
                "typed_slot_positions": torch.zeros((1, 4, 9), dtype=torch.float32),
                "typed_slot_source": torch.full((1, 4), -1, dtype=torch.int16),
                "src_token_type": torch.zeros((1, 3), dtype=torch.int8),
            }

    class _MockModel(torch.nn.Module):
        def forward(self, batch):
            L_out = batch["lm_decoder_input_ids"].shape[1]
            return {
                "lm_logits": torch.randn(1, L_out, 10),
                "slot_type_logits": torch.randn(1, L_out, 9),
                "source_hidden": torch.zeros(1, 3, 4),
                "simplex_trajectory": torch.ones(1, 3, 40) / 40.0,
                "simplex_final": torch.ones(1, 40) / 40.0,
                "p_copy": torch.full((1, L_out, 3), 1.0 / 3.0),
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros(1, L_out, 4),
            }

    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        _MockModel(), {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        _MockCollator(), _MockTok(), device=torch.device("cpu"),
        max_new_tokens=3,
    )
    assert "per_token_trace" not in out


def test_greedy_decode_trace_on_logs_per_token():
    """With trace=True, per_token_trace must be a list of dicts with
    all the diagnostic fields piece 3 requires."""
    class _MockTok:
        BOS_ID = 1
        EOS_ID = 2
        PAD_ID = 0
        def decode(self, ids, skip_special=True):
            return " ".join(str(i) for i in ids)

    class _MockCollator:
        def __init__(self):
            self.tokenizer = _MockTok()
        def __call__(self, records, device="cpu"):
            return {
                "input_ids": torch.zeros((1, 4), dtype=torch.long),
                "attention_mask": torch.ones((1, 4), dtype=torch.bool),
                "cas_prefix_ids": torch.zeros((1, 3), dtype=torch.long),
                "cas_prefix_mask": torch.ones((1, 3), dtype=torch.bool),
                "lm_decoder_input_ids": torch.tensor([[1]], dtype=torch.long),
                "lm_targets": torch.zeros((1, 4), dtype=torch.long),
                "loss_mask": torch.ones((1, 4), dtype=torch.float32),
                "typed_slot_positions": torch.zeros((1, 4, 9), dtype=torch.float32),
                "typed_slot_source": torch.full((1, 4), -1, dtype=torch.int16),
                "src_token_type": torch.zeros((1, 3), dtype=torch.int8),
            }

    class _MockModel(torch.nn.Module):
        def forward(self, batch):
            L_out = batch["lm_decoder_input_ids"].shape[1]
            # Bias toward token id 3 so we get a loop
            logits = torch.full((1, L_out, 10), -10.0)
            logits[..., 3] = 10.0
            return {
                "lm_logits": logits,
                "slot_type_logits": torch.randn(1, L_out, 9),
                "source_hidden": torch.zeros(1, 3, 4),
                "simplex_trajectory": torch.ones(1, 3, 40) / 40.0,
                "simplex_final": torch.ones(1, 40) / 40.0,
                "p_copy": torch.full((1, L_out, 3), 1.0 / 3.0),
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros(1, L_out, 4),
            }

    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        _MockModel(), {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        _MockCollator(), _MockTok(), device=torch.device("cpu"),
        max_new_tokens=5, trace=True, topk=3,
    )
    assert "per_token_trace" in out
    trace = out["per_token_trace"]
    assert len(trace) > 0
    required_fields = {
        "pos", "chosen_id", "chosen_token_str", "lm_top_k", "lm_entropy",
        "slot_type_argmax", "slot_type_top_prob", "slot_type_entropy",
        "copy_argmax", "copy_top_prob", "copy_entropy",
        "ngram_repeat_count", "ngram_repeat_phrase", "is_copy_eligible_slot",
    }
    missing = required_fields - set(trace[0].keys())
    assert not missing, f"per_token_trace[0] missing: {missing}"
    # top_k is k=3
    assert len(trace[0]["lm_top_k"]) == 3
    # The model is biased toward id 3 so we should see a repeat by pos 2
    # (chosen=3 at pos 0, =3 at pos 1, =3 at pos 2)
    assert trace[-1]["chosen_id"] == 3
    # And the n-gram repeat detector should fire at some point
    found_repeat = any(t["ngram_repeat_count"] > 0 for t in trace)
    assert found_repeat, "per-token trace should detect the loop"


# ---------------------------------------------------------------------------
# Architecture review Candidate C (2026-05-11) — hard typed-fiber emission
# ---------------------------------------------------------------------------

def _hard_emission_mock_fixtures(slot_argmax_value, p_copy_top_value,
                                 copy_argmax_value=2, lm_argmax_value=5,
                                 src_token_at_copy_pos=42,
                                 src_mask_valid=True):
    """Build mock tokenizer/collator/model that lets us inject a precise
    slot_type / p_copy / lm_logits state for a single decode step.
    Used by all 5 Candidate C tests below.
    """
    class _MockTok:
        BOS_ID = 1
        EOS_ID = 2
        PAD_ID = 0
        def decode(self, ids, skip_special=True):
            return " ".join(str(i) for i in ids)

    class _MockCollator:
        def __init__(self):
            self.tokenizer = _MockTok()
        def __call__(self, records, device="cpu"):
            L_src = 5
            L_out = 4
            # Place the target source token at copy_argmax_value position
            src_ids = torch.zeros((1, L_src), dtype=torch.long)
            src_ids[0, copy_argmax_value] = src_token_at_copy_pos
            src_mask = torch.ones((1, L_src), dtype=torch.bool)
            if not src_mask_valid:
                src_mask[0, copy_argmax_value] = False
            return {
                "input_ids": torch.zeros((1, 4), dtype=torch.long),
                "attention_mask": torch.ones((1, 4), dtype=torch.bool),
                "cas_prefix_ids": src_ids,
                "cas_prefix_mask": src_mask,
                "lm_decoder_input_ids": torch.tensor([[1]], dtype=torch.long),
                "lm_targets": torch.zeros((1, L_out), dtype=torch.long),
                "loss_mask": torch.ones((1, L_out), dtype=torch.float32),
                "typed_slot_positions": torch.zeros((1, L_out, 9), dtype=torch.float32),
                "typed_slot_source": torch.full((1, L_out), -1, dtype=torch.int16),
                "src_token_type": torch.zeros((1, L_src), dtype=torch.int8),
            }

    class _MockModel(torch.nn.Module):
        def forward(self, batch):
            L_out = batch["lm_decoder_input_ids"].shape[1]
            L_src = batch["cas_prefix_ids"].shape[1]
            # lm_logits: peaked at lm_argmax_value
            lm_logits = torch.full((1, L_out, 100), -50.0)
            lm_logits[..., lm_argmax_value] = 50.0
            # slot_type_logits: peaked at slot_argmax_value
            slot_logits = torch.full((1, L_out, 9), -50.0)
            slot_logits[..., slot_argmax_value] = 50.0
            # p_copy: peaked at copy_argmax_value with controllable top prob
            p_copy = torch.full((1, L_out, L_src), (1.0 - p_copy_top_value) / max(L_src - 1, 1))
            p_copy[..., copy_argmax_value] = p_copy_top_value
            return {
                "lm_logits": lm_logits,
                "slot_type_logits": slot_logits,
                "source_hidden": torch.zeros(1, L_src, 4),
                "simplex_trajectory": torch.ones(1, L_src, 40) / 40.0,
                "simplex_final": torch.ones(1, 40) / 40.0,
                "p_copy": p_copy,
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros(1, L_out, 4),
            }

    return _MockTok(), _MockCollator(), _MockModel()


def test_hard_typed_emission_default_off():
    """Default greedy_decode call must not produce emission_route_trace.
    Per user 2026-05-11 scope: 'opt-in, default off'."""
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=2,  # STAGE_VAR
        p_copy_top_value=0.95,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
    )
    assert "emission_route_trace" not in out
    assert "emission_route_counts" not in out


def test_hard_typed_emission_copy_slot_emits_source_token():
    """When slot_argmax is in {1..7} AND p_copy.max >= threshold AND the
    source token isn't a special, hard emission emits the source token."""
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=2,  # STAGE_VAR
        p_copy_top_value=0.95,
        copy_argmax_value=3,
        src_token_at_copy_pos=42,
        lm_argmax_value=5,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
    )
    # Every step should route to copy with src_token = 42
    assert all(r == "copy" for r in out["emission_route_trace"])
    assert all(tok_id == 42 for tok_id in out["token_ids"])
    assert out["emission_route_counts"]["copy"] >= 1
    assert out["emission_route_counts"]["lm"] == 0


def test_hard_typed_emission_connective_uses_lm():
    """slot_argmax = CONNECTIVE (0) must NEVER route to copy, even with
    high p_copy.max. Per user: 'do not hard-copy when slot is CONNECTIVE
    or NOETIC_PHRASE'."""
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=0,  # CONNECTIVE
        p_copy_top_value=0.99,  # very confident copy
        lm_argmax_value=7,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
    )
    assert all(r == "lm" for r in out["emission_route_trace"])
    assert all(tok_id == 7 for tok_id in out["token_ids"])
    assert out["emission_route_counts"]["copy"] == 0


def test_hard_typed_emission_noetic_phrase_uses_lm():
    """slot_argmax = NOETIC_PHRASE (8) must NEVER route to copy."""
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=8,  # NOETIC_PHRASE
        p_copy_top_value=0.99,
        lm_argmax_value=3,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
    )
    assert all(r == "lm" for r in out["emission_route_trace"])
    assert all(tok_id == 3 for tok_id in out["token_ids"])


def test_hard_typed_emission_low_confidence_falls_back_to_lm():
    """If slot_argmax is copy-eligible BUT p_copy.max < threshold,
    fall back to LM."""
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=2,  # STAGE_VAR — copy-eligible
        p_copy_top_value=0.35,  # below default 0.5 threshold
        lm_argmax_value=8,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
    )
    assert all(r == "lm" for r in out["emission_route_trace"])
    assert all(tok_id == 8 for tok_id in out["token_ids"])


def test_hard_typed_emission_all_pad_source_falls_back():
    """When the source position the copy points at is marked padded,
    hard emission must NOT emit that source token. Falls back to LM."""
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=2,
        p_copy_top_value=0.95,
        copy_argmax_value=3,
        src_token_at_copy_pos=42,
        lm_argmax_value=9,
        src_mask_valid=False,  # source position is PADDED
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
    )
    assert all(r == "lm" for r in out["emission_route_trace"])
    assert all(tok_id == 9 for tok_id in out["token_ids"])


def test_hard_typed_emission_rejects_special_token_copy():
    """If the source position holds a PAD/BOS/EOS id, hard emission
    must reject it as a copy candidate and fall back to LM."""
    # PAD_ID is 0 in the mock tokenizer; src_token_at_copy_pos=0 means
    # we'd be copying a PAD.
    tok, coll, model = _hard_emission_mock_fixtures(
        slot_argmax_value=4,  # REGISTER_LETTER
        p_copy_top_value=0.99,
        src_token_at_copy_pos=0,  # PAD
        lm_argmax_value=11,
    )
    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        model, {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        coll, tok, device=torch.device("cpu"), max_new_tokens=3,
        hard_typed_emission=True, copy_confidence_threshold=0.5,
    )
    assert all(r == "lm" for r in out["emission_route_trace"])
    assert all(tok_id == 11 for tok_id in out["token_ids"])


def test_per_token_trace_lm_entropy_near_zero_when_peaky():
    """A heavily-peaked logit distribution should produce near-zero LM entropy."""
    class _MockTok:
        BOS_ID = 1
        EOS_ID = 2
        PAD_ID = 0
        def decode(self, ids, skip_special=True):
            return ""

    class _MockCollator:
        def __init__(self):
            self.tokenizer = _MockTok()
        def __call__(self, records, device="cpu"):
            return {
                "input_ids": torch.zeros((1, 4), dtype=torch.long),
                "attention_mask": torch.ones((1, 4), dtype=torch.bool),
                "cas_prefix_ids": torch.zeros((1, 3), dtype=torch.long),
                "cas_prefix_mask": torch.ones((1, 3), dtype=torch.bool),
                "lm_decoder_input_ids": torch.tensor([[1]], dtype=torch.long),
                "lm_targets": torch.zeros((1, 4), dtype=torch.long),
                "loss_mask": torch.ones((1, 4), dtype=torch.float32),
                "typed_slot_positions": torch.zeros((1, 4, 9), dtype=torch.float32),
                "typed_slot_source": torch.full((1, 4), -1, dtype=torch.int16),
                "src_token_type": torch.zeros((1, 3), dtype=torch.int8),
            }

    class _MockModel(torch.nn.Module):
        def forward(self, batch):
            L_out = batch["lm_decoder_input_ids"].shape[1]
            # Extremely peaked at id 5 — entropy should be ~0
            logits = torch.full((1, L_out, 100), -50.0)
            logits[..., 5] = 50.0
            return {
                "lm_logits": logits,
                "slot_type_logits": torch.zeros(1, L_out, 9),
                "source_hidden": torch.zeros(1, 3, 4),
                "simplex_trajectory": torch.ones(1, 3, 40) / 40.0,
                "simplex_final": torch.ones(1, 40) / 40.0,
                "p_copy": torch.full((1, L_out, 3), 1.0 / 3.0),
                "copy_source_indices": torch.full((1, L_out), -1, dtype=torch.int16),
                "decoder_hidden_state": torch.zeros(1, L_out, 4),
            }

    from cas_native.evaluation.sample_decoder import greedy_decode
    out = greedy_decode(
        _MockModel(), {"prompt_text": "x", "reply_text": "y", "cas_expression": "z"},
        _MockCollator(), _MockTok(), device=torch.device("cpu"),
        max_new_tokens=2, trace=True,
    )
    assert out["per_token_trace"][0]["lm_entropy"] < 0.01
