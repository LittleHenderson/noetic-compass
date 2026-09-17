"""Versioned lossless frame-text tokens, with no numerical encoder or learner.

Only the explicit caller-supplied training frames fit the lexical vocabulary.
Caller/runner custody establishes that these frames belong to training; the
generic fitter cannot authenticate that assertion or admit a study.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
import re
from pathlib import Path

from . import input_frames, source

SCHEMA = "cas.typed-frame-text-tokenizer/0.1"
SEQUENCE_SCHEMA = "cas.typed-frame-token-sequence/0.1"
ALGORITHM = "unicode-lexical-units-with-exact-utf8-byte-fallback/1"
UNIT_RULE = r"\w+|[^\w\s]|\s+"
_UNIT = re.compile(UNIT_RULE, flags=re.UNICODE)
HEX = re.compile(r"[0-9a-f]{64}\Z")
START, END, BYTE_START = 0, 1, 2
WORD_START = BYTE_START + 256
FIXED = ("[FRAME]", "[END]") + tuple("[BYTE:%02x]" % b for b in range(256))
HARD_MAX_TOKENS = 262144
MAX_FIT_FRAMES = 4096
MAX_UNITS = 65536
MAX_UNIT_BYTES = 65536
_FIELDS = {"schema", "algorithm", "unit_rule", "vocabulary", "training_frame_digests",
           "max_tokens", "source_profile", "fit_scope", "numeric_compatibility"}

def _require(value, message):
    source.require(value, message)

def _text(value):
    _require(type(value) is str and bool(value), "TYPED_TOKEN_TEXT")
    try:
        raw = value.encode("utf-8")
    except UnicodeError as error:
        raise ValueError("TYPED_TOKEN_UTF8") from error
    return raw

def _units(text):
    _text(text)
    return _UNIT.findall(text)

def _word(unit):
    raw = _text(unit)
    _require(len(raw) <= MAX_UNIT_BYTES and _units(unit) == [unit], "TYPED_TOKEN_UNIT_BOUND")
    return "[UNIT:" + raw.hex() + "]"

def _unword(token):
    _require(type(token) is str and token.startswith("[UNIT:") and token.endswith("]"),
             "TYPED_TOKEN_WORD")
    body = token[6:-1]
    _require(0 < len(body) <= MAX_UNIT_BYTES * 2 and len(body) % 2 == 0
             and re.fullmatch("[0-9a-f]+", body), "TYPED_TOKEN_WORD_HEX")
    try:
        unit = bytes.fromhex(body).decode("utf-8")
    except (ValueError, UnicodeError) as error:
        raise ValueError("TYPED_TOKEN_WORD_UTF8") from error
    _require(_word(unit) == token, "TYPED_TOKEN_WORD_CANONICAL")
    return unit

def profile():
    raw = Path(__file__).read_bytes()
    body = {"schema": "cas.typed-frame-tokenizer-source/0.1",
            "algorithm": ALGORITHM, "unit_rule": UNIT_RULE,
            "file": {"path": "cas_meta2/typed_teaching/tokenization.py",
                     "bytes": len(raw), "sha256": sha256(raw).hexdigest()},
            "frame_profile": input_frames.profile(),
            "numeric_encoder_compatibility": False}
    return {**body, "profile_digest": source.digest(body)}

def _frame(frame):
    input_frames.validate_frame(frame)
    _text(frame["text"])
    return source.digest(frame)

def training_token_count(frame):
    """Exact count under a vocabulary that includes this training text."""
    _frame(frame)
    return len(_units(frame["text"])) + 2

@dataclass(frozen=True)
class FrameTokenizer:
    vocabulary: tuple[str, ...]
    training_frame_digests: tuple[str, ...]
    max_tokens: int
    source_profile: dict

    def __post_init__(self):
        _require(type(self.max_tokens) is int and 2 <= self.max_tokens <= HARD_MAX_TOKENS,
                 "TYPED_TOKEN_CAP")
        _require(type(self.vocabulary) is tuple
                 and WORD_START < len(self.vocabulary) <= WORD_START + MAX_UNITS
                 and self.vocabulary[:WORD_START] == FIXED, "TYPED_TOKEN_FIXED_VOCABULARY")
        units = [_unword(token) for token in self.vocabulary[WORD_START:]]
        _require(units == sorted(set(units)), "TYPED_TOKEN_CANONICAL_VOCABULARY")
        values = self.training_frame_digests
        _require(type(values) is tuple and 1 <= len(values) <= MAX_FIT_FRAMES
                 and all(type(v) is str and HEX.fullmatch(v) for v in values)
                 and list(values) == sorted(set(values)), "TYPED_TOKEN_FIT_IDENTITIES")
        source._bounded(self.source_profile)
        _require(source.canonical(self.source_profile) == source.canonical(profile()),
                 "TYPED_TOKEN_SOURCE_PROFILE")
        object.__setattr__(self, "source_profile", deepcopy(self.source_profile))

    def to_dict(self):
        # Roundtrip construction below verifies untrusted serialized metadata.
        source._bounded(self.source_profile)
        _require(source.canonical(self.source_profile) == source.canonical(profile()),
                 "TYPED_TOKEN_SOURCE_PROFILE")
        return {"schema": SCHEMA, "algorithm": ALGORITHM, "unit_rule": UNIT_RULE,
                "vocabulary": list(self.vocabulary),
                "training_frame_digests": list(self.training_frame_digests),
                "max_tokens": self.max_tokens, "source_profile": deepcopy(self.source_profile),
                "fit_scope": "CALLER_SUPPLIED_TRAINING_FRAMES_NO_FINAL_INPUTS_BY_RUNNER_CUSTODY",
                "numeric_compatibility": False}

    @classmethod
    def from_dict(cls, value):
        _require(type(value) is dict and set(value) == _FIELDS, "TYPED_TOKEN_FIELDS")
        _require(value["schema"] == SCHEMA and value["algorithm"] == ALGORITHM
                 and value["unit_rule"] == UNIT_RULE
                 and value["fit_scope"] == "CALLER_SUPPLIED_TRAINING_FRAMES_NO_FINAL_INPUTS_BY_RUNNER_CUSTODY"
                 and value["numeric_compatibility"] is False, "TYPED_TOKEN_CONTRACT")
        _require(type(value["vocabulary"]) is list
                 and type(value["training_frame_digests"]) is list, "TYPED_TOKEN_LISTS")
        return cls(tuple(value["vocabulary"]), tuple(value["training_frame_digests"]),
                   value["max_tokens"], deepcopy(value["source_profile"]))

    @property
    def digest(self):
        return source.digest(self.to_dict())

    def encode_text(self, text):
        """Return text IDs only; no truncation and no unknown replacement."""
        lookup = {_unword(t): i for i, t in enumerate(self.vocabulary[WORD_START:], WORD_START)}
        result = []
        for unit in _units(text):
            result.extend([lookup[unit]] if unit in lookup else
                          (BYTE_START + b for b in _text(unit)))
            _require(len(result) + 2 <= self.max_tokens, "TYPED_TOKEN_OVERFLOW_NO_TRUNCATION")
        return result

    def decode_text(self, ids):
        _require(type(ids) in (list, tuple) and len(ids) + 2 <= self.max_tokens,
                 "TYPED_TOKEN_ID_BOUND")
        parts, pending = [], bytearray()
        def flush():
            if pending:
                try:
                    parts.append(pending.decode("utf-8"))
                except UnicodeError as error:
                    raise ValueError("TYPED_TOKEN_INVALID_BYTE_SEQUENCE") from error
                pending.clear()
        for value in ids:
            _require(type(value) is int and BYTE_START <= value < len(self.vocabulary),
                     "TYPED_TOKEN_ID")
            if value < WORD_START:
                pending.append(value - BYTE_START)
            else:
                flush()
                parts.append(_unword(self.vocabulary[value]))
        flush()
        return "".join(parts)

    def encode_frame(self, frame):
        frame_digest = _frame(frame)
        ids = [START, *self.encode_text(frame["text"]), END]
        body = {"schema": SEQUENCE_SCHEMA, "frame_digest": frame_digest,
                "tokenizer_digest": self.digest, "ids": ids}
        return {**body, "sequence_digest": source.digest(body)}

    def validate_sequence(self, frame, value):
        _require(type(value) is dict and set(value) ==
                 {"schema", "frame_digest", "tokenizer_digest", "ids", "sequence_digest"},
                 "TYPED_TOKEN_SEQUENCE_FIELDS")
        _require(type(value["ids"]) is list
                 and all(type(token) is int for token in value["ids"]),
                 "TYPED_TOKEN_SEQUENCE_IDS")
        _require(source.canonical(value) == source.canonical(self.encode_frame(frame)),
                 "TYPED_TOKEN_SEQUENCE_BINDING")
        _require(self.decode_text(value["ids"][1:-1]) == frame["text"],
                 "TYPED_TOKEN_ROUNDTRIP")
        return True

def fit_train(frames, *, max_tokens):
    _require(type(frames) is list and 1 <= len(frames) <= MAX_FIT_FRAMES, "TYPED_TOKEN_FIT_LIST")
    units, identities = set(), []
    for frame in frames:
        identities.append(_frame(frame))
        units.update(_units(frame["text"]))
        _require(len(units) <= MAX_UNITS, "TYPED_TOKEN_UNIT_CEILING")
    _require(len(set(identities)) == len(identities), "TYPED_TOKEN_DUPLICATE_FIT_FRAME")
    result = FrameTokenizer(FIXED + tuple(_word(unit) for unit in sorted(units)),
                            tuple(sorted(identities)), max_tokens, profile())
    for frame in frames:
        encoded = result.encode_frame(frame)
        _require(result.decode_text(encoded["ids"][1:-1]) == frame["text"],
                 "TYPED_TOKEN_FIT_ROUNDTRIP")
    return result
