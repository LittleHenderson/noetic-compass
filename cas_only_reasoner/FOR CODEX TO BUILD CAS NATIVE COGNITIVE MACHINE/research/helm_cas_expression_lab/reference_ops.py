"""Reference implementations of the admitted CAS operations -- THE EVALUATOR'S ORACLE, NEVER THE LEARNER'S.

Q2 of `FABLE_HELM_CAS_Implementation_Directive_v1.md`. Every function here mirrors, line for line,
an implementation that already exists in the engine or in CAS-Native, and `OPERATION_CONTRACTS.json`
pins that implementation by file path and sha256. Nothing here is invented: where the source is
silent, this module raises rather than guesses.

REFERENCE / LEARNER SEPARATION (directive D04, section 7). This module generates targets and checks
results. It must never be imported by a learned arm, wrapped as a solver callback, or used to build
an answer-derived mask. A learned candidate that reaches its answer by calling this file is a
`HYBRID_FIXED_OPERATOR`, not neural acquisition, and must be labelled so. `test_operation_contracts.py`
asserts that nothing under `research/helm_cas_expression_lab/learner*` imports this module.

Pure Python. No torch. No randomness. Every function is total on its declared domain and raises
`InvalidInput` outside it -- `INVALID_INPUT` is a distinct outcome from a wrong answer.
"""
import math

NOETICS = tuple(range(10))                 # ^0 .. ^9 (the engine spells them CO-0 .. CO-9: its CognitiveOperator index)
DOMAINS = ("P", "C", "E", "O")             # the engine's Domain order: Principled=0, Cognitive=1, Evaluative=2, Operational=3
NUM_STATES = 40
# Involution partners, verbatim from cas-engine/src/ontology/operators.rs `involute`.
_INVOLUTE = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 6, 6: 5, 7: 7, 8: 9, 9: 8}
SELF_DUAL = frozenset((0, 1, 4, 7))
RMS_LAW_TOLERANCE = 2.0 * 2.220446049250313e-16   # f64::EPSILON * 2.0, verbatim from rpm/mod.rs


class InvalidInput(ValueError):
    """The input is outside the operation's declared domain. Not a wrong answer: a refused question."""


def _is_noetic(value):
    """STRICT: an `int` in 0..9. Python would otherwise accept `2.0` and `True` as members of `range(10)`
    (`2.0 == 2`, `True == 1`), which would let a float or a boolean slip through a contract that says
    "int in 0..9" and return a float answer. INVALID_INPUT must be strict or it is not a domain."""
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 9


# ---------------------------------------------------------------------------------------------
# Coordinates. TWO conventions exist in the repository and the contract keeps them explicitly related.
# ---------------------------------------------------------------------------------------------
def state_index(domain, noetic):
    """The ENGINE / COMPILER coordinate: domain-major, `index = 10 * domain + noetic`, P0=0 ... O9=39.

    Verbatim `cas-engine/src/ontology/states.rs:51` and `api/notation/compiler.py:1410`. This is the
    lab's internal convention.
    """
    d = _domain_index(domain)
    if not _is_noetic(noetic):
        raise InvalidInput("noetic must be 0..9, got %r" % (noetic,))
    return 10 * d + noetic


def state_from_index(index):
    """Inverse of `state_index`. Mirrors `CognitiveStateId::from_linear_index`."""
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < NUM_STATES:
        raise InvalidInput("state index must be 0..39, got %r" % (index,))
    return DOMAINS[index // 10], index % 10


def tokenizer_id(domain, noetic):
    """The FROZEN TOKENIZER coordinate: Noetic-major, `id = 213 + 4 * noetic + domain`, ^0^P=213 ... ^9^O=252.

    Verified against `cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json` for all 40
    entries on 2026-09-21. NOT the same order as `state_index`; the contract records both and the test
    round-trips the map.
    """
    d = _domain_index(domain)
    if not _is_noetic(noetic):
        raise InvalidInput("noetic must be 0..9, got %r" % (noetic,))
    return 213 + 4 * noetic + d


def _domain_index(domain):
    if domain not in DOMAINS:
        raise InvalidInput("domain must be one of P/C/E/O, got %r" % (domain,))
    return DOMAINS.index(domain)


# ---------------------------------------------------------------------------------------------
# OP-1  involute : Noetic -> Noetic.  Unary, fixed table, self-inverse.
# ---------------------------------------------------------------------------------------------
def involute(noetic):
    """`CognitiveOperator::involute`, operators.rs. Pairs 2<->3, 5<->6, 8<->9; 0,1,4,7 fixed."""
    if not _is_noetic(noetic):
        raise InvalidInput("noetic must be 0..9, got %r" % (noetic,))
    return _INVOLUTE[noetic]


# ---------------------------------------------------------------------------------------------
# OP-2  compose : Noetic x Noetic -> Noetic.  `(a + b) mod 10`, ^0 identity.
# COMMUTATIVE AND ASSOCIATIVE: a modular sum solves any nesting without preserving grouping, so this
# operation is a CONFORMANCE test and a strong baseline, never evidence of order-sensitive reasoning
# (directive section 9). The contract carries that flag.
# ---------------------------------------------------------------------------------------------
def compose(a, b):
    """`CognitiveOperator::compose`, operators.rs:102-105; matches `COMPOSE_TABLE` in cas-native composition.py."""
    if not (_is_noetic(a) and _is_noetic(b)):
        raise InvalidInput("both operands must be 0..9, got %r, %r" % (a, b))
    return (a + b) % 10


# ---------------------------------------------------------------------------------------------
# OP-3  is_admissible : Noetic x State x State -> bool.  ASYMMETRIC and CONTEXT-SENSITIVE.
# This is the order-sensitive operation the directive asks for (section 7, "add a directional or
# context-sensitive operation only after its semantics are confirmed" -- confirmed below by test).
# ---------------------------------------------------------------------------------------------
def is_admissible(operator, source, target):
    """`CognitiveOperator::is_admissible`, operators.rs:110-125, CORRECTION 1.

    `source` and `target` are `(domain, noetic)` pairs.
      ^0              : admissible only on the diagonal, source == target.
      any other ^k    : admissible if source.domain == target.domain (intra-domain),
                        else admissible iff target.noetic == k (the operator mediates the crossing).
    """
    if not _is_noetic(operator):
        raise InvalidInput("operator must be 0..9, got %r" % (operator,))
    sd, sn = _check_state(source)
    td, tn = _check_state(target)
    if operator == 0:
        return (sd, sn) == (td, tn)
    if sd == td:
        return True
    return tn == operator


def _check_state(state):
    try:
        domain, noetic = state
    except (TypeError, ValueError):
        raise InvalidInput("state must be a (domain, noetic) pair, got %r" % (state,))
    _domain_index(domain)
    if not _is_noetic(noetic):
        raise InvalidInput("noetic must be 0..9, got %r" % (noetic,))
    return domain, noetic


# ---------------------------------------------------------------------------------------------
# OP-4  domain_descent_mask : () -> 40x40 bool.  Fixed. A state in domain d may attend to every
# state in domains <= d (P -> C -> E -> O). Verbatim `build_domain_descent_mask`, cas-native
# domain_descent.py:27-36. NOTE: that function indexes the 40 slots DOMAIN-MAJOR (rows 0-9 = P),
# i.e. the ENGINE convention, not the tokenizer's Noetic-major ids. Recorded as discrepancy DR-1.
# ---------------------------------------------------------------------------------------------
def domain_descent_mask():
    mask = [[False] * NUM_STATES for _ in range(NUM_STATES)]
    for d in range(4):
        for row in range(10 * d, 10 * d + 10):
            for col in range(0, 10 * (d + 1)):
                mask[row][col] = True
    return mask


def may_attend(source, target):
    """`domain_descent_mask()[state_index(source)][state_index(target)]`, for readable tests."""
    sd, sn = _check_state(source)
    td, tn = _check_state(target)
    return domain_descent_mask()[state_index(sd, sn)][state_index(td, tn)]


# ---------------------------------------------------------------------------------------------
# OP-5  rpm_embed / rpm_realize : [0,1] -> (s, s^2, sqrt s) -> [0,1].  Section law eps o eta = id.
# Verbatim cas-engine/src/rpm/mod.rs `embed`, `realize`, `verify_section_law`. CORRECTION 2: this is
# a section-retraction, NOT an adjunction -- eta o eps != id, and the test asserts BOTH directions.
# NUMERICAL POLICY: `embed` and `realize` are exact float operations; the section law is checked at
# tolerance 2 * f64::EPSILON exactly as the engine does. This is the one contract with a tolerance.
# ---------------------------------------------------------------------------------------------
def rpm_embed(score):
    if not isinstance(score, (int, float)) or isinstance(score, bool) or math.isnan(score) \
            or not (0.0 <= score <= 1.0):
        raise InvalidInput("score must be a number in [0, 1] and not NaN, got %r" % (score,))
    s = float(score)
    return (s, s * s, math.sqrt(s))


def rpm_realize(embedded):
    try:
        a, b, c = embedded
    except (TypeError, ValueError):
        raise InvalidInput("embedded must be a 3-tuple, got %r" % (embedded,))
    return float(a)


def rpm_section_law_holds(score):
    """|realize(embed(s)) - s| <= 2 * f64::EPSILON. True for every valid s in this implementation."""
    return abs(rpm_realize(rpm_embed(score)) - float(score)) <= RMS_LAW_TOLERANCE


def rpm_retraction_law_fails_for(embedded):
    """eta(eps(e)) != e for a general e: the information-loss direction. Returns True when it FAILS.

    This is not a defect; it is what section-retraction means (CORRECTION 2). A test that expected
    round-trip equality here would be asserting an adjunction the framework explicitly denies.
    """
    return rpm_embed(rpm_realize(embedded)) != tuple(float(x) for x in embedded)


ADMITTED = ("involute", "compose", "is_admissible", "domain_descent_mask", "rpm_embed_realize")
