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

from typing import Any, Iterable, Sequence

import torch


DEFAULT_REGISTER_TO_ID: dict[str, int] = {"T": 0, "A": 1, "f": 2, "E": 3}


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
        """
        if not records:
            return None

        prompt_ids: list[list[int]] = []
        reply_ids: list[list[int]] = []
        cas_prefix_ids: list[list[int]] = []
        register_ids: list[int] = []
        record_ids: list[str] = []
        trace_ids: list[str] = []

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

        return {
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
