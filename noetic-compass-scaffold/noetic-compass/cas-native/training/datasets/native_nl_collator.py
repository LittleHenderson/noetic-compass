"""NativeNLCollator — bridge from Tier 3 dialogue records to forward_with_lm batches.

Takes a list of records of the shape produced by Codex's Tier 3 dialogue SDG
generator (``schema_version: native_nl.v1``) and produces a dict matching the
keyword-argument contract of ``CASNativeModel.forward_with_lm()``. The trainer
calls ``forward_with_lm`` with the kwargs this collator emits; loss is computed
from ``out["lm_logits"]`` and the ``lm_targets`` / ``loss_mask`` fields the
collator preserves alongside the forward kwargs.

One tokenizer object handles both prompt/reply text and the CAS expression:
``ExtendedHybridCASTokenizer`` (CAS reserved tokens at low IDs, English BPE
merges above). The base ``HybridCASTokenizer`` is also supported for callers
that have not yet trained an English BPE artifact. Both expose
``encode(text, max_length, *, add_special)``; with ``add_special=False`` no
BOS/EOS is added — the collator manages decoder shift explicitly.

Object provenance: every output batch carries the source records'
``id`` and ``trace_id`` lists in order, so downstream trace dumps can walk
each generated token back to its source record.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

import torch


DEFAULT_REGISTER_TO_ID: dict[str, int] = {"T": 0, "A": 1, "f": 2, "E": 3}

# v1e Phase C — aux label derivation defaults. K_max and C_max must match
# the AuxHeadsConfig the trainer attaches; if they diverge the loss
# computation will silently mask wrong positions.
DEFAULT_AUX_K_MAX: int = 16
DEFAULT_AUX_C_MAX: int = 6
NUM_NOETICS: int = 10
LABEL_IGNORE_INDEX: int = -100


class NativeNLCollator:
    """Convert dialogue records into ``forward_with_lm``-shaped batches.

    Args:
        tokenizer: a ``HybridCASTokenizer`` or ``ExtendedHybridCASTokenizer``.
            Must expose ``BOS_ID``, ``EOS_ID``, ``PAD_ID``, and an
            ``encode(text, max_length, *, add_special=False)`` method.
        max_prompt_len: cap for prompt token length (encoder side).
        max_reply_len: cap for reply token length, before BOS/EOS.
        max_cas_prefix_len: cap for the CAS expression token sequence.
        register_to_id: mapping from register character (``T/A/f/E``) to int
            in ``[0, NUM_REGISTERS)``. Default matches ``register_film.py``.
        ignore_index: target value for padded loss positions (default -100,
            matches ``F.cross_entropy`` ignore_index convention).
    """

    def __init__(
        self,
        tokenizer: Any,
        *,
        max_prompt_len: int = 256,
        max_reply_len: int = 256,
        max_cas_prefix_len: int = 32,
        register_to_id: dict[str, int] | None = None,
        ignore_index: int = -100,
        prepend_task_token: bool = False,
        task_token_id_for: Any = None,
        enable_aux_labels: bool = False,
        aux_k_max: int = DEFAULT_AUX_K_MAX,
        aux_c_max: int = DEFAULT_AUX_C_MAX,
    ) -> None:
        if not hasattr(tokenizer, "encode"):
            raise TypeError(
                "tokenizer must expose .encode(text, max_length, *, "
                f"add_special); got {type(tokenizer).__name__}"
            )
        for attr in ("BOS_ID", "EOS_ID", "PAD_ID"):
            if not hasattr(tokenizer, attr):
                raise TypeError(
                    f"tokenizer is missing required attribute {attr!r}; "
                    f"got {type(tokenizer).__name__}"
                )
        if int(max_prompt_len) <= 0:
            raise ValueError(f"max_prompt_len must be positive; got {max_prompt_len}")
        if int(max_reply_len) <= 0:
            raise ValueError(f"max_reply_len must be positive; got {max_reply_len}")
        if int(max_cas_prefix_len) < 0:
            raise ValueError(
                f"max_cas_prefix_len must be non-negative; got {max_cas_prefix_len}"
            )

        self.tokenizer = tokenizer
        self.max_prompt_len = int(max_prompt_len)
        self.max_reply_len = int(max_reply_len)
        self.max_cas_prefix_len = int(max_cas_prefix_len)
        self.register_to_id = (
            dict(register_to_id) if register_to_id is not None else dict(DEFAULT_REGISTER_TO_ID)
        )
        self.ignore_index = int(ignore_index)

        self.bos_id = int(tokenizer.BOS_ID)
        self.eos_id = int(tokenizer.EOS_ID)
        self.pad_id = int(tokenizer.PAD_ID)

        # Option C task-token injection (commit 6b23755 design):
        # when prepend_task_token=True, look up the per-record task
        # token id via task_token_id_for(task_type) and prepend to
        # cas_prefix_ids at position 0. The token_id_for callback
        # receives the record's "v1mix_task_type" / "task_type" /
        # "slot" string (whichever is set on the record). This keeps
        # the data file format unchanged (Path A in the design doc).
        self.prepend_task_token = bool(prepend_task_token)
        if self.prepend_task_token and task_token_id_for is None:
            raise ValueError(
                "prepend_task_token=True requires task_token_id_for "
                "callable that maps task_type strings to int token IDs"
            )
        self.task_token_id_for = task_token_id_for

        # v1e Phase C — auxiliary supervision label derivation. When
        # enabled, the collator parses each record's cas_expression at
        # batch time via parse_fractal / parse_meta_logic and emits
        # 9 additional tensor keys for the four aux heads. Default OFF
        # so existing v1 / v1c / v1d trainers see no behavior change.
        self.enable_aux_labels = bool(enable_aux_labels)
        if int(aux_k_max) <= 0:
            raise ValueError(f"aux_k_max must be positive; got {aux_k_max}")
        if int(aux_c_max) <= 0:
            raise ValueError(f"aux_c_max must be positive; got {aux_c_max}")
        self.aux_k_max = int(aux_k_max)
        self.aux_c_max = int(aux_c_max)

    # --- public API -----------------------------------------------------

    def __call__(
        self,
        records: Sequence[dict[str, Any]],
        *,
        device: torch.device | str = "cpu",
    ) -> dict[str, Any] | None:
        """Build a single batch from ``records``.

        Returns None if the input is empty or every record fails extraction
        (so the caller can skip the step rather than crash).

        When ``enable_aux_labels=True``, the returned batch additionally
        includes v1e Phase C aux-supervision keys (``aux_K_target``,
        ``aux_pos_targets``, ``aux_stop_targets``, ``aux_cluster_mh``,
        plus matching ``*_sample_weight`` / ``*_mask`` keys). These are
        derived per-record by parsing ``cas_expression`` and aligning
        Noetic indicators in ``reply_text``; see
        ``_derive_aux_labels_for_record``.
        """
        if not records:
            return None

        prompt_ids: list[list[int]] = []
        reply_ids: list[list[int]] = []
        cas_prefix_ids: list[list[int]] = []
        register_ids: list[int] = []
        record_ids: list[str] = []
        trace_ids: list[str] = []
        reply_texts: list[str] = []  # kept for aux label derivation
        cas_exprs: list[str] = []

        for rec in records:
            prompt_text = _extract_text(rec, ("prompt_text", "prompt"))
            reply_text = _extract_text(rec, ("reply_text", "reply"))
            cas_expr = _extract_text(rec, ("cas_expression",))
            if not prompt_text or not reply_text:
                continue

            p_ids = self._encode_capped(prompt_text, self.max_prompt_len)
            r_ids = self._encode_capped(reply_text, self.max_reply_len)
            if not p_ids or not r_ids:
                continue
            c_ids = (
                self._encode_capped(cas_expr, self.max_cas_prefix_len)
                if cas_expr
                else []
            )
            # Option C: prepend per-record task token to cas_prefix_ids.
            # Cap is applied AFTER prepending so the task token always
            # survives even when the encoded CAS is at max length.
            if self.prepend_task_token and c_ids:
                task_type = (
                    rec.get("v1mix_task_type")
                    or rec.get("task_type")
                    or rec.get("slot")
                )
                if task_type:
                    tok_id = int(self.task_token_id_for(task_type))
                    c_ids = [tok_id] + c_ids
                    if len(c_ids) > self.max_cas_prefix_len:
                        # Drop trailing CAS tokens, NOT the task token,
                        # if we exceeded the cap. The task token must
                        # always be at index 0.
                        c_ids = c_ids[: self.max_cas_prefix_len]
            reg_id = self._parse_register(rec.get("register"))

            prompt_ids.append(p_ids)
            reply_ids.append(r_ids)
            cas_prefix_ids.append(c_ids)
            register_ids.append(reg_id)
            record_ids.append(str(rec.get("id", "")))
            trace_ids.append(str(rec.get("trace_id", "")))
            # Keep raw text for aux label derivation (only used when
            # enable_aux_labels=True; cheap to retain otherwise).
            reply_texts.append(reply_text)
            cas_exprs.append(cas_expr or "")

        if not prompt_ids:
            return None

        device_t = torch.device(device)
        b = len(prompt_ids)

        # --- encoder side: prompt_ids -> input_ids + attention_mask -----
        s_prompt = max(len(x) for x in prompt_ids)
        input_ids = torch.full((b, s_prompt), self.pad_id, dtype=torch.long)
        attention_mask = torch.zeros((b, s_prompt), dtype=torch.bool)
        for i, ids in enumerate(prompt_ids):
            input_ids[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
            attention_mask[i, : len(ids)] = True

        # --- decoder side: BOS + reply, targets = reply + EOS -----------
        # dec_input[i, 0] = BOS; dec_input[i, 1..] = reply_ids[i, :-1] effectively
        # we build them as: dec_input = [BOS] + reply_ids; lm_targets = reply_ids + [EOS]
        # both length L_dec = 1 + len(reply_ids).
        dec_lens = [len(r) + 1 for r in reply_ids]
        l_dec = max(dec_lens)
        decoder_input_ids = torch.full((b, l_dec), self.pad_id, dtype=torch.long)
        lm_targets = torch.full((b, l_dec), self.ignore_index, dtype=torch.long)
        loss_mask = torch.zeros((b, l_dec), dtype=torch.bool)
        for i, ids in enumerate(reply_ids):
            n = len(ids)
            # decoder_input: [BOS, t1, t2, ..., tn]
            decoder_input_ids[i, 0] = self.bos_id
            if n > 0:
                decoder_input_ids[i, 1 : 1 + n] = torch.tensor(ids, dtype=torch.long)
            # lm_targets: [t1, t2, ..., tn, EOS]
            if n > 0:
                lm_targets[i, : n] = torch.tensor(ids, dtype=torch.long)
            lm_targets[i, n] = self.eos_id
            loss_mask[i, : n + 1] = True

        # --- CAS prefix --------------------------------------------------
        k_max = max((len(c) for c in cas_prefix_ids), default=0)
        if k_max > 0:
            cas_prefix_tensor = torch.full((b, k_max), self.pad_id, dtype=torch.long)
            cas_prefix_mask = torch.zeros((b, k_max), dtype=torch.bool)
            for i, ids in enumerate(cas_prefix_ids):
                if ids:
                    cas_prefix_tensor[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
                    cas_prefix_mask[i, : len(ids)] = True
        else:
            cas_prefix_tensor = None
            cas_prefix_mask = None

        register_tensor = torch.tensor(register_ids, dtype=torch.long)

        batch: dict[str, Any] = {
            # forward_with_lm() kwargs
            "input_ids": input_ids.to(device_t),
            "attention_mask": attention_mask.to(device_t),
            "lm_decoder_input_ids": decoder_input_ids.to(device_t),
            "cas_prefix_ids": cas_prefix_tensor.to(device_t) if cas_prefix_tensor is not None else None,
            "cas_prefix_mask": cas_prefix_mask.to(device_t) if cas_prefix_mask is not None else None,
            "register_id": register_tensor.to(device_t),
            # Loss-side artifacts (not passed to forward)
            "lm_targets": lm_targets.to(device_t),
            "loss_mask": loss_mask.to(device_t),
            # Provenance pass-through
            "record_ids": record_ids,
            "trace_ids": trace_ids,
        }

        if self.enable_aux_labels:
            aux_tensors = self._derive_aux_labels_batch(
                cas_exprs=cas_exprs,
                reply_texts=reply_texts,
                reply_ids_list=reply_ids,
                l_dec=l_dec,
                device=device_t,
            )
            batch.update(aux_tensors)

        return batch

    # --- aux label derivation (v1e Phase C) -----------------------------

    def _derive_aux_labels_batch(
        self,
        *,
        cas_exprs: list[str],
        reply_texts: list[str],
        reply_ids_list: list[list[int]],
        l_dec: int,
        device: torch.device,
    ) -> dict[str, Any]:
        """Build the 9 aux-label tensors for one batch.

        Lazy-imports the parsers from cas_native.inference to keep the
        collator's import surface unchanged when aux labels are off.

        Returns a dict mappable straight onto the batch:
            aux_K_target           (B,)              long
            aux_K_sample_weight    (B,)              float
            aux_pos_targets        (B, K_max)        long  (-100 = ignore)
            aux_pos_sample_weight  (B,)              float
            aux_stop_targets       (B, L_dec)        long  (-100 = ignore)
            aux_stop_sample_weight (B, L_dec)        float
            aux_cluster_mh         (B, C_max, 10)    float
            aux_cluster_mask       (B, C_max)        bool
            aux_cluster_sample_wt  (B,)              float
        """
        from cas_native.inference.fractal_repair import (
            parse_fractal,
            extract_noetic_sequence_with_positions,
        )
        from cas_native.inference.meta_logic_repair import parse_meta_logic

        b = len(cas_exprs)
        k_max = self.aux_k_max
        c_max = self.aux_c_max
        ig = LABEL_IGNORE_INDEX

        # Initialize tensors.
        aux_K_target = torch.full((b,), ig, dtype=torch.long)
        aux_K_sample_weight = torch.zeros((b,), dtype=torch.float)
        aux_pos_targets = torch.full((b, k_max), ig, dtype=torch.long)
        aux_pos_sample_weight = torch.zeros((b,), dtype=torch.float)
        aux_stop_targets = torch.full((b, l_dec), ig, dtype=torch.long)
        aux_stop_sample_weight = torch.zeros((b, l_dec), dtype=torch.float)
        aux_cluster_mh = torch.zeros((b, c_max, NUM_NOETICS), dtype=torch.float)
        aux_cluster_mask = torch.zeros((b, c_max), dtype=torch.bool)
        aux_cluster_sample_wt = torch.zeros((b,), dtype=torch.float)

        for i in range(b):
            cas_expr = cas_exprs[i]
            reply_text = reply_texts[i]
            r_ids = reply_ids_list[i]
            reply_len = len(r_ids)
            # Decoder len for this record: reply tokens + EOS = reply_len + 1
            rec_dec_len = reply_len + 1

            # --- H_card / H_pos: fractal-derived labels ------------------
            fractal_seq = parse_fractal(cas_expr) if cas_expr else None
            if fractal_seq is not None:
                k_actual = min(len(fractal_seq.k_values), k_max)
                aux_K_target[i] = k_actual
                aux_K_sample_weight[i] = 1.0
                for j in range(k_actual):
                    aux_pos_targets[i, j] = int(fractal_seq.k_values[j])
                aux_pos_sample_weight[i] = 1.0
            # Else: K_target stays ignore, sample weight 0 → no loss contribution.

            # --- H_stop: per-decoder-position stop target ----------------
            # Compute the token position where the LAST EXPECTED slot ends:
            #   fractal records: align expected k against found_with_positions
            #     in reply_text; approximate token position by char-fraction
            #   non-fractal records: stop boundary = end of reply (EOS only)
            stop_boundary_token_pos = self._stop_boundary_token_pos(
                fractal_seq=fractal_seq,
                reply_text=reply_text,
                reply_token_len=reply_len,
                extract_fn=extract_noetic_sequence_with_positions,
            )
            # stop_target = 0 for positions [0, stop_boundary_token_pos)
            # stop_target = 1 for positions [stop_boundary_token_pos, rec_dec_len)
            # PAD positions (>= rec_dec_len) stay ignore_index.
            for t in range(min(rec_dec_len, l_dec)):
                aux_stop_targets[i, t] = 1 if t >= stop_boundary_token_pos else 0
                aux_stop_sample_weight[i, t] = 1.0

            # --- H_cluster: meta-logic cluster membership ----------------
            meta_rel = parse_meta_logic(cas_expr) if cas_expr else None
            if meta_rel is not None and meta_rel.clusters:
                aux_cluster_sample_wt[i] = 1.0
                for c_idx, cluster in enumerate(meta_rel.clusters[:c_max]):
                    for n_val in cluster.noetics:
                        if 0 <= int(n_val) < NUM_NOETICS:
                            aux_cluster_mh[i, c_idx, int(n_val)] = 1.0
                    aux_cluster_mask[i, c_idx] = True
            # Else: all zeros + sample weight 0 → no loss contribution.

        return {
            "aux_K_target": aux_K_target.to(device),
            "aux_K_sample_weight": aux_K_sample_weight.to(device),
            "aux_pos_targets": aux_pos_targets.to(device),
            "aux_pos_sample_weight": aux_pos_sample_weight.to(device),
            "aux_stop_targets": aux_stop_targets.to(device),
            "aux_stop_sample_weight": aux_stop_sample_weight.to(device),
            "aux_cluster_mh": aux_cluster_mh.to(device),
            "aux_cluster_mask": aux_cluster_mask.to(device),
            "aux_cluster_sample_wt": aux_cluster_sample_wt.to(device),
        }

    @staticmethod
    def _stop_boundary_token_pos(
        *,
        fractal_seq: Any,
        reply_text: str,
        reply_token_len: int,
        extract_fn: Any,
    ) -> int:
        """Compute the decoder-token position where ``stop_target`` flips
        from 0 to 1 for one record.

        Algorithm:
          - Non-fractal record (``fractal_seq is None``): boundary at the
            EOS-token position (= reply_token_len). All reply tokens are
            "continue" (0); only the EOS slot is "stop" (1).
          - Fractal record: align expected k_values against
            ``extract_noetic_sequence_with_positions(reply_text)`` by
            greedy longest-prefix matching. Take the END char position of
            the last aligned indicator and scale to token position by
            ``int(reply_token_len * (last_end_char / len(reply_text)))``.
            If alignment fails (expected k sequence not fully found in
            reply), fall back to EOS-only as for non-fractal.
        """
        if fractal_seq is None or not reply_text:
            return reply_token_len
        expected = list(fractal_seq.k_values)
        if not expected:
            return reply_token_len
        # Greedy alignment of expected against found.
        found = extract_fn(reply_text)  # list of (start, end, k)
        ptr = 0
        last_end_char: Optional[int] = None
        for ek in expected:
            while ptr < len(found) and found[ptr][2] != int(ek):
                ptr += 1
            if ptr >= len(found):
                # Expected k not found — fall back to EOS-only boundary.
                return reply_token_len
            last_end_char = found[ptr][1]
            ptr += 1
        if last_end_char is None:
            return reply_token_len
        text_len = max(1, len(reply_text))
        token_pos = int(reply_token_len * (last_end_char / text_len))
        # Clamp to [0, reply_token_len] inclusive.
        return max(0, min(token_pos, reply_token_len))

    # --- internals ------------------------------------------------------

    def _encode_capped(self, text: str, max_len: int) -> list[int]:
        """Encode ``text`` without special tokens, truncate to ``max_len``."""
        if max_len <= 0:
            return []
        ids = self.tokenizer.encode(text, max_length=max_len, add_special=False)
        return list(ids)[:max_len]

    def _parse_register(self, raw: Any) -> int:
        """Map a register character to its integer id; default 0 for missing."""
        if isinstance(raw, str) and raw in self.register_to_id:
            return int(self.register_to_id[raw])
        return 0


def _extract_text(rec: dict[str, Any], keys: Iterable[str]) -> str:
    """Return the first non-empty string value for any of ``keys``, else ''."""
    for k in keys:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


__all__ = ["NativeNLCollator", "DEFAULT_REGISTER_TO_ID"]
