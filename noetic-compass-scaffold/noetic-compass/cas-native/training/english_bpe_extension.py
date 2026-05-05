"""English BPE extension for ``HybridCASTokenizer``.

This module trains a byte-level BPE vocabulary from scratch on the project's
own SDG corpus (no foreign tokenizer downloads, no pretrained merges) and
composes it on top of the existing CAS-aware hybrid tokenizer so that:

* CAS structural tokens keep priority and stable low IDs (``0..N_CAS-1``).
* English text is tokenized with compact BPE pieces instead of the
  per-character ``<CHAR:HEX>`` fallback.
* Every tokenizer artifact carries full provenance — corpus hash, vocab
  version, merge count, training timestamp.

Public surface:

* :func:`train_english_bpe` — train BPE on a JSONL corpus, save artifact.
* :func:`load_english_bpe_artifact` — load a saved artifact.
* :func:`extend_hybrid_tokenizer` — compose a base ``HybridCASTokenizer``
  with an English BPE artifact, returning ``ExtendedHybridCASTokenizer``.
* :class:`ExtendedHybridCASTokenizer` — the composed tokenizer.
* :func:`tokenize_with_provenance` — tokenization + ``vocab_version`` stamp.

The implementation is stdlib-only. ``hashlib``, ``json``, ``re``,
``collections``, ``pathlib``, ``time``. No torch, no numpy, no third-party
BPE libraries that ship pretrained merges.

See ``docs/working/native_nl_tokenizer_extension_spec_2026_05_04.md`` for
the full design doc.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from cas_native.training.tokenizer import HybridCASTokenizer


# ---------------------------------------------------------------------------
# Constants and provenance schema
# ---------------------------------------------------------------------------

ARTIFACT_SCHEMA_VERSION = "english_bpe_artifact.v1"
DEFAULT_VOCAB_VERSION = "english_bpe.v1.0"

# BPE-side specials. These get IDs but are NEVER emitted from the BPE
# encoder for input bytes. They are reserved positions only.
BPE_SPECIALS: tuple[str, ...] = (
    "<bpe_pad>",
    "<bpe_unk>",
    "<bpe_bow>",
    "<bpe_eow>",
)

# Field name fallbacks when reading SDG records. The parallel SDG agent
# writes `prompt`/`reply`; older corpora use `user_prompt`/`assistant_response`.
PROMPT_FIELDS = ("prompt", "user_prompt", "text")
REPLY_FIELDS = ("reply", "response", "assistant_response", "output")

# A simple word/punct splitter used before BPE. Greedy enough for an English
# corpus; CAS literals are handled separately by the reserved-token matcher.
_WORD_RE = re.compile(r"\S+", flags=re.UNICODE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_text(record: dict[str, Any]) -> str:
    """Concatenate a record's prompt + reply with a separator."""
    prompt = ""
    for f in PROMPT_FIELDS:
        v = record.get(f)
        if isinstance(v, str) and v.strip():
            prompt = v
            break
    reply = ""
    for f in REPLY_FIELDS:
        v = record.get(f)
        if isinstance(v, str) and v.strip():
            reply = v
            break
    parts = [p for p in (prompt, reply) if p]
    return " \n".join(parts)


def _hash_corpus_bytes(text_blocks: list[str]) -> str:
    """SHA-256 of the concatenated corpus, with explicit record separators.

    The separator ensures that two different records do not collide with one
    longer record producing the same flat byte sequence.
    """
    h = hashlib.sha256()
    h.update(b"english_bpe_corpus_v1\x00")
    for block in text_blocks:
        h.update(block.encode("utf-8"))
        h.update(b"\x1e")  # ASCII record-separator.
    return h.hexdigest()


def _hash_file_bytes(path: Path) -> str:
    """SHA-256 of the file's raw bytes — provenance-grade hash."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _byte_token(b: int) -> str:
    """Return a compact unique string for byte value ``b`` (0..255).

    We prefer a printable variant for ASCII bytes and a hex marker for
    non-ASCII bytes. The mapping is bijective with byte values.
    """
    if 0x21 <= b <= 0x7E and chr(b) not in {"<", ">"}:
        # printable ASCII (excluding < and > so they don't collide with
        # special-token brackets in JSON)
        return chr(b)
    return f"<0x{b:02X}>"


def _build_byte_alphabet() -> dict[str, int]:
    """Bijective byte-value -> string alphabet, 256 entries."""
    return {_byte_token(b): b for b in range(256)}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------------------------------------------------------------------------
# BPE training
# ---------------------------------------------------------------------------

@dataclass
class BPEArtifact:
    """A trained English BPE artifact, fully provenance-stamped."""

    schema_version: str
    vocab_version: str
    trained_from_corpus_hash: str
    trained_from_corpus_path: str
    trained_at_timestamp: str
    bpe_merge_count: int
    english_vocab_size: int
    target_vocab_size: int
    min_frequency: int
    n_records_trained_on: int
    byte_to_id: dict[str, int]
    special_to_id: dict[str, int]
    merge_to_id: dict[str, int]
    merges: list[tuple[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "vocab_version": self.vocab_version,
            "trained_from_corpus_hash": self.trained_from_corpus_hash,
            "trained_from_corpus_path": self.trained_from_corpus_path,
            "trained_at_timestamp": self.trained_at_timestamp,
            "bpe_merge_count": self.bpe_merge_count,
            "english_vocab_size": self.english_vocab_size,
            "target_vocab_size": self.target_vocab_size,
            "min_frequency": self.min_frequency,
            "n_records_trained_on": self.n_records_trained_on,
            "byte_to_id": dict(self.byte_to_id),
            "special_to_id": dict(self.special_to_id),
            "merge_to_id": dict(self.merge_to_id),
            "merges": [list(pair) for pair in self.merges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BPEArtifact":
        if data.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported BPE artifact schema_version: "
                f"{data.get('schema_version')!r}; expected {ARTIFACT_SCHEMA_VERSION!r}"
            )
        return cls(
            schema_version=str(data["schema_version"]),
            vocab_version=str(data["vocab_version"]),
            trained_from_corpus_hash=str(data["trained_from_corpus_hash"]),
            trained_from_corpus_path=str(data["trained_from_corpus_path"]),
            trained_at_timestamp=str(data["trained_at_timestamp"]),
            bpe_merge_count=int(data["bpe_merge_count"]),
            english_vocab_size=int(data["english_vocab_size"]),
            target_vocab_size=int(data["target_vocab_size"]),
            min_frequency=int(data["min_frequency"]),
            n_records_trained_on=int(data["n_records_trained_on"]),
            byte_to_id=dict(data["byte_to_id"]),
            special_to_id=dict(data["special_to_id"]),
            merge_to_id=dict(data["merge_to_id"]),
            merges=[tuple(p) for p in data["merges"]],  # type: ignore[misc]
        )


def _word_to_byte_pieces(word: str) -> list[str]:
    """Encode word to UTF-8 bytes and return one piece per byte."""
    return [_byte_token(b) for b in word.encode("utf-8")]


def _train_bpe_on_word_counts(
    word_counts: Counter[str],
    *,
    target_vocab_size: int,
    min_frequency: int,
    initial_vocab: dict[str, int],
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Run greedy BPE training on a corpus represented as word -> count.

    Returns ``(merges, merge_to_id)``.

    Determinism is enforced by sorting tied pairs by their lexicographic
    order so identical word-count inputs always produce identical merge
    sequences.
    """
    # Each word becomes a list of pieces; we track the (frequency, pieces)
    # tuples and the running vocab.
    word_pieces: list[list[str]] = []
    word_freq: list[int] = []
    for word, count in word_counts.items():
        pieces = _word_to_byte_pieces(word)
        if not pieces:
            continue
        word_pieces.append(pieces)
        word_freq.append(count)

    vocab: dict[str, int] = dict(initial_vocab)
    merges: list[tuple[str, str]] = []
    merge_to_id: dict[str, int] = {}

    # Build initial pair counts.
    pair_counts: Counter[tuple[str, str]] = Counter()
    for pieces, freq in zip(word_pieces, word_freq):
        for i in range(len(pieces) - 1):
            pair_counts[(pieces[i], pieces[i + 1])] += freq

    while len(vocab) + len(merges) < target_vocab_size:
        if not pair_counts:
            break
        # Pick the highest-frequency pair, breaking ties on lexicographic
        # ordering for determinism.
        best_pair = None
        best_count = -1
        for pair, count in pair_counts.items():
            if count > best_count:
                best_pair = pair
                best_count = count
            elif count == best_count and best_pair is not None:
                # Lexicographic tie-break — smaller (lex-wise) pair wins.
                if pair < best_pair:
                    best_pair = pair
        if best_pair is None or best_count < min_frequency:
            break

        merged = best_pair[0] + best_pair[1]
        merges.append(best_pair)
        merge_id = len(vocab) + len(merge_to_id)
        merge_to_id[merged] = merge_id

        # Apply the merge to every word, updating pair_counts incrementally.
        a, b = best_pair
        new_word_pieces: list[list[str]] = []
        for pieces, freq in zip(word_pieces, word_freq):
            if a not in pieces:
                new_word_pieces.append(pieces)
                continue
            new_pieces: list[str] = []
            i = 0
            while i < len(pieces):
                if (
                    i + 1 < len(pieces)
                    and pieces[i] == a
                    and pieces[i + 1] == b
                ):
                    new_pieces.append(merged)
                    i += 2
                else:
                    new_pieces.append(pieces[i])
                    i += 1
            # Update pair counts: subtract pairs from the old pieces, add
            # pairs from the new pieces. We just rebuild the affected word's
            # contribution rather than tracking deltas for simplicity and
            # correctness — the corpus is small enough.
            for j in range(len(pieces) - 1):
                pair_counts[(pieces[j], pieces[j + 1])] -= freq
            for j in range(len(new_pieces) - 1):
                pair_counts[(new_pieces[j], new_pieces[j + 1])] += freq
            new_word_pieces.append(new_pieces)

        # Drop pairs that fell to zero or below.
        for k in [k for k, v in pair_counts.items() if v <= 0]:
            del pair_counts[k]

        word_pieces = new_word_pieces

    return merges, merge_to_id


def train_english_bpe(
    corpus_path: str | Path,
    *,
    vocab_size: int = 24000,
    min_frequency: int = 2,
    output_path: str | Path | None = None,
    vocab_version: str = DEFAULT_VOCAB_VERSION,
    max_records: int | None = None,
) -> dict[str, Any]:
    """Train byte-level BPE from scratch on a JSONL SDG corpus.

    The function is the public entry point for v1 BPE training. It:

    1. Reads the JSONL at ``corpus_path``.
    2. Extracts ``prompt + reply`` text per record (field-name agnostic).
    3. Computes the SHA-256 of the input file for provenance.
    4. Trains greedy byte-level BPE deterministically.
    5. Saves a fully-stamped artifact JSON to ``output_path`` (if set) and
       returns the artifact dict.

    Args:
        corpus_path: path to the JSONL training corpus.
        vocab_size: target English vocab size cap (bytes + specials + merges).
        min_frequency: drop merges whose count is below this threshold.
        output_path: optional output artifact path. If None, no file is
            written; the returned dict is the artifact.
        vocab_version: semver-style version string baked into the artifact.
        max_records: optional cap on training records (smoke / test mode).

    Returns:
        The artifact dict (matches :class:`BPEArtifact.to_dict`).

    Raises:
        FileNotFoundError: if ``corpus_path`` does not exist.
        ValueError: if the corpus is empty after filtering or
            ``vocab_size`` is below the byte-alphabet floor.
    """
    corpus_p = Path(corpus_path)
    if not corpus_p.exists():
        raise FileNotFoundError(f"corpus path does not exist: {corpus_path}")

    byte_alphabet = _build_byte_alphabet()
    byte_to_id = dict(byte_alphabet)
    special_to_id = {tok: 256 + i for i, tok in enumerate(BPE_SPECIALS)}
    base_size = len(byte_to_id) + len(special_to_id)
    if vocab_size < base_size:
        raise ValueError(
            f"vocab_size ({vocab_size}) must be >= base size ({base_size}) "
            f"= 256 bytes + {len(BPE_SPECIALS)} specials"
        )

    records = _read_jsonl(corpus_p)
    if max_records is not None:
        records = records[: max_records]
    if not records:
        raise ValueError(f"corpus at {corpus_p} produced 0 records")

    text_blocks = [_record_text(r) for r in records]
    text_blocks = [t for t in text_blocks if t.strip()]
    if not text_blocks:
        raise ValueError(f"corpus at {corpus_p} has no usable prompt/reply text")

    # Word-level frequency pre-pass. Splitting on whitespace is good enough
    # for v1; CAS literals are handled separately by the reserved-token
    # matcher at compose time, so they don't need to be word-aware here.
    word_counts: Counter[str] = Counter()
    for block in text_blocks:
        for w in _WORD_RE.findall(block):
            word_counts[w] += 1

    if not word_counts:
        raise ValueError(f"corpus at {corpus_p} produced 0 words")

    initial_vocab = {**byte_to_id, **special_to_id}
    merges, merge_to_id = _train_bpe_on_word_counts(
        word_counts,
        target_vocab_size=vocab_size,
        min_frequency=min_frequency,
        initial_vocab=initial_vocab,
    )

    english_vocab_size = len(byte_to_id) + len(special_to_id) + len(merges)
    corpus_hash = _hash_file_bytes(corpus_p)
    timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")

    artifact = BPEArtifact(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        vocab_version=vocab_version,
        trained_from_corpus_hash=corpus_hash,
        trained_from_corpus_path=str(corpus_p.resolve()),
        trained_at_timestamp=timestamp,
        bpe_merge_count=len(merges),
        english_vocab_size=english_vocab_size,
        target_vocab_size=vocab_size,
        min_frequency=min_frequency,
        n_records_trained_on=len(records),
        byte_to_id=byte_to_id,
        special_to_id=special_to_id,
        merge_to_id=merge_to_id,
        merges=merges,
    )
    payload = artifact.to_dict()

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return payload


def load_english_bpe_artifact(path: str | Path) -> BPEArtifact:
    """Load a saved BPE artifact from JSON."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return BPEArtifact.from_dict(data)


# ---------------------------------------------------------------------------
# Extended hybrid tokenizer
# ---------------------------------------------------------------------------

class ExtendedHybridCASTokenizer:
    """``HybridCASTokenizer`` + English BPE on top.

    CAS reserved tokens get IDs ``0..N_CAS-1`` (inherited verbatim from the
    base hybrid tokenizer). English BPE pieces get IDs
    ``N_CAS..N_CAS + N_ENG - 1`` (offset from the artifact's internal IDs).

    The encoder runs the base tokenizer's reserved-token matcher first, so
    CAS literals like ``^3^P|A`` survive as atomic tokens. Whitespace is
    consumed as the base tokenizer's ``[SP]`` / ``[NL]`` / ``[TAB]`` tokens.
    Anything else (English alphanumerics, punctuation, multi-byte UTF-8) is
    BPE-encoded byte-level.

    The decoder reverses both layers cleanly: BPE pieces are concatenated
    back into UTF-8 bytes and decoded; CAS reserved tokens render verbatim;
    whitespace specials render to spaces/newlines/tabs.
    """

    VOCAB_VERSION_FIELD = "vocab_version"

    def __init__(
        self,
        base: HybridCASTokenizer,
        artifact: BPEArtifact,
    ) -> None:
        if not base.frozen:
            base = HybridCASTokenizer(token_to_id=dict(base.word2id), frozen=True)
        self.base = base
        self.artifact = artifact
        self._n_cas = base.vocab_size
        # Build the merge ranks for fast greedy encoding.
        self._merge_ranks: dict[tuple[str, str], int] = {
            tuple(pair): i for i, pair in enumerate(artifact.merges)  # type: ignore[misc]
        }
        # Build the English-side piece-string -> local-id map.
        self._eng_piece_to_local_id: dict[str, int] = {}
        for piece, local_id in artifact.byte_to_id.items():
            self._eng_piece_to_local_id[piece] = local_id
        for piece, local_id in artifact.special_to_id.items():
            self._eng_piece_to_local_id[piece] = local_id
        for piece, local_id in artifact.merge_to_id.items():
            self._eng_piece_to_local_id[piece] = local_id
        # Reverse mapping (local id -> piece string).
        self._eng_local_id_to_piece: dict[int, str] = {
            v: k for k, v in self._eng_piece_to_local_id.items()
        }
        # Composed id -> piece (covers both CAS and English).
        self._composed_id_to_token: dict[int, str] = {}
        for tok, idx in self.base.word2id.items():
            self._composed_id_to_token[idx] = tok
        for piece, local_id in self._eng_piece_to_local_id.items():
            self._composed_id_to_token[self._n_cas + local_id] = piece
        # Byte-token -> raw byte for decoding.
        self._byte_token_to_byte: dict[str, int] = {
            tok: val for tok, val in artifact.byte_to_id.items()
        }
        # For the encoder: map raw byte int -> byte-token string (one piece).
        self._byte_to_byte_token: dict[int, str] = {
            v: k for k, v in artifact.byte_to_id.items()
        }

    # ------------------------------------------------------------------
    # Public properties / introspection
    # ------------------------------------------------------------------

    @property
    def vocab_size(self) -> int:
        return self._n_cas + self.artifact.english_vocab_size

    @property
    def cas_reserved_token_count(self) -> int:
        return self._n_cas

    @property
    def english_vocab_size(self) -> int:
        return self.artifact.english_vocab_size

    @property
    def vocab_version(self) -> str:
        return self.artifact.vocab_version

    @property
    def PAD_ID(self) -> int:  # noqa: N802 — match base API
        return self.base.PAD_ID

    @property
    def UNK_ID(self) -> int:  # noqa: N802
        return self.base.UNK_ID

    @property
    def BOS_ID(self) -> int:  # noqa: N802
        return self.base.BOS_ID

    @property
    def EOS_ID(self) -> int:  # noqa: N802
        return self.base.EOS_ID

    def metadata(self) -> dict[str, Any]:
        base_meta = self.base.metadata()
        return {
            **base_meta,
            "extension_type": "english_bpe",
            "vocab_version": self.artifact.vocab_version,
            "trained_from_corpus_hash": self.artifact.trained_from_corpus_hash,
            "trained_at_timestamp": self.artifact.trained_at_timestamp,
            "bpe_merge_count": self.artifact.bpe_merge_count,
            "english_vocab_size": self.artifact.english_vocab_size,
            "cas_reserved_token_count": self._n_cas,
            "extended_vocab_size": self.vocab_size,
        }

    # ------------------------------------------------------------------
    # Tokenize / encode / decode
    # ------------------------------------------------------------------

    def tokenize(self, text: str) -> list[str]:
        """Return a list of pieces (CAS reserved tokens + BPE pieces).

        Pieces are mixed strings: CAS reserved tokens use their original
        string form; BPE pieces use either printable ASCII or ``<0xNN>``
        markers for non-ASCII bytes (and merged forms thereof).
        """
        tokens: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == " ":
                tokens.append("[SP]")
                i += 1
                continue
            if ch == "\n":
                tokens.append("[NL]")
                i += 1
                continue
            if ch == "\t":
                tokens.append("[TAB]")
                i += 1
                continue
            # CAS dynamic literals first (e.g. ^3, |A, Omega_safe).
            dyn_match = self.base._dynamic_re.match(text, i)  # noqa: SLF001
            if dyn_match is not None:
                raw = dyn_match.group(0)
                if raw in self.base.word2id:
                    tokens.append(raw)
                    i = dyn_match.end()
                    continue
            # Reserved CAS tokens (longest-prefix match).
            reserved = self.base._match_reserved(text, i)  # noqa: SLF001
            if reserved is not None:
                tokens.append(reserved)
                i += len(reserved)
                continue
            # Otherwise, find a contiguous run that is none of the above.
            j = i
            while j < n:
                cj = text[j]
                if cj in (" ", "\n", "\t"):
                    break
                if self.base._match_reserved(text, j) is not None:  # noqa: SLF001
                    break
                if self.base._dynamic_re.match(text, j) is not None:  # noqa: SLF001
                    raw = self.base._dynamic_re.match(text, j).group(0)  # noqa: SLF001
                    if raw in self.base.word2id:
                        break
                j += 1
            run = text[i:j]
            if not run:
                # Defensive: advance one char to avoid infinite loops.
                run = text[i]
                j = i + 1
            tokens.extend(self._bpe_encode_word(run))
            i = j
        return tokens

    def encode(
        self,
        text: str,
        max_length: int = 512,
        *,
        add_special: bool = True,
    ) -> list[int]:
        budget = max_length - 2 if add_special else max_length
        ids: list[int] = [self.base.BOS_ID] if add_special else []
        for tok in self.tokenize(text):
            if len(ids) >= budget + (1 if add_special else 0):
                break
            ids.append(self._id_for_token(tok))
        if add_special:
            ids.append(self.base.EOS_ID)
        return ids[:max_length]

    def decode(self, ids: Iterable[int], *, skip_special: bool = True) -> str:
        out_pieces: list[str] = []
        byte_buffer: list[int] = []

        def _flush_bytes() -> None:
            nonlocal byte_buffer
            if not byte_buffer:
                return
            try:
                out_pieces.append(bytes(byte_buffer).decode("utf-8", errors="replace"))
            finally:
                byte_buffer = []

        for raw_id in ids:
            idx = int(raw_id)
            tok = self._composed_id_to_token.get(idx)
            if tok is None:
                _flush_bytes()
                if not skip_special:
                    out_pieces.append("[UNK]")
                continue
            if tok in ("[PAD]", "[BOS]", "[EOS]"):
                _flush_bytes()
                if not skip_special:
                    out_pieces.append(tok)
                continue
            if tok == "[UNK]":
                _flush_bytes()
                if not skip_special:
                    out_pieces.append(tok)
                continue
            if tok == "[SP]":
                _flush_bytes()
                out_pieces.append(" ")
                continue
            if tok == "[NL]":
                _flush_bytes()
                out_pieces.append("\n")
                continue
            if tok == "[TAB]":
                _flush_bytes()
                out_pieces.append("\t")
                continue
            # English BPE piece? Decompose into bytes.
            if idx >= self._n_cas:
                # Walk the merge structure: for an English piece, walk back
                # through merges until it's a sequence of byte-tokens.
                for byte_tok in self._piece_to_byte_tokens(tok):
                    if byte_tok in self._byte_token_to_byte:
                        byte_buffer.append(self._byte_token_to_byte[byte_tok])
                continue
            # Otherwise it's a CAS reserved token — emit its surface form,
            # using base-tokenizer's char-token mapping when applicable.
            _flush_bytes()
            char_form = _maybe_char_token(tok)
            if char_form is not None:
                out_pieces.append(char_form)
            else:
                out_pieces.append(tok)
        _flush_bytes()
        return "".join(out_pieces)

    def token_ids_to_tokens(self, ids: Iterable[int]) -> list[str]:
        return [
            self._composed_id_to_token.get(int(i), "[UNK]")
            for i in ids
        ]

    def pad_id(self) -> int:
        return self.base.PAD_ID

    def unk_id(self) -> int:
        return self.base.UNK_ID

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _id_for_token(self, token: str) -> int:
        if token in self.base.word2id:
            return self.base.word2id[token]
        if token in self._eng_piece_to_local_id:
            return self._n_cas + self._eng_piece_to_local_id[token]
        return self.base.UNK_ID

    def _bpe_encode_word(self, word: str) -> list[str]:
        """Apply learned merges greedily to a piece of text."""
        if not word:
            return []
        # Convert to byte pieces.
        pieces: list[str] = [self._byte_to_byte_token[b] for b in word.encode("utf-8")]
        if len(pieces) < 2:
            return pieces
        # Iteratively apply the lowest-rank (earliest-learned) applicable
        # merge until none applies. This is the standard byte-pair encoder
        # decoding step.
        while True:
            best_rank: int | None = None
            best_idx: int = -1
            for i in range(len(pieces) - 1):
                rank = self._merge_ranks.get((pieces[i], pieces[i + 1]))
                if rank is not None and (best_rank is None or rank < best_rank):
                    best_rank = rank
                    best_idx = i
            if best_rank is None:
                break
            merged = pieces[best_idx] + pieces[best_idx + 1]
            pieces = pieces[:best_idx] + [merged] + pieces[best_idx + 2 :]
            if len(pieces) < 2:
                break
        return pieces

    def _piece_to_byte_tokens(self, piece: str) -> list[str]:
        """Walk a (possibly merged) piece back to its constituent byte tokens.

        The merge table records the binary tree of pair merges. We invert it
        by finding which merge produced ``piece`` and recursing on its
        components. Byte-token leaves (256 of them) terminate recursion.
        """
        if piece in self._byte_token_to_byte:
            return [piece]
        # Scan merges in order to find the one that produced `piece`.
        for left, right in self.artifact.merges:
            if left + right == piece:
                return self._piece_to_byte_tokens(left) + self._piece_to_byte_tokens(right)
        # Fallback: emit literally; will likely be replaced by the
        # error-replacement char during decode.
        return []


def _maybe_char_token(token: str) -> str | None:
    """If ``token`` is the ``<CHAR:HEX>`` form, return the underlying char."""
    if not (token.startswith("<CHAR:") and token.endswith(">")):
        return None
    try:
        return chr(int(token[6:-1], 16))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Composition + tokenization-with-provenance
# ---------------------------------------------------------------------------

def extend_hybrid_tokenizer(
    base_tokenizer_path: str | Path | HybridCASTokenizer,
    english_vocab_path: str | Path | BPEArtifact,
) -> ExtendedHybridCASTokenizer:
    """Compose a base ``HybridCASTokenizer`` with an English BPE artifact.

    Both arguments accept either filesystem paths or in-memory objects, so
    callers can wire this into a training run without round-tripping through
    disk.
    """
    if isinstance(base_tokenizer_path, HybridCASTokenizer):
        base = base_tokenizer_path
    else:
        base = HybridCASTokenizer.load(Path(base_tokenizer_path))

    if isinstance(english_vocab_path, BPEArtifact):
        artifact = english_vocab_path
    else:
        artifact = load_english_bpe_artifact(Path(english_vocab_path))

    return ExtendedHybridCASTokenizer(base=base, artifact=artifact)


def tokenize_with_provenance(
    text: str,
    tokenizer: ExtendedHybridCASTokenizer | HybridCASTokenizer,
) -> dict[str, Any]:
    """Tokenize ``text`` and stamp the result with vocab provenance.

    Returns a dict with ``tokens`` (list of piece strings), ``ids`` (list of
    integer IDs), ``vocab_version`` (string), and ``encoded_at`` (ISO8601
    UTC timestamp). For base ``HybridCASTokenizer`` callers (no extension)
    the vocab_version is ``"hybrid-cas-v1"``.

    This is the architectural-spine traceability rule: no tokenization
    output ever leaves this module without a vocab version attached.
    """
    if isinstance(tokenizer, ExtendedHybridCASTokenizer):
        tokens = tokenizer.tokenize(text)
        ids = tokenizer.encode(text, max_length=8192, add_special=False)
        vocab_version = tokenizer.vocab_version
    else:
        tokens = tokenizer.tokenize(text)
        ids = tokenizer.encode(text, max_length=8192, add_special=False)
        vocab_version = HybridCASTokenizer.VERSION

    return {
        "tokens": tokens,
        "ids": ids,
        "vocab_version": vocab_version,
        "encoded_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main(argv: Sequence[str] | None = None) -> int:
    """Tiny CLI: ``python -m cas_native.training.english_bpe_extension train --corpus ... --out ...``"""
    import argparse

    parser = argparse.ArgumentParser(description="English BPE extension CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_train = sub.add_parser("train", help="train BPE on a JSONL corpus")
    p_train.add_argument("--corpus", required=True, help="input JSONL path")
    p_train.add_argument("--out", required=True, help="output artifact JSON path")
    p_train.add_argument("--vocab-size", type=int, default=24000)
    p_train.add_argument("--min-frequency", type=int, default=2)
    p_train.add_argument("--max-records", type=int, default=None)
    p_train.add_argument("--vocab-version", default=DEFAULT_VOCAB_VERSION)

    args = parser.parse_args(argv)
    if args.cmd == "train":
        t0 = time.perf_counter()
        artifact = train_english_bpe(
            args.corpus,
            vocab_size=args.vocab_size,
            min_frequency=args.min_frequency,
            output_path=args.out,
            vocab_version=args.vocab_version,
            max_records=args.max_records,
        )
        elapsed = time.perf_counter() - t0
        print(
            f"Trained {artifact['bpe_merge_count']} merges "
            f"(english_vocab_size={artifact['english_vocab_size']}) "
            f"in {elapsed:.1f}s; corpus_hash={artifact['trained_from_corpus_hash'][:12]}"
        )
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())


__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "DEFAULT_VOCAB_VERSION",
    "BPEArtifact",
    "ExtendedHybridCASTokenizer",
    "extend_hybrid_tokenizer",
    "load_english_bpe_artifact",
    "tokenize_with_provenance",
    "train_english_bpe",
]
