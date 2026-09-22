"""Bounded learner inputs and R0 control; no compiler, reference, or evaluator.

Byte IDs preserve arbitrary CAS text without claiming to parse it. R0 sums
fixed one-hot byte rows, then retrieves a TRAINING label by nearest neighbor.
It is a diagnostic retrieval baseline, never a learned-operation result.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

SCHEMA = "helm-cas-expression-lab.q4-input/0.1"
MAX_INPUT_BYTES = 2048
MAX_R0_EXAMPLES = 2048


class Q4InputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SequenceInput:
    """Only input bytes, in order. 0 is reserved for neural batch padding."""
    byte_ids: tuple[int, ...]

    def __post_init__(self):
        if (type(self.byte_ids) is not tuple or not 1 <= len(self.byte_ids) <= MAX_INPUT_BYTES
                or any(type(x) is not int or not 1 <= x <= 256 for x in self.byte_ids)):
            raise Q4InputError("INVALID_INPUT: bounded, nonempty byte IDs required")


def encode_observation(observation: str) -> SequenceInput:
    if type(observation) is not str:
        raise Q4InputError("INVALID_INPUT: reconstruction observation must be text")
    try:
        body = observation.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise Q4InputError("INVALID_INPUT: observation is not valid Unicode") from error
    return SequenceInput(tuple(byte + 1 for byte in body))


def from_visible_record(row: dict) -> SequenceInput:
    """Accept one validated Q3 R/G visible row; strip identifiers and mode.

The caller uses q3_load.load_visible to verify the source file. This in-memory
adapter also rejects extra/target fields. It is not a replacement file loader.
Operation families A/C need their own typed adapter and are explicitly refused.
"""
    if type(row) is not dict or set(row) != {"record_id", "family", "mode", "observation"}:
        raise Q4InputError("INVALID_INPUT: exact Q3 reconstruction visible fields required")
    if row["family"] not in ("R", "G") or row["mode"] != "reconstruction":
        raise Q4InputError("UNSUPPORTED_OPERATION: this adapter handles R/G reconstruction")
    if type(row["record_id"]) is not str or not row["record_id"]:
        raise Q4InputError("INVALID_INPUT: Q3 record identity missing")
    return encode_observation(row["observation"])


def token_row_sum(observation: SequenceInput) -> tuple[int, ...]:
    """Sum fixed one-hot token rows: exactly order-blind, without hash collisions."""
    if type(observation) is not SequenceInput:
        raise Q4InputError("INVALID_INPUT: SequenceInput required")
    counts = [0] * 256
    for token in observation.byte_ids:
        counts[token - 1] += 1
    return tuple(counts)


@dataclass(frozen=True, slots=True)
class Retrieval:
    label: str
    squared_distance: int
    tied_training_positions: tuple[int, ...]
    mechanism: str = "R0_FIXED_TOKEN_SUM_NEAREST_TRAINING_NEIGHBOR"


class R0NearestNeighbor:
    """Bounded supervised TRAINING memory; fit never reads a data directory.

Exact squared Euclidean distance; earliest training row breaks ties. Report
all ties so same-bag contradictory labels cannot be concealed as unique matches.
The caller must keep dev/eval targets out of fit, as with any supervised learner.
"""
    def __init__(self, examples: Iterable[tuple[SequenceInput, str]]):
        rows = []
        for observation, label in examples:
            if len(rows) >= MAX_R0_EXAMPLES:
                raise Q4InputError("BUDGET_EXHAUSTED: R0 training memory is full")
            if type(label) is not str or not label:
                raise Q4InputError("INVALID_INPUT: bounded training label required")
            try:
                size = len(label.encode("utf-8"))
            except UnicodeEncodeError as error:
                raise Q4InputError("INVALID_INPUT: training label is not valid Unicode") from error
            if size > 32768:
                raise Q4InputError("BUDGET_EXHAUSTED: training label too long")
            rows.append((token_row_sum(observation), label))
        if not rows:
            raise Q4InputError("INVALID_INPUT: R0 needs at least one training example")
        self._rows = tuple(rows)

    def predict(self, observation: SequenceInput) -> Retrieval:
        query = token_row_sum(observation)
        distances = tuple(sum((a - b) ** 2 for a, b in zip(query, counts))
                          for counts, _ in self._rows)
        best = min(distances)
        ties = tuple(i for i, distance in enumerate(distances) if distance == best)
        return Retrieval(self._rows[ties[0]][1], best, ties)


@dataclass(frozen=True, slots=True)
class Bottleneck:
    """Strict decoder boundary: a bounded numeric vector and NOTHING else.

This prevents accidental input/AST fields. It cannot certify that a malicious
model has not encoded a covert channel in floats; that needs Q5 interventions.
"""
    values: tuple[float, ...]

    def __post_init__(self):
        if (type(self.values) is not tuple or not 1 <= len(self.values) <= 128
                or any(type(x) is not float or not isfinite(x) for x in self.values)):
            raise Q4InputError("INVALID_INPUT: finite numeric bottleneck, width 1..128 required")
