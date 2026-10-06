"""Exhaustive finite checks for the Noetic Topos 2.0 context site.

This module is deliberately small and dependency-free.  It checks a finite
model; it is not a proof-assistant artifact and it does not license empirical
or product claims.

The context category is the powerset poset of four atoms.  An arrow U -> V
exists exactly when U is a subset of V.  ACBE and RPM use the two coordinate
partitions of the four atoms.  Their generating covers at V are the two
intersections of V with the relevant partition blocks.  The empty context is
covered by the empty family.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations, product
from typing import Any, Hashable, Iterable, Mapping, Protocol, Sequence


Atom = int
Context = frozenset[Atom]
Section = Hashable

ACBE = "ACBE"
RPM = "RPM"
ACBE_RPM_JOIN = "ACBE_RPM_JOIN"

ATOM_LABELS: dict[Atom, str] = {
    0: "a0r0",
    1: "a0r1",
    2: "a1r0",
    3: "a1r1",
}
ALL_ATOMS: Context = frozenset(ATOM_LABELS)


def _powerset(values: Sequence[Atom]) -> tuple[Context, ...]:
    return tuple(
        frozenset(choice)
        for size in range(len(values) + 1)
        for choice in combinations(values, size)
    )


ALL_CONTEXTS: tuple[Context, ...] = _powerset(tuple(sorted(ALL_ATOMS)))

PARTITIONS: dict[str, tuple[Context, Context]] = {
    ACBE: (frozenset({0, 1}), frozenset({2, 3})),
    RPM: (frozenset({0, 2}), frozenset({1, 3})),
}

MARKED_COVER_SCHEMA = "noetic_topos2.marked_cover.v0.1"
MARKED_COVER_KEYS = frozenset(
    {
        "schema_version",
        "derivation_kind",
        "target",
        "members",
        "mark",
        "parent_cover_sha256s",
    }
)
MARK_RECORD_KEYS = frozenset(
    {
        "cover_kind",
        "source_authority_ref",
        "assumptions",
        "evidence_or_proof_refs",
        "review_state",
        "provenance_chain",
    }
)
REVIEW_STATES = frozenset(
    {"UNASSESSED", "IN_REVIEW", "REVIEWED", "FLAG_FOR_HUMAN_REVIEW"}
)
MARK_KINDS = frozenset({ACBE, RPM, ACBE_RPM_JOIN})
DERIVATION_KINDS = frozenset({"GENERATOR", "PULLBACK", "COMMON_REFINEMENT"})
DEFAULT_MARK_SOURCE = (
    "docs/working/project_coherence/gate1/noetic_topos2/"
    "NOETIC_TOPOS_2_SPEC_v0.1.md"
)


def _require_context(context: Context) -> None:
    if not context <= ALL_ATOMS:
        raise ValueError(f"unknown context atoms: {sorted(context - ALL_ATOMS)}")


def _require_kind(kind: str) -> None:
    if kind not in PARTITIONS:
        raise ValueError(f"unknown cover kind: {kind!r}")


def _require_mark_kind(kind: str) -> None:
    if kind not in MARK_KINDS:
        raise ValueError(f"unknown marked-cover kind: {kind!r}")


def _context_labels(context: Context) -> tuple[str, ...]:
    _require_context(context)
    return tuple(ATOM_LABELS[atom] for atom in sorted(context))


def _context_from_labels(labels: object) -> Context:
    if not isinstance(labels, list) or any(not isinstance(label, str) for label in labels):
        raise ValueError("a serialized context must be a list of atom labels")
    reverse = {label: atom for atom, label in ATOM_LABELS.items()}
    try:
        context = frozenset(reverse[label] for label in labels)
    except KeyError as exc:
        raise ValueError(f"unknown serialized atom label: {exc.args[0]!r}") from exc
    if len(context) != len(labels):
        raise ValueError("a serialized context contains a duplicate atom label")
    return context


def _nonblank_tuple(values: object, field: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValueError(f"{field} must be an ordered tuple or list of strings")
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{field} entries must be non-blank strings")
    return result


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class MarkRecord:
    """Immutable provenance that remains separate from the generated sieve."""

    cover_kind: str
    source_authority_ref: str
    assumptions: tuple[str, ...]
    evidence_or_proof_refs: tuple[str, ...]
    review_state: str
    provenance_chain: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_mark_kind(self.cover_kind)
        if not isinstance(self.source_authority_ref, str) or not self.source_authority_ref.strip():
            raise ValueError("source_authority_ref must be a non-blank string")
        if self.review_state not in REVIEW_STATES:
            raise ValueError(
                f"review_state must be one of {sorted(REVIEW_STATES)}, "
                f"not {self.review_state!r}"
            )
        object.__setattr__(
            self, "assumptions", _nonblank_tuple(self.assumptions, "assumptions")
        )
        object.__setattr__(
            self,
            "evidence_or_proof_refs",
            _nonblank_tuple(self.evidence_or_proof_refs, "evidence_or_proof_refs"),
        )
        object.__setattr__(
            self,
            "provenance_chain",
            _nonblank_tuple(self.provenance_chain, "provenance_chain"),
        )


@dataclass(frozen=True, slots=True)
class MarkedCover:
    """A topology family plus a hash-stable, provenance-bearing mark.

    ``members`` are deliberately retained independently of ``mark``.  Topology
    generation consumes only the members, while serialization and audit retain
    the cover kind even when ACBE and RPM have the same unmarked pullback.
    """

    derivation_kind: str
    target: Context
    members: tuple[Context, ...]
    mark: MarkRecord
    parent_cover_sha256s: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.derivation_kind not in DERIVATION_KINDS:
            raise ValueError(
                f"derivation_kind must be one of {sorted(DERIVATION_KINDS)}"
            )
        target = frozenset(self.target)
        _require_context(target)
        if not isinstance(self.mark, MarkRecord):
            raise TypeError("mark must be a MarkRecord")
        members = tuple(frozenset(member) for member in self.members)
        if any(not member <= target for member in members):
            raise ValueError("a marked-cover member is not a subcontext of its target")
        members = tuple(sorted(members, key=_context_labels))
        parent_digests = _nonblank_tuple(
            self.parent_cover_sha256s, "parent_cover_sha256s"
        )
        if len(set(parent_digests)) != len(parent_digests):
            raise ValueError("parent_cover_sha256s must be pairwise distinct")
        for digest in parent_digests:
            if (
                len(digest) != 64
                or any(character not in "0123456789ABCDEF" for character in digest)
            ):
                raise ValueError(
                    "each parent_cover_sha256s entry must be an uppercase SHA-256 digest"
                )
        expected_parent_count = {
            "GENERATOR": 0,
            "PULLBACK": 1,
            "COMMON_REFINEMENT": 2,
        }[self.derivation_kind]
        if len(parent_digests) != expected_parent_count:
            raise ValueError(
                f"{self.derivation_kind} requires {expected_parent_count} parent digest(s)"
            )
        if self.derivation_kind == "GENERATOR" and self.mark.cover_kind not in {
            ACBE,
            RPM,
        }:
            raise ValueError("a generator record must be marked ACBE or RPM")
        if (
            self.derivation_kind == "COMMON_REFINEMENT"
            and self.mark.cover_kind != ACBE_RPM_JOIN
        ):
            raise ValueError("a common refinement must carry the ACBE_RPM_JOIN mark")
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "members", members)
        object.__setattr__(self, "parent_cover_sha256s", tuple(sorted(parent_digests)))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": MARKED_COVER_SCHEMA,
            "derivation_kind": self.derivation_kind,
            "target": list(_context_labels(self.target)),
            "members": [list(_context_labels(member)) for member in self.members],
            "mark": {
                "cover_kind": self.mark.cover_kind,
                "source_authority_ref": self.mark.source_authority_ref,
                "assumptions": list(self.mark.assumptions),
                "evidence_or_proof_refs": list(self.mark.evidence_or_proof_refs),
                "review_state": self.mark.review_state,
                "provenance_chain": list(self.mark.provenance_chain),
            },
            "parent_cover_sha256s": list(self.parent_cover_sha256s),
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest().upper()

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        parent_records: Mapping[str, "MarkedCover"] | None = None,
    ) -> "MarkedCover":
        if not isinstance(payload, Mapping):
            raise ValueError("a marked cover payload must be a mapping")
        if set(payload) != MARKED_COVER_KEYS:
            raise ValueError(
                "a marked cover payload must contain exactly the canonical key set"
            )
        if payload.get("schema_version") != MARKED_COVER_SCHEMA:
            raise ValueError("unsupported marked-cover schema")
        raw_mark = payload.get("mark")
        if not isinstance(raw_mark, Mapping):
            raise ValueError("a marked cover payload needs a mark mapping")
        if set(raw_mark) != MARK_RECORD_KEYS:
            raise ValueError("a mark payload must contain exactly the canonical key set")
        members = payload.get("members")
        if not isinstance(members, list):
            raise ValueError("marked-cover members must be a list")
        parents = _nonblank_tuple(
            payload.get("parent_cover_sha256s"), "parent_cover_sha256s"
        )
        cover = cls(
            derivation_kind=payload.get("derivation_kind"),
            target=_context_from_labels(payload.get("target")),
            members=tuple(_context_from_labels(member) for member in members),
            mark=MarkRecord(
                cover_kind=raw_mark.get("cover_kind"),
                source_authority_ref=raw_mark.get("source_authority_ref"),
                assumptions=_nonblank_tuple(raw_mark.get("assumptions"), "assumptions"),
                evidence_or_proof_refs=_nonblank_tuple(
                    raw_mark.get("evidence_or_proof_refs"), "evidence_or_proof_refs"
                ),
                review_state=raw_mark.get("review_state"),
                provenance_chain=_nonblank_tuple(
                    raw_mark.get("provenance_chain"), "provenance_chain"
                ),
            ),
            parent_cover_sha256s=parents,
        )
        if not verify_marked_cover_derivation(cover, parent_records or {}):
            raise ValueError("marked-cover derivation could not be resolved and recomputed")
        return cover

    @classmethod
    def from_json(
        cls,
        payload: str,
        *,
        parent_records: Mapping[str, "MarkedCover"] | None = None,
    ) -> "MarkedCover":
        try:
            decoded = json.loads(payload, object_pairs_hook=_reject_duplicate_json_keys)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid marked-cover JSON") from exc
        return cls.from_payload(decoded, parent_records=parent_records)


def generating_cover(target: Context, kind: str) -> tuple[Context, ...]:
    """Return the selected marked cover of ``target``.

    The null cover at the empty object is included so Set-valued sheaves have
    exactly one section there.  For nonempty targets, the two returned pieces
    are the pullbacks of the relevant global partition blocks.
    """

    _require_context(target)
    _require_kind(kind)
    if not target:
        return ()
    return tuple(target & block for block in PARTITIONS[kind])


def generating_marked_cover(
    target: Context,
    kind: str,
    *,
    source_authority_ref: str = DEFAULT_MARK_SOURCE,
    assumptions: tuple[str, ...] = (
        "arrows in the context lattice are inclusions",
        "cover members are coordinate-partition pullbacks",
    ),
    evidence_or_proof_refs: tuple[str, ...] = (
        "THM-NT2-MARKED-COVERAGE",
        "FINITE_MODEL_CERTIFICATE_v0.1.json",
    ),
    review_state: str = "IN_REVIEW",
) -> MarkedCover:
    """Return a generating family without discarding its audit identity."""

    _require_context(target)
    _require_kind(kind)
    target_ref = ",".join(_context_labels(target)) or "EMPTY"
    return MarkedCover(
        derivation_kind="GENERATOR",
        target=target,
        members=generating_cover(target, kind),
        mark=MarkRecord(
            cover_kind=kind,
            source_authority_ref=source_authority_ref,
            assumptions=assumptions,
            evidence_or_proof_refs=evidence_or_proof_refs,
            review_state=review_state,
            provenance_chain=(f"GENERATED:{kind}:TARGET={target_ref}",),
        ),
    )


def generated_sieve(target: Context, family: Iterable[Context]) -> frozenset[Context]:
    """Return the sieve generated by a family of subcontexts of ``target``."""

    _require_context(target)
    members = tuple(family)
    if any(not member <= target for member in members):
        raise ValueError("a cover member is not a subcontext of its target")
    return frozenset(
        subcontext
        for subcontext in ALL_CONTEXTS
        if subcontext <= target and any(subcontext <= member for member in members)
    )


def is_covering_family(target: Context, family: Iterable[Context], kind: str) -> bool:
    """Check whether the family's sieve contains the selected marked cover."""

    _require_kind(kind)
    members = tuple(family)
    if not target and not members:
        return True
    sieve = generated_sieve(target, members)
    return all(piece in sieve for piece in generating_cover(target, kind))


def pullback_family(
    target: Context, family: Iterable[Context], along: Context
) -> tuple[Context, ...]:
    """Pull a family on ``target`` back along the inclusion ``along -> target``."""

    if not along <= target:
        raise ValueError("pullback arrow is not an inclusion into the target")
    return tuple(along & member for member in family)


def pullback_marked_cover(cover: MarkedCover, along: Context) -> MarkedCover:
    """Pull back a marked cover while binding the result to its parent digest."""

    if not isinstance(cover, MarkedCover):
        raise TypeError("cover must be a MarkedCover")
    if not along <= cover.target:
        raise ValueError("pullback arrow is not an inclusion into the target")
    parent_digest = cover.sha256()
    along_ref = ",".join(_context_labels(along)) or "EMPTY"
    mark = MarkRecord(
        cover_kind=cover.mark.cover_kind,
        source_authority_ref=cover.mark.source_authority_ref,
        assumptions=cover.mark.assumptions,
        evidence_or_proof_refs=cover.mark.evidence_or_proof_refs,
        review_state=cover.mark.review_state,
        provenance_chain=cover.mark.provenance_chain
        + (f"PULLBACK:PARENT={parent_digest}:ALONG={along_ref}",),
    )
    return MarkedCover(
        derivation_kind="PULLBACK",
        target=along,
        members=pullback_family(cover.target, cover.members, along),
        mark=mark,
        parent_cover_sha256s=(parent_digest,),
    )


def common_refinement_marked_cover(
    acbe_cover: MarkedCover, rpm_cover: MarkedCover
) -> MarkedCover:
    """Bind the ACBE/RPM common refinement to both parent records."""

    if not isinstance(acbe_cover, MarkedCover) or not isinstance(rpm_cover, MarkedCover):
        raise TypeError("both common-refinement inputs must be MarkedCover records")
    if acbe_cover.mark.cover_kind != ACBE or rpm_cover.mark.cover_kind != RPM:
        raise ValueError("common refinement requires an ACBE parent and an RPM parent")
    if acbe_cover.target != rpm_cover.target:
        raise ValueError("common-refinement parents must have the same target")
    expected_acbe_members = tuple(
        sorted(generating_cover(acbe_cover.target, ACBE), key=_context_labels)
    )
    expected_rpm_members = tuple(
        sorted(generating_cover(rpm_cover.target, RPM), key=_context_labels)
    )
    if acbe_cover.members != expected_acbe_members:
        raise ValueError("the ACBE parent is not the canonical generating cover")
    if rpm_cover.members != expected_rpm_members:
        raise ValueError("the RPM parent is not the canonical generating cover")
    acbe_digest = acbe_cover.sha256()
    rpm_digest = rpm_cover.sha256()
    target_ref = ",".join(_context_labels(acbe_cover.target)) or "EMPTY"
    source_ref = (
        acbe_cover.mark.source_authority_ref
        if acbe_cover.mark.source_authority_ref == rpm_cover.mark.source_authority_ref
        else f"{acbe_cover.mark.source_authority_ref} + {rpm_cover.mark.source_authority_ref}"
    )
    return MarkedCover(
        derivation_kind="COMMON_REFINEMENT",
        target=acbe_cover.target,
        members=tuple(
            acbe_piece & rpm_piece
            for acbe_piece in acbe_cover.members
            for rpm_piece in rpm_cover.members
        ),
        mark=MarkRecord(
            cover_kind=ACBE_RPM_JOIN,
            source_authority_ref=source_ref,
            assumptions=(
                "the parents are generating ACBE and RPM context-factor covers",
                "common-refinement members are pairwise intersections",
            ),
            evidence_or_proof_refs=(
                "THM-NT2-JOIN-DISCRETE-CONTEXT",
                "FINITE_MODEL_CERTIFICATE_v0.1.json",
            ),
            review_state="IN_REVIEW",
            provenance_chain=(
                "COMMON_REFINEMENT:"
                f"ACBE_PARENT={acbe_digest}:RPM_PARENT={rpm_digest}:TARGET={target_ref}",
            ),
        ),
        parent_cover_sha256s=(acbe_digest, rpm_digest),
    )


def verify_marked_cover_derivation(
    cover: MarkedCover,
    parent_records: Mapping[str, MarkedCover],
    *,
    _visiting: frozenset[str] = frozenset(),
) -> bool:
    """Resolve and recompute the complete derivation DAG for one marked cover."""

    if not isinstance(cover, MarkedCover) or not isinstance(parent_records, Mapping):
        return False
    cover_digest = cover.sha256()
    if cover_digest in _visiting:
        return False
    if cover.derivation_kind == "GENERATOR":
        expected_members = tuple(
            sorted(
                generating_cover(cover.target, cover.mark.cover_kind),
                key=_context_labels,
            )
        )
        return not cover.parent_cover_sha256s and cover.members == expected_members

    resolved_parents: list[MarkedCover] = []
    next_visiting = _visiting | {cover_digest}
    for digest in cover.parent_cover_sha256s:
        parent = parent_records.get(digest)
        if not isinstance(parent, MarkedCover) or parent.sha256() != digest:
            return False
        if not verify_marked_cover_derivation(
            parent, parent_records, _visiting=next_visiting
        ):
            return False
        resolved_parents.append(parent)

    if cover.derivation_kind == "PULLBACK":
        parent = resolved_parents[0]
        if not cover.target <= parent.target:
            return False
        return pullback_marked_cover(parent, cover.target) == cover

    if cover.derivation_kind == "COMMON_REFINEMENT":
        by_kind = {parent.mark.cover_kind: parent for parent in resolved_parents}
        if set(by_kind) != {ACBE, RPM}:
            return False
        try:
            expected = common_refinement_marked_cover(by_kind[ACBE], by_kind[RPM])
        except (TypeError, ValueError):
            return False
        return expected == cover
    return False


def split_epimorphism_sieve_contains_identity() -> bool:
    """Check the inherited RPM collapse in a minimal symbolic arrow model.

    ``epsilon`` lies in the sieve and closure under precomposition adds every
    declared composite with it.  The section equation is encoded as the one
    relevant composition rule, epsilon o eta = id.
    """

    sieve = {"epsilon"}
    composition = {("epsilon", "eta"): "identity"}
    changed = True
    while changed:
        changed = False
        for (outer, _inner), composite in composition.items():
            if outer in sieve and composite not in sieve:
                sieve.add(composite)
                changed = True
    return "identity" in sieve


class FinitePresheaf(Protocol):
    def sections(self, context: Context) -> tuple[Section, ...]: ...

    def restrict(self, section: Section, source: Context, target: Context) -> Section: ...


@dataclass(frozen=True)
class PartitionWitnessPresheaf:
    """A finite presheaf that distinguishes the two marked topologies.

    A section assigns a bit to each complete block of ``partition_kind`` that
    is contained in the current context.  Restriction forgets coordinates.
    """

    partition_kind: str

    def __post_init__(self) -> None:
        _require_kind(self.partition_kind)

    def _coordinates(self, context: Context) -> tuple[int, ...]:
        _require_context(context)
        return tuple(
            index
            for index, block in enumerate(PARTITIONS[self.partition_kind])
            if block <= context
        )

    def sections(self, context: Context) -> tuple[Section, ...]:
        coordinates = self._coordinates(context)
        return tuple(tuple(bits) for bits in product((0, 1), repeat=len(coordinates)))

    def restrict(self, section: Section, source: Context, target: Context) -> Section:
        if not target <= source:
            raise ValueError("presheaf restriction requires target <= source")
        source_coordinates = self._coordinates(source)
        target_coordinates = self._coordinates(target)
        values = tuple(section)
        if len(values) != len(source_coordinates):
            raise ValueError("section has the wrong arity for its source context")
        by_coordinate = dict(zip(source_coordinates, values, strict=True))
        return tuple(by_coordinate[index] for index in target_coordinates)


@dataclass(frozen=True)
class RepresentablePresheaf:
    """The representable y(W) on the powerset poset."""

    represented_context: Context

    def __post_init__(self) -> None:
        _require_context(self.represented_context)

    def sections(self, context: Context) -> tuple[Section, ...]:
        _require_context(context)
        return (("unique",),) if context <= self.represented_context else ()

    def restrict(self, section: Section, source: Context, target: Context) -> Section:
        if not target <= source:
            raise ValueError("presheaf restriction requires target <= source")
        if section not in self.sections(source):
            raise ValueError("section does not belong to the source context")
        result = ("unique",)
        if result not in self.sections(target):
            raise AssertionError("representable restriction is ill-typed")
        return result


def matching_families(
    presheaf: FinitePresheaf, target: Context, kind: str
) -> frozenset[tuple[Section, ...]]:
    """Enumerate matching families for the selected finite generating cover."""

    pieces = generating_cover(target, kind)
    candidates = product(*(presheaf.sections(piece) for piece in pieces))
    matching: set[tuple[Section, ...]] = set()
    for family in candidates:
        compatible = True
        for left_index, left_piece in enumerate(pieces):
            for right_index, right_piece in enumerate(pieces):
                overlap = left_piece & right_piece
                left_value = presheaf.restrict(
                    family[left_index], left_piece, overlap
                )
                right_value = presheaf.restrict(
                    family[right_index], right_piece, overlap
                )
                if left_value != right_value:
                    compatible = False
                    break
            if not compatible:
                break
        if compatible:
            matching.add(tuple(family))
    return frozenset(matching)


def gluing_map_image(
    presheaf: FinitePresheaf, target: Context, kind: str
) -> tuple[tuple[Section, ...], ...]:
    pieces = generating_cover(target, kind)
    return tuple(
        tuple(presheaf.restrict(section, target, piece) for piece in pieces)
        for section in presheaf.sections(target)
    )


def sheaf_condition_at(presheaf: FinitePresheaf, target: Context, kind: str) -> bool:
    """Check that the gluing map is a bijection at one generating cover."""

    image = gluing_map_image(presheaf, target, kind)
    matching = matching_families(presheaf, target, kind)
    return len(image) == len(set(image)) and frozenset(image) == matching


def is_sheaf_for(presheaf: FinitePresheaf, kind: str) -> bool:
    """Validate the finite presheaf first, then check every generating cover."""

    return validate_finite_presheaf(presheaf) and all(
        sheaf_condition_at(presheaf, target, kind) for target in ALL_CONTEXTS
    )


def validate_finite_presheaf(presheaf: FinitePresheaf) -> bool:
    """Exhaustively certify section sets, typed restrictions, and functor laws."""

    try:
        sections = {
            context: tuple(presheaf.sections(context)) for context in ALL_CONTEXTS
        }
        if any(len(values) != len(set(values)) for values in sections.values()):
            return False
        for source in ALL_CONTEXTS:
            for section in sections[source]:
                identity_restriction = presheaf.restrict(section, source, source)
                if identity_restriction not in sections[source]:
                    return False
                if identity_restriction != section:
                    return False
                for middle in ALL_CONTEXTS:
                    if not middle <= source:
                        continue
                    middle_section = presheaf.restrict(section, source, middle)
                    if middle_section not in sections[middle]:
                        return False
                    for target in ALL_CONTEXTS:
                        if not target <= middle:
                            continue
                        direct = presheaf.restrict(section, source, target)
                        staged = presheaf.restrict(middle_section, middle, target)
                        if direct not in sections[target] or staged not in sections[target]:
                            return False
                        if direct != staged:
                            return False
    except (TypeError, ValueError, KeyError, IndexError):
        return False
    return True


def check_reference_model() -> dict[str, object]:
    """Exhaustively check the finite claims used by the v0.1 specification."""

    proper_global_covers = {
        kind: all(piece < ALL_ATOMS for piece in generating_cover(ALL_ATOMS, kind))
        for kind in PARTITIONS
    }
    jointly_exhaustive = {
        kind: all(
            frozenset().union(*generating_cover(context, kind)) == context
            if context
            else generating_cover(context, kind) == ()
            for context in ALL_CONTEXTS
        )
        for kind in PARTITIONS
    }
    pullback_stable = {
        kind: all(
            is_covering_family(
                along,
                pullback_family(target, generating_cover(target, kind), along),
                kind,
            )
            for target in ALL_CONTEXTS
            for along in ALL_CONTEXTS
            if along <= target
        )
        for kind in PARTITIONS
    }

    acbe_witness = PartitionWitnessPresheaf(ACBE)
    rpm_witness = PartitionWitnessPresheaf(RPM)
    representables_subcanonical = all(
        is_sheaf_for(RepresentablePresheaf(represented), kind)
        for represented in ALL_CONTEXTS
        for kind in PARTITIONS
    )

    atom_refinement = frozenset(
        acbe_block & rpm_block
        for acbe_block in PARTITIONS[ACBE]
        for rpm_block in PARTITIONS[RPM]
    )
    expected_atom_refinement = frozenset(frozenset({atom}) for atom in ALL_ATOMS)

    singleton = frozenset({0})
    singleton_acbe = generating_marked_cover(singleton, ACBE)
    singleton_rpm = generating_marked_cover(singleton, RPM)
    global_acbe = generating_marked_cover(ALL_ATOMS, ACBE)
    global_rpm = generating_marked_cover(ALL_ATOMS, RPM)
    global_join = common_refinement_marked_cover(global_acbe, global_rpm)
    marked_covers = tuple(
        generating_marked_cover(target, kind)
        for target in ALL_CONTEXTS
        for kind in PARTITIONS
    )
    marked_pullbacks = tuple(
        (cover, along, pullback_marked_cover(cover, along))
        for cover in marked_covers
        for along in ALL_CONTEXTS
        if along <= cover.target
    )
    generated_by_digest = {cover.sha256(): cover for cover in marked_covers}
    join_parents = {
        global_acbe.sha256(): global_acbe,
        global_rpm.sha256(): global_rpm,
    }

    result = {
        "atom_count": len(ALL_ATOMS),
        "context_count": len(ALL_CONTEXTS),
        "proper_global_covers": proper_global_covers,
        "jointly_exhaustive": jointly_exhaustive,
        "pullback_stable": pullback_stable,
        "representables_are_sheaves": representables_subcanonical,
        "acbe_witness_functorial": validate_finite_presheaf(acbe_witness),
        "rpm_witness_functorial": validate_finite_presheaf(rpm_witness),
        "acbe_witness_is_acbe_sheaf": is_sheaf_for(acbe_witness, ACBE),
        "acbe_witness_is_rpm_sheaf": is_sheaf_for(acbe_witness, RPM),
        "rpm_witness_is_rpm_sheaf": is_sheaf_for(rpm_witness, RPM),
        "rpm_witness_is_acbe_sheaf": is_sheaf_for(rpm_witness, ACBE),
        "transverse_refinement_is_singletons": atom_refinement
        == expected_atom_refinement,
        "singleton_unmarked_families_coincide": generating_cover(singleton, ACBE)
        == generating_cover(singleton, RPM),
        "singleton_marked_covers_distinct": (
            singleton_acbe.mark.cover_kind != singleton_rpm.mark.cover_kind
            and singleton_acbe.sha256() != singleton_rpm.sha256()
        ),
        "marked_cover_roundtrip_stable": all(
            MarkedCover.from_json(cover.canonical_json()) == cover
            and MarkedCover.from_json(cover.canonical_json()).sha256() == cover.sha256()
            for cover in marked_covers
        ),
        "marked_pullbacks_bind_parent_provenance": all(
            pulled.parent_cover_sha256s == (cover.sha256(),)
            and pulled.mark.cover_kind == cover.mark.cover_kind
            and pulled.mark.source_authority_ref == cover.mark.source_authority_ref
            and pulled.mark.provenance_chain[:-1] == cover.mark.provenance_chain
            for cover, _along, pulled in marked_pullbacks
        ),
        "marked_pullbacks_preserve_topology_family": all(
            frozenset(pulled.members)
            == frozenset(pullback_family(cover.target, cover.members, along))
            for cover, along, pulled in marked_pullbacks
        ),
        "joint_refinement_is_four_singletons": frozenset(global_join.members)
        == expected_atom_refinement,
        "joint_refinement_retains_both_parent_digests": set(
            global_join.parent_cover_sha256s
        )
        == {global_acbe.sha256(), global_rpm.sha256()}
        and global_join.mark.cover_kind == ACBE_RPM_JOIN,
        "marked_derived_records_resolve": all(
            verify_marked_cover_derivation(pulled, generated_by_digest)
            and MarkedCover.from_json(
                pulled.canonical_json(), parent_records=generated_by_digest
            )
            == pulled
            for _cover, _along, pulled in marked_pullbacks
        )
        and verify_marked_cover_derivation(global_join, join_parents)
        and MarkedCover.from_json(
            global_join.canonical_json(), parent_records=join_parents
        )
        == global_join,
        "legacy_acbe_identity_forces_maximal_sieve": generated_sieve(
            ALL_ATOMS, (ALL_ATOMS,)
        )
        == frozenset(ALL_CONTEXTS),
        "legacy_rpm_split_epi_forces_identity": split_epimorphism_sieve_contains_identity(),
    }
    result["all_required_checks_pass"] = (
        all(proper_global_covers.values())
        and all(jointly_exhaustive.values())
        and all(pullback_stable.values())
        and representables_subcanonical
        and result["acbe_witness_functorial"]
        and result["rpm_witness_functorial"]
        and result["acbe_witness_is_acbe_sheaf"]
        and not result["acbe_witness_is_rpm_sheaf"]
        and result["rpm_witness_is_rpm_sheaf"]
        and not result["rpm_witness_is_acbe_sheaf"]
        and result["transverse_refinement_is_singletons"]
        and result["singleton_unmarked_families_coincide"]
        and result["singleton_marked_covers_distinct"]
        and result["marked_cover_roundtrip_stable"]
        and result["marked_pullbacks_bind_parent_provenance"]
        and result["marked_pullbacks_preserve_topology_family"]
        and result["joint_refinement_is_four_singletons"]
        and result["joint_refinement_retains_both_parent_digests"]
        and result["marked_derived_records_resolve"]
        and result["legacy_acbe_identity_forces_maximal_sieve"]
        and result["legacy_rpm_split_epi_forces_identity"]
    )
    return result
