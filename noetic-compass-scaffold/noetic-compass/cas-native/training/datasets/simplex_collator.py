"""SimplexCollator — subclass of NativeNLCollator adding 7 simplex-MVP batch keys.

Per build-spec §4: extends the existing native_nl collator with the auxiliary
tensors needed for the simplex MVP — Fisher-Rao target trajectory + anchor
mask, source-side type tags, and target-side slot-type / pointer-source labels.

Backward compatibility contract: with ``enable_simplex_aux=False`` the
returned batch is byte-identical to what ``NativeNLCollator`` would have
produced. With ``enable_simplex_aux=True`` the batch additionally includes:

    fr_target_path:        (B, L_src_max, 40)   target simplex points
    fr_target_mask:        (B, L_src_max)       bool, True at anchors
    fr_target_len:         (B,)                 per-record valid trajectory length
    typed_slot_positions:  (B, L_out, 9)        one-hot OR class id per output position
    typed_slot_source:     (B, L_out)           int16 source-position index at typed slots; -1 elsewhere
    src_token_type:        (B, L_src_max)       int8 source-side type tags (9 classes)
    parser_strategy:       (B,)                 int diagnostic (which derivation branch fired)

Auxiliary derivation reuses existing parsers (``parse_fractal``,
``parse_meta_logic``, ``extract_noetic_sequence_with_positions``); no new SDG
and no new parsers are introduced. Records that fail derivation get
``fr_target_mask`` all-zero — the FR loss naturally drops them.

Stage 1 status: skeleton with all 7 new keys present and shape-correct.
Anchor placement (Option γ) is wired but uses minimal heuristics; the real
parser dispatch lands in Stage 2-3 alongside the unit-test corpus.
"""
from __future__ import annotations

import re
from typing import Any, Optional, Sequence

import torch

from .native_nl_collator import NativeNLCollator


# Token-string classifiers for the four single-token-mappable typed slot
# types. Wired in Stage 6 v5 (2026-05-11). STAGE_VAR / COEFFICIENT /
# FRACTAL_K_LITERAL remain deferred (multi-token or context-aware).
DOMAIN_LETTER_RE = re.compile(r"^\^[PCEO]$")
DRIVE_LETTER_RE = re.compile(r"^F_?[1-7]$")
REGISTER_LETTER_RE = re.compile(r"^\|[TAfE]$")
OMEGA_RE = re.compile(r"^(Ω(_\w+)?|Omega(_\w+)?)$")


def classify_source_token(token_string: str) -> int:
    """Map a single decoded source token string to a typed-slot id.

    Returns:
        SLOT_DOMAIN_LETTER / SLOT_DRIVE_LETTER / SLOT_REGISTER_LETTER /
        SLOT_OMEGA when the string is one of the recognised single-token
        identifiers. SLOT_CONNECTIVE otherwise (CONNECTIVE is the default
        for un-classified tokens — including raw letters, digits, and
        grammar punctuation).
    """
    if token_string is None:
        return SLOT_CONNECTIVE
    if DOMAIN_LETTER_RE.match(token_string):
        return SLOT_DOMAIN_LETTER
    if DRIVE_LETTER_RE.match(token_string):
        return SLOT_DRIVE_LETTER
    if REGISTER_LETTER_RE.match(token_string):
        return SLOT_REGISTER_LETTER
    if OMEGA_RE.match(token_string):
        return SLOT_OMEGA
    return SLOT_CONNECTIVE


# ---------------------------------------------------------------------------
# Multi-token-span detection (Stage 6 v7, 2026-05-11)
# ---------------------------------------------------------------------------
# Per user 2026-05-11: STAGE_VAR and OMEGA-suffix derivations land here as
# strict multi-token-span matching. No fuzzy alignment — when source and
# target tokenize the identifier compatibly, the copy fires; otherwise it
# stays NOT MEASURED. Domain/drive/register single-token classifiers
# remain (above) because they fire on synthetic copy-bearing fixtures
# (v5), even though they don't fire on paraphrased v1c replies (v6).

_OMEGA_CHAR_TOKEN = "<CHAR:03A9>"     # Greek capital Omega
_UNDERSCORE_CHAR_TOKEN = "<CHAR:005F>"  # '_'


def _is_identifier_continuation(token_string: str) -> bool:
    """Return True if the token is an identifier-continuation token —
    a single alphanumeric/underscore char OR a multi-char alphanumeric
    word. Excludes special tokens ([SP], [BOS], …) and grammar punctuation.

    Used by multi-token-span detection for STAGE_VAR / OMEGA-suffix.
    """
    if not token_string:
        return False
    if token_string.startswith("[") and token_string.endswith("]"):
        return False  # [SP], [BOS], [EOS], [PAD], [UNK], [NL], [TAB], etc.
    if token_string.startswith("<CHAR:") and token_string.endswith(">"):
        try:
            ch = chr(int(token_string[6:-1], 16))
            return ch.isalnum() or ch == "_"
        except ValueError:
            return False
    return all((c.isalnum() or c == "_") for c in token_string)


def find_stage_var_spans(token_strings: list[str]) -> list[tuple[int, int]]:
    """Detect contiguous STAGE_VAR multi-token spans on the source side.

    Pattern: a ``stage`` token followed by one-or-more identifier-
    continuation tokens (alphanumeric or underscore chars, or short
    identifier words). The span terminates at the first non-identifier
    token (whitespace, ``=``, ``;``, etc.).

    Returns list of ``(start, end_exclusive)`` tuples in token-position
    space — same indexing as the source ``cas_prefix_ids`` tensor.
    """
    spans: list[tuple[int, int]] = []
    i = 0
    n = len(token_strings)
    while i < n:
        if token_strings[i] == "stage":
            j = i + 1
            while j < n and _is_identifier_continuation(token_strings[j]):
                j += 1
            if j > i + 1:  # at least one continuation token after "stage"
                spans.append((i, j))
            i = j
        else:
            i += 1
    return spans


def find_omega_suffix_spans(token_strings: list[str]) -> list[tuple[int, int, int]]:
    """Detect char-decomposed Ω-suffix spans on the source side.

    Pattern: ``<CHAR:03A9>`` (Ω) followed by ``<CHAR:005F>`` (_) followed
    by one-or-more identifier-continuation tokens. Fires only on the
    char-decomposed form — novel Ω-names NOT in ``CAS_RESERVED_TOKENS``.
    Reserved Ω-names (``Ω_resolve`` etc.) tokenize as a single token and
    are handled by the single-token classifier above.

    Returns list of ``(omega_start, suffix_start, suffix_end_exclusive)``:
    - ``omega_start`` is the Ω token position
    - ``suffix_start = omega_start + 2`` (skip Ω + _)
    - The full source span tagged as OMEGA is ``[omega_start, suffix_end)``
    - The target-side match looks for ``token_ids[suffix_start:suffix_end]``
    """
    spans: list[tuple[int, int, int]] = []
    i = 0
    n = len(token_strings)
    while i < n - 1:
        if (
            token_strings[i] == _OMEGA_CHAR_TOKEN
            and token_strings[i + 1] == _UNDERSCORE_CHAR_TOKEN
        ):
            suffix_start = i + 2
            j = suffix_start
            while j < n and _is_identifier_continuation(token_strings[j]):
                j += 1
            if j > suffix_start:
                spans.append((i, suffix_start, j))
            i = j
        else:
            i += 1
    return spans


def find_subsequence(haystack: list[int], needle: list[int]) -> Optional[int]:
    """Return the first index where ``haystack`` contains ``needle`` as a
    contiguous subsequence, or None if not found. Strict equality, no
    fuzzy matching.
    """
    if not needle:
        return None
    n_len = len(needle)
    last = len(haystack) - n_len
    for start in range(last + 1):
        if haystack[start:start + n_len] == needle:
            return start
    return None


def find_all_subsequences(haystack: list[int], needle: list[int]) -> list[int]:
    """Return ALL non-overlapping start indices where ``haystack`` contains
    ``needle`` as a contiguous subsequence. Non-overlapping: after a match
    at position i, the next search resumes at i + len(needle).

    Added 2026-05-12 per Candidate E pre-Stage-1 audit. The original
    ``find_subsequence`` (first-match only) caused repeat target identifier
    occurrences to go unlabelled — combined with the source-cap truncation
    bug, this meant only the first 2 of 4 unique rpm-chain identifiers per
    record received STAGE_VAR copy supervision. Both bugs together produced
    the universal "2 spans per record" pattern.
    """
    if not needle:
        return []
    n_len = len(needle)
    matches: list[int] = []
    i = 0
    end = len(haystack) - n_len
    while i <= end:
        if haystack[i:i + n_len] == needle:
            matches.append(i)
            i += n_len
        else:
            i += 1
    return matches


# Build-spec §2.3 slot ids — must match TypedFiberDecoder.SLOT_TYPE_TO_ID
SLOT_CONNECTIVE: int = 0
SLOT_OMEGA: int = 1
SLOT_STAGE_VAR: int = 2
SLOT_COEFFICIENT: int = 3
SLOT_REGISTER_LETTER: int = 4
SLOT_DOMAIN_LETTER: int = 5
SLOT_DRIVE_LETTER: int = 6
SLOT_FRACTAL_K_LITERAL: int = 7
SLOT_NOETIC_PHRASE: int = 8
NUM_SLOT_TYPES: int = 9

# Anchor placement defaults (Option γ — hybrid). The build spec allows the
# anchor to be a near-one-hot on (noetic × domain) index, with ε-floor.
ANCHOR_PEAK: float = 0.9
ANCHOR_EPS: float = (1.0 - ANCHOR_PEAK) / 39.0  # spread remainder across other 39 dims
NUM_STATES: int = 40

# Parser strategy diagnostic codes
PARSER_NONE: int = 0       # no anchors derived
PARSER_FRACTAL: int = 1
PARSER_META_LOGIC: int = 2
PARSER_NOETIC_SEQ: int = 3
PARSER_HYBRID: int = 4


class SimplexCollator(NativeNLCollator):
    """Adds 7 simplex-MVP batch keys; preserves the 9 existing keys verbatim."""

    def __init__(
        self,
        tokenizer: Any,
        *,
        enable_simplex_aux: bool = False,
        anchor_peak: float = ANCHOR_PEAK,
        anchor_eps: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(tokenizer, **kwargs)
        self.enable_simplex_aux = bool(enable_simplex_aux)
        if not (0.0 < anchor_peak < 1.0):
            raise ValueError(f"anchor_peak must be in (0, 1); got {anchor_peak}")
        self.anchor_peak = float(anchor_peak)
        if anchor_eps is None:
            anchor_eps = (1.0 - self.anchor_peak) / (NUM_STATES - 1)
        if anchor_eps <= 0.0:
            raise ValueError(f"anchor_eps must be positive; got {anchor_eps}")
        self.anchor_eps = float(anchor_eps)

    def __call__(
        self,
        records: Sequence[dict[str, Any]],
        *,
        device: torch.device | str = "cpu",
    ) -> dict[str, Any] | None:
        batch = super().__call__(records, device=device)
        if batch is None or not self.enable_simplex_aux:
            return batch

        # Hydrate the simplex-MVP keys. We always emit the 7 aux keys when
        # enable_simplex_aux=True — even on malformed/empty records — so the
        # trainer's forward + loss assembly never trips on a missing key.
        # User-named "malformed source gives zero/empty aux labels without
        # crashing" applies here.
        device = batch["input_ids"].device if hasattr(batch.get("input_ids"), "device") else device
        cas_prefix = batch.get("cas_prefix_ids")
        lm_targets = batch.get("lm_targets")
        B = batch["input_ids"].shape[0] if isinstance(batch.get("input_ids"), torch.Tensor) else 0
        L_src_max = cas_prefix.shape[1] if isinstance(cas_prefix, torch.Tensor) and cas_prefix.dim() == 2 else 0
        L_out = lm_targets.shape[1] if isinstance(lm_targets, torch.Tensor) and lm_targets.dim() == 2 else 0

        fr_target_path = torch.full(
            (B, L_src_max, NUM_STATES),
            fill_value=1.0 / NUM_STATES,
            dtype=torch.float32,
            device=device,
        )
        fr_target_mask = torch.zeros((B, L_src_max), dtype=torch.bool, device=device)
        fr_target_len = torch.zeros((B,), dtype=torch.int32, device=device)
        typed_slot_positions = torch.zeros(
            (B, L_out, NUM_SLOT_TYPES), dtype=torch.float32, device=device
        )
        typed_slot_source = torch.full(
            (B, L_out), fill_value=-1, dtype=torch.int16, device=device
        )
        src_token_type = torch.zeros((B, L_src_max), dtype=torch.int8, device=device)
        parser_strategy = torch.zeros((B,), dtype=torch.int32, device=device)

        for b, rec in enumerate(records[:B]):
            anchors = self._derive_anchors(rec)
            if not anchors:
                # Default everything to CONNECTIVE / no anchors; the FR loss
                # contributes zero for this record.
                typed_slot_positions[b, :, SLOT_CONNECTIVE] = 1.0
                continue

            fr_target_len[b] = int(anchors["src_len"])
            parser_strategy[b] = int(anchors["strategy"])

            # Place anchor points
            for src_pos, state_idx in anchors["src_anchors"]:
                if 0 <= src_pos < L_src_max and 0 <= state_idx < NUM_STATES:
                    fr_target_mask[b, src_pos] = True
                    point = torch.full(
                        (NUM_STATES,), self.anchor_eps, dtype=torch.float32, device=device,
                    )
                    point[state_idx] = self.anchor_peak
                    fr_target_path[b, src_pos] = point

            # Source-side type tags
            for src_pos, type_id in anchors["src_token_types"]:
                if 0 <= src_pos < L_src_max:
                    src_token_type[b, src_pos] = int(type_id)

            # Target-side slot-type positions
            for out_pos, slot_id, source_idx in anchors["target_slots"]:
                if 0 <= out_pos < L_out and 0 <= slot_id < NUM_SLOT_TYPES:
                    typed_slot_positions[b, out_pos, :] = 0.0
                    typed_slot_positions[b, out_pos, slot_id] = 1.0
                    if source_idx is not None and 0 <= source_idx < L_src_max:
                        typed_slot_source[b, out_pos] = int(source_idx)

            # Backfill remaining (un-tagged) output positions with CONNECTIVE
            untagged = typed_slot_positions[b].sum(dim=-1) == 0
            typed_slot_positions[b, untagged, SLOT_CONNECTIVE] = 1.0

        batch["fr_target_path"] = fr_target_path
        batch["fr_target_mask"] = fr_target_mask
        batch["fr_target_len"] = fr_target_len
        batch["typed_slot_positions"] = typed_slot_positions
        batch["typed_slot_source"] = typed_slot_source
        batch["src_token_type"] = src_token_type
        batch["parser_strategy"] = parser_strategy
        return batch

    # -- anchor derivation (Option γ, hybrid) --------------------------------

    # Slot → simplex state index mapping. Used to place FR anchor at the
    # source position where the typed slot lives. DOMAIN_LETTER P/C/E/O →
    # state 0/10/20/30 (^0 in each domain — neutral Idea anchor). OMEGA
    # also anchors at state 0. REGISTER/DRIVE letters anchor at state 0
    # because they don't carry a domain — the FR anchor here is a coarse
    # "this source position is typed-significant" signal, not a fine-
    # grained semantic anchor. The full Option γ derivation lands later.
    _DOMAIN_STATE = {"^P": 0, "^C": 10, "^E": 20, "^O": 30}

    def _derive_anchors(self, record: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Derive anchors for one record. Returns None if no anchors found.

        Stage 6 v5 (2026-05-11): LIVE typed_slot_source derivation for the
        four single-token-mappable slot types — DOMAIN_LETTER,
        DRIVE_LETTER, REGISTER_LETTER, OMEGA. Re-tokenises the record's
        cas_expression and reply_text using ``self.tokenizer`` (the same
        tokenizer the base collator uses) so source/target token ids line
        up exactly with the cas_prefix_ids and lm_targets tensors. Then:

        1. Classifies every source token via ``classify_source_token`` on
           its decoded string (token_ids_to_tokens).
        2. For each target token, scans source positions for an id-match
           where ``src_token_type`` is a typed slot (1..7). First match
           wins — emits (out_pos, slot_id, source_idx).
        3. Emits one FR anchor per typed source token, mapping
           DOMAIN_LETTER P/C/E/O to states 0/10/20/30 (^0 anchor in each
           domain) and OMEGA/REGISTER/DRIVE to state 0.

        STAGE_VAR, COEFFICIENT, FRACTAL_K_LITERAL classifications are
        deferred (multi-token / context-aware derivation; future stage).
        """
        cas_expr = record.get("cas_expression") or ""
        reply_text = record.get("reply_text") or record.get("reply") or ""
        if not cas_expr:
            return None

        # Re-tokenise to match the base collator's encoded ids exactly.
        c_ids = self._encode_capped(cas_expr, self.max_cas_prefix_len)
        if not c_ids:
            return None
        r_ids = self._encode_capped(reply_text, self.max_reply_len) if reply_text else []

        # Decode source token strings for classification
        tk = self.tokenizer
        if not hasattr(tk, "token_ids_to_tokens"):
            # Fallback: tokenizer doesn't expose token-name decoding;
            # we can't classify. Return empty derivation rather than crash.
            return {
                "src_len": len(c_ids),
                "strategy": PARSER_NONE,
                "src_anchors": [],
                "src_token_types": [],
                "target_slots": [],
            }
        src_token_strings = tk.token_ids_to_tokens(c_ids)
        src_type_by_pos: list[int] = [
            classify_source_token(s) for s in src_token_strings
        ]

        # Anchors + src_token_types
        src_anchors: list[tuple[int, int]] = []
        src_token_types: list[tuple[int, int]] = []
        for k, slot_id in enumerate(src_type_by_pos):
            if slot_id == SLOT_CONNECTIVE:
                continue
            src_token_types.append((k, slot_id))
            tok_string = src_token_strings[k]
            state_idx = self._DOMAIN_STATE.get(tok_string, 0)
            src_anchors.append((k, state_idx))

        # Target → source copy: for each target token, find first source
        # position with the same token id AND non-CONNECTIVE classification.
        # Note: decoder output position j predicts reply_ids[j] (per base
        # collator: lm_targets[i, j] = reply_ids[i][j] for j < n, EOS at n).
        target_slots: list[tuple[int, int, Optional[int]]] = []
        if r_ids:
            for j, target_id in enumerate(r_ids):
                # Find first source position whose id == target_id and
                # whose source-side type is a copy-bearing slot.
                src_pos: Optional[int] = None
                for k, src_id in enumerate(c_ids):
                    if (
                        int(src_id) == int(target_id)
                        and src_type_by_pos[k] != SLOT_CONNECTIVE
                    ):
                        src_pos = k
                        break
                if src_pos is not None:
                    target_slots.append((j, src_type_by_pos[src_pos], src_pos))

        # ----- Stage 6 v7 → Path D (2026-05-11) — STAGE_VAR copy only -----
        # User 2026-05-11: OMEGA suffix copy dropped from MVP because v1c
        # tokenizer is path-dependent (source 'Ω_X' char-decomposes while
        # target 'X' BPE-merges; exact subseq match fails). Multi-target-to-
        # one-source mapping would weaken pointer-copy semantics right
        # before Stage 7. OMEGA becomes a v1.1 copy-fiber task. The
        # find_omega_suffix_spans helper is kept in the module for future
        # use but not wired into _derive_anchors.
        #
        # STAGE_VAR span match is the only multi-token-span derivation in
        # the Path D MVP. It hits exactly the failure mode that v1e Phase
        # C broke (rpm_chain stage identifier preservation) and aligns
        # cleanly on the v1c tokenizer (verified in Stage 6 v7: 56 valid
        # copy slots on 3 rpm_chain records).
        stage_spans = find_stage_var_spans(src_token_strings)
        for (s_start, s_end) in stage_spans:
            # Tag source positions with STAGE_VAR
            for k in range(s_start, s_end):
                src_token_types.append((k, SLOT_STAGE_VAR))
            # Place an FR anchor at the span start (state 0 — neutral)
            src_anchors.append((s_start, 0))
            # Find ALL matching target subsequences (every occurrence of
            # this identifier in the reply gets per-position copy
            # supervision). Per Candidate E pre-Stage-1 audit 2026-05-12:
            # was find_subsequence first-match only, which left repeat
            # occurrences and any post-first-match identifiers unlabelled
            # (root cause of the "2 spans per record" universal pattern).
            if r_ids:
                src_subseq = c_ids[s_start:s_end]
                for t_start in find_all_subsequences(r_ids, src_subseq):
                    for offset in range(s_end - s_start):
                        target_slots.append(
                            (t_start + offset, SLOT_STAGE_VAR, s_start + offset)
                        )

        if not src_anchors and not target_slots:
            return None

        strategy = PARSER_HYBRID if (src_anchors and target_slots) else (
            PARSER_NOETIC_SEQ if src_anchors else PARSER_NONE
        )
        return {
            "src_len": len(c_ids),
            "strategy": strategy,
            "src_anchors": src_anchors,
            "src_token_types": src_token_types,
            "target_slots": target_slots,
        }
