"""Deterministic canonicalization and strict scalar validation for CAS-Ohm v1.

The research candidate deliberately has no implicit conversion from binary
floating point.  Scientific quantities must arrive as :class:`Decimal`
instances so their exact lexical value is under the caller's control.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import unicodedata
from dataclasses import is_dataclass
from decimal import Context, Decimal, localcontext
from enum import Enum
from typing import Any

SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
CAS_OHM_DECIMAL_PRECISION = 50
CANONICAL_MAX_DEPTH = 64
CANONICAL_MAX_NODES = 20_000
CANONICAL_MAX_CONTAINER_ITEMS = 10_000
CANONICAL_MAX_TEXT_BYTES = 1_048_576
CANONICAL_MAX_OUTPUT_BYTES = 8_388_608
CANONICAL_MAX_INTEGER_BITS = 2_048

_CANONICAL_ENUM_TYPES = frozenset(
    {
        "cas_ohm_v1.calibration.DriftState",
        "cas_ohm_v1.calibration.Q4Band",
        "cas_ohm_v1.diagnostics.ResidualCensoring",
        "cas_ohm_v1.model.AsomLabel",
        "cas_ohm_v1.model.AuthorizationState",
        "cas_ohm_v1.model.Capability",
        "cas_ohm_v1.model.ClassificationMode",
        "cas_ohm_v1.model.DirectionProvenance",
        "cas_ohm_v1.model.DirectionSign",
        "cas_ohm_v1.model.DoseResponseRegion",
        "cas_ohm_v1.model.IFSMethod",
        "cas_ohm_v1.model.MeasurementKind",
        "cas_ohm_v1.model.QuantityKind",
        "cas_ohm_v1.model.ResistanceRole",
        "cas_ohm_v1.model.ReviewState",
        "cas_ohm_v1.model.SemanticOutcome",
        "cas_ohm_v1.model.TrustMode",
        "cas_ohm_v1.model.UnitKind",
        "cas_ohm_v1.networks.NetworkKind",
        "cas_ohm_v1.synthetic.SyntheticFault",
    }
)

_CANONICAL_OBJECT_TYPES = frozenset(
    {
        "cas_ohm_v1.calibration.AuthorityKey",
        "cas_ohm_v1.calibration.AuthorityManifest",
        "cas_ohm_v1.calibration.CalibrationProfile",
        "cas_ohm_v1.calibration.CapabilityAttestation",
        "cas_ohm_v1.calibration.CurrentClockReceipt",
        "cas_ohm_v1.calibration.ExactRatio",
        "cas_ohm_v1.calibration.FullScaleValue",
        "cas_ohm_v1.calibration.NormalizedFlow",
        "cas_ohm_v1.calibration.ToleranceProfile",
        "cas_ohm_v1.diagnostics.ResidualResult",
        "cas_ohm_v1.evidence.ArtifactEvidence",
        "cas_ohm_v1.model.ArtifactRef",
        "cas_ohm_v1.model.ControlBinding",
        "cas_ohm_v1.model.FieldProvenance",
        "cas_ohm_v1.model.InstrumentIdentity",
        "cas_ohm_v1.model.MeasurementValue",
        "cas_ohm_v1.model.ModelIdentity",
        "cas_ohm_v1.model.NonClaimExtension",
        "cas_ohm_v1.model.OperatingAssessment",
        "cas_ohm_v1.model.OperatingClassification",
        "cas_ohm_v1.model.OperationBinding",
        "cas_ohm_v1.model.ParentRef",
        "cas_ohm_v1.model.SweepObservation",
        "cas_ohm_v1.model.TestPointIdentity",
        "cas_ohm_v1.model.Uncertainty",
        "cas_ohm_v1.networks.CoordinateIdentity",
        "cas_ohm_v1.networks.GainCompositionResult",
        "cas_ohm_v1.networks.GainStage",
        "cas_ohm_v1.networks.NetworkResult",
        "cas_ohm_v1.networks.ResistanceComponent",
        "cas_ohm_v1.records.CJTQRecord",
        "cas_ohm_v1.records.EligibilityResult",
        "cas_ohm_v1.synthetic.SyntheticBoard",
        "cas_ohm_v1.synthetic.SyntheticObservation",
    }
)


class ValidationError(ValueError):
    """Raised when a CAS-Ohm object violates its research schema."""


class CapabilityError(PermissionError):
    """Raised when an operation lacks an evidence-backed capability grant."""


def require_decimal(value: Any, field_name: str) -> Decimal:
    """Return a finite Decimal, rejecting floats and implicit coercions."""

    if type(value) is not Decimal:
        raise ValidationError(
            f"{field_name} must be a Decimal; bare numeric coercion is forbidden"
        )
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite")
    return value


def require_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    _reject_unsafe_unicode(value, field_name)
    return value


def _reject_unsafe_unicode(value: str, field_name: str) -> None:
    for character in value:
        if unicodedata.category(character) in {"Cc", "Cf", "Cs"}:
            code_point = f"U+{ord(character):04X}"
            raise ValidationError(
                f"{field_name} contains forbidden control/format character {code_point}"
            )


def require_sha256(value: Any, field_name: str) -> str:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        raise ValidationError(
            f"{field_name} must be an uppercase 64-character SHA-256 digest"
        )
    return value


def require_positive_int(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer")
    return value


def canonical_decimal(value: Decimal) -> str:
    """Return a unique, exponent-free representation of a finite Decimal."""

    require_decimal(value, "decimal")
    if value == 0:
        return "0"
    # Decimal.normalize() applies the caller's ambient arithmetic context and
    # can therefore round long values.  Fixed-point formatting is exact; only
    # insignificant fractional zeroes are removed here.
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def arithmetic_context():
    """Return the fixed arithmetic context used by all derived CAS-Ohm values."""

    return localcontext(
        Context(
            prec=50,
            rounding="ROUND_HALF_EVEN",
            Emin=-999999,
            Emax=999999,
            capitals=1,
            clamp=0,
        )
    )


def canonical_type_id(value_or_type: Any) -> str:
    """Return the stable domain tag used by canonical evidence identities."""

    value_type = (
        value_or_type if isinstance(value_or_type, type) else type(value_or_type)
    )
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _require_registered_exact_type(
    value: object, type_id: str, registry: frozenset[str]
) -> None:
    if type_id not in registry:
        raise ValidationError(f"unregistered canonical type: {type_id}")
    module_name, _, qualname = type_id.rpartition(".")
    try:
        expected: object = importlib.import_module(module_name)
        for component in qualname.split("."):
            expected = getattr(expected, component)
    except (AttributeError, ImportError) as exc:
        raise ValidationError(f"canonical type cannot be resolved: {type_id}") from exc
    if type(value) is not expected:
        raise ValidationError(f"canonical type identity is spoofed: {type_id}")


class _CanonicalState:
    __slots__ = ("active_ids", "node_count", "text_bytes")

    def __init__(self) -> None:
        self.active_ids: set[int] = set()
        self.node_count = 0
        self.text_bytes = 0

    def visit(self, depth: int) -> None:
        if depth > CANONICAL_MAX_DEPTH:
            raise ValidationError("canonical payload exceeds maximum depth")
        self.node_count += 1
        if self.node_count > CANONICAL_MAX_NODES:
            raise ValidationError("canonical payload exceeds maximum node count")

    def add_text(self, value: str) -> None:
        self.text_bytes += len(value.encode("utf-8", errors="strict"))
        if self.text_bytes > CANONICAL_MAX_TEXT_BYTES:
            raise ValidationError("canonical payload exceeds maximum text size")

    def enter(self, value: object) -> int:
        identity = id(value)
        if identity in self.active_ids:
            raise ValidationError("canonical payload contains a reference cycle")
        self.active_ids.add(identity)
        return identity

    def leave(self, identity: int) -> None:
        self.active_ids.remove(identity)


def _canonical_tree(value: Any, state: _CanonicalState, depth: int = 0) -> Any:
    state.visit(depth)
    if value is None:
        return {"$type": "none"}
    if isinstance(value, float):
        raise ValidationError("floats are forbidden in canonical CAS-Ohm payloads")
    if type(value) is Decimal:
        rendered = canonical_decimal(value)
        state.add_text(rendered)
        return {
            "$type": "decimal",
            "class": canonical_type_id(value),
            "value": rendered,
        }
    if isinstance(value, Enum):
        enum_type = canonical_type_id(value)
        _require_registered_exact_type(value, enum_type, _CANONICAL_ENUM_TYPES)
        return {
            "$type": "enum",
            "class": enum_type,
            "value": _canonical_tree(value.value, state, depth + 1),
        }
    if type(value) is bool:
        return {"$type": "boolean", "value": value}
    if type(value) is int:
        if value.bit_length() > CANONICAL_MAX_INTEGER_BITS:
            raise ValidationError(
                "canonical integer exceeds maximum bit length "
                f"{CANONICAL_MAX_INTEGER_BITS}"
            )
        try:
            rendered = str(value)
        except (OverflowError, ValueError) as exc:
            raise ValidationError("canonical integer conversion failed") from exc
        state.add_text(rendered)
        return {
            "$type": "integer",
            "class": canonical_type_id(value),
            "value": rendered,
        }
    if type(value) is str:
        _reject_unsafe_unicode(value, "canonical string")
        state.add_text(value)
        return {
            "$type": "string",
            "class": canonical_type_id(value),
            "value": value,
        }
    if type(value) is dict:
        if len(value) > CANONICAL_MAX_CONTAINER_ITEMS:
            raise ValidationError("canonical mapping exceeds maximum item count")
        identity = state.enter(value)
        try:
            items: list[list[Any]] = []
            for key, item in value.items():
                if type(key) is not str:
                    raise ValidationError(
                        "canonical mapping keys must be exact strings"
                    )
                _reject_unsafe_unicode(key, "canonical mapping key")
                state.add_text(key)
                items.append([key, _canonical_tree(item, state, depth + 1)])
            items.sort(key=lambda pair: pair[0])
            return {
                "$type": "mapping",
                "class": "builtins.dict",
                "items": items,
            }
        finally:
            state.leave(identity)
    if type(value) in {tuple, list}:
        if len(value) > CANONICAL_MAX_CONTAINER_ITEMS:
            raise ValidationError("canonical sequence exceeds maximum item count")
        identity = state.enter(value)
        try:
            return {
                "$type": "sequence",
                "class": canonical_type_id(value),
                "items": [_canonical_tree(item, state, depth + 1) for item in value],
            }
        finally:
            state.leave(identity)
    if isinstance(value, (set, frozenset)):
        raise ValidationError(
            "unordered collections are forbidden in canonical payloads"
        )
    payload = getattr(value, "canonical_payload", None)
    if callable(payload):
        object_type = canonical_type_id(value)
        _require_registered_exact_type(value, object_type, _CANONICAL_OBJECT_TYPES)
        identity = state.enter(value)
        try:
            payload_value = payload()
            if type(payload_value) is not dict:
                raise ValidationError("canonical_payload() must return an exact dict")
            return {
                "$type": "object",
                "class": object_type,
                "payload": _canonical_tree(payload_value, state, depth + 1),
            }
        finally:
            state.leave(identity)
    if is_dataclass(value):
        raise ValidationError(
            f"dataclass {type(value).__name__} must define "
            "canonical_payload() explicitly"
        )
    raise ValidationError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Serialize a value to deterministic UTF-8 JSON bytes."""

    encoded = json.dumps(
        _canonical_tree(value, _CanonicalState()),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > CANONICAL_MAX_OUTPUT_BYTES:
        raise ValidationError("canonical payload exceeds maximum output size")
    return encoded


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest().upper()
