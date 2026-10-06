"""Exact finite-context sheafification reflectors and composition checks.

Let ``L`` be the powerset of four atoms, ordered by inclusion.  ACBE and RPM
are the two transverse two-block partitions.  For either partition ``P``, the
endofunctor implemented here is

    (R_P F)(V) = product_{B in P, V intersect B nonempty} F(V intersect B),

with the empty product at the empty context.  The accompanying proof artifact
shows that this is the associated-sheaf reflector for the stated coverage.

The code uses tuples as finite products.  Nested tuples are not asserted to be
strictly equal to flattened tuples: the exported conversion functions realize
the canonical natural isomorphisms.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Hashable, Protocol, Sequence


Atom = int
Context = frozenset[Atom]
Section = Hashable
Sieve = frozenset[Context]

ACBE = "ACBE"
RPM = "RPM"
ATOMIC = "ATOMIC"

ALL_ATOMS: Context = frozenset(range(4))


def _powerset(values: Sequence[Atom]) -> tuple[Context, ...]:
    return tuple(
        frozenset(choice)
        for size in range(len(values) + 1)
        for choice in combinations(values, size)
    )


ALL_CONTEXTS: tuple[Context, ...] = _powerset(tuple(sorted(ALL_ATOMS)))

PARTITION_BLOCKS: dict[str, tuple[Context, ...]] = {
    ACBE: (frozenset({0, 1}), frozenset({2, 3})),
    RPM: (frozenset({0, 2}), frozenset({1, 3})),
    ATOMIC: tuple(frozenset({atom}) for atom in sorted(ALL_ATOMS)),
}


def _require_context(context: Context) -> None:
    if not isinstance(context, frozenset) or not context <= ALL_ATOMS:
        raise ValueError("a context must be a frozenset of registered atoms")


def _blocks(kind: str) -> tuple[Context, ...]:
    try:
        return PARTITION_BLOCKS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown partition kind: {kind!r}") from exc


def generating_family(context: Context, kind: str) -> tuple[Context, ...]:
    """Return the site generator, retaining empty pieces away from the null case."""

    _require_context(context)
    blocks = _blocks(kind)
    if not context:
        return ()
    return tuple(context & block for block in blocks)


def normalized_support(context: Context, kind: str) -> tuple[Context, ...]:
    """Return the nonempty pieces indexing the explicit reflector product."""

    _require_context(context)
    return tuple(piece for piece in generating_family(context, kind) if piece)


class FinitePresheaf(Protocol):
    """Set-valued presheaf interface on the inclusion poset."""

    def sections(self, context: Context) -> tuple[Section, ...]: ...

    def restrict(self, section: Section, source: Context, target: Context) -> Section: ...


def validate_finite_presheaf(presheaf: FinitePresheaf) -> bool:
    """Exhaustively check section uniqueness, typing, identity, and composition."""

    try:
        sections = {
            context: tuple(presheaf.sections(context)) for context in ALL_CONTEXTS
        }
        if any(len(values) != len(set(values)) for values in sections.values()):
            return False
        for source in ALL_CONTEXTS:
            for section in sections[source]:
                if presheaf.restrict(section, source, source) != section:
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
                        if direct not in sections[target] or direct != staged:
                            return False
    except (KeyError, TypeError, ValueError, IndexError):
        return False
    return True


@dataclass(frozen=True, slots=True)
class ReflectedPresheaf:
    """The explicit partition reflector ``R_kind`` applied to a presheaf."""

    base: FinitePresheaf
    kind: str

    def __post_init__(self) -> None:
        _blocks(self.kind)

    def sections(self, context: Context) -> tuple[Section, ...]:
        factors = tuple(
            tuple(self.base.sections(piece))
            for piece in normalized_support(context, self.kind)
        )
        return tuple(tuple(values) for values in product(*factors))

    def restrict(self, section: Section, source: Context, target: Context) -> Section:
        _require_context(source)
        _require_context(target)
        if not target <= source:
            raise ValueError("presheaf restriction requires target <= source")
        values = tuple(section)
        source_pieces = normalized_support(source, self.kind)
        if len(values) != len(source_pieces):
            raise ValueError("reflected section has the wrong source arity")
        if any(
            value not in self.base.sections(piece)
            for value, piece in zip(values, source_pieces, strict=True)
        ):
            raise ValueError("reflected section contains an ill-typed component")

        by_block: dict[Context, tuple[Context, Section]] = {}
        value_index = 0
        for block in _blocks(self.kind):
            source_piece = source & block
            if source_piece:
                by_block[block] = (source_piece, values[value_index])
                value_index += 1

        restricted: list[Section] = []
        for block in _blocks(self.kind):
            target_piece = target & block
            if not target_piece:
                continue
            source_piece, source_value = by_block[block]
            restricted.append(
                self.base.restrict(source_value, source_piece, target_piece)
            )
        return tuple(restricted)

    def unit(self, section: Section, context: Context) -> Section:
        """The component of ``F -> R_kind F`` at one section."""

        _require_context(context)
        if section not in self.base.sections(context):
            raise ValueError("unit input is not a section at the stated context")
        return tuple(
            self.base.restrict(section, context, piece)
            for piece in normalized_support(context, self.kind)
        )


def _require_transverse(outer_kind: str, inner_kind: str) -> None:
    if {outer_kind, inner_kind} != {ACBE, RPM}:
        raise ValueError("composition conversion requires the transverse ACBE/RPM pair")
    intersections = {
        outer & inner
        for outer in _blocks(outer_kind)
        for inner in _blocks(inner_kind)
    }
    if intersections != {frozenset({atom}) for atom in ALL_ATOMS}:
        raise AssertionError("registered partitions are not transverse")


def composite_to_atomic_section(
    section: Section,
    context: Context,
    outer_kind: str,
    inner_kind: str,
) -> tuple[Section, ...]:
    """Flatten ``R_outer(R_inner(F))(V)`` to ``R_ATOMIC(F)(V)``.

    The operation depends only on the product indices, so it is valid for an
    arbitrary base presheaf.  The returned tuple is ordered by registered atom.
    """

    _require_context(context)
    _require_transverse(outer_kind, inner_kind)
    outer_values = tuple(section)
    outer_pieces = normalized_support(context, outer_kind)
    if len(outer_values) != len(outer_pieces):
        raise ValueError("composite section has the wrong outer arity")

    by_atom: dict[Atom, Section] = {}
    for outer_piece, inner_section in zip(
        outer_pieces, outer_values, strict=True
    ):
        inner_values = tuple(inner_section)
        inner_pieces = normalized_support(outer_piece, inner_kind)
        if len(inner_values) != len(inner_pieces):
            raise ValueError("composite section has the wrong inner arity")
        for singleton, value in zip(inner_pieces, inner_values, strict=True):
            if len(singleton) != 1:
                raise AssertionError("transverse block intersection is not singleton")
            atom = next(iter(singleton))
            if atom in by_atom:
                raise AssertionError("an atom occurs in two composite factors")
            by_atom[atom] = value

    expected_atoms = set(context)
    if set(by_atom) != expected_atoms:
        raise ValueError("composite section does not have exactly the context atoms")
    return tuple(by_atom[atom] for atom in sorted(context))


def atomic_to_composite_section(
    section: Section,
    context: Context,
    outer_kind: str,
    inner_kind: str,
) -> tuple[Section, ...]:
    """Inverse reindexing from atomic products to a nested transverse product."""

    _require_context(context)
    _require_transverse(outer_kind, inner_kind)
    atomic_values = tuple(section)
    if len(atomic_values) != len(context):
        raise ValueError("atomic section has the wrong arity")
    by_atom = dict(zip(sorted(context), atomic_values, strict=True))
    nested: list[Section] = []
    for outer_piece in normalized_support(context, outer_kind):
        inner_values: list[Section] = []
        for singleton in normalized_support(outer_piece, inner_kind):
            if len(singleton) != 1:
                raise AssertionError("transverse block intersection is not singleton")
            inner_values.append(by_atom[next(iter(singleton))])
        nested.append(tuple(inner_values))
    return tuple(nested)


def _all_sieves(target: Context) -> tuple[Sieve, ...]:
    below = tuple(context for context in ALL_CONTEXTS if context <= target)
    sieves: list[Sieve] = []
    for selected_bits in product((False, True), repeat=len(below)):
        selected = frozenset(
            context
            for context, is_selected in zip(below, selected_bits, strict=True)
            if is_selected
        )
        if all(
            subcontext in selected
            for context in selected
            for subcontext in below
            if subcontext <= context
        ):
            sieves.append(selected)
    return tuple(sieves)


SIEVES_BY_TARGET: dict[Context, tuple[Sieve, ...]] = {
    target: _all_sieves(target) for target in ALL_CONTEXTS
}


def _pullback_sieve(sieve: Sieve, along: Context) -> Sieve:
    return frozenset(context for context in sieve if context <= along)


def generated_topology(kinds: tuple[str, ...]) -> frozenset[tuple[Context, Sieve]]:
    """Compute the least finite Grothendieck topology containing the generators.

    The closure is exhaustive over every sieve on every one of the 16 objects.
    It seeds maximal sieves and generator-containing sieves, then saturates
    pullback stability and local character to a fixed point.
    """

    if not kinds:
        raise ValueError("at least one generator kind is required")
    for kind in kinds:
        _blocks(kind)

    covering: set[tuple[Context, Sieve]] = set()
    for target in ALL_CONTEXTS:
        maximal = frozenset(context for context in ALL_CONTEXTS if context <= target)
        for sieve in SIEVES_BY_TARGET[target]:
            if sieve == maximal:
                covering.add((target, sieve))
                continue
            if any(
                all(piece in sieve for piece in generating_family(target, kind))
                for kind in kinds
            ):
                covering.add((target, sieve))

    changed = True
    while changed:
        changed = False

        for target, sieve in tuple(covering):
            for along in ALL_CONTEXTS:
                if along <= target:
                    pulled = (along, _pullback_sieve(sieve, along))
                    if pulled not in covering:
                        covering.add(pulled)
                        changed = True

        for target in ALL_CONTEXTS:
            covering_sieves = tuple(
                sieve for cover_target, sieve in covering if cover_target == target
            )
            for local_cover in covering_sieves:
                for candidate in SIEVES_BY_TARGET[target]:
                    candidate_record = (target, candidate)
                    if candidate_record in covering:
                        continue
                    if all(
                        (member, _pullback_sieve(candidate, member)) in covering
                        for member in local_cover
                    ):
                        covering.add(candidate_record)
                        changed = True

    return frozenset(covering)


def _topology_axioms_hold(topology: frozenset[tuple[Context, Sieve]]) -> bool:
    """Independently check maximality, stability, and local character."""

    for target in ALL_CONTEXTS:
        maximal = frozenset(context for context in ALL_CONTEXTS if context <= target)
        if (target, maximal) not in topology:
            return False
    for target, sieve in topology:
        for along in ALL_CONTEXTS:
            if along <= target and (
                along,
                _pullback_sieve(sieve, along),
            ) not in topology:
                return False
    for target in ALL_CONTEXTS:
        covering_sieves = tuple(
            sieve for cover_target, sieve in topology if cover_target == target
        )
        for local_cover in covering_sieves:
            for candidate in SIEVES_BY_TARGET[target]:
                if all(
                    (member, _pullback_sieve(candidate, member)) in topology
                    for member in local_cover
                ) and (target, candidate) not in topology:
                    return False
    return True


def _composite_unit(
    presheaf: FinitePresheaf,
    section: Section,
    context: Context,
    outer_kind: str,
    inner_kind: str,
) -> Section:
    inner = ReflectedPresheaf(presheaf, inner_kind)
    outer = ReflectedPresheaf(inner, outer_kind)
    return outer.unit(inner.unit(section, context), context)


def verify_composition_for(presheaf: FinitePresheaf) -> dict[str, object]:
    """Exhaustively verify both canonical isomorphisms for one finite presheaf."""

    valid_base = validate_finite_presheaf(presheaf)
    if not valid_base:
        return {"presheaf_valid": False, "all_checks_pass": False}

    atomic = ReflectedPresheaf(presheaf, ATOMIC)
    ar = ReflectedPresheaf(ReflectedPresheaf(presheaf, RPM), ACBE)
    ra = ReflectedPresheaf(ReflectedPresheaf(presheaf, ACBE), RPM)
    functors_valid = all(validate_finite_presheaf(item) for item in (atomic, ar, ra))

    section_count = 0
    restriction_checks = 0
    unit_checks = 0
    bijections_hold = True
    inverse_laws_hold = True
    naturality_holds = True
    units_agree = True
    commutation_naturality_holds = True

    for context in ALL_CONTEXTS:
        atomic_sections = tuple(atomic.sections(context))
        for nested, outer_kind, inner_kind in (
            (ar, ACBE, RPM),
            (ra, RPM, ACBE),
        ):
            nested_sections = tuple(nested.sections(context))
            images = tuple(
                composite_to_atomic_section(
                    section, context, outer_kind, inner_kind
                )
                for section in nested_sections
            )
            section_count += len(nested_sections)
            if len(images) != len(set(images)) or set(images) != set(atomic_sections):
                bijections_hold = False
            if any(
                atomic_to_composite_section(
                    image, context, outer_kind, inner_kind
                )
                != nested_section
                for nested_section, image in zip(
                    nested_sections, images, strict=True
                )
            ):
                inverse_laws_hold = False
            if any(
                composite_to_atomic_section(
                    atomic_to_composite_section(
                        atomic_section, context, outer_kind, inner_kind
                    ),
                    context,
                    outer_kind,
                    inner_kind,
                )
                != atomic_section
                for atomic_section in atomic_sections
            ):
                inverse_laws_hold = False

            for nested_section in nested_sections:
                flattened = composite_to_atomic_section(
                    nested_section, context, outer_kind, inner_kind
                )
                for target in ALL_CONTEXTS:
                    if not target <= context:
                        continue
                    restriction_checks += 1
                    left = composite_to_atomic_section(
                        nested.restrict(nested_section, context, target),
                        target,
                        outer_kind,
                        inner_kind,
                    )
                    right = atomic.restrict(flattened, context, target)
                    if left != right:
                        naturality_holds = False

        for section in presheaf.sections(context):
            atomic_unit = atomic.unit(section, context)
            for outer_kind, inner_kind in ((ACBE, RPM), (RPM, ACBE)):
                unit_checks += 1
                nested_unit = _composite_unit(
                    presheaf, section, context, outer_kind, inner_kind
                )
                if (
                    composite_to_atomic_section(
                        nested_unit, context, outer_kind, inner_kind
                    )
                    != atomic_unit
                ):
                    units_agree = False

        for ar_section in ar.sections(context):
            flattened = composite_to_atomic_section(ar_section, context, ACBE, RPM)
            commuted = atomic_to_composite_section(flattened, context, RPM, ACBE)
            for target in ALL_CONTEXTS:
                if not target <= context:
                    continue
                left_restricted = ar.restrict(ar_section, context, target)
                left_flat = composite_to_atomic_section(
                    left_restricted, target, ACBE, RPM
                )
                left_commuted = atomic_to_composite_section(
                    left_flat, target, RPM, ACBE
                )
                right_restricted = ra.restrict(commuted, context, target)
                if left_commuted != right_restricted:
                    commutation_naturality_holds = False

    empty_context = frozenset()
    empty_context_terminalized = all(
        item.sections(empty_context) == ((),) for item in (atomic, ar, ra)
    )

    result: dict[str, object] = {
        "presheaf_valid": valid_base,
        "reflected_functors_valid": functors_valid,
        "canonical_maps_bijective": bijections_hold,
        "canonical_maps_inverse_laws": inverse_laws_hold,
        "canonical_maps_natural": naturality_holds,
        "composite_units_equal_atomic_unit": units_agree,
        "commutation_map_natural": commutation_naturality_holds,
        "empty_context_terminalized": empty_context_terminalized,
        "nested_sections_checked": section_count,
        "restriction_squares_checked": restriction_checks,
        "unit_components_checked": unit_checks,
    }
    result["all_checks_pass"] = all(
        result[key]
        for key in (
            "presheaf_valid",
            "reflected_functors_valid",
            "canonical_maps_bijective",
            "canonical_maps_inverse_laws",
            "canonical_maps_natural",
            "composite_units_equal_atomic_unit",
            "commutation_map_natural",
            "empty_context_terminalized",
        )
    )
    return result


def symbolic_certificate() -> dict[str, object]:
    """Return exhaustive context/topology facts independent of section values."""

    inclusions = tuple(
        (target, source)
        for source in ALL_CONTEXTS
        for target in ALL_CONTEXTS
        if target <= source
    )
    null_cover_exact = all(
        generating_family(frozenset(), kind) == ()
        for kind in (ACBE, RPM, ATOMIC)
    )
    support_pullback_stable = all(
        tuple(piece for piece in (target & item for item in normalized_support(source, kind)) if piece)
        == normalized_support(target, kind)
        for kind in (ACBE, RPM, ATOMIC)
        for target, source in inclusions
    )

    composite_indices_are_atoms = True
    for context in ALL_CONTEXTS:
        expected = tuple(frozenset({atom}) for atom in sorted(context))
        for outer_kind, inner_kind in ((ACBE, RPM), (RPM, ACBE)):
            flattened = tuple(
                inner_piece
                for outer_piece in normalized_support(context, outer_kind)
                for inner_piece in normalized_support(outer_piece, inner_kind)
            )
            if set(flattened) != set(expected) or len(flattened) != len(expected):
                composite_indices_are_atoms = False

    join_topology = generated_topology((ACBE, RPM))
    atomic_topology = generated_topology((ATOMIC,))
    topology_join_is_atomic = join_topology == atomic_topology
    join_topology_axioms_hold = _topology_axioms_hold(join_topology)
    atomic_topology_axioms_hold = _topology_axioms_hold(atomic_topology)

    result: dict[str, object] = {
        "atom_count": len(ALL_ATOMS),
        "context_count": len(ALL_CONTEXTS),
        "inclusion_count": len(inclusions),
        "sieve_count": sum(len(sieves) for sieves in SIEVES_BY_TARGET.values()),
        "null_cover_exact_at_empty": null_cover_exact,
        "normalized_support_pullback_stable": support_pullback_stable,
        "both_composite_index_families_are_atomic": composite_indices_are_atoms,
        "generated_join_topology_equals_atomic_topology": topology_join_is_atomic,
        "generated_join_satisfies_topology_axioms": join_topology_axioms_hold,
        "generated_atomic_satisfies_topology_axioms": atomic_topology_axioms_hold,
        "join_covering_sieve_count": len(join_topology),
        "atomic_covering_sieve_count": len(atomic_topology),
    }
    result["all_checks_pass"] = all(
        result[key]
        for key in (
            "null_cover_exact_at_empty",
            "normalized_support_pullback_stable",
            "both_composite_index_families_are_atomic",
            "generated_join_topology_equals_atomic_topology",
            "generated_join_satisfies_topology_axioms",
            "generated_atomic_satisfies_topology_axioms",
        )
    )
    return result


@dataclass(frozen=True, slots=True)
class _ConstantTwoPresheaf:
    def sections(self, context: Context) -> tuple[Section, ...]:
        _require_context(context)
        return (0, 1)

    def restrict(self, section: Section, source: Context, target: Context) -> Section:
        if not target <= source or section not in (0, 1):
            raise ValueError("ill-typed constant-presheaf restriction")
        return section


@dataclass(frozen=True, slots=True)
class _BitAssignmentPresheaf:
    def sections(self, context: Context) -> tuple[Section, ...]:
        _require_context(context)
        return tuple(tuple(bits) for bits in product((0, 1), repeat=len(context)))

    def restrict(self, section: Section, source: Context, target: Context) -> Section:
        if not target <= source:
            raise ValueError("ill-typed bit-assignment restriction")
        values = tuple(section)
        if len(values) != len(source):
            raise ValueError("bit assignment has the wrong arity")
        by_atom = dict(zip(sorted(source), values, strict=True))
        return tuple(by_atom[atom] for atom in sorted(target))


@dataclass(frozen=True, slots=True)
class _RepresentablePresheaf:
    represented: Context

    def sections(self, context: Context) -> tuple[Section, ...]:
        _require_context(context)
        return (("unique",),) if context <= self.represented else ()

    def restrict(self, section: Section, source: Context, target: Context) -> Section:
        if not target <= source or section not in self.sections(source):
            raise ValueError("ill-typed representable restriction")
        return ("unique",)


def run_certificate() -> dict[str, object]:
    """Run the symbolic audit and a deterministic suite of finite presheaves."""

    fixtures: tuple[tuple[str, FinitePresheaf], ...] = (
        ("constant_two_with_nonterminal_empty", _ConstantTwoPresheaf()),
        ("bit_assignments", _BitAssignmentPresheaf()),
    ) + tuple(
        (f"representable_{index:02d}", _RepresentablePresheaf(context))
        for index, context in enumerate(ALL_CONTEXTS)
    )
    fixture_results = {
        name: verify_composition_for(presheaf) for name, presheaf in fixtures
    }
    symbolic = symbolic_certificate()
    all_checks_pass = bool(symbolic["all_checks_pass"]) and all(
        bool(result["all_checks_pass"]) for result in fixture_results.values()
    )
    return {
        "symbolic": symbolic,
        "fixture_count": len(fixtures),
        "fixtures": fixture_results,
        "all_checks_pass": all_checks_pass,
    }
