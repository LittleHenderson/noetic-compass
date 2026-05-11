"""Phase 1B — opt-in shadow-mode fractal-aware constrained decoder.

Per the v1e architecture design (audit-modified 2026-05-10):
``docs/working/v1e_pointer_copy_fractal_decoder_design_2026_05_10.md``.

Decoder helper that biases generation toward the canonical Noetic-class
colloquialism phrases when the source CAS is a ``Φ<…>`` fractal. The
helper does NOT mutate the rendered text directly — it applies a hard
logits mask at every decoder step where the constraint is active, then
the existing autoregressive loop in ``native_nl_generate.generate_reply``
runs to completion. The orchestrator (``routed_generate``) wraps this
helper with the fail-closed comparator: BOTH baseline and constrained
generations run; whichever scores better on the verifier + prose-quality
heuristic is returned to the caller.

Audit-mandated design constraints:

- **Phrase-trie, not first-token mask alone.** The constraint is built
  over the TOKENIZED prefixes of approved Noetic-class phrases from
  ``fractal_repair._NOETIC_INDICATORS``. Constraint mode is only ENTERED
  via the slot detector; never via raw first-token presence. Common
  words like "a", "that", "who", "popped" cannot trigger constraint by
  themselves — they only constrain when we're mid-walk and the next
  step must extend an approved phrase prefix.
- **Fail closed.** If constrained decoding produces a worse verifier
  result, worse prose quality, truncation, or a stuck state, the
  orchestrator returns the baseline and logs the failed attempt.
- **Opt-in shadow mode.** ``apply_fractal_decoder`` defaults False in
  ``routed_generate``. The constraint runs in addition to baseline,
  not in place of it, until eval data proves a production-default
  promotion.

Three-layer source-shape gate (mirrors ``rpm_repair`` / ``meta_logic_repair``):
  1. ``apply_fractal_decoder`` flag in ``routed_generate`` (default False).
  2. ``routing.task_type == "cas_to_english"`` — invalid CAS skipped.
  3. ``parse_fractal`` returns None for non-fractal sources (state literals,
     recipes, rpm_chains, meta-logic, CRO all no-op).

When the gate is satisfied, the constrained decode runs side-by-side
with the baseline and the orchestrator picks the better output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import torch

from cas_native.inference.fractal_repair import (
    FractalRepairLog,
    FractalSequence,
    _NOETIC_INDICATORS,
    _compare_sequences,
    extract_noetic_sequence,
    parse_fractal,
    verify_fractal_rendering,
)


# Soft secondary trigger: if too many tokens pass since the last slot
# committed and pos < n, the slot detector force-fires regardless of
# clause-boundary signals. Bounds damage from a missed boundary.
MAX_TOKENS_BETWEEN_SLOTS = 25

# Punctuation characters that count as clause boundaries when found at
# the tail of decoded prose.
_BOUNDARY_PUNCTUATION = frozenset({",", ".", ";", ":", "?", "!"})

# Connective words that count as clause boundaries when they appear as
# the rightmost whitespace-delimited token in the decoded prose tail.
# Extracted from Record 14's successful prose silhouette
# ("rubs the wrong way LED TO a thought that THEN became muscle memory")
# plus standard English coordinators. Curated to AVOID words that are
# also phrase-internal in canonical Noetic indicators — e.g. "into"
# appears in "popped into mind", so it cannot fire as a boundary or
# the slot detector would try to land slot N+1 mid-phrase.
_BOUNDARY_WORDS = frozenset({
    "then", "which", "and", "finally", "so", "led", "became",
    "but", "or", "thereafter", "next",
})

# Number of trailing decoder tokens to decode-and-scan when checking the
# slot detector's boundary condition. Small to keep the per-step cost low.
_BOUNDARY_TAIL_TOKEN_WINDOW = 16


@dataclass
class TrieNode:
    """One node of a phrase trie keyed on tokenizer token ids.

    ``children`` maps the next token id → next ``TrieNode``. ``is_leaf``
    is True when the path from root to here corresponds to a complete
    approved phrase from ``_NOETIC_INDICATORS``. ``phrase_text`` records
    the original phrase string (for logs); ``k_value`` records which
    Noetic this phrase belongs to.
    """
    children: dict[int, "TrieNode"] = field(default_factory=dict)
    is_leaf: bool = False
    phrase_text: Optional[str] = None
    k_value: Optional[int] = None


@dataclass
class FractalPhraseTrie:
    """Per-Noetic phrase tries, built lazily against a specific tokenizer.

    Each ``roots[k]`` is the root of a trie whose paths spell out every
    approved phrase from ``_NOETIC_INDICATORS[k]``. The trie is keyed
    on TOKEN IDS from the tokenizer's BPE encoding. Each indicator
    phrase is added in TWO forms — with a leading space and without —
    because the same phrase may tokenize differently at start-of-prose
    vs mid-sentence.

    The trie is the data structure the constrained decoder walks; the
    orchestrator builds one ``FractalPhraseTrie`` per call (cheap;
    ~50 phrases × 2 forms = 100 trie paths over ~5-10 tokens each)
    or caches across calls keyed on the tokenizer's hash.
    """
    roots: dict[int, TrieNode]
    tokenizer_hash: str

    def first_token_ids_for(self, k: int) -> set[int]:
        """All token ids that are valid first tokens for a phrase of
        Noetic ``k``. Used to decide if entering trie mode is licensed
        on the model's natural next-token preference."""
        root = self.roots.get(k)
        if root is None:
            return set()
        return set(root.children.keys())


def _safe_tokenizer_hash(tokenizer: Any) -> str:
    """Best-effort stable identifier for a tokenizer instance, used to
    cache or invalidate the trie. Falls back to id() if the tokenizer
    doesn't expose a hash attribute."""
    h = getattr(tokenizer, "hash", None) or getattr(tokenizer, "vocab_size", None)
    if h is not None:
        return f"{type(tokenizer).__name__}:{h}"
    return f"{type(tokenizer).__name__}:{id(tokenizer)}"


def _encode_phrase(tokenizer: Any, phrase: str) -> list[int]:
    """Tokenize ``phrase`` via the tokenizer's encode contract. Returns
    a flat list of token ids with no specials prepended/appended."""
    return list(tokenizer.encode(phrase, max_length=64, add_special=False))


def _insert_phrase(root: TrieNode, ids: list[int], phrase: str, k: int) -> None:
    """Insert a tokenized phrase into the trie rooted at ``root``."""
    if not ids:
        return
    node = root
    for tok in ids:
        nxt = node.children.get(tok)
        if nxt is None:
            nxt = TrieNode()
            node.children[tok] = nxt
        node = nxt
    # Only OVERWRITE leaf marker if not already a leaf (preserve the
    # first phrase that landed at this leaf for log clarity).
    if not node.is_leaf:
        node.is_leaf = True
        node.phrase_text = phrase
        node.k_value = k


def build_fractal_phrase_trie(tokenizer: Any) -> FractalPhraseTrie:
    """Build per-Noetic phrase tries from ``_NOETIC_INDICATORS``.

    Each indicator phrase is tokenized in two forms — with leading
    space and without — because BPE encoders typically produce different
    token sequences at sentence-start (no leading space) vs mid-sentence
    (with leading space). Both forms share trie suffixes when their
    token sequences converge.

    Cost: O(sum of phrase token counts) once at build time. ~100 phrases
    × ~5-10 tokens each = ~500-1000 trie-node insertions. Trivial.
    """
    roots: dict[int, TrieNode] = {k: TrieNode() for k in range(10)}
    for k, indicators in _NOETIC_INDICATORS.items():
        for phrase in indicators:
            # Two forms: with leading space (mid-prose context) and
            # without (start-of-prose context).
            no_lead_ids = _encode_phrase(tokenizer, phrase)
            with_lead_ids = _encode_phrase(tokenizer, " " + phrase)
            if no_lead_ids:
                _insert_phrase(roots[k], no_lead_ids, phrase, k)
            if with_lead_ids and with_lead_ids != no_lead_ids:
                _insert_phrase(roots[k], with_lead_ids, phrase, k)
    return FractalPhraseTrie(
        roots=roots, tokenizer_hash=_safe_tokenizer_hash(tokenizer),
    )


@dataclass
class SlotCommitEvent:
    """One log record for a Noetic-phrase slot that the constrained
    decoder committed during a run. Recorded ON LEAF reach."""
    pos: int
    k_value: int
    phrase_chosen: str
    start_step: int
    end_step: int
    hard_forced: bool  # True if soft-trigger threshold was bypassed via force-fire


@dataclass
class FractalDecoderLog:
    """Per-run artifact for the fractal-aware decoder.

    The orchestrator preserves BOTH baseline and constrained outputs in
    eval artifacts (audit §4 mandate). This dataclass records what the
    constrained run did and why fail-closed kept or replaced the
    baseline.
    """
    enabled: bool = False  # was apply_fractal_decoder True for this call?
    fired: bool = False    # did the source-shape gate let us enter constrained decode?
    notation: Optional[str] = None  # "Φ" or "Phi" or None when not fired
    expected_k_values: list[int] = field(default_factory=list)
    constrained_text: Optional[str] = None
    constrained_verifier: Optional[dict[str, object]] = None
    baseline_text: Optional[str] = None
    baseline_verifier: Optional[dict[str, object]] = None
    slot_commits: list[SlotCommitEvent] = field(default_factory=list)
    selected: str = "baseline"  # "baseline" or "constrained"
    fallback_reason: Optional[str] = None  # why baseline was selected over constrained
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "fired": self.fired,
            "notation": self.notation,
            "expected_k_values": list(self.expected_k_values),
            "constrained_text": self.constrained_text,
            "constrained_verifier": self.constrained_verifier,
            "baseline_text": self.baseline_text,
            "baseline_verifier": self.baseline_verifier,
            "slot_commits": [
                {
                    "pos": s.pos,
                    "k_value": s.k_value,
                    "phrase_chosen": s.phrase_chosen,
                    "start_step": s.start_step,
                    "end_step": s.end_step,
                    "hard_forced": s.hard_forced,
                }
                for s in self.slot_commits
            ],
            "selected": self.selected,
            "fallback_reason": self.fallback_reason,
            "notes": list(self.notes),
        }


@dataclass
class FractalConstraintState:
    """Per-call mutable state for the constrained decoder.

    Mutated INSIDE the step callback closure during a single call to
    ``generate_reply``. Held outside the callback so the orchestrator
    can inspect it after the run completes (e.g., to populate the
    ``FractalDecoderLog.slot_commits``).
    """
    expected_k: tuple[int, ...]
    pos: int = 0
    mode: str = "prose"  # "prose" or "trie"
    current_node: Optional[TrieNode] = None
    current_phrase_start_step: int = -1
    tokens_since_last_commit: int = 0
    slot_commits: list[SlotCommitEvent] = field(default_factory=list)
    failure_reason: Optional[str] = None


def _decode_tail_text(
    tokenizer: Any,
    seq: list[int],
    window: int = _BOUNDARY_TAIL_TOKEN_WINDOW,
) -> str:
    """Decode the last ``window`` tokens of ``seq`` to plain text for
    boundary inspection. Skip-special so BOS/EOS/PAD don't contaminate
    the tail string."""
    if not seq:
        return ""
    tail_ids = seq[-window:]
    try:
        return str(tokenizer.decode(tail_ids, skip_special=True))
    except Exception:
        return ""


def _tail_indicates_boundary(tail: str) -> bool:
    """True iff the rolling decoded tail ends with a clause-boundary
    signature: rightmost non-whitespace char in ``_BOUNDARY_PUNCTUATION``,
    OR rightmost whitespace-delimited word in ``_BOUNDARY_WORDS``."""
    stripped = tail.rstrip()
    if not stripped:
        return False
    if stripped[-1] in _BOUNDARY_PUNCTUATION:
        return True
    # Check the rightmost word (strip trailing punctuation).
    parts = stripped.split()
    if not parts:
        return False
    last_word = parts[-1].rstrip(",.;:!?").lower()
    return last_word in _BOUNDARY_WORDS


def _should_fire_slot(
    state: FractalConstraintState,
    seq: list[int],
    step: int,
    tokenizer: Any,
    trie: FractalPhraseTrie,
    natural_next_id: Optional[int] = None,
) -> tuple[bool, bool]:
    """Slot-fire decision. Returns ``(fire, hard_forced)``.

    Fire conditions, in priority order:
    1. If pos == 0 AND no tokens generated yet (step 0), fire SOFT (the
       very first natural argmax decides whether to commit a phrase).
    2. If natural_next_id is in the allowed first-token set for K[pos],
       fire SOFT (the model is already trying to start a phrase there).
    3. If the decoded tail indicates a clause boundary, fire SOFT.
    4. If tokens_since_last_commit >= MAX_TOKENS_BETWEEN_SLOTS, fire
       HARD (force entry to constrain output to K slots even if the
       model isn't naturally near a boundary).
    """
    if state.pos >= len(state.expected_k):
        return False, False
    target_k = state.expected_k[state.pos]
    allowed_first = trie.first_token_ids_for(target_k)
    if not allowed_first:
        # Trie missing entries for this k — no phrases available, can't fire.
        return False, False

    # Soft trigger 1: pos==0 at step 0 (just-after-BOS) — fire so the
    # very first natural argmax decides whether to enter constraint.
    if state.pos == 0 and step == 0:
        return True, False

    # Soft trigger 2: model's natural next-token is in the allowed set.
    if natural_next_id is not None and natural_next_id in allowed_first:
        return True, False

    # Soft trigger 3: decoded tail ends at a clause boundary.
    tail = _decode_tail_text(tokenizer, seq)
    if _tail_indicates_boundary(tail):
        return True, False

    # Hard force: too many tokens since last commit, slot must land.
    if state.tokens_since_last_commit >= MAX_TOKENS_BETWEEN_SLOTS:
        return True, True

    return False, False


def make_logits_processor(
    state: FractalConstraintState,
    trie: FractalPhraseTrie,
    tokenizer: Any,
    *,
    eos_id: Optional[int] = None,
    eos_bias: float = 0.0,
) -> Callable[[list[int], int, torch.Tensor], torch.Tensor]:
    """Return a callable suitable for ``generate_reply(step_callback=…)``.

    The callable inspects ``seq[-1]`` to advance the trie walk for any
    just-committed token (if currently in trie mode), then optionally
    masks ``logits`` to constrain the next token if entering or continuing
    a trie walk.

    Args:
        state: per-call mutable state, see ``FractalConstraintState``.
        trie: tokenized phrase trie, see ``FractalPhraseTrie``.
        tokenizer: the same tokenizer used to build ``trie``.
        eos_id: token id of the EOS special, optional. When provided
            along with a positive ``eos_bias``, the processor adds
            ``eos_bias`` to the EOS logit AFTER all expected slots are
            committed (``state.pos >= len(state.expected_k)``). This
            suppresses trailing prose past the final slot, which
            otherwise contaminates the fractal verifier's
            ``found_k_count`` by picking up extra Noetic indicators
            from the post-slot prose. v1e Phase 1B tuning lever 1.
        eos_bias: log-prob bias added to ``eos_id``'s logit when active.
            Default 0.0 (no bias). Larger values force EOS sooner.

    Side effects: mutates ``state.pos``, ``state.mode``,
    ``state.current_node``, ``state.slot_commits``, and
    ``state.failure_reason`` over the lifetime of a single
    ``generate_reply`` call.
    """

    def processor(seq: list[int], step: int, logits: torch.Tensor) -> torch.Tensor:
        # ----- 1. Process the token that was JUST sampled at step-1 -----
        # ``seq`` includes BOS plus all committed tokens. When step > 0,
        # seq[-1] is the most recently sampled non-BOS token.
        if state.mode == "trie" and state.current_node is not None and step > 0:
            last_tok = seq[-1]
            child = state.current_node.children.get(last_tok)
            if child is not None:
                state.current_node = child
                if child.is_leaf:
                    # Phrase commit. Append slot event, exit trie mode.
                    state.slot_commits.append(SlotCommitEvent(
                        pos=state.pos,
                        k_value=state.expected_k[state.pos],
                        phrase_chosen=child.phrase_text or "",
                        start_step=state.current_phrase_start_step,
                        end_step=step,
                        hard_forced=False,  # populated separately if needed
                    ))
                    state.pos += 1
                    state.mode = "prose"
                    state.current_node = None
                    state.tokens_since_last_commit = 0
            else:
                # Defensive: the mask should have prevented this. If it
                # happens (e.g., upstream sampler picked a token not in
                # the allowed set), abort the trie walk.
                state.failure_reason = (
                    f"trie_unexpected_token: pos={state.pos} "
                    f"k={state.expected_k[state.pos]} "
                    f"last_tok={last_tok}"
                )
                state.mode = "prose"
                state.current_node = None

        if state.mode == "prose" and step > 0:
            state.tokens_since_last_commit += 1

        # ----- 2. Decide whether to constrain the NEXT prediction ------
        if state.pos >= len(state.expected_k):
            # All slots committed — free decode for the trailing prose.
            # Optionally bias toward EOS to suppress trailing prose that
            # would otherwise contaminate the verifier's noetic count.
            if (
                eos_id is not None
                and eos_bias > 0.0
                and 0 <= eos_id < logits.shape[0]
            ):
                biased = logits.clone()
                biased[eos_id] = biased[eos_id] + float(eos_bias)
                return biased
            return logits

        if state.mode == "prose":
            # Compute natural argmax for soft-trigger comparison.
            natural_id = int(torch.argmax(logits).item())
            fire, hard_forced = _should_fire_slot(
                state=state,
                seq=seq,
                step=step,
                tokenizer=tokenizer,
                trie=trie,
                natural_next_id=natural_id,
            )
            if fire:
                target_k = state.expected_k[state.pos]
                state.mode = "trie"
                state.current_node = trie.roots.get(target_k)
                state.current_phrase_start_step = step
                # Mark hard-forced on the slot event later via a small
                # in-flight tag (set when we land the leaf).
                state._pending_hard_forced = hard_forced  # type: ignore[attr-defined]

        if state.mode == "trie" and state.current_node is not None:
            allowed = set(state.current_node.children.keys())
            if not allowed:
                # current_node is a leaf with no further children but
                # we somehow re-entered. Defensive: exit trie mode and
                # log a failure reason. Should not happen because leaves
                # exit trie mode in step 1 above.
                state.failure_reason = (
                    f"trie_no_children: pos={state.pos} step={step}"
                )
                state.mode = "prose"
                state.current_node = None
                return logits
            masked = logits.clone()
            # Build a boolean mask of disallowed token ids and set them
            # to -inf in one tensor op for speed.
            vocab_size = masked.shape[0]
            allow_mask = torch.zeros(vocab_size, dtype=torch.bool, device=logits.device)
            for tok in allowed:
                if 0 <= tok < vocab_size:
                    allow_mask[tok] = True
            masked = torch.where(
                allow_mask,
                masked,
                torch.full_like(masked, float("-inf")),
            )
            return masked

        return logits

    return processor


# ---------------------------------------------------------------------------
# Fail-closed comparison helpers
# ---------------------------------------------------------------------------

def _verifier_score(verifier_log: FractalRepairLog) -> tuple[bool, bool, int]:
    """Score a fractal verifier log for fail-closed comparison.

    Returns ``(sequence_matches, cardinality_matches, mismatch_count)``.
    Higher tuple comparisons are NOT defined — the caller chooses the
    field-by-field comparison rule (see ``constrained_strictly_beats``).
    """
    return (
        verifier_log.sequence_matches,
        verifier_log.cardinality_matches,
        len(verifier_log.mismatch_positions),
    )


# Cheap prose-quality heuristic: 1.0 = clean prose, lower = visible
# stiltedness / repetition / truncation. Used as the second axis of the
# fail-closed comparator.
_REPEATED_PHRASE_RX = re.compile(r"\b(\w+(?:\s+\w+){0,3})\b(?:\s+\1\b){1,}", re.IGNORECASE)
_MIN_PROSE_LEN = 20  # generated outputs shorter than this are likely truncated


def _prose_quality_score(text: str, *, stopped_on_eos: bool) -> float:
    """Heuristic prose-quality score in ``[0, 1]``.

    Penalizes:
      - very short outputs (< MIN_PROSE_LEN chars) — truncation signal
      - repeated consecutive phrases (the Record 13 ``^9`` loop pattern)
      - sequences that didn't end on EOS (truncation flag)
    """
    if not text:
        return 0.0
    score = 1.0
    if len(text) < _MIN_PROSE_LEN:
        score -= 0.4
    if not stopped_on_eos:
        score -= 0.2
    # Repeated phrase detection — the v1d Record 13 failure mode emits
    # ``popped into mind`` 6 times in a row. The regex catches any 1-4-word
    # phrase repeating consecutively at least once.
    if _REPEATED_PHRASE_RX.search(text):
        score -= 0.3
    return max(0.0, score)


def constrained_strictly_beats_baseline(
    *,
    constrained_text: str,
    constrained_stopped_on_eos: bool,
    constrained_verifier: FractalRepairLog,
    baseline_text: str,
    baseline_stopped_on_eos: bool,
    baseline_verifier: FractalRepairLog,
    constraint_failure_reason: Optional[str] = None,
    first_n_mode: bool = False,
) -> tuple[bool, str]:
    """Fail-closed comparator.

    Constrained is selected ONLY if BOTH:
      (a) constrained verifier strictly improves on baseline verifier
          (sequence_matches True when baseline was False, OR fewer
          mismatch_positions when cardinality matches in both)
      (b) constrained prose-quality is within 0.2 of baseline
          (i.e., we don't accept structural improvements that come at
          a heavy prose-quality cost)
      (c) the constraint did not hit a failure_reason mid-decode.

    Args:
        first_n_mode: v1e Phase 1B tuning lever 2. When True, the
            comparator scores BOTH baseline and constrained on only the
            FIRST ``n`` extracted noetics (where ``n`` is the expected
            k-count). This suppresses contamination from trailing
            post-slot prose that pushes ``found_k_count`` above
            expected — a known failure mode where the model commits all
            slots correctly in order but then keeps emitting prose
            containing extra Noetic indicators. Default False (compare
            against full extracted sequence).

    Returns ``(better, reason)``. ``better=False`` means return
    baseline; the reason is logged in the FractalDecoderLog.
    """
    if constraint_failure_reason:
        return False, f"constrained run hit failure: {constraint_failure_reason}"

    if first_n_mode:
        n_expected = constrained_verifier.expected_k_count
        c_cardinality, c_sequence, c_mismatches = _compare_sequences(
            list(constrained_verifier.expected_k_values),
            list(constrained_verifier.found_k_sequence)[:n_expected],
        )
        b_cardinality, b_sequence, b_mismatches = _compare_sequences(
            list(baseline_verifier.expected_k_values),
            list(baseline_verifier.found_k_sequence)[:n_expected],
        )
        cs = (c_sequence, c_cardinality, len(c_mismatches))
        bs = (b_sequence, b_cardinality, len(b_mismatches))
    else:
        cs = _verifier_score(constrained_verifier)
        bs = _verifier_score(baseline_verifier)

    # First check: structural strict improvement.
    structural_better = False
    if cs[0] and not bs[0]:
        structural_better = True
        reason_seg = "sequence_matches: False -> True"
    elif cs[1] and bs[1]:
        # Both cardinality match — compare mismatch counts.
        if cs[2] < bs[2]:
            structural_better = True
            reason_seg = f"mismatch_positions: {bs[2]} -> {cs[2]}"
        elif cs[2] > bs[2]:
            return False, (
                f"constrained had MORE structural mismatches "
                f"({bs[2]} -> {cs[2]})"
            )
        else:
            return False, (
                "constrained matched baseline structurally; "
                "no improvement to justify replacement"
            )
    elif not bs[1] and cs[1]:
        # Constrained gained cardinality match.
        structural_better = True
        reason_seg = "cardinality_matches: False -> True"
    elif bs[1] and not cs[1]:
        return False, (
            "constrained LOST cardinality match; falling back to baseline"
        )
    else:
        return False, (
            "neither baseline nor constrained achieved cardinality "
            "match; falling back to baseline"
        )

    if not structural_better:
        return False, "no structural improvement"

    # Second check: prose-quality not too much worse.
    pq_c = _prose_quality_score(
        constrained_text, stopped_on_eos=constrained_stopped_on_eos,
    )
    pq_b = _prose_quality_score(
        baseline_text, stopped_on_eos=baseline_stopped_on_eos,
    )
    if pq_c < pq_b - 0.2:
        return False, (
            f"constrained had {pq_b - pq_c:.2f} lower prose quality "
            f"(baseline={pq_b:.2f}, constrained={pq_c:.2f}); "
            f"structural gain not enough to justify"
        )

    return True, (
        f"constrained strictly better — {reason_seg}; "
        f"prose_quality baseline={pq_b:.2f} constrained={pq_c:.2f}"
    )


__all__ = [
    "FractalConstraintState",
    "FractalDecoderLog",
    "FractalPhraseTrie",
    "MAX_TOKENS_BETWEEN_SLOTS",
    "SlotCommitEvent",
    "TrieNode",
    "build_fractal_phrase_trie",
    "constrained_strictly_beats_baseline",
    "make_logits_processor",
]
