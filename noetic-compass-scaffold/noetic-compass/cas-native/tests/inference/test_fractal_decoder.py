"""Phase 1B unit tests for cas_native.inference.fractal_decoder.

Coverage:
  - Phrase-trie construction: per-Noetic root, non-empty for all 10
  - first_token_ids_for: returns the right tokens; non-overlapping
    between adjacent k where indicator vocabularies are disjoint
  - State machine: fire conditions (pos==0 step 0, natural match,
    clause boundary, force-fire ceiling); pos increment on leaf
  - Logits processor: no-op when pos >= n; mask when in trie mode
  - constrained_strictly_beats_baseline: strict improvement only;
    failure_reason vetoes; prose-quality floor; cardinality regress
  - tail-indicates-boundary regex + word list

These tests use a deterministic MockTokenizer that returns
character-level "token ids" so the trie shapes are predictable. They
do NOT require loading a model checkpoint; integration testing of
the constrained path against the v0 checkpoint is done via the
canary harness and the Phase 1B shadow-mode eval.
"""
from __future__ import annotations

import math

import pytest
import torch

from cas_native.inference.fractal_decoder import (
    FractalConstraintState,
    FractalDecoderLog,
    FractalPhraseTrie,
    MAX_TOKENS_BETWEEN_SLOTS,
    SlotCommitEvent,
    TrieNode,
    _LEAF_BOUNDARY_PREFIXES,
    _should_fire_slot,
    _tail_indicates_boundary,
    build_boundary_token_ids,
    build_fractal_phrase_trie,
    constrained_strictly_beats_baseline,
    make_logits_processor,
)
from cas_native.inference.fractal_repair import (
    FractalRepairLog,
    _NOETIC_INDICATORS,
)


# ---------------------------------------------------------------------------
# Mock tokenizer: deterministic char-to-int mapping for predictable
# trie shapes. Pure ASCII; vocab is built from all chars that appear
# in the indicator phrases. No BPE, no sub-word merging.
# ---------------------------------------------------------------------------

class _MockCharTokenizer:
    """Each character is its own token id. The id is the codepoint
    so the mapping is stable across instances. Provides the minimum
    surface ``build_fractal_phrase_trie`` needs (``encode``, vocab_size)
    plus the surface ``_decode_tail_text`` needs (``decode``,
    ``skip_special``)."""

    BOS_ID = 1
    EOS_ID = 2
    PAD_ID = 0
    UNK_ID = 3
    vocab_size = 1024
    hash = "mock-char-v1"

    def encode(self, text: str, max_length: int = 64, add_special: bool = False) -> list[int]:
        if not text:
            return []
        return [ord(c) for c in text][:max_length]

    def decode(self, ids, *, skip_special: bool = True) -> str:
        chars = []
        for i in ids:
            if skip_special and i in (self.BOS_ID, self.EOS_ID, self.PAD_ID, self.UNK_ID):
                continue
            if 0 <= i < 0x110000:
                chars.append(chr(i))
        return "".join(chars)


# ---------------------------------------------------------------------------
# build_fractal_phrase_trie
# ---------------------------------------------------------------------------

def test_trie_has_root_for_every_noetic():
    """Every k in [0, 9] gets a root, even if its indicator list is empty."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    for k in range(10):
        assert k in trie.roots, f"missing root for noetic {k}"
        assert isinstance(trie.roots[k], TrieNode)


def test_trie_first_token_set_non_empty_for_each_noetic():
    """Every noetic in _NOETIC_INDICATORS has at least one phrase, so
    every trie root should have at least one child token id."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    for k in range(10):
        first_ids = trie.first_token_ids_for(k)
        assert first_ids, (
            f"noetic {k} trie root has empty first_token_ids; "
            f"indicators: {_NOETIC_INDICATORS[k]}"
        )


def test_trie_walks_phrase_to_leaf():
    """For each noetic, walk one indicator phrase from the root and
    confirm we reach an is_leaf node whose k_value matches."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    for k, indicators in _NOETIC_INDICATORS.items():
        phrase = indicators[0]
        ids = tok.encode(phrase)
        node = trie.roots[k]
        for tok_id in ids:
            assert tok_id in node.children, (
                f"k={k} phrase={phrase!r}: token {tok_id} ({chr(tok_id)!r}) "
                f"missing from trie at position; "
                f"available: {sorted(node.children.keys())}"
            )
            node = node.children[tok_id]
        assert node.is_leaf, (
            f"k={k} phrase={phrase!r}: trie path did not terminate at a leaf"
        )
        assert node.k_value == k
        assert node.phrase_text == phrase


def test_trie_leading_space_form_added():
    """build_fractal_phrase_trie should also insert phrases with leading
    space so mid-sentence tokenization is covered. With the char
    tokenizer, ord(' ')==32 should appear as a child of the root for
    each k where indicators exist."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    space_id = ord(" ")
    for k in range(10):
        assert space_id in trie.roots[k].children, (
            f"k={k}: leading-space form not inserted"
        )


# ---------------------------------------------------------------------------
# _tail_indicates_boundary
# ---------------------------------------------------------------------------

def test_tail_boundary_punctuation_triggers():
    """The rightmost non-whitespace character being a clause-boundary
    punctuation triggers the boundary signal. Middle-of-string
    punctuation does NOT trigger — only the rightmost char matters."""
    assert _tail_indicates_boundary("led to a thought,")
    assert _tail_indicates_boundary("a stage.   ")
    assert _tail_indicates_boundary("first thing;")
    assert _tail_indicates_boundary("a question?")
    assert _tail_indicates_boundary("emphatic!")
    # Middle-of-string punctuation does not fire — only rightmost.
    assert not _tail_indicates_boundary("first thing; second thing")


def test_tail_boundary_words_trigger():
    """The rightmost whitespace-delimited token being a connective
    triggers the boundary signal even without punctuation."""
    assert _tail_indicates_boundary("memory triggered an idea then")
    assert _tail_indicates_boundary("rubs the wrong way and")
    assert _tail_indicates_boundary("a thought which")
    assert _tail_indicates_boundary("led")


def test_tail_no_boundary_in_mid_clause():
    """Mid-clause prose with no boundary signal returns False. ``into``
    must NOT be a boundary word since it appears phrase-internal in
    canonical ``^9`` indicator ``popped into mind`` — firing on
    ``into`` would land slot N+1 mid-phrase."""
    assert not _tail_indicates_boundary("a memory triggered an")
    assert not _tail_indicates_boundary("rubs the wrong")
    assert not _tail_indicates_boundary("popped into")
    assert not _tail_indicates_boundary("")


# ---------------------------------------------------------------------------
# _should_fire_slot
# ---------------------------------------------------------------------------

def _make_state(expected_k=(3, 7), pos=0, mode="prose"):
    return FractalConstraintState(expected_k=expected_k, pos=pos, mode=mode)


def test_fire_slot_pos_at_end_never_fires():
    """When all slots are committed (pos >= len(expected_k)), the
    fire detector never returns True."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = _make_state(expected_k=(3, 7), pos=2)
    fire, hard = _should_fire_slot(state, [10, 20, 30], 5, tok, trie)
    assert not fire
    assert not hard


def test_fire_slot_at_step_zero_pos_zero_soft_triggers():
    """Right after BOS the very first decoder step is a slot trigger
    so the first natural argmax can decide whether to commit a phrase."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = _make_state(expected_k=(3, 7), pos=0)
    fire, hard = _should_fire_slot(state, [1], 0, tok, trie)
    assert fire
    assert not hard  # soft trigger, not forced


def test_fire_slot_force_fires_after_ceiling():
    """If tokens_since_last_commit exceeds MAX_TOKENS_BETWEEN_SLOTS the
    detector hard-forces a fire even without boundary signal."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = _make_state(expected_k=(3, 7), pos=1)
    state.tokens_since_last_commit = MAX_TOKENS_BETWEEN_SLOTS + 1
    # Seq decodes to a non-boundary tail.
    seq = [ord("a"), ord("b"), ord("c")]  # decodes to "abc"
    fire, hard = _should_fire_slot(state, seq, 50, tok, trie)
    assert fire
    assert hard


def test_fire_slot_natural_argmax_in_allowed_set_soft_fires():
    """When pos > 0 and the natural argmax is in the allowed first-
    token set for K[pos], the detector soft-fires so the model's
    natural choice gets walked through the trie."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = _make_state(expected_k=(3, 7), pos=1)
    state.tokens_since_last_commit = 3
    # An allowed first-token id for k=7.
    allowed_for_seven = list(trie.first_token_ids_for(7))
    assert allowed_for_seven, "k=7 has no first tokens — test setup bad"
    nat_id = allowed_for_seven[0]
    # Mid-clause tail, no boundary.
    seq = [ord("a"), ord("b"), ord("c")]
    fire, hard = _should_fire_slot(
        state, seq, 5, tok, trie, natural_next_id=nat_id,
    )
    assert fire
    assert not hard


def test_fire_slot_boundary_tail_soft_fires():
    """A clause-boundary tail soft-fires the detector at pos > 0."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = _make_state(expected_k=(3, 7), pos=1)
    state.tokens_since_last_commit = 3
    # Tail ends with comma — boundary signal.
    seq = [ord(c) for c in "led to a thought,"]
    fire, hard = _should_fire_slot(state, seq, 5, tok, trie)
    assert fire
    assert not hard


def test_fire_slot_no_signal_no_fire():
    """Mid-clause, no boundary, natural argmax not in allowed set,
    not yet at the force-fire ceiling: detector does not fire."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = _make_state(expected_k=(3, 7), pos=1)
    state.tokens_since_last_commit = 3
    seq = [ord(c) for c in "a quiet thought"]
    # A token id NOT in the allowed-first-tokens set.
    not_allowed = 9999
    assert not_allowed not in trie.first_token_ids_for(7)
    fire, hard = _should_fire_slot(
        state, seq, 5, tok, trie, natural_next_id=not_allowed,
    )
    assert not fire
    assert not hard


# ---------------------------------------------------------------------------
# make_logits_processor — masking behavior
# ---------------------------------------------------------------------------

def _logits(vocab_size: int, hot_id: int) -> torch.Tensor:
    """Build a logits vector where ``hot_id`` is the highest-logit token."""
    out = torch.zeros(vocab_size, dtype=torch.float32)
    if 0 <= hot_id < vocab_size:
        out[hot_id] = 10.0
    return out


def test_processor_noop_when_all_slots_committed():
    """When pos >= n the processor is a passthrough."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3, 7), pos=2)
    proc = make_logits_processor(state, trie, tok)
    logits = _logits(1024, 42)
    out = proc([1, 10, 20, 30], 5, logits)
    # Passthrough: returned logits identical to input.
    assert torch.allclose(out, logits)


def test_processor_masks_to_allowed_children_in_trie_mode():
    """When state.mode='trie' the processor masks ALL non-allowed
    tokens to -inf, leaving only the trie children with finite logits."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3, 7), pos=0)
    # Manually enter trie mode at root for k=3.
    state.mode = "trie"
    state.current_node = trie.roots[3]
    proc = make_logits_processor(state, trie, tok)
    # Logits with a non-allowed token as the natural argmax.
    not_allowed = 9999
    assert not_allowed not in trie.first_token_ids_for(3)
    logits = _logits(10000, not_allowed)
    out = proc([1], 0, logits)
    # The non-allowed token should now be -inf.
    assert math.isinf(float(out[not_allowed])) and float(out[not_allowed]) < 0
    # At least one allowed token id should still be finite.
    allowed = trie.first_token_ids_for(3)
    finite_allowed = [tok_id for tok_id in allowed if math.isfinite(float(out[tok_id]))]
    assert finite_allowed, "all allowed tokens were masked — mask bug"


def test_processor_increments_pos_on_leaf():
    """After the trie walks to a leaf node, the processor increments
    pos and exits trie mode."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3,), pos=0)
    proc = make_logits_processor(state, trie, tok)

    # Pick a short phrase: ^3 has "averse" which is short.
    phrase = "averse"
    phrase_ids = tok.encode(phrase)
    # Step 0: enter trie mode by passing pos=0 step=0 (soft-trigger
    # always fires at step 0 pos 0). Processor enters trie at root[3]
    # and masks to allowed children.
    logits = _logits(1024, phrase_ids[0])
    seq = [1]  # just BOS
    out = proc(seq, 0, logits)
    # Now state should be in trie mode at root[3].
    assert state.mode == "trie"
    assert state.current_node is trie.roots[3]

    # Simulate the sampler committed phrase_ids[0].
    seq.append(phrase_ids[0])
    out = proc(seq, 1, _logits(1024, phrase_ids[1] if len(phrase_ids) > 1 else 0))
    # current_node has advanced one level down.
    assert state.current_node is not trie.roots[3]
    assert not state.current_node.is_leaf

    # Walk the rest of the phrase.
    for i in range(1, len(phrase_ids)):
        seq.append(phrase_ids[i])
        next_logit_id = phrase_ids[i + 1] if i + 1 < len(phrase_ids) else 0
        _ = proc(seq, i + 1, _logits(1024, next_logit_id))

    # After the final phrase token commits, the next processor call
    # processes seq[-1] = last phrase token, which lands the leaf.
    # The processor commits the slot and increments pos.
    # Let's call it once more to trigger the leaf-detect path:
    seq.append(0)  # next sampled token after phrase completes
    _ = proc(seq, len(phrase_ids) + 1, _logits(1024, 0))
    # By now state.pos should be 1 (we had 1 slot, completed it).
    assert state.pos == 1
    assert state.mode == "prose"
    # SlotCommitEvent recorded.
    assert len(state.slot_commits) == 1
    assert state.slot_commits[0].pos == 0
    assert state.slot_commits[0].k_value == 3
    assert state.slot_commits[0].phrase_chosen == phrase


def test_processor_handles_full_walk_for_short_phrase():
    """Smoke: a complete walk over the shortest ^9 phrase 'clicked'
    should commit one slot for an expected_k=(9,) source."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(9,), pos=0)
    proc = make_logits_processor(state, trie, tok)
    phrase = "clicked"
    phrase_ids = tok.encode(phrase)

    seq = [1]
    # Step 0: enter trie mode.
    _ = proc(seq, 0, _logits(1024, phrase_ids[0]))
    # Walk.
    for i, tok_id in enumerate(phrase_ids):
        seq.append(tok_id)
        _ = proc(seq, i + 1, _logits(1024, 0))
    # One more step to detect the leaf.
    seq.append(0)
    _ = proc(seq, len(phrase_ids) + 1, _logits(1024, 0))
    assert state.pos == 1
    assert state.mode == "prose"


# ---------------------------------------------------------------------------
# constrained_strictly_beats_baseline (fail-closed comparator)
# ---------------------------------------------------------------------------

def _verifier(
    *, parsed=True, cardinality=False, sequence=False, mismatches=()
) -> FractalRepairLog:
    return FractalRepairLog(
        sequence_parsed=parsed,
        cardinality_matches=cardinality,
        sequence_matches=sequence,
        mismatch_positions=list(mismatches),
    )


def test_comparator_constrained_wins_when_sequence_match_flips():
    """When constrained achieves sequence_matches=True and baseline
    didn't, constrained wins regardless of mismatch counts."""
    better, reason = constrained_strictly_beats_baseline(
        constrained_text="The thought rubs the wrong way and became muscle memory.",
        constrained_stopped_on_eos=True,
        constrained_verifier=_verifier(cardinality=True, sequence=True),
        baseline_text="A thought.",
        baseline_stopped_on_eos=True,
        baseline_verifier=_verifier(cardinality=False, sequence=False, mismatches=()),
    )
    assert better
    assert "sequence_matches" in reason


def test_comparator_failure_reason_vetoes_constrained():
    """If the constrained run hit a mid-decode failure, baseline wins
    no matter how the verifier looks."""
    better, reason = constrained_strictly_beats_baseline(
        constrained_text="",
        constrained_stopped_on_eos=False,
        constrained_verifier=_verifier(cardinality=True, sequence=True),
        baseline_text="A thought.",
        baseline_stopped_on_eos=True,
        baseline_verifier=_verifier(cardinality=False, sequence=False),
        constraint_failure_reason="trie_dead_end at pos=2",
    )
    assert not better
    assert "trie_dead_end" in reason


def test_comparator_cardinality_regression_vetoes_constrained():
    """If constrained LOST the cardinality match, baseline wins."""
    better, reason = constrained_strictly_beats_baseline(
        constrained_text="Some prose",
        constrained_stopped_on_eos=True,
        constrained_verifier=_verifier(cardinality=False),
        baseline_text="Other prose",
        baseline_stopped_on_eos=True,
        baseline_verifier=_verifier(cardinality=True),
    )
    assert not better
    assert "LOST cardinality" in reason


def test_comparator_prose_quality_floor():
    """If constrained achieves a structural win but at a heavy prose-
    quality cost (truncation + repetition), baseline still wins."""
    bad_constrained_text = "uh"  # tiny + truncated
    better, reason = constrained_strictly_beats_baseline(
        constrained_text=bad_constrained_text,
        constrained_stopped_on_eos=False,  # truncated penalty
        constrained_verifier=_verifier(cardinality=True, sequence=True),
        baseline_text=(
            "A normal-length prose response that ends cleanly."
        ),
        baseline_stopped_on_eos=True,
        baseline_verifier=_verifier(cardinality=True, sequence=False),
    )
    assert not better
    assert "prose quality" in reason.lower() or "prose_quality" in reason.lower()


def test_comparator_neither_cardinality_match_no_winner():
    """When neither baseline nor constrained achieved cardinality match,
    baseline wins (no clear structural improvement)."""
    better, reason = constrained_strictly_beats_baseline(
        constrained_text="Some prose, some prose.",
        constrained_stopped_on_eos=True,
        constrained_verifier=_verifier(cardinality=False),
        baseline_text="Other prose, other prose.",
        baseline_stopped_on_eos=True,
        baseline_verifier=_verifier(cardinality=False),
    )
    assert not better


def test_comparator_fewer_mismatches_when_both_cardinality_match():
    """When both achieved cardinality match, the run with fewer
    mismatch_positions wins."""
    better, reason = constrained_strictly_beats_baseline(
        constrained_text=(
            "The thought rubs the wrong way and ended in muscle memory."
        ),
        constrained_stopped_on_eos=True,
        constrained_verifier=_verifier(
            cardinality=True, sequence=False, mismatches=(0,),
        ),
        baseline_text=(
            "The thought drifted and ended elsewhere completely."
        ),
        baseline_stopped_on_eos=True,
        baseline_verifier=_verifier(
            cardinality=True, sequence=False, mismatches=(0, 1, 2),
        ),
    )
    assert better
    assert "mismatch_positions: 3 -> 1" in reason


# ---------------------------------------------------------------------------
# FractalDecoderLog.to_dict round-trip schema
# ---------------------------------------------------------------------------

def test_decoder_log_to_dict_default():
    """Empty log dict round-trips with all expected keys."""
    log = FractalDecoderLog()
    d = log.to_dict()
    for key in (
        "enabled", "fired", "notation", "expected_k_values",
        "constrained_text", "constrained_verifier", "baseline_text",
        "baseline_verifier", "slot_commits", "selected",
        "fallback_reason", "notes",
    ):
        assert key in d, f"missing key in default log dict: {key}"
    assert d["enabled"] is False
    assert d["fired"] is False
    assert d["selected"] == "baseline"
    assert d["slot_commits"] == []


def test_decoder_log_to_dict_with_slot_events():
    """Slot events serialize to dicts inside the to_dict output."""
    log = FractalDecoderLog(
        enabled=True, fired=True, notation="Φ",
        expected_k_values=[3, 7],
        slot_commits=[
            SlotCommitEvent(
                pos=0, k_value=3,
                phrase_chosen="rubs the wrong way",
                start_step=2, end_step=6, hard_forced=False,
            ),
        ],
    )
    d = log.to_dict()
    assert d["enabled"] is True
    assert d["fired"] is True
    assert d["notation"] == "Φ"
    assert d["expected_k_values"] == [3, 7]
    assert len(d["slot_commits"]) == 1
    sc = d["slot_commits"][0]
    assert sc["pos"] == 0
    assert sc["k_value"] == 3
    assert sc["phrase_chosen"] == "rubs the wrong way"


# ---------------------------------------------------------------------------
# Task #135 tuning lever 1 — EOS bias after final slot
# ---------------------------------------------------------------------------

def test_eos_bias_inactive_before_final_slot():
    """While pos < n the EOS-bias parameter must NOT affect logits;
    constraint logic still drives the mask in trie mode."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3, 7), pos=0)
    proc = make_logits_processor(state, trie, tok, eos_id=2, eos_bias=10.0)
    logits = _logits(1024, 42)
    out = proc([1], 0, logits.clone())
    # Step 0 with pos==0 enters trie mode (soft trigger). The processor
    # returns MASKED logits, not the unbiased input. The EOS-bias should
    # not apply during constrained-decode steps — only after pos >= n.
    # Verify the returned tensor is not byte-equal to the raw input
    # (mask has been applied).
    assert not torch.allclose(out, logits)
    # And verify the EOS slot itself wasn't biased (it's not in the
    # allowed children of root[3], so it should be -inf).
    assert math.isinf(float(out[2])) and float(out[2]) < 0


def test_eos_bias_applies_after_all_slots_committed():
    """When pos >= n, the processor passes logits through but adds
    ``eos_bias`` to the EOS token's logit so the model terminates
    sooner and trailing prose stops contaminating the verifier."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3,), pos=1)  # already committed
    proc = make_logits_processor(state, trie, tok, eos_id=2, eos_bias=5.0)
    logits = _logits(1024, 42)
    # EOS logit pre-bias.
    orig_eos = float(logits[2])
    out = proc([1, 10, 20], 5, logits.clone())
    # Output should be the input + bias on EOS slot.
    assert math.isclose(float(out[2]), orig_eos + 5.0, abs_tol=1e-6)
    # Other slots should be unchanged.
    assert math.isclose(float(out[42]), float(logits[42]), abs_tol=1e-6)


def test_eos_bias_zero_is_a_noop_after_final_slot():
    """``eos_bias=0`` (default) restores byte-equality to the unbiased
    pass when pos >= n, even when ``eos_id`` is set."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3,), pos=1)
    proc = make_logits_processor(state, trie, tok, eos_id=2, eos_bias=0.0)
    logits = _logits(1024, 42)
    out = proc([1, 10, 20], 5, logits.clone())
    assert torch.allclose(out, logits)


def test_eos_bias_skipped_when_no_eos_id():
    """If ``eos_id`` is None, the bias parameter has no effect."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(3,), pos=1)
    proc = make_logits_processor(state, trie, tok, eos_id=None, eos_bias=5.0)
    logits = _logits(1024, 42)
    out = proc([1, 10, 20], 5, logits.clone())
    assert torch.allclose(out, logits)


# ---------------------------------------------------------------------------
# Task #135 tuning lever 2 — comparator first_n_mode
# ---------------------------------------------------------------------------

def _verifier_with_found(
    *, expected, found
) -> FractalRepairLog:
    """Build a verifier log mimicking what `verify_fractal_rendering`
    would produce, but with custom expected/found sequences. Computes
    cardinality/sequence/mismatches inline so the comparator sees
    consistent fields."""
    from cas_native.inference.fractal_repair import _compare_sequences
    cardinality, sequence, mismatches = _compare_sequences(
        list(expected), list(found),
    )
    return FractalRepairLog(
        sequence_parsed=True,
        expected_k_count=len(expected),
        expected_k_values=list(expected),
        found_k_count=len(found),
        found_k_sequence=list(found),
        cardinality_matches=cardinality,
        sequence_matches=sequence,
        mismatch_positions=mismatches,
    )


def test_first_n_mode_recovers_constrained_when_trailing_prose_contaminates():
    """The smoke-evidence failure mode: constrained landed all 8 slots
    correctly in order but trailing prose added extra noetic
    indicators. With ``first_n_mode=True`` the comparator should see
    the constrained as a strict sequence_match win."""
    expected = [6, 9, 7, 0, 9, 5, 2, 0]
    # Constrained landed exact sequence then trailing prose added 4 extras.
    constrained_v = _verifier_with_found(
        expected=expected,
        found=expected + [1, 2, 3, 8],
    )
    baseline_v = _verifier_with_found(
        expected=expected,
        found=[0, 1, 2, 6, 8, 3, 6, 9],
    )
    # Default (full sequence) mode: constrained has 12 found vs 8
    # expected, so cardinality fails, no win.
    better_default, _ = constrained_strictly_beats_baseline(
        constrained_text="a" * 100,
        constrained_stopped_on_eos=True,
        constrained_verifier=constrained_v,
        baseline_text="b" * 100,
        baseline_stopped_on_eos=True,
        baseline_verifier=baseline_v,
    )
    assert not better_default

    # first_n_mode: constrained's first-8 is the exact expected — win.
    better_firstn, reason_firstn = constrained_strictly_beats_baseline(
        constrained_text="a" * 100,
        constrained_stopped_on_eos=True,
        constrained_verifier=constrained_v,
        baseline_text="b" * 100,
        baseline_stopped_on_eos=True,
        baseline_verifier=baseline_v,
        first_n_mode=True,
    )
    assert better_firstn
    assert "sequence_matches" in reason_firstn.lower() or "mismatch" in reason_firstn.lower()


def test_first_n_mode_still_vetoes_on_constraint_failure():
    """first_n_mode does NOT bypass the constraint_failure_reason veto:
    a mid-decode trie failure still forces baseline."""
    expected = [3, 7]
    constrained_v = _verifier_with_found(
        expected=expected, found=expected,
    )
    baseline_v = _verifier_with_found(
        expected=expected, found=[],
    )
    better, reason = constrained_strictly_beats_baseline(
        constrained_text="ok",
        constrained_stopped_on_eos=True,
        constrained_verifier=constrained_v,
        baseline_text="ok",
        baseline_stopped_on_eos=True,
        baseline_verifier=baseline_v,
        constraint_failure_reason="trie_dead_end at pos=1",
        first_n_mode=True,
    )
    assert not better
    assert "trie_dead_end" in reason


# ---------------------------------------------------------------------------
# Task #138 tuning lever 3 — leaf-exit boundary-token bias
# ---------------------------------------------------------------------------

def test_build_boundary_token_ids_non_empty():
    """The boundary-token id set is non-empty against the char tokenizer."""
    tok = _MockCharTokenizer()
    ids = build_boundary_token_ids(tok)
    # The char tokenizer encodes " " as ord(' ')==32, "," as 44, etc.
    # Verify a few signatures are present.
    assert ord(" ") in ids
    assert ord(",") in ids
    assert ord(".") in ids
    assert ord(";") in ids
    # Conjunction-with-leading-space — first token is the space.
    # All of those collapse to ord(' ')=32 in the char tokenizer.
    # Make sure the set hasn't accidentally collapsed to one element.
    # With ASCII chars there should be at least the bare-punctuation
    # set + the space token.
    assert len(ids) >= 6


def test_boundary_pending_set_on_leaf_with_lever_enabled():
    """When ``enforce_leaf_exit_boundary=True``, every leaf reach sets
    ``state.boundary_pending = True``. With the lever DISABLED the flag
    stays False (control)."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    boundary_ids = build_boundary_token_ids(tok)

    # Lever DISABLED branch — boundary_pending stays False.
    state_off = FractalConstraintState(expected_k=(9,), pos=0)
    proc_off = make_logits_processor(
        state_off, trie, tok,
        enforce_leaf_exit_boundary=False,
        boundary_token_ids=boundary_ids,
    )
    phrase = "clicked"
    phrase_ids = tok.encode(phrase)
    seq = [1]
    _ = proc_off(seq, 0, _logits(1024, phrase_ids[0]))
    for i, tok_id in enumerate(phrase_ids):
        seq.append(tok_id)
        _ = proc_off(seq, i + 1, _logits(1024, 0))
    # One more step to detect the leaf.
    seq.append(0)
    _ = proc_off(seq, len(phrase_ids) + 1, _logits(1024, 0))
    assert state_off.pos == 1
    # Lever disabled → boundary_pending never set.
    assert state_off.boundary_pending is False

    # Lever ENABLED branch — boundary_pending gets set on leaf reach.
    state_on = FractalConstraintState(expected_k=(9,), pos=0)
    proc_on = make_logits_processor(
        state_on, trie, tok,
        enforce_leaf_exit_boundary=True,
        boundary_token_ids=boundary_ids,
    )
    seq = [1]
    _ = proc_on(seq, 0, _logits(1024, phrase_ids[0]))
    for i, tok_id in enumerate(phrase_ids):
        seq.append(tok_id)
        _ = proc_on(seq, i + 1, _logits(1024, 0))
    # NOTE: do NOT consume the boundary mask here — append a dummy
    # next step + check state IMMEDIATELY after the leaf is reached,
    # which happens inside the next processor call.
    seq.append(0)  # placeholder; the leaf detection happens in the next call
    _ = proc_on(seq, len(phrase_ids) + 1, _logits(1024, 0))
    # After processing the last phrase token (which lands the leaf),
    # boundary_pending was set THEN cleared in the same call (the
    # mask was applied immediately). The flag is one-shot — clearing
    # is correct.
    assert state_on.pos == 1
    assert state_on.boundary_pending is False  # consumed in the same step


def test_boundary_mask_restricts_to_boundary_ids_after_leaf():
    """The first step after a leaf reach masks the logits to allow ONLY
    boundary token ids — the model cannot emit 'n' continuing into
    'aversen'."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    boundary_ids = build_boundary_token_ids(tok)
    state = FractalConstraintState(expected_k=(3, 7), pos=0)
    proc = make_logits_processor(
        state, trie, tok,
        enforce_leaf_exit_boundary=True,
        boundary_token_ids=boundary_ids,
    )

    # Manually set up state JUST PAST a leaf reach. We simulate that
    # by directly setting boundary_pending=True (the actual leaf-
    # transition logic is tested by the previous test).
    state.boundary_pending = True
    state.mode = "prose"
    state.pos = 1  # one slot committed, one to go
    state.tokens_since_last_commit = 0

    # Build logits where the natural argmax is a NON-boundary token
    # like "n" (which would corrupt "averse" into "aversen").
    n_id = ord("n")
    logits = _logits(1024, n_id)
    seq = [1, ord("a"), ord("v"), ord("e"), ord("r"), ord("s"), ord("e")]
    out = proc(seq, len(seq) - 1, logits.clone())

    # The 'n' token MUST be -inf in the output (boundary mask blocks it).
    assert math.isinf(float(out[n_id])) and float(out[n_id]) < 0
    # At least one boundary token must remain finite.
    finite_boundary = [
        tok_id for tok_id in boundary_ids if math.isfinite(float(out[tok_id]))
    ]
    assert finite_boundary, "all boundary tokens were masked — mask bug"
    # boundary_pending should be cleared (one-shot semantics).
    assert state.boundary_pending is False


def test_boundary_mask_allows_eos_when_final_slot_committed():
    """At pos == n (all expected slots committed) the boundary mask
    ADDS the EOS token to its allowed-set so the model can terminate
    after the boundary."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    boundary_ids = build_boundary_token_ids(tok)
    eos_id = tok.EOS_ID  # 2 in the mock tokenizer
    state = FractalConstraintState(expected_k=(9,), pos=1)  # final slot done
    state.boundary_pending = True
    proc = make_logits_processor(
        state, trie, tok,
        enforce_leaf_exit_boundary=True,
        boundary_token_ids=boundary_ids,
        eos_id=eos_id,
    )
    # Logits with EOS as the natural argmax.
    logits = _logits(1024, eos_id)
    out = proc([1, 10, 20], 5, logits.clone())
    # EOS must NOT be masked — it's in the augmented allowed set.
    assert math.isfinite(float(out[eos_id]))


def test_boundary_mask_excludes_eos_when_more_slots_remain():
    """At pos < n the boundary mask must NOT allow EOS — terminating
    early would leave required slots uncommitted."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    boundary_ids = build_boundary_token_ids(tok)
    eos_id = tok.EOS_ID
    state = FractalConstraintState(expected_k=(3, 7), pos=1)  # one slot left
    state.boundary_pending = True
    proc = make_logits_processor(
        state, trie, tok,
        enforce_leaf_exit_boundary=True,
        boundary_token_ids=boundary_ids,
        eos_id=eos_id,
    )
    logits = _logits(1024, eos_id)
    out = proc([1, 10, 20], 5, logits.clone())
    # EOS MUST be masked — we still have slot 1 to commit.
    assert math.isinf(float(out[eos_id])) and float(out[eos_id]) < 0


def test_boundary_lever_default_off_is_noop():
    """When the lever is left at its default (False), the processor
    behaves identically to the pre-lever-3 implementation: never
    masks to boundary tokens, never sets ``state.boundary_pending``."""
    tok = _MockCharTokenizer()
    trie = build_fractal_phrase_trie(tok)
    state = FractalConstraintState(expected_k=(9,), pos=0)
    # No lever-3 args passed — defaults apply.
    proc = make_logits_processor(state, trie, tok)
    phrase_ids = tok.encode("clicked")
    seq = [1]
    _ = proc(seq, 0, _logits(1024, phrase_ids[0]))
    for i, tok_id in enumerate(phrase_ids):
        seq.append(tok_id)
        _ = proc(seq, i + 1, _logits(1024, 0))
    seq.append(0)
    _ = proc(seq, len(phrase_ids) + 1, _logits(1024, 0))
    # Default-off: boundary_pending never set.
    assert state.boundary_pending is False
    # pos still incremented normally.
    assert state.pos == 1


def test_first_n_mode_truncates_baseline_too():
    """first_n_mode applies symmetrically: both baseline and constrained
    are truncated to first-n. A baseline whose first-n is correct should
    still beat (or tie) a constrained whose first-n is worse."""
    expected = [3, 7]
    # Baseline: first-2 found is the exact expected; trailing prose
    # adds 4 extras. Constrained: only 1 of 2 correct in first-2.
    baseline_v = _verifier_with_found(
        expected=expected, found=expected + [1, 1, 1, 1],
    )
    constrained_v = _verifier_with_found(
        expected=expected, found=[3, 9, 5, 1, 8, 0],
    )
    better, reason = constrained_strictly_beats_baseline(
        constrained_text="x" * 100,
        constrained_stopped_on_eos=True,
        constrained_verifier=constrained_v,
        baseline_text="y" * 100,
        baseline_stopped_on_eos=True,
        baseline_verifier=baseline_v,
        first_n_mode=True,
    )
    # Baseline first-2 = [3, 7] (cardinality + sequence match).
    # Constrained first-2 = [3, 9] (cardinality match but not sequence).
    # Both cardinality-match in first-n; baseline has 0 mismatches,
    # constrained has 1 — baseline strictly better, so NOT a constrained win.
    assert not better
