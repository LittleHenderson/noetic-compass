"""CAS meta-logic construct vocabulary for CAS-Native surfaces.

This module is intentionally symbolic. It gives data generation, proposer
metadata, type checks, and validation bridges a shared representation for the
compiler-admitted set/cluster/diagram constructs without claiming that the
native model has learned weights for those constructs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable

__all__ = [
    "CASConstructKind",
    "ConstructSpec",
    "CONSTRUCT_SPECS",
    "CONSTRUCT_VOCABULARY",
    "EXPRESSION_KIND_LABELS",
    "META_LOGIC_EXEMPLARS",
    "classify_expression",
    "construct_tokens",
    "is_finite_meet_pullback",
]


class CASConstructKind(str, Enum):
    """Expression-kind labels for compiler-admitted meta-logic constructs."""

    STATE = "state"
    NOETIC_SET = "noetic_set"
    NOETIC_CLUSTER = "noetic_cluster"
    STATE_SET = "state_set"
    STATE_CLUSTER = "state_cluster"
    STATE_VARIANT_SET = "state_variant_set"
    STATE_VARIANT_CLUSTER = "state_variant_cluster"
    RELATION_SET = "relation_set"
    RELATION_CLUSTER = "relation_cluster"
    DRIVE_SET = "drive_set"
    DOMAIN_SET = "domain_set"
    REGISTER_SET = "register_set"
    FOUNDATION_SET = "foundation_set"
    SUBFOUNDATION_SET = "subfoundation_set"
    SET_OPERATION = "set_operation"
    TYPED_MEMBERSHIP = "typed_membership"
    TYPED_SUBSET = "typed_subset"
    COORDINATE = "coordinate"
    PRODUCT = "product"
    PULLBACK_FINITE_MEET = "pullback_finite_meet"
    COVER = "cover"
    PARTITION = "partition"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ConstructSpec:
    """Shared vocabulary entry for native integration surfaces."""

    kind: CASConstructKind
    tokens: tuple[str, ...]
    description: str
    exemplar: str


CONSTRUCT_SPECS: tuple[ConstructSpec, ...] = (
    ConstructSpec(
        CASConstructKind.NOETIC_SET,
        ("NoeticSet",),
        "Typed finite set over admitted Noetic operators.",
        "NoeticSet{^2, ^7}",
    ),
    ConstructSpec(
        CASConstructKind.NOETIC_CLUSTER,
        ("NoeticCluster",),
        "Typed cluster over admitted Noetic operators.",
        "NoeticCluster{^2, ^7}",
    ),
    ConstructSpec(
        CASConstructKind.STATE_SET,
        ("StateSet",),
        "Typed finite set over domain-qualified states.",
        "StateSet{^2^P, ^7^O}",
    ),
    ConstructSpec(
        CASConstructKind.STATE_CLUSTER,
        ("StateCluster",),
        "Typed cluster over domain-qualified states.",
        "StateCluster{^2^P, ^7^O}",
    ),
    ConstructSpec(
        CASConstructKind.STATE_VARIANT_SET,
        ("StateVariantSet", "|"),
        "Typed finite set over drive/register-qualified state variants.",
        "StateVariantSet{^3^P_{F2}|A, ^2^C|f}",
    ),
    ConstructSpec(
        CASConstructKind.STATE_VARIANT_CLUSTER,
        ("StateVariantCluster", "|"),
        "Typed cluster over drive/register-qualified state variants.",
        "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}",
    ),
    ConstructSpec(
        CASConstructKind.RELATION_SET,
        ("RelationSet", "->"),
        "Typed finite set of admissible state relations.",
        "RelationSet{^5^P -> ^5^C, ^5^C -> ^5^E}",
    ),
    ConstructSpec(
        CASConstructKind.RELATION_CLUSTER,
        ("RelationCluster", "->"),
        "Typed cluster of admissible state relations.",
        "RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E}",
    ),
    ConstructSpec(
        CASConstructKind.DRIVE_SET,
        ("DriveSet",),
        "Typed finite set over Core Drive primitives.",
        "DriveSet{F2, F3}",
    ),
    ConstructSpec(
        CASConstructKind.DOMAIN_SET,
        ("DomainSet",),
        "Typed finite set over processing domains.",
        "DomainSet{P, C}",
    ),
    ConstructSpec(
        CASConstructKind.REGISTER_SET,
        ("RegisterSet",),
        "Typed finite set over phenomenological registers.",
        "RegisterSet{A, f}",
    ),
    ConstructSpec(
        CASConstructKind.FOUNDATION_SET,
        ("FoundationSet",),
        "Typed finite set over Foundation families.",
        "FoundationSet{Foundation_1, Foundation_7}",
    ),
    ConstructSpec(
        CASConstructKind.SUBFOUNDATION_SET,
        ("SubFoundationSet",),
        "Typed finite set over Drive/Register subfoundation positions.",
        "SubFoundationSet{F1|A, F2|f}",
    ),
    ConstructSpec(
        CASConstructKind.SET_OPERATION,
        ("∪", "∩", "∖"),
        "Finite set union, intersection, and relative complement.",
        "NoeticCluster{^2, ^7} ∩ NoeticCluster{^7}",
    ),
    ConstructSpec(
        CASConstructKind.TYPED_MEMBERSHIP,
        ("∈", "Noetics", "States", "Domains"),
        "Typed membership against compiler-known carriers.",
        "^2 ∈ Noetics",
    ),
    ConstructSpec(
        CASConstructKind.TYPED_SUBSET,
        ("⊆", "Noetics", "States", "Domains"),
        "Typed subset assertion against compiler-known carriers.",
        "NoeticCluster{^2, ^7} ⊆ Noetics",
    ),
    ConstructSpec(
        CASConstructKind.COORDINATE,
        ("Coordinate", "<", ">"),
        "Coordinate tuple constructor over noetic/domain/drive/register axes.",
        "Coordinate{^2, P, F2, A}",
    ),
    ConstructSpec(
        CASConstructKind.PRODUCT,
        ("Product",),
        "Finite product constructor over admitted type carriers.",
        "Product(Noetics, Domains)",
    ),
    ConstructSpec(
        CASConstructKind.PULLBACK_FINITE_MEET,
        ("Pullback",),
        "Pullback represented only as finite subobject meet/intersection.",
        "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
    ),
    ConstructSpec(
        CASConstructKind.COVER,
        ("CoverOf",),
        "Cover declaration over a base object and finite pieces.",
        "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
    ),
    ConstructSpec(
        CASConstructKind.PARTITION,
        ("PartitionOf",),
        "Partition declaration over a base object and finite parts.",
        "PartitionOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
    ),
)

CONSTRUCT_VOCABULARY: tuple[str, ...] = tuple(
    dict.fromkeys(token for spec in CONSTRUCT_SPECS for token in spec.tokens)
)
EXPRESSION_KIND_LABELS: tuple[str, ...] = tuple(kind.value for kind in CASConstructKind)
META_LOGIC_EXEMPLARS: tuple[str, ...] = tuple(spec.exemplar for spec in CONSTRUCT_SPECS)


_DIRECT_PATTERNS: tuple[tuple[CASConstructKind, re.Pattern[str]], ...] = (
    (CASConstructKind.COORDINATE, re.compile(r"\bCoordinate\s*\{|<\s*\^\d+\s*,")),
    (CASConstructKind.PRODUCT, re.compile(r"\bProduct\s*\(")),
    (CASConstructKind.PULLBACK_FINITE_MEET, re.compile(r"\bPullback\s*\(")),
    (CASConstructKind.COVER, re.compile(r"\bCoverOf\s*\(")),
    (CASConstructKind.PARTITION, re.compile(r"\bPartitionOf\s*\(")),
    (CASConstructKind.TYPED_SUBSET, re.compile(r"⊆|\\subseteq")),
    (CASConstructKind.TYPED_MEMBERSHIP, re.compile(r"∈|\\in\b")),
    (CASConstructKind.SET_OPERATION, re.compile(r"∪|∩|∖|\\cup|\\cap|\\setminus")),
    (CASConstructKind.NOETIC_SET, re.compile(r"\bNoeticSet\s*\{")),
    (CASConstructKind.NOETIC_CLUSTER, re.compile(r"\bNoeticCluster\s*\{")),
    (CASConstructKind.STATE_VARIANT_SET, re.compile(r"\bStateVariantSet\s*\{")),
    (CASConstructKind.STATE_VARIANT_CLUSTER, re.compile(r"\bStateVariantCluster\s*\{")),
    (CASConstructKind.STATE_SET, re.compile(r"\bStateSet\s*\{")),
    (CASConstructKind.STATE_CLUSTER, re.compile(r"\bStateCluster\s*\{")),
    (CASConstructKind.RELATION_SET, re.compile(r"\bRelationSet\s*\{")),
    (CASConstructKind.RELATION_CLUSTER, re.compile(r"\bRelationCluster\s*\{")),
    (CASConstructKind.DRIVE_SET, re.compile(r"\bDriveSet\s*\{")),
    (CASConstructKind.DOMAIN_SET, re.compile(r"\bDomainSet\s*\{")),
    (CASConstructKind.REGISTER_SET, re.compile(r"\bRegisterSet\s*\{")),
    (CASConstructKind.FOUNDATION_SET, re.compile(r"\bFoundationSet\s*\{")),
    (CASConstructKind.SUBFOUNDATION_SET, re.compile(r"\bSubFoundationSet\s*\{")),
    (CASConstructKind.STATE, re.compile(r"CO-\d+\^[PCEO]|\^\d+\^[PCEO]")),
)


def classify_expression(expression: str) -> CASConstructKind:
    """Return the first recognized construct kind for ``expression``."""

    for kind, pattern in _DIRECT_PATTERNS:
        if pattern.search(expression):
            return kind
    return CASConstructKind.UNKNOWN


def construct_tokens(expression: str) -> tuple[str, ...]:
    """Return known construct vocabulary tokens present in ``expression``."""

    found: list[str] = []
    for token in CONSTRUCT_VOCABULARY:
        if token in expression:
            found.append(token)
    return tuple(found)


def is_finite_meet_pullback(expression: str) -> bool:
    """True for compiler-admitted ``Pullback(...)`` finite-meet notation."""

    return classify_expression(expression) is CASConstructKind.PULLBACK_FINITE_MEET
