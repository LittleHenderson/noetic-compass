"""Task-token overlay for ExtendedHybridCASTokenizer.

Adds ``[VALID]`` and ``[INVALID]`` tokens at IDs above the existing
extended vocabulary so that every existing token ID stays stable. This
preserves embedding-row alignment for v1 PREFIX128 5ep checkpoints
that did NOT have task tokens; the trainer's warm-start logic resizes
the embedding by the small delta and copies semantic anchors into the
two new rows.

Why a wrapper instead of editing the base ``HybridCASTokenizer``:
inserting tokens into the base would shift every English BPE token's
composed ID upward, breaking v1 checkpoint compatibility. The wrapper
appends at the top of the composed vocabulary, so the trained
embedding rows 0..38682 keep their meaning and only rows 38683 and
38684 are new.

Public surface mirrors ``ExtendedHybridCASTokenizer`` so callers
(collator, generate_reply, eval scripts) can drop this in via the
existing ``tokenizer.encode(...) / tokenizer.decode(...) /
tokenizer.vocab_size`` contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from cas_native.training.english_bpe_extension import ExtendedHybridCASTokenizer


# Canonical task-token names. Order is fixed: VALID first, INVALID
# second. IDs are assigned sequentially after the wrapped tokenizer's
# vocab_size, so loading order matters.
TASK_TOKENS: tuple[str, ...] = ("[VALID]", "[INVALID]")


@dataclass(frozen=True)
class TaskTokenIds:
    """ID lookup for the task tokens after extension."""
    valid: int
    invalid: int

    def for_task_type(self, task_type: str) -> int:
        """Return the task token ID for a Path D ``task_type``."""
        if task_type == "cas_to_english":
            return self.valid
        if task_type == "invalid_to_explanation":
            return self.invalid
        raise ValueError(
            f"unknown task_type {task_type!r}; expected "
            "'cas_to_english' or 'invalid_to_explanation'"
        )


class TaskTokenExtendedTokenizer:
    """Wraps an ``ExtendedHybridCASTokenizer`` with two trailing task
    tokens, ``[VALID]`` and ``[INVALID]``.

    The wrapped tokenizer's IDs 0..vocab_size-1 are preserved verbatim.
    Two new tokens land at IDs ``vocab_size`` and ``vocab_size + 1``.

    All ID-returning methods (encode, BOS_ID, EOS_ID, etc.) defer to
    the wrapped tokenizer EXCEPT lookups for the two task token strings.
    All decode lookups defer to the wrapped tokenizer EXCEPT IDs at
    the two new positions.
    """

    VERSION = "task-token-overlay-v1"

    def __init__(
        self,
        wrapped: ExtendedHybridCASTokenizer,
        task_tokens: tuple[str, ...] = TASK_TOKENS,
    ) -> None:
        if len(task_tokens) != len(TASK_TOKENS):
            raise ValueError(
                f"task_tokens must have exactly {len(TASK_TOKENS)} entries"
            )
        self._wrapped = wrapped
        self._task_tokens = tuple(task_tokens)
        self._wrapped_vocab_size = int(wrapped.vocab_size)
        self._task_token_to_id: dict[str, int] = {
            tok: self._wrapped_vocab_size + i
            for i, tok in enumerate(self._task_tokens)
        }
        self._id_to_task_token: dict[int, str] = {
            v: k for k, v in self._task_token_to_id.items()
        }

    # ------------------------------------------------------------------
    # Wrapped-property pass-through
    # ------------------------------------------------------------------
    @property
    def vocab_size(self) -> int:
        return self._wrapped_vocab_size + len(self._task_tokens)

    @property
    def BOS_ID(self) -> int:
        return self._wrapped.BOS_ID

    @property
    def EOS_ID(self) -> int:
        return self._wrapped.EOS_ID

    @property
    def PAD_ID(self) -> int:
        return self._wrapped.PAD_ID

    @property
    def UNK_ID(self) -> int:
        return self._wrapped.UNK_ID

    @property
    def task_token_ids(self) -> TaskTokenIds:
        return TaskTokenIds(
            valid=self._task_token_to_id[TASK_TOKENS[0]],
            invalid=self._task_token_to_id[TASK_TOKENS[1]],
        )

    @property
    def base(self) -> Any:
        """Return the deepest ``HybridCASTokenizer`` for serialization.

        ``save_tokenizer_artifacts`` walks ``tokenizer.base`` to find the
        savable serialization root. The task-token overlay is reapplied
        at load time via ``extend_with_task_tokens(...)``, so we do NOT
        serialize the wrapper — only the base. This matches the design
        of ``ExtendedHybridCASTokenizer``: composed BPE is also stored
        as a separate artifact and reapplied at load time.
        """
        # ExtendedHybridCASTokenizer exposes ``.base`` -> HybridCASTokenizer.
        inner = getattr(self._wrapped, "base", self._wrapped)
        return inner

    def metadata(self) -> dict[str, Any]:
        """Tokenizer-introspection block included in the checkpoint
        manifest's tokenizer provenance entry."""
        wrapped_meta: dict[str, Any] = {}
        if hasattr(self._wrapped, "metadata"):
            try:
                wrapped_meta = dict(self._wrapped.metadata())
            except Exception:
                wrapped_meta = {}
        wrapped_meta.update({
            "task_token_overlay_version": self.VERSION,
            "task_tokens": list(self._task_tokens),
            "task_token_ids": {
                "valid": self._task_token_to_id[TASK_TOKENS[0]],
                "invalid": self._task_token_to_id[TASK_TOKENS[1]],
            },
            "wrapped_vocab_size": int(self._wrapped_vocab_size),
            "extended_vocab_size": int(self.vocab_size),
        })
        return wrapped_meta

    # ------------------------------------------------------------------
    # Encode / decode with task-token override
    # ------------------------------------------------------------------
    def encode(
        self,
        text: str,
        max_length: int | None = None,
        *,
        add_special: bool = False,
    ) -> list[int]:
        """Encode text. Bare ``[VALID]`` / ``[INVALID]`` substrings are
        replaced with their high IDs; everything else delegates to the
        wrapped tokenizer.

        For the typical Path D collator workflow, callers will NOT pass
        ``[VALID]`` as a substring of text. Instead, they'll call
        ``task_token_ids.for_task_type(...)`` to get the integer ID and
        prepend it directly to a list of CAS-token ids. This encode()
        path is kept for completeness and unit testing.
        """
        # Greedy substring replacement: scan text for task tokens, emit
        # their IDs at those positions, and tokenize the surrounding
        # text via the wrapped tokenizer.
        result: list[int] = []
        cursor = 0
        while cursor < len(text):
            hit = None
            hit_token = None
            for tok in self._task_tokens:
                idx = text.find(tok, cursor)
                if idx >= 0 and (hit is None or idx < hit):
                    hit = idx
                    hit_token = tok
            if hit is None:
                # No more task tokens; tokenize the remainder.
                rest = text[cursor:]
                if rest:
                    result.extend(
                        self._wrapped.encode(
                            rest, max_length=10**6, add_special=add_special,
                        )
                    )
                break
            # Tokenize text BEFORE the hit, then emit the task-token ID,
            # then continue scanning AFTER the task token.
            before = text[cursor:hit]
            if before:
                result.extend(
                    self._wrapped.encode(
                        before, max_length=10**6, add_special=add_special,
                    )
                )
            result.append(self._task_token_to_id[hit_token])
            cursor = hit + len(hit_token)

        if max_length is not None and max_length > 0:
            result = result[:max_length]
        return result

    def decode(self, ids: Iterable[int], *, skip_special: bool = True) -> str:
        """Decode IDs back to text. Task-token IDs render as
        ``[VALID]`` / ``[INVALID]`` literals (or are skipped when
        ``skip_special=True`` matches the wrapped tokenizer's behavior
        for special tokens — we treat task tokens as 'special' so they
        don't leak into reply text)."""
        ids_list = list(int(i) for i in ids)
        # Split into runs of wrapped-id vs task-token-id.
        out_pieces: list[str] = []
        wrapped_run: list[int] = []

        def flush_wrapped() -> None:
            if wrapped_run:
                out_pieces.append(
                    self._wrapped.decode(wrapped_run, skip_special=skip_special)
                )
                wrapped_run.clear()

        for tok_id in ids_list:
            if tok_id in self._id_to_task_token:
                flush_wrapped()
                if not skip_special:
                    out_pieces.append(self._id_to_task_token[tok_id])
            else:
                wrapped_run.append(tok_id)
        flush_wrapped()
        return "".join(out_pieces)


def extend_with_task_tokens(
    wrapped: ExtendedHybridCASTokenizer,
) -> TaskTokenExtendedTokenizer:
    """Public factory for the task-token overlay."""
    return TaskTokenExtendedTokenizer(wrapped)


__all__ = [
    "TASK_TOKENS",
    "TaskTokenIds",
    "TaskTokenExtendedTokenizer",
    "extend_with_task_tokens",
]
