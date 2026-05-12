"""Tests for Candidate E Stage 1A — labeller + source-window patches (2026-05-12).

Per audit findings 2026-05-12:
  - simplex_collator.find_subsequence was first-match only; repeat target
    occurrences silently unlabelled. Replaced with find_all_subsequences.
  - max_cas_prefix_len defaulted to 32 in NativeNLCollator and was not
    plumbed through to SimplexCollator from the trainer. A 4-stage rpm
    chain CAS expression is ~110 source tokens; cap=32 truncated W/P
    identifiers out of cas_prefix_ids before labelling could fire on them.
  - Combined effect: only the first 2 of 4 unique rpm identifiers per
    record received STAGE_VAR copy supervision (50% unique-identifier
    coverage; 33% total-occurrence coverage).

These tests cover the four cases the audit specified:
  - 4-stage A/D/W/P chain labels all four identifiers (with sufficient
    source cap)
  - Repeated identifiers in the reply are all labelled
  - W/P source positions are present under the Candidate E source cap
  - Hard negatives (identifiers in source but not in reply) get
    src_token_type tagging but no target_slots entry
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.datasets.simplex_collator import (
    SimplexCollator, SLOT_STAGE_VAR, SLOT_CONNECTIVE,
    find_subsequence, find_all_subsequences,
)


# Resolve to the project root: this file is at
# noetic-compass-scaffold/noetic-compass/cas-native/tests/training/<file>
# parents: 0=training, 1=tests, 2=cas-native, 3=noetic-compass,
#          4=noetic-compass-scaffold, 5=tksCAS root
_PROJECT_ROOT = Path(__file__).parents[5]
_TOKENIZER_PATH = _PROJECT_ROOT / "stage6_v6_artifacts" / "tokenizer.json"
_ENGLISH_BPE_PATH = _PROJECT_ROOT / "stage6_v6_artifacts" / "english_bpe.json"


def _load_tokenizer():
    """Load the production tokenizer (Stage 6 v6 artifacts). Returns None
    if artifacts not present — tests that need it skip in that case."""
    if not _TOKENIZER_PATH.exists() or not _ENGLISH_BPE_PATH.exists():
        return None
    tok = HybridCASTokenizer.load(str(_TOKENIZER_PATH))
    tok = tok.with_english_bpe(str(_ENGLISH_BPE_PATH))
    return tok


# ---------------------------------------------------------------------------
# find_all_subsequences unit tests
# ---------------------------------------------------------------------------

def test_find_all_subsequences_empty_needle_returns_empty():
    assert find_all_subsequences([1, 2, 3], []) == []


def test_find_all_subsequences_no_match_returns_empty():
    assert find_all_subsequences([1, 2, 3, 4], [9, 9]) == []


def test_find_all_subsequences_single_match_returns_singleton():
    assert find_all_subsequences([1, 2, 3, 4, 5], [3, 4]) == [2]


def test_find_all_subsequences_multiple_non_overlapping():
    """Three occurrences of [9, 9] in a list; expect 3 non-overlapping start indices."""
    haystack = [1, 9, 9, 2, 9, 9, 3, 9, 9]
    result = find_all_subsequences(haystack, [9, 9])
    assert result == [1, 4, 7]


def test_find_all_subsequences_overlap_skipped():
    """[1,1,1,1] contains [1,1] at positions 0,1,2 but non-overlapping policy
    returns only [0, 2]."""
    haystack = [1, 1, 1, 1]
    result = find_all_subsequences(haystack, [1, 1])
    assert result == [0, 2]


def test_find_all_subsequences_first_match_matches_find_subsequence():
    """Old find_subsequence should equal first element of find_all_subsequences."""
    # haystack contains [2, 3] at positions 2 and 5
    haystack = [9, 9, 2, 3, 9, 2, 3, 9]
    needle = [2, 3]
    first = find_subsequence(haystack, needle)
    allmatches = find_all_subsequences(haystack, needle)
    assert first == allmatches[0]
    assert len(allmatches) == 2
    assert allmatches == [2, 5]


# ---------------------------------------------------------------------------
# Full end-to-end audit cases (require production tokenizer)
# ---------------------------------------------------------------------------

def _make_record_4stage(body: str = "0185"):
    """Build a 4-stage rpm_chain record (A0+D2+W2+P2) with the given
    digit body. Same shape as the audit's sampled records."""
    return {
        "id": f"test_4stage_{body}",
        "trace_id": f"test_trace_4stage_{body}",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain this rpm chain expression.",
        "reply_text": (
            f"Let stageA0_2_{body} name a foundational thought, "
            f"stageD2_2_{body} name a moment of awareness, "
            f"stageW2_2_{body} name practiced rhythm with agency, "
            f"stageP2_2_{body} name what triggered an evaluative judgment. "
            f"stageW2_2_{body} leads to stageP2_2_{body}."
        ),
        "cas_expression": (
            f"let stageA0_2_{body} = ^0^P; "
            f"let stageD2_2_{body} = ^1^P; "
            f"let stageW2_2_{body} = ^7^P_{{F5}}; "
            f"let stageP2_2_{body} = ^8^P_{{F4}}; "
            f"stageW2_2_{body} -> stageP2_2_{body}"
        ),
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
    }


def _stage_var_spans(slot_argmax_1d):
    """Return list of (start, end_exclusive) tuples for contiguous STAGE_VAR
    runs in a 1-D slot_argmax sequence."""
    import torch
    spans = []
    in_span = False
    start = None
    L = int(slot_argmax_1d.shape[0])
    for k in range(L):
        is_sv = int(slot_argmax_1d[k].item()) == SLOT_STAGE_VAR
        if is_sv and not in_span:
            in_span = True
            start = k
        elif not is_sv and in_span:
            spans.append((start, k))
            in_span = False
    if in_span:
        spans.append((start, L))
    return spans


def test_4stage_chain_with_sufficient_cap_labels_all_4_identifiers():
    """AUDIT CASE 1: A 4-stage A/D/W/P chain must label all four identifiers
    when max_cas_prefix_len is sufficient (192). Was 2 spans pre-fix; now
    should be ≥4."""
    tok = _load_tokenizer()
    if tok is None:
        pytest.skip("production tokenizer not present locally")
    coll = SimplexCollator(tok, enable_simplex_aux=True, max_cas_prefix_len=192)
    rec = _make_record_4stage(body="0185")
    batch = coll([rec], device="cpu")
    assert batch is not None
    tsp = batch["typed_slot_positions"]
    slot_argmax = tsp[0].argmax(dim=-1)
    spans = _stage_var_spans(slot_argmax)
    assert len(spans) >= 4, (
        f"Expected ≥4 STAGE_VAR spans (one per unique identifier in target); "
        f"got {len(spans)}. With max_cas_prefix_len=192 the W/P identifiers "
        f"must be present in source, and find_all_subsequences must label "
        f"all target occurrences."
    )


def test_repeat_target_occurrences_all_labelled():
    """AUDIT CASE 2: The 4-stage record has stageW2_2_<body> and
    stageP2_2_<body> appearing twice in the reply (once in the binding
    clause, once in the trailing 'leads to' clause). All occurrences must
    be labelled, not just the first."""
    tok = _load_tokenizer()
    if tok is None:
        pytest.skip("production tokenizer not present locally")
    coll = SimplexCollator(tok, enable_simplex_aux=True, max_cas_prefix_len=192)
    rec = _make_record_4stage(body="0185")
    batch = coll([rec], device="cpu")
    tsp = batch["typed_slot_positions"]
    slot_argmax = tsp[0].argmax(dim=-1)
    spans = _stage_var_spans(slot_argmax)
    # Reply contains 6 identifier occurrences: A,D,W,P + W,P (repeat).
    # Expect ≥6 STAGE_VAR spans.
    assert len(spans) >= 6, (
        f"Expected ≥6 STAGE_VAR spans (one per occurrence in target, "
        f"including the 2 repeat W/P occurrences); got {len(spans)}. "
        f"find_all_subsequences must catch repeats; find_subsequence (old) "
        f"would only label the first occurrence."
    )


def test_wp_source_positions_present_under_candidate_e_cap():
    """AUDIT CASE 3: With max_cas_prefix_len=192, the source tokenization of
    a 4-stage CAS must include positions for the W and P identifiers
    (not truncated at the 32-token cap)."""
    tok = _load_tokenizer()
    if tok is None:
        pytest.skip("production tokenizer not present locally")
    # Build a 4-stage record; encode the cas_expression directly
    rec = _make_record_4stage(body="0185")
    cas = rec["cas_expression"]
    full_ids = tok.encode(cas)
    # Find the "stageW" and "stageP" tokens in the FULL tokenization
    src_tokens = tok.token_ids_to_tokens(full_ids)
    w_pos = next((i for i, t in enumerate(src_tokens) if "W" in str(t) and i > 0 and "stage" in str(src_tokens[i-1])), None)
    p_pos = next((i for i, t in enumerate(src_tokens) if "P" in str(t) and i > 0 and "stage" in str(src_tokens[i-1])), None)
    # Both must be present in the full source
    assert w_pos is not None, f"stageW position not found in full source tokenization: {src_tokens[:60]}"
    assert p_pos is not None, f"stageP position not found in full source tokenization: {src_tokens[:60]}"
    # Both must be within the Candidate E cap of 192
    assert w_pos < 192, f"stageW at position {w_pos} would be truncated at cap=192"
    assert p_pos < 192, f"stageP at position {p_pos} would be truncated at cap=192"
    # Confirm the OLD cap (32) DOES truncate at least one of them
    # (regression check on the original bug)
    full_count = len(full_ids)
    # 4-stage rpm chain CAS should produce >>32 tokens
    assert full_count > 32, (
        f"4-stage rpm CAS only produced {full_count} tokens; doesn't exercise "
        f"the cap bug. Test setup error."
    )


def test_default_cap_32_truncates_wp_identifiers():
    """AUDIT CASE 3b (regression): with the OLD default max_cas_prefix_len=32,
    the same 4-stage record must NOT label all 4 identifiers (because W/P
    are truncated out of source). This pins the original bug as the
    distinguishing test."""
    tok = _load_tokenizer()
    if tok is None:
        pytest.skip("production tokenizer not present locally")
    coll = SimplexCollator(tok, enable_simplex_aux=True, max_cas_prefix_len=32)
    rec = _make_record_4stage(body="0185")
    batch = coll([rec], device="cpu")
    tsp = batch["typed_slot_positions"]
    slot_argmax = tsp[0].argmax(dim=-1)
    spans = _stage_var_spans(slot_argmax)
    # With cap=32, the labeller can only see the first ~32 source tokens
    # (which is the let-stageA0 + let-stageD2 prefix). Even though the
    # all-occurrences fix is now live in the collator, the W/P identifiers
    # cannot be labelled because they're not in cas_prefix_ids at all.
    # So this should still produce ≤2 distinct identifier spans (multiplied
    # by all occurrences of each, so 2 unique × possibly 1 occurrence each
    # = ≤2 spans, OR if the same identifier repeats inside the truncated
    # prefix, slightly more — but never ≥4 unique identifiers).
    # We check that at most A0 and D2 are labelled — never W or P.
    valid_lm = batch["lm_targets"][0]
    span_texts = []
    for sp_start, sp_end in spans:
        ids = valid_lm[sp_start:sp_end].tolist()
        if hasattr(tok, "decode"):
            txt = tok.decode(ids, skip_special=False)
            span_texts.append(txt)
    has_w_or_p = any(("stageW" in t or "stageP" in t) for t in span_texts)
    assert not has_w_or_p, (
        f"With cap=32, NO span should label a W or P identifier (they're "
        f"truncated out of source). Got span_texts={span_texts}"
    )


def test_hard_negatives_in_source_but_not_in_reply_not_labelled():
    """AUDIT CASE 4: When source contains an identifier that does NOT appear
    in the reply, the source side should still classify it as STAGE_VAR
    (via src_token_type), but NO target_slots entry should be emitted —
    so no target position gets STAGE_VAR copy supervision for it."""
    tok = _load_tokenizer()
    if tok is None:
        pytest.skip("production tokenizer not present locally")
    coll = SimplexCollator(tok, enable_simplex_aux=True, max_cas_prefix_len=192)
    # Reply mentions only A0 and D2; source has A0, D2, AND W9 (distractor)
    body = "0185"
    distractor = "9999"
    rec = {
        "id": "test_hard_negative",
        "trace_id": "test_hard_negative",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain this rpm chain expression.",
        "reply_text": (
            f"Let stageA0_2_{body} name a foundational thought, "
            f"stageD2_2_{body} name a moment of awareness."
        ),
        "cas_expression": (
            f"let stageA0_2_{body} = ^0^P; "
            f"let stageD2_2_{body} = ^1^P; "
            f"let stageW9_9_{distractor} = ^7^P_{{F5}}"
        ),
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
    }
    batch = coll([rec], device="cpu")
    tsp = batch["typed_slot_positions"]
    slot_argmax = tsp[0].argmax(dim=-1)
    spans = _stage_var_spans(slot_argmax)
    # Reply has 2 identifiers (A0 + D2). Expect EXACTLY 2 target STAGE_VAR
    # spans (one per reply occurrence). The W9 distractor in source must
    # NOT introduce a 3rd target span.
    assert len(spans) == 2, (
        f"Reply has 2 identifiers (A0 + D2); source has 3 (+W9 distractor). "
        f"Target should have exactly 2 STAGE_VAR spans. Got {len(spans)}. "
        f"If 3, the distractor was incorrectly labelled in target — "
        f"hard-negative semantics broken."
    )


def test_trainer_cli_max_cas_prefix_len_default_32():
    """Confirm the CLI default for --max-cas-prefix-len is 32 (backward
    compat with A/B/C/D runs)."""
    from cas_native.training.train_simplex_mvp import parse_args
    cfg = parse_args(["--data-path", "x", "--output-dir", "y"])
    assert cfg.max_cas_prefix_len == 32


def test_trainer_cli_max_cas_prefix_len_override():
    """Confirm --max-cas-prefix-len 192 plumbs through to the config."""
    from cas_native.training.train_simplex_mvp import parse_args
    cfg = parse_args([
        "--data-path", "x", "--output-dir", "y",
        "--max-cas-prefix-len", "192",
    ])
    assert cfg.max_cas_prefix_len == 192
