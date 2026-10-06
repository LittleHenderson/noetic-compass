"""Canonical tagged identities for the finite PCBA/TKS boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json

from .integrity import canonical_json, sha256_payload


FINITE_VALUE_PROFILE = "cas-pcba-v8.tagged-finite-value.v1"


class FiniteValueError(ValueError):
    """Raised when an unsupported or type-confused finite atom is used."""


def finite_value_payload(value: object) -> dict[str, object]:
    if type(value) is bool:
        return {
            "profile": FINITE_VALUE_PROFILE,
            "type": "bool",
            "value": value,
        }
    if type(value) is int:
        return {
            "profile": FINITE_VALUE_PROFILE,
            "type": "int",
            "value": str(value),
        }
    if type(value) is str:
        return {
            "profile": FINITE_VALUE_PROFILE,
            "type": "string",
            "value": value,
        }
    raise FiniteValueError("finite atoms must have exact type bool, int, or str")


def finite_value_key(value: object) -> str:
    return canonical_json(finite_value_payload(value))


def finite_value_sha256(value: object) -> str:
    return sha256_payload(finite_value_payload(value))


@dataclass(frozen=True, slots=True)
class TaggedFiniteValue:
    """Hash-safe token used inside kernels whose native equality conflates types."""

    type_tag: str
    canonical_value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not TaggedFiniteValue:
            raise FiniteValueError("tagged finite tokens must use the exact type")
        if type(self.type_tag) is not str or type(self.canonical_value) is not str:
            raise FiniteValueError("tagged finite token fields must be exact strings")
        if self.type_tag == "bool":
            valid = self.canonical_value in {"true", "false"}
        elif self.type_tag == "int":
            try:
                parsed = json.loads(self.canonical_value)
                valid = (
                    type(parsed) is str
                    and str(int(parsed)) == parsed
                    and canonical_json(parsed) == self.canonical_value
                )
            except (TypeError, ValueError):
                parsed = None
                valid = False
        elif self.type_tag == "string":
            try:
                parsed = json.loads(self.canonical_value)
            except (TypeError, ValueError):
                parsed = None
            valid = type(parsed) is str and canonical_json(parsed) == self.canonical_value
        else:
            valid = False
        if not valid:
            raise FiniteValueError("tagged finite token is noncanonical")

    @classmethod
    def from_value(cls, value: object) -> "TaggedFiniteValue":
        if cls is not TaggedFiniteValue:
            raise FiniteValueError("tagged finite token subclasses are unsupported")
        payload = finite_value_payload(value)
        return cls(str(payload["type"]), canonical_json(payload["value"]))
