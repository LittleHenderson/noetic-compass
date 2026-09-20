"""Noetica category discipline: Corrections 1, 2 and 3.

The project's master instructions mark four mathematical corrections MUST IMPLEMENT.
Correction 4 lives in :mod:`cncm.simplex`. This module carries the other three, which are
inseparable because they are all statements about the same objects: the state set ``I``, the
realization ``R(I)``, and the two morphisms between them.

CORRECTION 1 — admissibility relations
    Noetica is the smallest pullback-complete subcategory of FinSet. Each operator ``CO-k``
    has an admissibility relation ``Dk ⊆ I × I`` of valid ``(source, target)`` pairs, and
    ``D0 = {(I, I) : I ∈ I}`` is the identity on the diagonal only. Every operator
    application is guarded by :func:`is_admissible`.

    Only ``D0`` is frozen by the instructions. The other nine relations are an unresolved
    authority decision, and this module refuses rather than inventing them:

    * :func:`is_admissible` **raises** :class:`UnregisteredAdmissibility` for an operator
      whose relation is not frozen. It does not return ``False``. "We do not know" is not
      "no", and collapsing the two is the silent-failure mode this project exists to avoid.
    * :func:`admissibility_status` reports which relations are frozen, so a caller can tell
      the two refusals apart on purpose.

CORRECTION 2 — RPM is a section-retraction, NOT an adjunction
    ``ε ∘ η = id`` holds. ``η ∘ ε = id`` does **not** hold in general: re-embedding after
    realization may lose information. So

    * the gate must not assume reversibility, and
    * prerequisite satisfaction is ONE-DIRECTIONAL, and
    * initial satisfaction results are cached rather than re-derived after realization.

    The honest law for ``η ∘ ε`` is idempotence, and that is what is checked here.

CORRECTION 3 — Noetic Coverage uses the COUNIT, not the unit
    A covering morphism ``ε : R(I) → I`` points TOWARD the covered object. A unit-directed
    covering is refused by :func:`is_covering` with :class:`UnitCoveringRefused`.

``I`` here is the 40-element Cognitive State set, not the open simplex. Correction 4 says
the *target space* of a state vector is the open simplex; Correction 1's relation is over the
state labels. Both are 40, and :data:`COGNITIVE_STATES` is checked against
:data:`cncm.simplex.NUM_STATES` so the two cannot drift apart.

Pure standard library. No numeric runtime, no device, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .canonical import content_id, digest
from .model import CANONICAL_DOMAINS, CANONICAL_NOETICS
from .simplex import NUM_STATES

SCHEMA_VERSION = "cncm.noetica/0.1"

#: The ten cognitive operators, ``^0`` … ``^9``, in canonical order.
OPERATORS = tuple(f"^{index}" for index in range(len(CANONICAL_NOETICS)))

#: The 40 Cognitive States, listed ``P0-P9, C0-C9, E0-E9, O0-O9``, which is how the master
#: instructions enumerate them. This is the set the admissibility relation ranges over, and
#: **it is also the index authority for the 40 components of a state vector**: a
#: :class:`cncm.simplex.CognitiveStateVector` component ``k`` is the probability of
#: ``COGNITIVE_STATES[k]``. :mod:`cncm.simplex` deliberately says nothing about ordering, so
#: the ordering is fixed here, once, rather than assumed at each use.
COGNITIVE_STATES = tuple(
    f"{domain}{noetic}" for domain in CANONICAL_DOMAINS for noetic in CANONICAL_NOETICS
)

#: ``state label -> its index in a 40-component state vector``.
STATE_INDEX: dict[str, int] = {
    state: index for index, state in enumerate(COGNITIVE_STATES)
}


def state_at(index: int) -> str:
    """The state label for a state-vector component index."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise NoeticaError("a state index must be an integer")
    if not 0 <= index < len(COGNITIVE_STATES):
        raise NoeticaError(f"state index {index} is outside 0..{len(COGNITIVE_STATES) - 1}")
    return COGNITIVE_STATES[index]


def index_of(state: str) -> int:
    """The state-vector component index for a state label."""
    if state not in STATE_INDEX:
        raise NoeticaError(f"{state!r} is not one of the 40 cognitive states")
    return STATE_INDEX[state]

#: The 22 Capability Pathways: A0 (Pure Desire) + D1-D7 + W1-W7 + P1-P7.
DESIRE_ROOT = "A0"
DRIVE_NODES = tuple(f"D{index}" for index in range(1, 8))
WILL_NODES = tuple(f"W{index}" for index in range(1, 8))
PURPOSE_NODES = tuple(f"P{index}" for index in range(1, 8))
PATHWAY_NODES = (DESIRE_ROOT,) + DRIVE_NODES + WILL_NODES + PURPOSE_NODES

#: Names for the two label sets. Realization is a structure over *some* set of labelled
#: objects, and the set has to be named: the labels are not disjoint.
STATE_DOMAIN = "COGNITIVE_STATES"
PATHWAY_DOMAIN = "PATHWAY_NODES"
DOMAINS: dict[str, tuple] = {
    STATE_DOMAIN: COGNITIVE_STATES,
    PATHWAY_DOMAIN: PATHWAY_NODES,
}

#: Labels that name a cognitive state AND a pathway node. ``P1``-``P7`` are each
#: ``P<noetic>`` in the domain-major state listing and ``P<purpose>`` in the pathway
#: listing. **These are genuinely ambiguous and no resolution is invented here.** Every
#: function in this module takes the domain explicitly so that a caller must say which one
#: it means, and :func:`label_kinds` reports the collision instead of guessing.
AMBIGUOUS_LABELS = frozenset(COGNITIVE_STATES) & frozenset(PATHWAY_NODES)


def labels_for(domain: str) -> tuple:
    if domain not in DOMAINS:
        raise NoeticaError(f"unknown label domain {domain!r}")
    return DOMAINS[domain]


def label_kinds(label: str) -> tuple[str, ...]:
    """Which label sets contain ``label``: one name, both names, or none."""
    return tuple(domain for domain, labels in DOMAINS.items() if label in labels)


class NoeticaError(ValueError):
    """A Noetica law was violated, or an unfrozen authority was asked to decide."""


class UnregisteredAdmissibility(NoeticaError):
    """Correction 1: the operator's admissibility relation is not frozen.

    Raised instead of returning ``False``. A relation that has not been decided cannot
    answer "no", and a guard that silently refuses everything is indistinguishable from a
    guard that works.
    """

    def __init__(self, operator: str) -> None:
        self.operator = operator
        super().__init__(
            f"admissibility relation for operator {operator!r} is not frozen; refusing to "
            f"decide, because an undecided relation is not an empty one"
        )


class SectionRetractionError(NoeticaError):
    """Correction 2: ``ε ∘ η = id`` was violated. This one is a real failure."""


class UnitCoveringRefused(NoeticaError):
    """Correction 3: a covering morphism was requested in the unit direction."""


class RefusesRecomputation(NoeticaError):
    """Correction 2: a cached satisfaction result was asked to be re-derived."""


# --------------------------------------------------------------------------- #
# CORRECTION 1 — admissibility relations.
# --------------------------------------------------------------------------- #


class AdmissibilityStatus(Enum):
    FROZEN = "FROZEN"
    UNRESOLVED_AUTHORITY_DECISION = "UNRESOLVED_AUTHORITY_DECISION"


@dataclass(frozen=True)
class AdmissibilityRelation:
    """``Dk ⊆ I × I`` for one operator, with the authority it came from."""

    operator: str
    status: AdmissibilityStatus
    pairs: frozenset
    authority: str
    note: str = ""

    def contains(self, source: str, target: str) -> bool:
        return (source, target) in self.pairs

    def digest(self) -> str:
        return digest(
            {
                "schema": SCHEMA_VERSION,
                "operator": self.operator,
                "status": self.status.value,
                "pairs": sorted(self.pairs),
                "authority": self.authority,
            }
        )


def _relation(operator: str, pairs: Iterable[tuple[str, str]], authority: str, note: str = ""):
    return AdmissibilityRelation(
        operator=operator,
        status=AdmissibilityStatus.FROZEN,
        pairs=frozenset(pairs),
        authority=authority,
        note=note,
    )


def _unresolved(operator: str, note: str):
    return AdmissibilityRelation(
        operator=operator,
        status=AdmissibilityStatus.UNRESOLVED_AUTHORITY_DECISION,
        pairs=frozenset(),
        authority="NOT_FROZEN",
        note=note,
    )


#: ``D0 = {(I, I) : I ∈ I}`` — the identity on the diagonal only. This is the one relation
#: the master instructions state verbatim, so it is the one relation populated here.
#: The other nine are marked unresolved and :func:`is_admissible` refuses on them.
ADMISSIBILITY: dict[str, AdmissibilityRelation] = {
    "^0": _relation(
        "^0",
        ((state, state) for state in COGNITIVE_STATES),
        authority="CLAUDE.md CORRECTION 1, verbatim: D0 = {(I,I) : I in I}",
        note="identity on the diagonal only; every off-diagonal pair is inadmissible",
    ),
    **{
        operator: _unresolved(
            operator,
            "no frozen authority states Dk for this operator; the instruction names the "
            "mechanism but not the relation, so it is not invented here",
        )
        for operator in OPERATORS
        if operator != "^0"
    },
}


def admissibility_status(operator: str) -> AdmissibilityStatus:
    relation = ADMISSIBILITY.get(operator)
    if relation is None:
        raise NoeticaError(f"unknown operator {operator!r}")
    return relation.status


def frozen_operators() -> tuple[str, ...]:
    """Operators whose admissibility relation is frozen, in canonical order."""
    return tuple(
        operator
        for operator in OPERATORS
        if ADMISSIBILITY[operator].status is AdmissibilityStatus.FROZEN
    )


def unresolved_operators() -> tuple[str, ...]:
    """Operators whose admissibility relation is an open authority decision."""
    return tuple(
        operator
        for operator in OPERATORS
        if ADMISSIBILITY[operator].status is not AdmissibilityStatus.FROZEN
    )


def is_admissible(operator: str, source: str, target: str) -> bool:
    """The guard that must precede every operator application.

    Raises :class:`UnregisteredAdmissibility` when the relation is not frozen, and
    :class:`NoeticaError` when the operator or a state label is unknown. Returns the
    membership test only when the relation is actually frozen.
    """
    relation = ADMISSIBILITY.get(operator)
    if relation is None:
        raise NoeticaError(f"unknown operator {operator!r}")
    if relation.status is not AdmissibilityStatus.FROZEN:
        raise UnregisteredAdmissibility(operator)
    for label, value in (("source", source), ("target", target)):
        if value not in COGNITIVE_STATES:
            raise NoeticaError(f"{label} {value!r} is not one of the 40 cognitive states")
    return relation.contains(source, target)


def admissibility_profile() -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "correction": "CORRECTION_1_ADMISSIBILITY_RELATIONS",
        "states": len(COGNITIVE_STATES),
        "operators": len(OPERATORS),
        "frozen": list(frozen_operators()),
        "unresolved": list(unresolved_operators()),
        "relations": {
            operator: {
                "status": ADMISSIBILITY[operator].status.value,
                "pairs": len(ADMISSIBILITY[operator].pairs),
                "authority": ADMISSIBILITY[operator].authority,
                "digest": ADMISSIBILITY[operator].digest(),
            }
            for operator in OPERATORS
        },
    }


# --------------------------------------------------------------------------- #
# CORRECTION 2 — realization is a section-retraction.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Realization:
    """An element of ``R(I)``: a labelled object together with whatever structure realizing
    it added. ``context`` is that extra structure, and it is exactly what ``ε`` forgets.

    ``domain`` names which label set ``state`` belongs to. It is not decoration: ``P1``-``P7``
    belong to both sets, so a realization that did not say which one it meant would be
    ambiguous exactly where the pathway graph meets the state space.
    """

    state: str
    context: tuple = ()
    domain: str = STATE_DOMAIN

    def identity(self) -> str:
        return content_id(
            "cncm-realization",
            {"domain": self.domain, "state": self.state, "context": list(self.context)},
        )


def _check_label(label: str, domain: str, role: str) -> None:
    if domain not in DOMAINS:
        raise NoeticaError(f"unknown label domain {domain!r}")
    if label not in DOMAINS[domain]:
        raise NoeticaError(f"{role} {label!r} is not in {domain}")


def embed(state: str, *, domain: str = STATE_DOMAIN) -> Realization:
    """``η : I → R(I)``. The embedding always carries the neutral context.

    The neutral context is the choice this model makes explicit: it is why ``η ∘ ε`` loses
    information whenever a realization carries anything else.
    """
    _check_label(state, domain, "state")
    return Realization(state=state, context=(), domain=domain)


def realize(realization: Realization, *, domain: str = STATE_DOMAIN) -> str:
    """``ε : R(I) → I``. Forgets the context and returns the label.

    ``domain`` is checked against the realization's own domain, so a pathway realization can
    never be realized as a cognitive state just because the labels happen to look alike.
    """
    if not isinstance(realization, Realization):
        raise NoeticaError("realize expects a Realization")
    if realization.domain != domain:
        raise NoeticaError(
            f"realization is in {realization.domain}, not {domain}; {realization.state!r} "
            f"does not identify which object is meant"
        )
    _check_label(realization.state, domain, "state")
    return realization.state


def elaborate(
    state: str, context: Iterable[str], *, domain: str = STATE_DOMAIN
) -> Realization:
    """Build a realization that carries structure beyond its image under ``ε``.

    This exists so the loss in ``η ∘ ε`` can be witnessed rather than asserted.
    """
    _check_label(state, domain, "state")
    return Realization(state=state, context=tuple(context), domain=domain)


@dataclass(frozen=True)
class SectionRetractionWitness:
    """What the two round trips actually do, measured rather than assumed."""

    state: str
    section_holds: bool
    retraction_holds: bool
    idempotent: bool
    information_lost: bool
    lost_context: tuple

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "section_holds": self.section_holds,
            "retraction_holds": self.retraction_holds,
            "idempotent": self.idempotent,
            "information_lost": self.information_lost,
            "lost_context": list(self.lost_context),
        }


def section_retraction_witness(
    state: str, context: Iterable[str] = (), *, domain: str = STATE_DOMAIN
) -> SectionRetractionWitness:
    """Check both round trips for one realization.

    ``ε ∘ η = id`` must hold — a violation raises :class:`SectionRetractionError`, because
    that law is not optional. ``η ∘ ε`` is *measured*: ``retraction_holds`` is ``False``
    whenever the realization carried context, which is the whole content of Correction 2.
    ``idempotent`` is the law that does hold, and is the one a gate may rely on.
    """
    realization = elaborate(state, context, domain=domain)
    embedded = embed(state, domain=domain)
    if realize(embedded, domain=domain) != state:
        raise SectionRetractionError(
            f"epsilon after eta is not the identity at {state!r}: "
            f"got {realize(embedded, domain=domain)!r}"
        )
    once = embed(realize(realization, domain=domain), domain=domain)
    twice = embed(realize(once, domain=domain), domain=domain)
    return SectionRetractionWitness(
        state=state,
        section_holds=True,
        retraction_holds=once == realization,
        idempotent=once == twice,
        information_lost=once != realization,
        lost_context=tuple(realization.context),
    )


def round_trip_is_identity(
    state: str, context: Iterable[str] = (), *, domain: str = STATE_DOMAIN
) -> bool:
    """``η ∘ ε = id`` at this realization. ``False`` whenever context was lost."""
    return section_retraction_witness(state, context, domain=domain).retraction_holds


# The 22 capability pathways. ``A0 → Dn → Wn → Pn → Outcome``.
def rpm_chain(index: int) -> tuple[str, str, str, str]:
    """The four prerequisite nodes of one RPM chain, ``A0 → Dn → Wn → Pn``."""
    if not 1 <= index <= 7:
        raise NoeticaError("RPM chains are indexed 1..7")
    return (DESIRE_ROOT, f"D{index}", f"W{index}", f"P{index}")


#: ``node -> its single prerequisite``. One-directional by construction: the map is not
#: invertible on purpose, and no reverse entry exists.
PREREQUISITE: dict[str, str | None] = {DESIRE_ROOT: None}
for _index in range(1, 8):
    PREREQUISITE[f"D{_index}"] = DESIRE_ROOT
    PREREQUISITE[f"W{_index}"] = f"D{_index}"
    PREREQUISITE[f"P{_index}"] = f"W{_index}"


def prerequisite_of(node: str) -> str | None:
    if node not in PREREQUISITE:
        raise NoeticaError(f"unknown pathway node {node!r}")
    return PREREQUISITE[node]


def enables(prerequisite: str, node: str) -> bool:
    """Is ``prerequisite`` the immediate prerequisite of ``node``? One-directional.

    ``enables("A0", "D1")`` is ``True`` and ``enables("D1", "A0")`` is ``False``. There is no
    path from a node back to its prerequisite: satisfaction flows one way only.
    """
    if prerequisite not in PREREQUISITE or node not in PREREQUISITE:
        raise NoeticaError("enables takes two known pathway nodes")
    return PREREQUISITE[node] == prerequisite


def satisfied_chain(node: str) -> tuple[str, ...]:
    """The prerequisites that must be satisfied before ``node``, nearest last.

    Returned in the order they have to be satisfied. The chain is walked toward the root,
    never back down it.
    """
    if node not in PREREQUISITE:
        raise NoeticaError(f"unknown pathway node {node!r}")
    chain: list[str] = []
    cursor = PREREQUISITE[node]
    while cursor is not None:
        chain.append(cursor)
        cursor = PREREQUISITE[cursor]
    chain.reverse()
    return tuple(chain)


@dataclass
class PrerequisiteGate:
    """An RPM gate that caches initial satisfaction instead of re-deriving it.

    The instruction is explicit: the gate must not assume reversibility, and initial
    satisfaction results are cached. Two consequences are enforced here rather than
    documented and hoped for.

    * :meth:`satisfy` freezes a node's satisfaction the first time it is established. Later
      attempts raise :class:`RefusesRecomputation` unless :meth:`reset` is called with a
      reason. A gate that silently re-derives is a gate whose answer depends on when it was
      asked.
    * :meth:`realize_node` changes the node's realization without touching the cache. This is
      the section-retraction asymmetry made operational: realization may move the object, and
      the cached satisfaction of its prerequisites is still the cached satisfaction.
    """

    satisfied_on_initial: dict = field(default_factory=dict)
    realizations: dict = field(default_factory=dict)
    recomputation_refusals: int = 0
    realizations_applied: int = 0

    def satisfy(self, node: str, *, evidence: str) -> None:
        if node not in PREREQUISITE:
            raise NoeticaError(f"unknown pathway node {node!r}")
        if not isinstance(evidence, str) or not evidence:
            raise NoeticaError("satisfaction needs non-empty evidence")
        if node in self.satisfied_on_initial:
            self.recomputation_refusals += 1
            raise RefusesRecomputation(
                f"{node!r} was already satisfied on initial evaluation with "
                f"{self.satisfied_on_initial[node]!r}; the cached result is not re-derived"
            )
        self.satisfied_on_initial[node] = evidence

    def is_satisfied(self, node: str) -> bool:
        if node not in PREREQUISITE:
            raise NoeticaError(f"unknown pathway node {node!r}")
        return node in self.satisfied_on_initial

    def evidence(self, node: str) -> str | None:
        return self.satisfied_on_initial.get(node)

    def realize_node(self, node: str, context: Iterable[str] = ()) -> Realization:
        """Apply ``η`` to a satisfied pathway node, leaving the satisfaction cache untouched."""
        if node not in PATHWAY_NODES:
            raise NoeticaError(f"unknown pathway node {node!r}")
        if node not in self.satisfied_on_initial:
            raise NoeticaError(f"{node!r} is not satisfied; realization is not admission")
        realization = elaborate(node, context, domain=PATHWAY_DOMAIN)
        self.realizations[node] = realization
        self.realizations_applied += 1
        return realization

    def admits(self, node: str) -> bool:
        """Admission requires the node itself and every prerequisite, read from the cache."""
        return all(
            self.is_satisfied(step) for step in (*satisfied_chain(node), node)
        )

    def reset(self, node: str, *, reason: str) -> None:
        """The only way to clear a cached satisfaction, and it must be justified."""
        if not isinstance(reason, str) or not reason:
            raise NoeticaError("a reset must carry a reason")
        self.satisfied_on_initial.pop(node, None)

    def profile(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "correction": "CORRECTION_2_SECTION_RETRACTION",
            "cached": dict(sorted(self.satisfied_on_initial.items())),
            "realizations": {
                node: realization.identity()
                for node, realization in sorted(self.realizations.items())
            },
            "recomputation_refusals": self.recomputation_refusals,
            "realizations_applied": self.realizations_applied,
            "gate_assumes_reversibility": False,
        }


# --------------------------------------------------------------------------- #
# CORRECTION 3 — covering morphisms use the counit.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CoveringMorphism:
    """``ε : R(I) → I``, pointing TOWARD the covered object ``I``."""

    covered: str
    direction: str
    counit_digest: str

    def apply(self, realization: Realization) -> str:
        if realization.domain != STATE_DOMAIN or realization.state != self.covered:
            raise NoeticaError(
                f"covering of {self.covered!r} cannot be applied to a realization of "
                f"{realization.state!r} in {realization.domain}"
            )
        return realize(realization)


def covering_morphism(covered: str) -> CoveringMorphism:
    """The covering morphism onto ``covered``, built from the counit ``ε``."""
    if covered not in COGNITIVE_STATES:
        raise NoeticaError(f"{covered!r} is not one of the 40 cognitive states")
    return CoveringMorphism(
        covered=covered,
        direction="TOWARD_COVERED_OBJECT",
        counit_digest=digest({"counit": "epsilon", "covered": covered}),
    )


def is_covering(source: Realization, target: str) -> bool:
    """Is ``source`` a covering of state ``target``, with the morphism pointing target-ward?

    Yes exactly when ``source`` is a realization of ``target`` and the morphism used is the
    counit ``ε``. The unit direction is refused: a covering that points away from the thing
    it covers is not a covering, and accepting one would silently invert Correction 3.
    """
    if not isinstance(source, Realization):
        raise NoeticaError("is_covering expects a Realization as the source")
    if source.domain != STATE_DOMAIN:
        raise NoeticaError(
            f"covering is a statement about cognitive states, not {source.domain}"
        )
    if target not in COGNITIVE_STATES:
        raise NoeticaError(f"{target!r} is not one of the 40 cognitive states")
    if source.state != target:
        raise UnitCoveringRefused(
            f"a realization of {source.state!r} cannot cover {target!r}; a covering "
            f"morphism points toward the object it covers, and the two must agree"
        )
    return covering_morphism(target).apply(source) == target


def covering_profile() -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "correction": "CORRECTION_3_COVERAGE_USES_COUNIT",
        "rule": "Noe-Cov-3 uses epsilon: R(I) -> I, toward the covered object",
        "unit_direction": "REFUSED",
        "noetic_cov_3": "counit",
    }


__all__ = [
    "ADMISSIBILITY",
    "AMBIGUOUS_LABELS",
    "COGNITIVE_STATES",
    "DESIRE_ROOT",
    "DOMAINS",
    "DRIVE_NODES",
    "OPERATORS",
    "PATHWAY_DOMAIN",
    "PATHWAY_NODES",
    "PREREQUISITE",
    "PURPOSE_NODES",
    "RefusesRecomputation",
    "AdmissibilityRelation",
    "AdmissibilityStatus",
    "CoveringMorphism",
    "NoeticaError",
    "PrerequisiteGate",
    "Realization",
    "SCHEMA_VERSION",
    "STATE_DOMAIN",
    "SectionRetractionError",
    "SectionRetractionWitness",
    "UnitCoveringRefused",
    "UnregisteredAdmissibility",
    "WILL_NODES",
    "admissibility_profile",
    "admissibility_status",
    "covering_morphism",
    "covering_profile",
    "elaborate",
    "embed",
    "enables",
    "frozen_operators",
    "is_admissible",
    "is_covering",
    "label_kinds",
    "labels_for",
    "prerequisite_of",
    "realize",
    "rpm_chain",
    "satisfied_chain",
    "section_retraction_witness",
    "round_trip_is_identity",
    "unresolved_operators",
]
