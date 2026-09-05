"""Lossless public TEXT features; no model, parser, target, or evaluator.

Lexical units are fitted on training problems/tags only. Case, punctuation and
whitespace are retained exactly. Every unseen unit falls back to its complete
UTF-8 bytes in a fixed vocabulary. Numeric rows deliberately retain the frozen
eight-Python-float representation: text losslessness is NOT numeric tensor
losslessness, nor a claim about what a learned model can recover.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .codec import PolicyContractError, validate_public

SCHEMA = "cas-meta2-lossless-public-tokenizer/2"
PAD_ID, CLS_ID, SEP_ID, OBS_ID, VALUES_ID = range(5)
SPECIAL = ("[PAD]", "[CLS]", "[SEP]", "[OBS]", "[VALUES]")
BYTE_START = len(SPECIAL)
BYTE_VOCABULARY = tuple(f"[BYTE:{value:02x}]" for value in range(256))
FIXED_VOCABULARY = SPECIAL + BYTE_VOCABULARY
WORD_START = len(FIXED_VOCABULARY)
MAX_SEQUENCE_LENGTH = 65536
MAX_LEXICAL_UNITS = 65536
MAX_TRAIN_EXAMPLES = 100000
UNIT_RULE = r"\w+|[^\w\s]|\s+"
NUMERIC_BOUNDARY = "Text round trips exactly; eight-float rows and downstream numeric tensors need separate precision checks."
_UNIT = re.compile(UNIT_RULE, flags=re.UNICODE)
_WORD = re.compile(r"\[WORD:([0-9a-f]+)\]\Z")


def _require(condition, reason):
    if not condition:
        raise PolicyContractError(reason)


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _utf8(text):
    _require(type(text) is str, "LOSSLESS_TEXT_TYPE_INVALID")
    try:
        return text.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise PolicyContractError("LOSSLESS_INVALID_UNICODE") from error


def _units(text):
    _utf8(text)
    return _UNIT.findall(text)


def _word_token(unit):
    return "[WORD:" + _utf8(unit).hex() + "]"


def _word_value(token):
    _require(type(token) is str, "LOSSLESS_VOCABULARY_TOKEN_TYPE_INVALID")
    match = _WORD.fullmatch(token)
    _require(match is not None and len(match[1]) % 2 == 0 and len(match[1]) <= 8192 * 8, "LOSSLESS_WORD_TOKEN_INVALID")
    try:
        value = bytes.fromhex(match[1]).decode("utf-8", errors="strict")
    except (ValueError, UnicodeError) as error:
        raise PolicyContractError("LOSSLESS_WORD_UTF8_INVALID") from error
    _require(_units(value) == [value] and _word_token(value) == token, "LOSSLESS_WORD_UNIT_INVALID")
    return value


def _validated(public):
    try:
        validate_public(public)
    except PolicyContractError:
        raise
    except (TypeError, ValueError, OverflowError) as error:
        raise PolicyContractError("PUBLIC_VALUES_INVALID") from error
    _utf8(public["problem"])
    for observation in public["observations"]:
        _utf8(observation["tag"])
    return public


@dataclass(frozen=True)
class LosslessPublicTokenizer:
    vocabulary: tuple[str, ...]
    fitted_public_sha256: str
    fitted_examples: int
    max_length: int = 1024

    def __post_init__(self):
        _require(type(self.max_length) is int and 16 <= self.max_length <= MAX_SEQUENCE_LENGTH,
                 "LOSSLESS_MAX_LENGTH_INVALID")
        _require(type(self.fitted_examples) is int and 1 <= self.fitted_examples <= MAX_TRAIN_EXAMPLES,
                 "LOSSLESS_FITTED_EXAMPLES_INVALID")
        _require(type(self.fitted_public_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", self.fitted_public_sha256) is not None,
                 "LOSSLESS_FIT_DIGEST_INVALID")
        _require(type(self.vocabulary) is tuple and WORD_START < len(self.vocabulary) <= WORD_START + MAX_LEXICAL_UNITS
                 and all(type(token) is str for token in self.vocabulary)
                 and self.vocabulary[:WORD_START] == FIXED_VOCABULARY, "LOSSLESS_FIXED_VOCABULARY_INVALID")
        units = [_word_value(token) for token in self.vocabulary[WORD_START:]]
        _require(units == sorted(set(units)), "LOSSLESS_LEXICAL_VOCABULARY_NOT_CANONICAL")

    @classmethod
    def fit_train(cls, train_public, max_length=1024):
        _require(type(train_public) is list and 1 <= len(train_public) <= MAX_TRAIN_EXAMPLES,
                 "LOSSLESS_TRAIN_INPUT_INVALID")
        _require(type(max_length) is int and 16 <= max_length <= MAX_SEQUENCE_LENGTH, "LOSSLESS_MAX_LENGTH_INVALID")
        units = set()
        for public in train_public:
            _validated(public)
            units.update(_units(public["problem"]))
            for observation in public["observations"]:
                units.update(_units(observation["tag"]))
            _require(len(units) <= MAX_LEXICAL_UNITS, "LOSSLESS_VOCABULARY_CEILING")
        tokenizer = cls(FIXED_VOCABULARY + tuple(_word_token(unit) for unit in sorted(units)),
                        _hash(train_public), len(train_public), max_length)
        for public in train_public:
            tokenizer.encode_public(public)  # No training sequence may silently truncate.
        return tokenizer

    def _text_ids(self, text):
        lookup = {_word_value(token): index for index, token in enumerate(self.vocabulary[WORD_START:], WORD_START)}
        for unit in _units(text):
            if unit in lookup:
                yield lookup[unit]
            else:
                yield from (BYTE_START + byte for byte in _utf8(unit))

    def encode_public(self, public):
        public = _validated(public)
        encoded = {"ids": [], "kinds": [], "slots": [], "values": []}
        def add(token_id, kind, slot, values=None):
            _require(len(encoded["ids"]) < self.max_length, "PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION")
            encoded["ids"].append(token_id)
            encoded["kinds"].append(kind)
            encoded["slots"].append(slot)
            encoded["values"].append([0.0] * 8 if values is None else [float(value) for value in values])
        add(CLS_ID, 0, 0)
        for token_id in self._text_ids(public["problem"]):
            add(token_id, 0, 0)
        add(SEP_ID, 1, 0)
        for observation in sorted(public["observations"], key=lambda item: item["slot"]):
            slot = observation["slot"] + 1
            add(OBS_ID, 2, slot)
            for token_id in self._text_ids(observation["tag"]):
                add(token_id, 2, slot)
            add(VALUES_ID, 3, slot, observation["values"])
        return encoded

    def decode_text(self, ids):
        """Decode unpadded TEXT IDs only; reject special markers and invalid UTF-8."""
        _require(type(ids) in (list, tuple) and len(ids) <= self.max_length, "LOSSLESS_TEXT_IDS_INVALID")
        pieces, pending = [], bytearray()
        def flush():
            if pending:
                try:
                    pieces.append(pending.decode("utf-8", errors="strict"))
                except UnicodeError as error:
                    raise PolicyContractError("LOSSLESS_BYTE_SEQUENCE_INVALID_UTF8") from error
                pending.clear()
        for token_id in ids:
            _require(type(token_id) is int and BYTE_START <= token_id < len(self.vocabulary), "LOSSLESS_TEXT_TOKEN_ID_INVALID")
            if token_id < WORD_START:
                pending.append(token_id - BYTE_START)
            else:
                flush()
                pieces.append(_word_value(self.vocabulary[token_id]))
        flush()
        return "".join(pieces)

    def decode_public_text(self, encoded):
        """Recover exact problem/tag text; numeric rows are checked, not reversed."""
        _require(type(encoded) is dict and set(encoded) == {"ids", "kinds", "slots", "values"}, "LOSSLESS_ENCODED_FIELDS_INVALID")
        _require(all(type(encoded[name]) is list for name in encoded), "LOSSLESS_ENCODED_ROWS_INVALID")
        length = len(encoded["ids"])
        _require(0 < length <= self.max_length and all(len(rows) == length for rows in encoded.values()), "LOSSLESS_ENCODED_LENGTH_INVALID")
        for token_id, kind, slot, values in zip(encoded["ids"], encoded["kinds"], encoded["slots"], encoded["values"]):
            _require(type(token_id) is int and 0 <= token_id < len(self.vocabulary)
                     and type(kind) is int and 0 <= kind <= 3 and type(slot) is int and 0 <= slot <= 3,
                     "LOSSLESS_ENCODED_ROW_ID_INVALID")
            try:
                valid_values = type(values) is list and len(values) == 8 and all(
                    type(value) in (int, float) and math.isfinite(value) for value in values)
            except OverflowError:
                valid_values = False
            _require(valid_values, "LOSSLESS_ENCODED_VALUES_INVALID")
            _require(kind == 3 or values == [0.0] * 8, "LOSSLESS_NONTENSOR_ROW_VALUES_INVALID")
        cursor = 0
        def marker(token_id, kind, slot):
            nonlocal cursor
            _require(cursor < length and encoded["ids"][cursor] == token_id
                     and encoded["kinds"][cursor] == kind and encoded["slots"][cursor] == slot,
                     "LOSSLESS_PUBLIC_MARKER_INVALID")
            cursor += 1
        def text_until(end_id, kind, slot):
            nonlocal cursor
            result = []
            while cursor < length and encoded["ids"][cursor] != end_id:
                _require(encoded["kinds"][cursor] == kind and encoded["slots"][cursor] == slot, "LOSSLESS_PUBLIC_TEXT_SCOPE_INVALID")
                result.append(encoded["ids"][cursor]);cursor += 1
            return self.decode_text(result)
        marker(CLS_ID, 0, 0)
        problem = text_until(SEP_ID, 0, 0)
        marker(SEP_ID, 1, 0)
        observations = []
        for slot in range(1, 4):
            marker(OBS_ID, 2, slot)
            tag = text_until(VALUES_ID, 2, slot)
            _require(cursor < length, "LOSSLESS_PUBLIC_MARKER_INVALID")
            values = encoded["values"][cursor]
            marker(VALUES_ID, 3, slot)
            observations.append({"slot": slot - 1, "tag": tag, "values": values})
        _require(cursor == length, "LOSSLESS_PUBLIC_TRAILING_DATA")
        _validated({"problem": problem, "observations": observations})
        return {"problem": problem, "observations": [{"slot": row["slot"], "tag": row["tag"]} for row in observations]}

    def check_round_trip(self, public):
        public = _validated(public)
        expected = {"problem": public["problem"], "observations": [
            {"slot": row["slot"], "tag": row["tag"]} for row in sorted(public["observations"], key=lambda row: row["slot"])]}
        _require(self.decode_public_text(self.encode_public(public)) == expected, "LOSSLESS_TEXT_ROUND_TRIP_FAILED")
        return True

    def to_dict(self):
        return {"schema": SCHEMA, "fit_split": "train_only", "text_unit_rule": UNIT_RULE,
                "byte_fallback": "UTF8_FIXED_256_NO_UNK", "numeric_boundary": NUMERIC_BOUNDARY,
                "vocabulary": list(self.vocabulary), "fitted_public_sha256": self.fitted_public_sha256,
                "fitted_examples": self.fitted_examples, "max_length": self.max_length}

    @classmethod
    def from_dict(cls, value):
        expected = {"schema", "fit_split", "text_unit_rule", "byte_fallback", "numeric_boundary", "vocabulary",
                    "fitted_public_sha256", "fitted_examples", "max_length"}
        _require(type(value) is dict and set(value) == expected, "LOSSLESS_SERIALIZED_FIELDS_INVALID")
        _require(value["schema"] == SCHEMA and value["fit_split"] == "train_only" and value["text_unit_rule"] == UNIT_RULE
                 and value["byte_fallback"] == "UTF8_FIXED_256_NO_UNK" and value["numeric_boundary"] == NUMERIC_BOUNDARY,
                 "LOSSLESS_SERIALIZED_CONTRACT_INVALID")
        _require(type(value["vocabulary"]) is list, "LOSSLESS_SERIALIZED_VOCABULARY_INVALID")
        return cls(tuple(value["vocabulary"]), value["fitted_public_sha256"], value["fitted_examples"], value["max_length"])

    @property
    def digest(self):
        return _hash(self.to_dict())
