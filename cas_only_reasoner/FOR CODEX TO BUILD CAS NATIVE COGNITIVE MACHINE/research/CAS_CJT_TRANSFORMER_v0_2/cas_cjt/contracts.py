"""Canonical serialization and schema checks for Neural CJT wire contracts."""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .types import ContractModel, ContractTypeError


SCHEMA_FILENAME = "neural_cjt_contracts.schema.json"


class ContractSchemaError(ValueError):
    """Raised when a mapping does not conform to the versioned wire schema."""


def _wire_value(value: Any) -> Any:
    if isinstance(value, ContractModel):
        return value.to_dict()
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise ContractTypeError("authoritative JSON keys must be non-empty strings")
            result[key] = _wire_value(value[key])
        return result
    if isinstance(value, (tuple, list)):
        return [_wire_value(item) for item in value]
    if isinstance(value, float):
        raise ContractTypeError(
            "authoritative JSON contains a float; use a scaled integer, decimal string, or tensor artifact"
        )
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ContractTypeError(f"unsupported authoritative JSON type: {type(value).__name__}")


def assert_no_json_floats(value: Any) -> None:
    """Fail if any nested value is floating point or otherwise not JSON-safe."""

    _wire_value(value)


def canonical_json(value: Any) -> str:
    """Return the frozen compact JSON representation used for local digests."""

    wire = _wire_value(value)
    return json.dumps(
        wire,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any, *, omit_keys: Sequence[str] = ()) -> str:
    """Hash one contract, optionally omitting named root fields."""

    wire = _wire_value(value)
    if omit_keys:
        if not isinstance(wire, dict):
            raise ContractTypeError("omit_keys is valid only for an object")
        wire = {key: item for key, item in wire.items() if key not in set(omit_keys)}
    return sha256(canonical_json(wire).encode("ascii")).hexdigest()


def verify_declared_digest(value: Any, field_name: str) -> bool:
    """Verify a root digest field against all remaining root fields."""

    wire = _wire_value(value)
    if not isinstance(wire, dict):
        return False
    declared = wire.get(field_name)
    if not isinstance(declared, str):
        return False
    return declared == canonical_digest(wire, omit_keys=(field_name,))


@lru_cache(maxsize=1)
def load_contract_schema() -> dict[str, Any]:
    path = Path(__file__).resolve().with_name("schemas") / SCHEMA_FILENAME
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ContractSchemaError("contract schema root must be an object")
    return value


@lru_cache(maxsize=1)
def _validator() -> Any:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - exercised only without test extra
        raise RuntimeError("jsonschema>=4.21 is required for schema validation") from exc
    schema = load_contract_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_contract(value: ContractModel | Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached JSON mapping, or raise one concise error."""

    wire = _wire_value(value)
    if not isinstance(wire, dict):
        raise ContractSchemaError("a contract must be a JSON object")
    errors = sorted(
        _validator().iter_errors(wire),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        first = errors[0]
        path = ".".join(str(item) for item in first.absolute_path) or "$"
        contexts = sorted(
            (
                f"{'.'.join(str(item) for item in child.absolute_path) or '$'}: {child.message}"
                for child in first.context
            )
        )
        detail = f"; alternatives: {' | '.join(contexts[:4])}" if contexts else ""
        raise ContractSchemaError(f"{path}: {first.message}{detail}")
    return wire


def is_valid_contract(value: ContractModel | Mapping[str, Any]) -> bool:
    try:
        validate_contract(value)
    except (ContractSchemaError, ContractTypeError):
        return False
    return True


__all__ = [
    "SCHEMA_FILENAME",
    "ContractSchemaError",
    "assert_no_json_floats",
    "canonical_json",
    "canonical_digest",
    "verify_declared_digest",
    "load_contract_schema",
    "validate_contract",
    "is_valid_contract",
]
