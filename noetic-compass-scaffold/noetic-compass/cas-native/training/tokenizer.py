"""CAS-aware tokenizer for CAS-Native training and inference.

The original whitespace tokenizer was acceptable for smoke tests, but it
destroyed CAS structure: it lowercased register/domain symbols, treated whole
expressions as sparse words, and let model output IDs drift outside the learned
vocabulary. This tokenizer keeps CAS symbols exact, freezes vocabulary before
training, and persists the token-ID contract for inference.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


SPECIAL_TOKENS = [
    "[PAD]",
    "[UNK]",
    "[BOS]",
    "[EOS]",
    "[SEP]",
    "[CAS]",
    "[/CAS]",
    "[TASK_EXPR]",
    "[TASK_EXPLAIN]",
    "[TASK_CHAT]",
    "[PROMPT]",
    "[RESPONSE]",
    "[SP]",
    "[NL]",
    "[TAB]",
]


CAS_RESERVED_TOKENS = [
    # Core state pieces.
    *[f"^{i}" for i in range(10)],
    "^P",
    "^C",
    "^E",
    "^O",
    *[f"F{i}" for i in range(1, 8)],
    *[f"F_{i}" for i in range(1, 8)],
    "|T",
    "|A",
    "|f",
    "|E",
    # Operators and delimiters.
    "^",
    "_",
    "_{",
    "}",
    "{",
    "(",
    ")",
    "[",
    "]",
    "<",
    ">",
    "⟨",
    "⟩",
    ",",
    ":",
    ";",
    "=",
    "+",
    "-",
    "*",
    "·",
    "/",
    "÷",
    "×",
    "∘",
    "|",
    "->",
    "→",
    "<-",
    "←",
    "<->",
    "↔",
    "∈",
    "∉",
    "⊂",
    "⊆",
    "⊃",
    "⊇",
    "∪",
    "∩",
    "∖",
    "∅",
    # Builtins, carriers, and constructors.
    "CO-",
    *[f"CO-{i}" for i in range(10)],
    "RPM",
    "Phi",
    "Φ",
    "Noetics",
    "Domains",
    "Worlds",
    "Drives",
    "Registers",
    "States",
    "Foundations",
    "SubFoundations",
    "DriveRegisterPositions",
    "SubFoundationPositions",
    *[f"Foundation_{i}" for i in range(1, 8)],
    "Set",
    "MetaSet",
    "NoeticSet",
    "NoeticCluster",
    "Cluster",
    "StateSet",
    "StateCluster",
    "StateVariantSet",
    "StateVariantCluster",
    "RelationSet",
    "RelationCluster",
    "DriveSet",
    "DomainSet",
    "RegisterSet",
    "FoundationSet",
    "SubFoundationSet",
    "Tuple",
    "Coordinate",
    "CASTuple",
    "CASCoordinate",
    "Pullback",
    "Product",
    "Union",
    "Intersection",
    "Difference",
    "CoverOf",
    "PartitionOf",
    "union",
    "intersect",
    "intersection",
    "setminus",
    "difference",
    "diff",
    # Production semantics and named emergents.
    "Theta",
    "Θ",
    "Omega",
    "Ω",
    "Ω_",
    "Omega_",
    "Lambda",
    "Λ",
    "kappa",
    "κ",
    "iota",
    "ι",
    "eta",
    "η",
    "Y_T",
    "Y_A",
    "S",
    "Ω_presence",
    "Ω_refusal",
    "Ω_grounding",
    "Ω_alignment",
    "Ω_clarity",
    "Ω_resolve",
    "Ω_witness",
    "Ω_attunement",
    "Ω_genesis",
    "Ω_cadence",
    "Ω_invocation",
    "Ω_landing",
    "Omega_presence",
    "Omega_refusal",
    "Omega_grounding",
    "Omega_alignment",
    "Omega_clarity",
    "Omega_resolve",
    "Omega_witness",
    "Omega_attunement",
    "Omega_genesis",
    "Omega_cadence",
    "Omega_invocation",
    "Omega_landing",
    # DSL/type labels seen by the compiler and meta-logic layer.
    "export",
    "let",
    "fn",
    "use",
    "state",
    "drive",
    "string",
    "void",
    "function",
    "fractal",
    "rpm",
    "relation",
    "program",
    "number",
    "tuple",
    "meta_set",
    "meta_symbol",
    "meta_assertion",
    "any",
]


_DYNAMIC_CAS_PATTERNS = [
    r"Omega_[A-Za-z][A-Za-z0-9_]*",
    r"Ω_[A-Za-z][A-Za-z0-9_]*",
    r"Foundation_\d+",
    r"CO-\d+",
    r"Y_[TA]",
    r"F_?\d+",
    r"\^\d+",
    r"\^[PCEO]",
    r"\|[TAfE]",
]


def _char_token(ch: str) -> str:
    return f"<CHAR:{ord(ch):04X}>"


def _char_from_token(token: str) -> str | None:
    if not (token.startswith("<CHAR:") and token.endswith(">")):
        return None
    try:
        return chr(int(token[6:-1], 16))
    except ValueError:
        return None


def _record_text(record: dict[str, Any]) -> str:
    prompt = record.get("prompt") or record.get("user_prompt") or record.get("text") or ""
    response = record.get("response") or record.get("assistant_response") or record.get("output") or ""
    expr = record.get("cas_expression") or ""
    parts = [str(p) for p in (prompt, response, expr) if p is not None and str(p)]
    return " [SEP] ".join(parts)


class HybridCASTokenizer:
    """Frozen CAS-aware tokenizer with reversible character fallback."""

    PAD_ID = 0
    UNK_ID = 1
    BOS_ID = 2
    EOS_ID = 3

    VERSION = "hybrid-cas-v1"

    def __init__(
        self,
        *,
        token_to_id: dict[str, int] | None = None,
        frozen: bool = False,
    ):
        self.word2id: dict[str, int] = {}
        self.id2word: dict[int, str] = {}
        self.frozen = False

        if token_to_id is None:
            for token in SPECIAL_TOKENS:
                self._add_token(token)
            for token in CAS_RESERVED_TOKENS:
                self._add_token(token)
            self._add_default_char_tokens()
        else:
            for token, idx in sorted(token_to_id.items(), key=lambda kv: kv[1]):
                self.word2id[token] = int(idx)
                self.id2word[int(idx)] = token

        self.frozen = frozen
        self._reserved_sorted = sorted(
            (t for t in self.word2id if not t.startswith("<CHAR:")),
            key=len,
            reverse=True,
        )
        self._dynamic_re = re.compile("|".join(f"(?:{p})" for p in _DYNAMIC_CAS_PATTERNS))

    @property
    def vocab_size(self) -> int:
        return len(self.word2id)

    def __len__(self) -> int:
        return self.vocab_size

    @classmethod
    def from_records(
        cls,
        records: Iterable[dict[str, Any]],
        *,
        max_records: int | None = None,
        freeze: bool = True,
    ) -> "HybridCASTokenizer":
        tokenizer = cls()
        for i, record in enumerate(records):
            if max_records is not None and i >= max_records:
                break
            tokenizer.fit_text(_record_text(record))
        if freeze:
            tokenizer.freeze()
        return tokenizer

    @classmethod
    def from_texts(cls, texts: Iterable[str], *, freeze: bool = True) -> "HybridCASTokenizer":
        tokenizer = cls()
        for text in texts:
            tokenizer.fit_text(text)
        if freeze:
            tokenizer.freeze()
        return tokenizer

    @classmethod
    def load(cls, path: str | Path) -> "HybridCASTokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("version") != cls.VERSION:
            raise ValueError(f"Unsupported tokenizer version: {payload.get('version')!r}")
        return cls(token_to_id=dict(payload["token_to_id"]), frozen=bool(payload.get("frozen", True)))

    def save(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "frozen": self.frozen,
            "token_to_id": dict(sorted(self.word2id.items(), key=lambda kv: kv[1])),
            "metadata": self.metadata(),
        }

    def metadata(self) -> dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "version": self.VERSION,
            "vocab_size": self.vocab_size,
            "hash": self.vocab_hash(),
            "frozen": self.frozen,
            "special_tokens": list(SPECIAL_TOKENS),
            "reserved_token_count": len(CAS_RESERVED_TOKENS),
        }

    def vocab_hash(self) -> str:
        raw = json.dumps(dict(sorted(self.word2id.items(), key=lambda kv: kv[1])), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def freeze(self) -> None:
        self.frozen = True

    def fit_text(self, text: str) -> None:
        for token in self.tokenize(text):
            self._id_for_token(token)

    def encode(self, text: str, max_length: int = 512, *, add_special: bool = True) -> list[int]:
        budget = max_length - 2 if add_special else max_length
        ids: list[int] = [self.BOS_ID] if add_special else []
        for token in self.tokenize(text):
            if len(ids) >= budget + (1 if add_special else 0):
                break
            ids.append(self._id_for_token(token))
        if add_special:
            ids.append(self.EOS_ID)
        return ids[:max_length]

    def decode(self, ids: Iterable[int], *, skip_special: bool = True) -> str:
        out: list[str] = []
        for raw_id in ids:
            token = self.id2word.get(int(raw_id), "[UNK]")
            if token in ("[PAD]", "[BOS]", "[EOS]"):
                if skip_special:
                    continue
            if token == "[UNK]":
                if skip_special:
                    continue
            if token == "[SP]":
                out.append(" ")
                continue
            if token == "[NL]":
                out.append("\n")
                continue
            if token == "[TAB]":
                out.append("\t")
                continue
            ch = _char_from_token(token)
            out.append(ch if ch is not None else token)
        return "".join(out)

    def token_ids_to_tokens(self, ids: Iterable[int]) -> list[str]:
        return [self.id2word.get(int(i), "[UNK]") for i in ids]

    def disallowed_generation_ids(self) -> set[int]:
        return {
            self.PAD_ID,
            self.UNK_ID,
            self.BOS_ID,
            self.word2id.get("[PROMPT]", -1),
            self.word2id.get("[RESPONSE]", -1),
            self.word2id.get("[TASK_EXPR]", -1),
            self.word2id.get("[TASK_EXPLAIN]", -1),
            self.word2id.get("[TASK_CHAT]", -1),
        } - {-1}

    def pad_id(self) -> int:
        return self.PAD_ID

    def unk_id(self) -> int:
        return self.UNK_ID

    def unk_rate(self, texts: Iterable[str]) -> float:
        total = 0
        unk = 0
        for text in texts:
            ids = self.encode(text, add_special=False)
            total += len(ids)
            unk += sum(1 for i in ids if i == self.UNK_ID)
        return unk / max(total, 1)

    def tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        i = 0
        while i < len(text):
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

            dynamic = self._dynamic_re.match(text, i)
            if dynamic is not None:
                raw = dynamic.group(0)
                if self.frozen and raw not in self.word2id:
                    tokens.extend(_char_token(c) for c in raw)
                else:
                    tokens.append(raw)
                i = dynamic.end()
                continue

            reserved = self._match_reserved(text, i)
            if reserved is not None:
                tokens.append(reserved)
                i += len(reserved)
                continue

            word = re.match(r"[A-Za-z0-9_]+", text[i:])
            if word is not None:
                raw = word.group(0)
                if self.frozen and raw not in self.word2id:
                    tokens.extend(_char_token(c) for c in raw)
                else:
                    tokens.append(raw)
                i += len(raw)
                continue

            char_tok = _char_token(ch)
            if char_tok in self.word2id or not self.frozen:
                tokens.append(char_tok)
            else:
                tokens.append("[UNK]")
            i += 1
        return tokens

    def _match_reserved(self, text: str, offset: int) -> str | None:
        for token in self._reserved_sorted:
            if text.startswith(token, offset):
                return token
        return None

    def _id_for_token(self, token: str) -> int:
        if token in self.word2id:
            return self.word2id[token]
        if self.frozen:
            # Frozen tokenizers must not mutate during Dataset.__getitem__.
            if len(token) > 1 and not token.startswith("<CHAR:"):
                return self.UNK_ID
            return self.word2id.get(_char_token(token), self.UNK_ID)
        return self._add_token(token)

    def _add_token(self, token: str) -> int:
        if token in self.word2id:
            return self.word2id[token]
        idx = len(self.word2id)
        self.word2id[token] = idx
        self.id2word[idx] = token
        return idx

    def _add_default_char_tokens(self) -> None:
        for code in range(32, 127):
            self._add_token(_char_token(chr(code)))
        for ch in "ΘΩΛκιηΦ→←↔×·∘∈∉⊂⊆⊃⊇∪∩∖∅⟨⟩":
            self._add_token(_char_token(ch))


class SimpleTokenizer:
    """Legacy-compatible whitespace tokenizer.

    Kept for older unit tests and call sites that intentionally construct a
    tiny-vocab model. New training runs use :class:`HybridCASTokenizer` via
    ``create_data_loaders`` / ``run_pipeline``.
    """

    PAD_ID = 0
    UNK_ID = 1
    BOS_ID = 2
    EOS_ID = 3

    def __init__(self, vocab_size: int = 32000):
        self.vocab_size = vocab_size
        self.word2id: dict[str, int] = {
            "[PAD]": self.PAD_ID,
            "[UNK]": self.UNK_ID,
            "[BOS]": self.BOS_ID,
            "[EOS]": self.EOS_ID,
        }
        self.id2word: dict[int, str] = {v: k for k, v in self.word2id.items()}
        self._next_id = 4

    def _get_or_add(self, word: str) -> int:
        if word not in self.word2id:
            if self._next_id < self.vocab_size:
                self.word2id[word] = self._next_id
                self.id2word[self._next_id] = word
                self._next_id += 1
            else:
                return self.UNK_ID
        return self.word2id[word]

    def encode(self, text: str, max_length: int = 512) -> list[int]:
        words = text.lower().split()
        ids = [self.BOS_ID]
        for w in words[: max_length - 2]:
            ids.append(self._get_or_add(w))
        ids.append(self.EOS_ID)
        return ids

    def decode(self, ids: Iterable[int], *, skip_special: bool = True) -> str:
        special = {self.PAD_ID, self.BOS_ID, self.EOS_ID}
        return " ".join(
            self.id2word.get(int(i), "[UNK]")
            for i in ids
            if not (skip_special and int(i) in special)
        )

    def pad_id(self) -> int:
        return self.PAD_ID


TokenizerLike = SimpleTokenizer | HybridCASTokenizer


def build_tokenizer_from_records(records: Iterable[dict[str, Any]]) -> HybridCASTokenizer:
    return HybridCASTokenizer.from_records(records, freeze=True)


def tokenizer_from_loader(loader: Any) -> TokenizerLike | None:
    """Recover the underlying dataset tokenizer from a DataLoader/Subsets."""
    dataset = getattr(loader, "dataset", None)
    while dataset is not None:
        tokenizer = getattr(dataset, "tokenizer", None)
        if tokenizer is not None:
            return tokenizer
        dataset = getattr(dataset, "dataset", None)
    return None


__all__ = [
    "CAS_RESERVED_TOKENS",
    "HybridCASTokenizer",
    "SimpleTokenizer",
    "TokenizerLike",
    "build_tokenizer_from_records",
    "tokenizer_from_loader",
]
