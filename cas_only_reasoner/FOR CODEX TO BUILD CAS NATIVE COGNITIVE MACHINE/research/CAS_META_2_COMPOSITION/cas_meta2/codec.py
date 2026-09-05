"""Pure-Python public-input and program-token contracts.

The vocabulary describes individual declarations, calls, runs, variables and
bindings. It does not contain a label for any complete procedure or graph.
No torch import, tensor work, gold lookup or evaluator is needed here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any


class PolicyContractError(ValueError):
    pass


SCHEMA = "cas-meta2-program/0.1"
PROCEDURE_NAMES = ("main",) + tuple(f"p{i}" for i in range(16))
VARIABLE_NAMES = ("arg",) + tuple(f"v{i}" for i in range(32))
CJT_NAMES = ("A", "B", "C", "R")
ACTION_VOCABULARY = (
    "[PAD]", "[BOS]", "[EOS]", "BIND0", "BIND1", "BIND2",
    "PROC", "ALLOW", "ENDALLOW", "RUN", "CALL", "RETURN", "ENDPROC",
) + PROCEDURE_NAMES + VARIABLE_NAMES + CJT_NAMES
ACTION_TO_ID = {word: index for index, word in enumerate(ACTION_VOCABULARY)}
PAD_ID, BOS_ID, EOS_ID = 0, 1, 2
BINDING_TOKEN_IDS = tuple(ACTION_TO_ID[f"BIND{i}"] for i in range(3))
DEFAULT_MAX_ACTION_LENGTH = 512
SPECIAL = ("[PAD]", "[UNK]", "[CLS]", "[SEP]", "[OBS]", "[VALUES]")


def canonical_sha256(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def validate_public(public: dict) -> dict:
    """Accept only the problem and declared observations, never gold or IDs."""
    if type(public) is not dict or set(public) != {"problem", "observations"}:
        raise PolicyContractError("PUBLIC_INPUT_FIELDS_INVALID")
    if type(public["problem"]) is not str or not public["problem"] or len(public["problem"]) > 8192:
        raise PolicyContractError("PUBLIC_PROBLEM_INVALID")
    observations = public["observations"]
    if type(observations) is not list or len(observations) != 3:
        raise PolicyContractError("PUBLIC_OBSERVATIONS_INVALID")
    slots = []
    for item in observations:
        if type(item) is not dict or set(item) != {"slot", "tag", "values"}:
            raise PolicyContractError("PUBLIC_OBSERVATION_FIELDS_INVALID")
        if type(item["slot"]) is not int or item["slot"] not in (0, 1, 2):
            raise PolicyContractError("PUBLIC_SLOT_INVALID")
        if type(item["tag"]) is not str or not item["tag"] or len(item["tag"]) > 256:
            raise PolicyContractError("PUBLIC_TAG_INVALID")
        values = item["values"]
        if type(values) is not list or len(values) != 8 or any(
            type(value) not in (int, float) or not math.isfinite(value) for value in values
        ):
            raise PolicyContractError("PUBLIC_VALUES_INVALID")
        slots.append(item["slot"])
    if sorted(slots) != [0, 1, 2]:
        raise PolicyContractError("PUBLIC_SLOT_COVERAGE_INVALID")
    return public


def _public_sequence(public: dict) -> list[tuple[str, int, int, list[float]]]:
    validate_public(public)
    zero = [0.0] * 8
    words = lambda text: re.findall(r"\w+|[^\w\s]", text.lower(), flags=re.UNICODE)
    rows = [("[CLS]", 0, 0, zero)]
    rows.extend((word, 0, 0, zero) for word in words(public["problem"]))
    rows.append(("[SEP]", 1, 0, zero))
    for observation in sorted(public["observations"], key=lambda item: item["slot"]):
        slot = observation["slot"] + 1
        rows.append(("[OBS]", 2, slot, zero))
        rows.extend((word, 2, slot, zero) for word in words(observation["tag"]))
        rows.append(("[VALUES]", 3, slot, [float(value) for value in observation["values"]]))
    return rows


@dataclass(frozen=True)
class PublicTokenizer:
    vocabulary: tuple[str, ...]
    fitted_public_sha256: str
    fitted_examples: int
    max_length: int = 512

    @classmethod
    def fit_train(cls, train_public: list[dict], *, max_length: int = 512):
        if not train_public or type(max_length) is not int or max_length < 16:
            raise PolicyContractError("TOKENIZER_TRAIN_INPUT_INVALID")
        words = set()
        for public in train_public:
            rows = _public_sequence(public)
            if len(rows) > max_length:
                raise PolicyContractError("PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION")
            words.update(row[0] for row in rows)
        return cls(SPECIAL + tuple(sorted(words.difference(SPECIAL))),
                   canonical_sha256(train_public), len(train_public), max_length)

    def encode_public(self, public: dict) -> dict:
        rows = _public_sequence(public)
        if len(rows) > self.max_length:
            raise PolicyContractError("PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION")
        lookup = {word: index for index, word in enumerate(self.vocabulary)}
        return {"ids": [lookup.get(row[0], 1) for row in rows],
                "kinds": [row[1] for row in rows], "slots": [row[2] for row in rows],
                "values": [row[3] for row in rows]}

    def to_dict(self) -> dict:
        return {"schema": "cas-meta2-public-tokenizer/1", "fit_split": "train_only",
                **asdict(self)}

    @property
    def digest(self) -> str:
        return canonical_sha256(self.to_dict())


def validate_action(action: dict) -> dict:
    if type(action) is not dict or set(action) != {"program", "binding"}:
        raise PolicyContractError("ACTION_FIELDS_INVALID")
    if type(action["binding"]) is not int or action["binding"] not in (0, 1, 2):
        raise PolicyContractError("ACTION_BINDING_INVALID")
    program = action["program"]
    if type(program) is not dict or set(program) != {"schema", "entry", "procedures"}:
        raise PolicyContractError("PROGRAM_FIELDS_INVALID")
    if program["schema"] != SCHEMA or program["entry"] != "main":
        raise PolicyContractError("PROGRAM_SCHEMA_OR_ENTRY_INVALID")
    procedures = program["procedures"]
    if type(procedures) is not dict or not 1 <= len(procedures) <= 16 or "main" not in procedures:
        raise PolicyContractError("PROGRAM_PROCEDURES_INVALID")
    if any(name not in PROCEDURE_NAMES for name in procedures):
        raise PolicyContractError("PROGRAM_NAME_OUTSIDE_CODEC_BOUND")
    calls = {}
    for name, procedure in procedures.items():
        if type(procedure) is not dict or set(procedure) != {"input", "allowed_cjts", "steps", "return"}:
            raise PolicyContractError("PROCEDURE_FIELDS_INVALID")
        if procedure["input"] != "arg":
            raise PolicyContractError("PROCEDURE_INPUT_INVALID")
        allowed = procedure["allowed_cjts"]
        if type(allowed) is not list or any(type(value) is not str or value not in CJT_NAMES for value in allowed):
            raise PolicyContractError("PROCEDURE_ALLOWLIST_INVALID")
        if len(set(allowed)) != len(allowed):
            raise PolicyContractError("PROCEDURE_ALLOWLIST_DUPLICATE")
        steps = procedure["steps"]
        if type(steps) is not list or not 1 <= len(steps) <= 32:
            raise PolicyContractError("PROCEDURE_STEPS_OUTSIDE_CODEC_BOUND")
        available = {"arg"}
        calls[name] = []
        for step in steps:
            if type(step) is not dict or step.get("kind") not in ("RUN", "CALL"):
                raise PolicyContractError("STEP_KIND_INVALID")
            target = "cjt_id" if step["kind"] == "RUN" else "procedure"
            if set(step) != {"kind", target, "input", "output"}:
                raise PolicyContractError("STEP_FIELDS_INVALID")
            if type(step["input"]) is not str or step["input"] not in available:
                raise PolicyContractError("STEP_INPUT_UNBOUND")
            if type(step["output"]) is not str or step["output"] not in VARIABLE_NAMES[1:]:
                raise PolicyContractError("STEP_OUTPUT_NAME_INVALID")
            if step["output"] in available:
                raise PolicyContractError("STEP_OUTPUT_NOT_FRESH")
            available.add(step["output"])
            if step["kind"] == "RUN":
                if type(step[target]) is not str or step[target] not in allowed:
                    raise PolicyContractError("STEP_CJT_OUTSIDE_SCOPE")
            else:
                if type(step[target]) is not str or step[target] not in procedures:
                    raise PolicyContractError("STEP_CALLEE_MISSING")
                calls[name].append(step[target])
        if type(procedure["return"]) is not str or procedure["return"] not in available:
            raise PolicyContractError("PROCEDURE_RETURN_UNBOUND")
    visiting, complete = set(), set()
    def visit(name):
        if name in visiting:
            raise PolicyContractError("PROGRAM_CALL_CYCLE")
        if name in complete:
            return
        visiting.add(name)
        for child in calls[name]:
            if not set(procedures[child]["allowed_cjts"]).issubset(procedures[name]["allowed_cjts"]):
                raise PolicyContractError("CALL_SCOPE_ESCALATION")
            visit(child)
        visiting.remove(name)
        complete.add(name)
    for name in procedures:
        visit(name)
    return action


def action_to_tokens(action: dict, *, max_length: int = DEFAULT_MAX_ACTION_LENGTH) -> list[str]:
    validate_action(action)
    if type(max_length) is not int or max_length < 2:
        raise PolicyContractError("ACTION_LENGTH_BOUND_INVALID")
    tokens = ["[BOS]", f"BIND{action['binding']}"]
    procedures = action["program"]["procedures"]
    for name in sorted(procedures, key=lambda value: (value != "main", value)):
        procedure = procedures[name]
        tokens += ["PROC", name, "ALLOW", *procedure["allowed_cjts"], "ENDALLOW"]
        for step in procedure["steps"]:
            target = "cjt_id" if step["kind"] == "RUN" else "procedure"
            tokens += [step["kind"], step[target], step["input"], step["output"]]
        tokens += ["RETURN", procedure["return"], "ENDPROC"]
    tokens.append("[EOS]")
    if len(tokens) > max_length:
        raise PolicyContractError("ACTION_TOO_LONG:NO_SILENT_TRUNCATION")
    return tokens


def tokens_to_action(tokens: list[str], *, max_length: int = DEFAULT_MAX_ACTION_LENGTH) -> dict:
    if type(max_length) is not int or max_length < 2:
        raise PolicyContractError("ACTION_LENGTH_BOUND_INVALID")
    if type(tokens) is not list or not 2 <= len(tokens) <= max_length:
        raise PolicyContractError("ACTION_TOKEN_LENGTH_INVALID")
    if any(type(token) is not str or token not in ACTION_TO_ID for token in tokens):
        raise PolicyContractError("ACTION_TOKEN_UNKNOWN")
    index = 0
    def take(expected=None):
        nonlocal index
        if index >= len(tokens):
            raise PolicyContractError("ACTION_TOKEN_STREAM_INCOMPLETE")
        value = tokens[index]
        index += 1
        if expected is not None and value != expected:
            raise PolicyContractError("ACTION_TOKEN_UNEXPECTED:" + str(expected))
        return value
    take("[BOS]")
    binding_token = take()
    if binding_token not in ("BIND0", "BIND1", "BIND2"):
        raise PolicyContractError("ACTION_BINDING_TOKEN_INVALID")
    procedures = {}
    while index < len(tokens) and tokens[index] != "[EOS]":
        take("PROC")
        name = take()
        if name in procedures:
            raise PolicyContractError("PROCEDURE_DUPLICATE")
        take("ALLOW")
        allowed = []
        while index < len(tokens) and tokens[index] != "ENDALLOW":
            value = take()
            if value not in CJT_NAMES:
                raise PolicyContractError("PROCEDURE_ALLOWLIST_TOKEN_INVALID")
            allowed.append(value)
        take("ENDALLOW")
        steps = []
        while index < len(tokens) and tokens[index] in ("RUN", "CALL"):
            kind = take()
            target = "cjt_id" if kind == "RUN" else "procedure"
            steps.append({"kind": kind, target: take(), "input": take(), "output": take()})
        take("RETURN")
        returned = take()
        take("ENDPROC")
        procedures[name] = {"input": "arg", "allowed_cjts": allowed,
                            "steps": steps, "return": returned}
    take("[EOS]")
    if index != len(tokens):
        raise PolicyContractError("ACTION_TOKEN_TRAILING_DATA")
    action = {"program": {"schema": SCHEMA, "entry": "main", "procedures": procedures},
              "binding": int(binding_token[-1])}
    validate_action(action)
    if action_to_tokens(action, max_length=max_length) != tokens:
        raise PolicyContractError("ACTION_TOKEN_NONCANONICAL_ORDER")
    return action


def action_to_ids(action: dict, *, max_length: int = DEFAULT_MAX_ACTION_LENGTH) -> list[int]:
    return [ACTION_TO_ID[token] for token in action_to_tokens(action, max_length=max_length)]


def ids_to_action(ids: list[int], *, max_length: int = DEFAULT_MAX_ACTION_LENGTH) -> dict:
    if type(ids) is not list or any(type(value) is not int or not 0 <= value < len(ACTION_VOCABULARY)
                                   for value in ids):
        raise PolicyContractError("ACTION_TOKEN_ID_INVALID")
    return tokens_to_action([ACTION_VOCABULARY[value] for value in ids], max_length=max_length)
