"""Canonical tagged identities for values entering traces and measurements."""

from __future__ import annotations

from decimal import Decimal

from .arithmetic import DECIMAL_CONTEXT_SHA256, exact_decimal_sum
from .finite_values import FINITE_VALUE_PROFILE, finite_value_payload
from .geometry import (
    MAX_PROJECTOR_TOLERANCE,
    MIXED_SIMPLEX_PROFILE,
    PROJECTOR_VALIDATION_PROFILE,
    MixedSimplexAddress,
    ProjectorProfile,
)
from .integrity import canonical_json, require_safe_reference, require_sha256, sha256_payload
from .types import (
    CANONICAL_ND_LABELS,
    CasState,
    Domain,
    Drive,
    Noetic,
    PortSpec,
    Register,
    SignalKind,
)


VALUE_IDENTITY_PROFILE = "cas-pcba-v8.trace-value.v1"


class ValueIdentityError(ValueError):
    """Raised when a value lacks a canonical trace identity."""


def value_identity_payload(value: object) -> dict[str, object]:
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueIdentityError("non-finite Decimal cannot enter an identity")
        return {
            "profile": VALUE_IDENTITY_PROFILE,
            "type": "decimal",
            "value": str(value),
            "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
        }
    if type(value) in (bool, int, str):
        return {
            "profile": VALUE_IDENTITY_PROFILE,
            "type": "finite",
            "finite": finite_value_payload(value),
        }
    if type(value) is CasState:
        value.revalidate()
        return {
            "profile": VALUE_IDENTITY_PROFILE,
            "type": "cas-state",
            "noetic": int(value.noetic),
            "domain": value.domain.value,
            "drive": value.drive.value if value.drive is not None else None,
            "register": value.register.value if value.register is not None else None,
        }
    if type(value) is MixedSimplexAddress:
        return {
            "profile": VALUE_IDENTITY_PROFILE,
            "type": "mixed-simplex",
            "identity": value.identity_payload(),
            "profile_sha256": value.profile_sha256,
        }
    if type(value) is ProjectorProfile:
        value.revalidate()
        return {
            "profile": VALUE_IDENTITY_PROFILE,
            "type": "projector-profile",
            "identity": value.identity_payload(),
            "profile_sha256": value.profile_sha256,
            "matrix_sha256": value.matrix_sha256,
        }
    raise ValueIdentityError(
        f"unsupported trace value type: {type(value).__name__}"
    )


def canonical_value_text(value: object) -> str:
    return canonical_json(value_identity_payload(value))


def value_identity_sha256(value: object) -> str:
    return sha256_payload(value_identity_payload(value))


def value_text_sha256(value_text: str) -> str:
    if type(value_text) is not str:
        raise ValueIdentityError("value_repr must be an exact string")
    try:
        import json

        payload = json.loads(value_text)
    except (TypeError, ValueError) as exc:
        raise ValueIdentityError("value_repr must be canonical tagged JSON") from exc
    if canonical_json(payload) != value_text:
        raise ValueIdentityError("value_repr is not canonical tagged JSON")
    _validate_value_payload(payload)
    return sha256_payload(payload)


def validate_value_text_for_port(value_text: str, port: PortSpec) -> None:
    """Revalidate a serialized semantic value against one exact typed port."""

    if type(port) is not PortSpec:
        raise ValueIdentityError("serialized value validation requires exact PortSpec")
    port.revalidate()
    value_text_sha256(value_text)
    import json

    payload = json.loads(value_text)
    value_type = payload["type"]
    kind = port.signal_kind
    if kind is SignalKind.ACTIVATION:
        if value_type != "decimal":
            raise ValueIdentityError("activation value identity must be Decimal")
        value = Decimal(payload["value"])
        if not Decimal("0") <= value <= Decimal("1"):
            raise ValueIdentityError("activation value identity lies outside [0,1]")
    elif kind is SignalKind.DECISION:
        finite = payload.get("finite")
        if value_type != "finite" or finite.get("type") != "bool":
            raise ValueIdentityError("decision value identity must be exact bool")
    elif kind is SignalKind.CAS_STATE:
        if value_type != "cas-state":
            raise ValueIdentityError("CAS-state port value identity is mistyped")
    elif kind is SignalKind.FINITE_STATE:
        if value_type != "finite":
            raise ValueIdentityError("finite-state port value identity is mistyped")
    elif kind is SignalKind.MIXED_SIMPLEX_ADDRESS:
        if value_type != "mixed-simplex":
            raise ValueIdentityError("mixed-simplex port value identity is mistyped")
    elif kind is SignalKind.PROJECTOR_PROFILE:
        if value_type != "projector-profile":
            raise ValueIdentityError("projector port value identity is mistyped")
    elif kind is SignalKind.TEXT:
        finite = payload.get("finite")
        if value_type != "finite" or finite.get("type") != "string":
            raise ValueIdentityError("text port value identity must be exact string")
    elif kind in {SignalKind.CLOCK, SignalKind.SCALAR}:
        if value_type != "decimal":
            raise ValueIdentityError("numeric port value identity must be Decimal")


def _validate_value_payload(payload: object) -> None:
    if not isinstance(payload, dict) or payload.get("profile") != VALUE_IDENTITY_PROFILE:
        raise ValueIdentityError("value identity profile is missing or unsupported")
    value_type = payload.get("type")
    if value_type == "decimal":
        if payload.get("decimal_context_sha256") != DECIMAL_CONTEXT_SHA256:
            raise ValueIdentityError("decimal value context identity is stale")
        value = payload.get("value")
        if not isinstance(value, str):
            raise ValueIdentityError("decimal value identity is malformed")
        try:
            decimal_value = Decimal(value)
        except Exception as exc:  # Decimal raises several arithmetic subclasses
            raise ValueIdentityError("decimal value identity is malformed") from exc
        if not decimal_value.is_finite() or str(decimal_value) != value:
            raise ValueIdentityError("decimal value is non-finite or noncanonical")
    elif value_type == "finite":
        finite = payload.get("finite")
        if not isinstance(finite, dict) or finite.get("profile") != FINITE_VALUE_PROFILE:
            raise ValueIdentityError("finite value identity is malformed")
        tag = finite.get("type")
        value = finite.get("value")
        if tag == "bool":
            candidate = value if type(value) is bool else None
        elif tag == "int":
            try:
                candidate = int(value) if isinstance(value, str) else None
            except ValueError:
                candidate = None
            if candidate is not None and str(candidate) != value:
                candidate = None
        elif tag == "string":
            candidate = value if type(value) is str else None
        else:
            candidate = None
        if candidate is None or finite_value_payload(candidate) != finite:
            raise ValueIdentityError("finite value type/value tag is inconsistent")
    elif value_type == "cas-state":
        if set(payload) != {
            "profile",
            "type",
            "noetic",
            "domain",
            "drive",
            "register",
        }:
            raise ValueIdentityError("CAS-state value identity is incomplete")
        noetic = payload.get("noetic")
        domain = payload.get("domain")
        drive = payload.get("drive")
        register = payload.get("register")
        if (
            type(noetic) is not int
            or type(domain) is not str
            or (drive is not None and type(drive) is not str)
            or (register is not None and type(register) is not str)
        ):
            raise ValueIdentityError("CAS-state value identity has untyped fields")
        try:
            CasState(
                noetic=Noetic(noetic),
                domain=Domain(domain),
                drive=Drive(drive) if drive is not None else None,
                register=Register(register) if register is not None else None,
            )
        except (TypeError, ValueError) as exc:
            raise ValueIdentityError("CAS-state value identity is invalid") from exc
    elif value_type in {"mixed-simplex", "projector-profile"}:
        identity = payload.get("identity")
        profile_sha = payload.get("profile_sha256")
        if type(identity) is not dict or type(profile_sha) is not str:
            raise ValueIdentityError("geometry value identity is malformed")
        if profile_sha != sha256_payload(identity):
            raise ValueIdentityError("geometry value identity is stale or tampered")
        if value_type == "mixed-simplex":
            _validate_mixed_identity(identity)
        else:
            _validate_projector_identity(identity)
            if payload.get("matrix_sha256") != identity.get("matrix_sha256"):
                raise ValueIdentityError("projector matrix identity linkage is stale")
    else:
        raise ValueIdentityError("value identity type is unsupported")


def _decimal_from_payload(value: object, field_name: str) -> Decimal:
    if type(value) is not dict or set(value) != {"type", "value"}:
        raise ValueIdentityError(f"{field_name} Decimal identity is malformed")
    if value.get("type") != "decimal" or type(value.get("value")) is not str:
        raise ValueIdentityError(f"{field_name} Decimal identity is malformed")
    try:
        result = Decimal(value["value"])
    except Exception as exc:  # Decimal raises several arithmetic subclasses
        raise ValueIdentityError(f"{field_name} Decimal identity is malformed") from exc
    if not result.is_finite() or str(result) != value["value"]:
        raise ValueIdentityError(f"{field_name} Decimal identity is noncanonical")
    return result


def _validate_mixed_identity(identity: dict[str, object]) -> None:
    if set(identity) != {
        "profile",
        "profile_kind",
        "decimal_context_sha256",
        "cells",
        "weights",
    }:
        raise ValueIdentityError("mixed-simplex identity fields are incomplete")
    if (
        identity.get("profile") != MIXED_SIMPLEX_PROFILE
        or identity.get("profile_kind") != "CANONICAL_MIXED_SIMPLEX_BASELINE"
        or identity.get("decimal_context_sha256") != DECIMAL_CONTEXT_SHA256
    ):
        raise ValueIdentityError("mixed-simplex profile identity is unsupported")
    cells = identity.get("cells")
    weights = identity.get("weights")
    expected_cells = list(CANONICAL_ND_LABELS)
    if type(cells) is not list or cells != expected_cells or type(weights) is not list:
        raise ValueIdentityError("mixed-simplex structure is noncanonical")
    decimal_weights = tuple(
        _decimal_from_payload(item, "mixed-simplex weight") for item in weights
    )
    if (
        len(decimal_weights) != 40
        or any(item <= 0 for item in decimal_weights)
        or exact_decimal_sum(decimal_weights) != Decimal("1")
    ):
        raise ValueIdentityError("mixed-simplex weights are invalid")


def _validate_projector_identity(identity: dict[str, object]) -> None:
    expected_fields = {
        "profile",
        "profile_id",
        "profile_kind",
        "canonical_pcba_address",
        "basis_id",
        "source_id",
        "dimension",
        "rank",
        "tolerance",
        "symmetry_residual",
        "idempotence_residual",
        "trace_residual",
        "matrix_sha256",
        "decimal_context_sha256",
        "boundary",
    }
    if set(identity) != expected_fields:
        raise ValueIdentityError("projector identity fields are incomplete")
    if (
        identity.get("profile") != PROJECTOR_VALIDATION_PROFILE
        or identity.get("profile_kind") != "FRONTIER_PROJECTOR_PROFILE"
        or identity.get("canonical_pcba_address") is not False
        or identity.get("decimal_context_sha256") != DECIMAL_CONTEXT_SHA256
    ):
        raise ValueIdentityError("projector identity profile is unsupported")
    for field_name in ("profile_id", "basis_id", "source_id"):
        require_safe_reference(identity.get(field_name), f"projector {field_name}")
    dimension = identity.get("dimension")
    rank = identity.get("rank")
    if (
        type(dimension) is not int
        or type(rank) is not int
        or dimension <= 0
        or not 0 < rank <= dimension
    ):
        raise ValueIdentityError("projector dimension/rank identity is invalid")
    tolerance = _decimal_from_payload(identity.get("tolerance"), "projector tolerance")
    residuals = tuple(
        _decimal_from_payload(identity.get(name), f"projector {name}")
        for name in (
            "symmetry_residual",
            "idempotence_residual",
            "trace_residual",
        )
    )
    if (
        tolerance < 0
        or tolerance > MAX_PROJECTOR_TOLERANCE
        or any(item < 0 or item > tolerance for item in residuals)
    ):
        raise ValueIdentityError("projector tolerance/residual identity is invalid")
    require_sha256(identity.get("matrix_sha256"), "projector matrix_sha256")
    boundary = identity.get("boundary")
    from .boundary import fixed_research_boundary

    if type(boundary) is not dict or boundary != fixed_research_boundary().to_dict():
        raise ValueIdentityError("projector boundary identity is invalid")
