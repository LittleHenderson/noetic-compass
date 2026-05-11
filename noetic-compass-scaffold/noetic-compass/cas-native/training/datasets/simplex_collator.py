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

from typing import Any, Optional, Sequence

import torch

from .native_nl_collator import NativeNLCollator


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

        # Hydrate the simplex-MVP keys. We work off batch shapes so the new
        # tensors match the existing batch device / batch order.
        device = batch["input_ids"].device if hasattr(batch.get("input_ids"), "device") else device
        cas_prefix = batch.get("cas_prefix_ids")
        if cas_prefix is None:
            return batch
        B, L_src_max = cas_prefix.shape
        lm_targets = batch.get("lm_targets")
        if lm_targets is None:
            return batch
        L_out = lm_targets.shape[1]

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

    def _derive_anchors(self, record: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Derive anchors for one record. Returns None if no anchors found.

        Stage 1 implementation is intentionally minimal: it produces shape-
        correct anchor structures from the record's ``cas_expression`` text
        using simple regex-style heuristics. The full Option-γ derivation
        (calling ``parse_fractal`` / ``parse_meta_logic`` /
        ``extract_noetic_sequence_with_positions`` from existing parsers)
        lands in Stage 2-3 as the unit tests force correctness.
        """
        cas_expr = record.get("cas_expression") or ""
        if not cas_expr:
            return None

        src_anchors: list[tuple[int, int]] = []
        src_token_types: list[tuple[int, int]] = []
        target_slots: list[tuple[int, int, Optional[int]]] = []

        # Very-lightweight Stage 1 placeholder: tag the first source token
        # with OMEGA type (for shape testing) and place a single anchor at
        # state index 0 (^0 / Idea in P-domain). Real parser dispatch lands
        # in Stage 2 when unit tests force it.
        src_token_types.append((0, SLOT_OMEGA))
        src_anchors.append((0, 0))

        return {
            "src_len": 1,
            "strategy": PARSER_HYBRID,
            "src_anchors": src_anchors,
            "src_token_types": src_token_types,
            "target_slots": target_slots,
        }
