"""Strict, bounded JSON transport. Serialized records never carry authority."""
from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, fields, is_dataclass
from typing import ClassVar


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def integer(value: object, minimum: int, maximum: int, name: str) -> None:
    require(type(value) is int and minimum <= value <= maximum, f"invalid {name}")


def plain(value: object) -> object:
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)
                if not f.name.startswith("_")}
    if isinstance(value, tuple):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def canonical(value: object) -> str:
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(text: str) -> dict:
    require(type(text) is str and len(text.encode()) <= 65536, "record exceeds 64 KiB")
    try:
        data = json.loads(text, object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ContractError(f"nonfinite JSON number: {value}")))
    except (ValueError, RecursionError) as exc:
        raise ContractError(str(exc)) from exc
    require(type(data) is dict, "expected JSON object")
    return data


class Record:
    _nested: ClassVar[dict] = {}
    _tuples: ClassVar[tuple[str, ...]] = ()

    def to_dict(self) -> dict:
        return plain(self)

    def to_json(self) -> str:
        return canonical(self)

    @classmethod
    def from_json(cls, text: str, **context):
        return cls.from_dict(read_json(text), **context)

    @classmethod
    def from_dict(cls, data: dict, **context):
        require(type(data) is dict, "expected record object")
        expected = {f.name for f in fields(cls) if not f.name.startswith("_")}
        require(set(data) == expected, "missing or unknown record fields")
        values = dict(data)
        for name, nested in cls._nested.items():
            values[name] = nested.from_dict(values[name])
        for name in cls._tuples:
            require(type(values[name]) is list, f"{name} must be an array")
            require(len(values[name]) <= 64, f"{name} exceeds bound")
            values[name] = tuple(values[name])
        private = {f.name for f in fields(cls) if f.name.startswith("_")}
        required = {f.name[1:] for f in fields(cls)
                    if f.name.startswith("_") and f.default is MISSING}
        require(required <= set(context) <= {key[1:] for key in private}, "trusted context required")
        return cls(**values, **{"_" + key: value for key, value in context.items()})
