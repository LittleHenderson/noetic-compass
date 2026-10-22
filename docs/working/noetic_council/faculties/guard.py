"""guard.py -- the guardrail, made out of types instead of checks.

WHAT THIS MODULE DOES
---------------------
RB-I (helm_rb_i_faculties_design_v1) puts seven scheduled actions on top of a recipe brain
and states the one rule that keeps them honest (FACULTIES.md section 1):

    imagination may propose candidates, but imagined data may never verify a candidate or
    change what the brain believes. "Randomness may only propose; the verifier, the receipts
    and the RPM Gate always decide."

This module makes that rule a property of the objects rather than a promise in a docstring.
Three doors, and each is shut by construction:

  1. **`RealEvidence` and `ImaginedEvidence` are two different types, and neither inherits
     from the other.** A verifier call takes `RealEvidence`. `isinstance(imagined, RealEvidence)`
     is `False`, so an imagined world's rows cannot be handed to a verification call at all --
     not blocked by a flag, blocked by the type of the argument. `verify` refuses the imagined
     type with `IMAGINED_EVIDENCE_CANNOT_VERIFY` before any checker is looked at.

  2. **Real evidence refuses an `INTERNAL` row.** A row is tagged `REAL` or `INTERNAL`
     (FACULTIES.md Rule P). `RealEvidence` refuses any row tagged `INTERNAL` with the design's
     own code, `REFUSE:INTERNAL_WITNESS`. So imagined rows cannot be laundered into real
     evidence by building a `RealEvidence` around them, and `ImaginedEvidence` refuses to hold
     a `REAL` row at all.

  3. **A faculty's return value is checked for the two things it may never carry** -- a Bias
     write, and a candidate that is not `HELD`. `check_faculty_return` walks the returned
     value and refuses either. The faculties in `faculties.py` pass every return through it.

A fourth door is here because "changing what the brain believes" has exactly one shape in this
package: a write to the Bias. `believe()` is the only function that writes to a Bias on a
verified candidate, and it refuses anything but an `ADMITTED` verdict minted on
`RealEvidence`. A candidate that was never verified, or that was refused, or that came from a
daydream, has nothing to pass to it.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT run a faculty, a buffer or a loop. It mints verdicts and it checks return
    values; `held.py` keeps the store, `faculties.py` runs the four faculties, `drive_loop.py`
    schedules them.
  * It does NOT decide what a candidate must prove. The default checker is one exact-fit rule
    (`MIN_SUPPORT_ROWS` rows carrying the candidate's canonical form); a caller may pass its
    own. The checker only ever runs on `RealEvidence` -- it cannot be reached with anything
    else, which is the whole point of door 1.
  * It does NOT decide provenance. A caller that labels an imagined row `REAL` is lying about
    where a row came from, and no type in this module can stop a lie. Door 2 stops the
    accidental and the structural routes; the design's answer to a lie is the writer's witness
    set and the receipt (Rule P, test plan H4), and neither the writer nor the receipts are in
    this build.
  * It does NOT gate, score, threshold, learn or call any network. Standard library only.
  * It is NOT a security boundary against someone editing these files. It is a boundary of the
    API's shape: through the public surface, imagined data has no route to a verdict and a
    faculty has no route to the Bias.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

__all__ = [
    "GuardRefusal",
    # the four buffer words (the guardrail's vocabulary; held.py imports them from here)
    "HELD", "ADMITTED", "REFUSED", "EXPIRED", "STATE_WORDS",
    # evidence
    "Row", "Evidence", "RealEvidence", "ImaginedEvidence",
    "REAL", "INTERNAL", "REAL_EVIDENCE", "IMAGINED_EVIDENCE", "REAL_SOURCES",
    "evidence_kind",
    # verdicts and the one verifier
    "Verdict", "is_verdict", "verify", "exact_fit_checker", "MIN_SUPPORT_ROWS",
    # the faculty return check
    "BiasWriteAttempt", "check_faculty_return",
    # the Bias door
    "BiasReading", "bias_reading", "coordinator_for_faculty", "FACULTY_COORDINATOR_PREFIX",
    "believe",
]

#: The four words a held candidate can be in. `HELD` is the only one a faculty can write.
HELD = "HELD"
ADMITTED = "ADMITTED"
REFUSED = "REFUSED"
EXPIRED = "EXPIRED"
STATE_WORDS = (HELD, ADMITTED, REFUSED, EXPIRED)

#: The two row tags, and the two evidence kinds. Spelled once, read everywhere.
REAL = "REAL"
INTERNAL = "INTERNAL"
ROW_TAGS = (REAL, INTERNAL)
REAL_EVIDENCE = "REAL"
IMAGINED_EVIDENCE = "IMAGINED"

#: Where a real row may come from (ARCHITECTURE.md section 1 step 0: new real rows / world
#: answers, tagged REAL). Kept closed so "real" is a named source, not a default.
REAL_SOURCES = ("REAL_ROWS", "WORLD_ANSWER")

#: Refusal codes. Every refusal in this package carries one of these, so a caller reads one
#: vocabulary. The three the owning instruction names are the first three.
IMAGINED_EVIDENCE_CANNOT_VERIFY = "IMAGINED_EVIDENCE_CANNOT_VERIFY"
REFUSE_INTERNAL_WITNESS = "REFUSE:INTERNAL_WITNESS"
FACULTY_RETURNED_ADMITTED_CANDIDATE = "FACULTY_RETURNED_ADMITTED_CANDIDATE"
EVIDENCE_IS_NOT_REAL_EVIDENCE = "EVIDENCE_IS_NOT_REAL_EVIDENCE"
IMAGINED_EVIDENCE_TAKES_INTERNAL_ROWS_ONLY = "IMAGINED_EVIDENCE_TAKES_INTERNAL_ROWS_ONLY"
REAL_EVIDENCE_NEEDS_ROWS = "REAL_EVIDENCE_NEEDS_ROWS"
REAL_EVIDENCE_SOURCE_NOT_NAMED = "REAL_EVIDENCE_SOURCE_NOT_NAMED"
IMAGINED_EVIDENCE_NEEDS_A_WORLD = "IMAGINED_EVIDENCE_NEEDS_A_WORLD"
ROW_TAG_NOT_A_WORD = "ROW_TAG_NOT_A_WORD"
ROW_NEEDS_A_NAME = "ROW_NEEDS_A_NAME"
CANDIDATE_NOT_A_CANDIDATE = "CANDIDATE_NOT_A_CANDIDATE"
CHECKER_NOT_CALLABLE = "CHECKER_NOT_CALLABLE"
VERDICT_MUST_BE_MINTED = "VERDICT_MUST_BE_MINTED"
FACULTY_RETURNED_BIAS_WRITE = "FACULTY_RETURNED_BIAS_WRITE"
FACULTY_RETURNED_A_VERDICT = "FACULTY_RETURNED_A_VERDICT"
FACULTY_RETURNED_UNHELD_CANDIDATE = "FACULTY_RETURNED_UNHELD_CANDIDATE"
FACULTY_RETURNED_EVIDENCE = "FACULTY_RETURNED_EVIDENCE"
FACULTY_RETURNED_LIVE_OBJECT = "FACULTY_RETURNED_LIVE_OBJECT"
FACULTY_NOT_NAMED = "FACULTY_NOT_NAMED"
BELIEF_NEEDS_AN_ADMITTED_VERDICT = "BELIEF_NEEDS_AN_ADMITTED_VERDICT"
BELIEF_NEEDS_REAL_EVIDENCE = "BELIEF_NEEDS_REAL_EVIDENCE"
BELIEVE_CALLED_WITHOUT_A_VERDICT = "BELIEVE_CALLED_WITHOUT_A_VERDICT"
BIAS_READING_NEEDS_A_BIAS = "BIAS_READING_NEEDS_A_BIAS"
COORDINATOR_NOT_NAMED = "COORDINATOR_NOT_NAMED"

#: The prefix every faculty's coordinator name carries. The Bias's owner is a different name,
#: so the Bias itself refuses a write under any name starting with this one -- that refusal is
#: `BIAS_OWNED_BY_ANOTHER_COORDINATOR`, and it comes from the copied Bias, not from this file.
FACULTY_COORDINATOR_PREFIX = "FACULTY:"

#: How many real rows must carry a candidate's canonical form before the default checker
#: admits it.
MIN_SUPPORT_ROWS = 8
# UNDECIDED IN DESIGN: whether the support mark for admitting a faculty's candidate is the LSR-T4 8-new-rows mark -- DEFINITION.md section 2 U-c names "the 8-new-rows support mark of LSR-T4" for VERIFY and RB-I never states whether a candidate born in the held buffer must clear the same number, so this build applies 8 and lets a caller override it.

#: Deepest nesting a return value may carry before the scanner refuses to walk it. Not a
#: design number: a bound so a cyclic structure cannot hang the check.
MAX_SCAN_DEPTH = 8


class GuardRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# Rows: the smallest unit of evidence, and its tag
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Row:
    """One row of data, tagged with where it came from.

    A row is `REAL` (it arrived from outside; ARCHITECTURE.md section 1 step 0) or `INTERNAL`
    (the brain's imagination produced it; FACULTIES.md section 1 Rule P). The tag is the whole
    of the row's provenance as far as this build is concerned, and it is checked by both
    evidence types.
    """

    row_id: str
    tag: str
    data: object = None

    def __post_init__(self) -> None:
        if not isinstance(self.row_id, str) or not self.row_id.strip():
            raise GuardRefusal(ROW_NEEDS_A_NAME, f"a row needs a name, got {self.row_id!r}")
        if self.tag not in ROW_TAGS:
            raise GuardRefusal(
                ROW_TAG_NOT_A_WORD,
                f"row {self.row_id!r} is tagged {self.tag!r}; a row is {REAL} or {INTERNAL}",
            )

    @property
    def is_real(self) -> bool:
        return self.tag == REAL

    @property
    def is_internal(self) -> bool:
        return self.tag == INTERNAL


class Evidence:
    """The base of the two evidence types. It has no verify power and no conversion method.

    This class exists only so `evidence_kind` can answer for both. It deliberately carries no
    `as_real`, no `rows_as_real`, no `verify` and no flag: the two concrete types below are
    siblings, and no path turns one into the other.
    """

    KIND = None

    def rows(self) -> tuple:
        raise NotImplementedError


class RealEvidence(Evidence):
    """Rows that came from outside. The only type a verification call accepts.

    Refuses, in this order: no rows, rows that are not `Row`s, any row tagged `INTERNAL`
    (`REFUSE:INTERNAL_WITNESS`, FACULTIES.md Rule P), and a source that is not one of
    `REAL_SOURCES`. There is no flag that relaxes any of it.
    """

    KIND = REAL_EVIDENCE

    def __init__(self, rows, source) -> None:
        if source not in REAL_SOURCES:
            raise GuardRefusal(
                REAL_EVIDENCE_SOURCE_NOT_NAMED,
                f"real evidence must name its source, one of {list(REAL_SOURCES)}, got "
                f"{source!r}; 'real' is a named source here, not a default",
            )
        try:
            materialised = tuple(rows)
        except TypeError:
            raise GuardRefusal(
                EVIDENCE_IS_NOT_REAL_EVIDENCE,
                f"real evidence was built from a {type(rows).__name__}, which is not a set of "
                f"rows at all; another evidence type cannot be read as a witness set",
            ) from None
        if not materialised:
            raise GuardRefusal(
                REAL_EVIDENCE_NEEDS_ROWS,
                "real evidence with no rows proves nothing, and an empty witness set would "
                "admit every candidate",
            )
        for row in materialised:
            if not isinstance(row, Row):
                raise GuardRefusal(
                    EVIDENCE_IS_NOT_REAL_EVIDENCE,
                    f"real evidence holds Row objects, got {type(row).__name__}; an "
                    f"{type(row).__name__} cannot be read as a witnessed row",
                )
            if row.tag == INTERNAL:
                raise GuardRefusal(
                    REFUSE_INTERNAL_WITNESS,
                    f"row {row.row_id!r} is tagged INTERNAL, so it cannot be a witness "
                    f"(FACULTIES.md Rule P: a write whose witness set contains one INTERNAL "
                    f"row is refused). Imagined data does not become real by being placed in "
                    f"a RealEvidence",
                )
        self._rows = materialised
        self._source = source

    @property
    def source(self) -> str:
        return self._source

    def rows(self) -> tuple:
        return self._rows

    def canonical_forms(self) -> tuple:
        """Every `canonical_form` named by these rows, in row order."""
        out = []
        for row in self._rows:
            if isinstance(row.data, Mapping):
                form = row.data.get("canonical_form")
                if isinstance(form, str) and form:
                    out.append(form)
        return tuple(out)

    def __repr__(self) -> str:
        return f"RealEvidence({len(self._rows)} rows, source={self._source!r})"


class ImaginedEvidence(Evidence):
    """Rows an imagined world produced. It is NOT a `RealEvidence` and cannot become one.

    Two things make that structural rather than stated:

      * it is a sibling of `RealEvidence`, not a subclass, so `isinstance(imagined,
        RealEvidence)` is `False` without anybody checking anything;
      * it refuses to hold a `REAL` row (`IMAGINED_EVIDENCE_TAKES_INTERNAL_ROWS_ONLY`), so it
        cannot carry a real witness even by accident.

    It also has no `canonical_forms` reader, which is the method the default checker reads. So
    a caller that removed every type check in this module would still not get imagined data
    past `exact_fit_checker`: the object does not have the reader.

    It has no method that returns rows a `RealEvidence` would accept, because every row it
    holds is tagged `INTERNAL` and `RealEvidence` refuses those.
    """

    KIND = IMAGINED_EVIDENCE

    def __init__(self, world_id, rows) -> None:
        if not isinstance(world_id, str) or not world_id.strip():
            raise GuardRefusal(
                IMAGINED_EVIDENCE_NEEDS_A_WORLD,
                f"imagined evidence belongs to a named imagined world, got {world_id!r}",
            )
        try:
            materialised = tuple(rows)
        except TypeError:
            raise GuardRefusal(
                EVIDENCE_IS_NOT_REAL_EVIDENCE,
                f"imagined evidence was built from a {type(rows).__name__}, which is not a set "
                f"of rows at all",
            ) from None
        if not materialised:
            raise GuardRefusal(
                REAL_EVIDENCE_NEEDS_ROWS,
                "an imagined world with no rows has simulated nothing",
            )
        for row in materialised:
            if not isinstance(row, Row):
                raise GuardRefusal(
                    EVIDENCE_IS_NOT_REAL_EVIDENCE,
                    f"imagined evidence holds Row objects, got {type(row).__name__}",
                )
            if row.tag == REAL:
                raise GuardRefusal(
                    IMAGINED_EVIDENCE_TAKES_INTERNAL_ROWS_ONLY,
                    f"row {row.row_id!r} is tagged REAL; an imagined world holds INTERNAL "
                    f"rows only, so imagined evidence can never carry a real witness",
                )
        self._world_id = world_id
        self._rows = materialised

    @property
    def world_id(self) -> str:
        return self._world_id

    def rows(self) -> tuple:
        return self._rows

    def __repr__(self) -> str:
        return f"ImaginedEvidence(world={self._world_id!r}, {len(self._rows)} INTERNAL rows)"


def evidence_kind(value):
    """`REAL`, `IMAGINED`, or `None` for anything that is not evidence at all."""
    if isinstance(value, RealEvidence):
        return REAL_EVIDENCE
    if isinstance(value, ImaginedEvidence):
        return IMAGINED_EVIDENCE
    return None


# --------------------------------------------------------------------------- #
# Verdicts: minted by verify and by nothing else
# --------------------------------------------------------------------------- #
_SEAL = object()


class Verdict:
    """What the verifier decided, and on what kind of evidence.

    A `Verdict` can only be built through `verify()`. Its constructor demands a sealed token
    that exists only as a private name in this module, so `Verdict("ADMITTED", ...)` from
    outside raises `VERDICT_MUST_BE_MINTED`. `is_verdict` re-checks the seal, so an object
    built by hand (`object.__new__(Verdict)`) is not a verdict either.
    """

    __slots__ = ("word", "code", "evidence_kind", "verifier", "detail", "support", "_seal")

    def __init__(self, word, code, kind, verifier, detail="", support=0, seal=None) -> None:
        if seal is not _SEAL:
            raise GuardRefusal(
                VERDICT_MUST_BE_MINTED,
                "a Verdict is minted by guard.verify() and by nothing else; this object was "
                "constructed directly, so it is not a verification result",
            )
        self.word = word
        self.code = code
        self.evidence_kind = kind
        self.verifier = verifier
        self.detail = detail
        self.support = support
        self._seal = seal

    @property
    def admitted(self) -> bool:
        return self.word == ADMITTED

    @property
    def refused(self) -> bool:
        return self.word == REFUSED

    def as_dict(self) -> dict:
        return {
            "word": self.word,
            "code": self.code,
            "evidence_kind": self.evidence_kind,
            "verifier": self.verifier,
            "support": self.support,
            "detail": self.detail,
        }

    def __repr__(self) -> str:
        # getattr with defaults: an object built with object.__new__ has no fields, and a
        # repr that raises inside a refusal message would turn a refusal into a crash.
        return "Verdict(%r, %r, evidence=%r)" % (
            getattr(self, "word", None),
            getattr(self, "code", None),
            getattr(self, "evidence_kind", None),
        )


def is_verdict(value) -> bool:
    """True only for a verdict this module minted."""
    return (
        isinstance(value, Verdict)
        and getattr(value, "_seal", None) is _SEAL
        and value.evidence_kind == REAL_EVIDENCE
        and value.word in (ADMITTED, REFUSED)
    )


def _mint(word, code, kind, verifier, detail="", support=0) -> Verdict:
    return Verdict(
        word=word,
        code=code,
        kind=kind,
        verifier=verifier,
        detail=detail,
        support=support,
        seal=_SEAL,
    )


# --------------------------------------------------------------------------- #
# The one verifier
# --------------------------------------------------------------------------- #
def exact_fit_checker(candidate, evidence: RealEvidence, min_support: int = MIN_SUPPORT_ROWS):
    """The default check: enough real rows carry the candidate's canonical form.

    Returns `(passed, code, support)`. It is only ever called with `RealEvidence`; `verify`
    refuses every other type before a checker is reached.
    """
    form = _canonical_form(candidate)
    support = sum(1 for seen in evidence.canonical_forms() if seen == form)
    if support >= min_support:
        return True, "VERIFY_ADMITS_ON_REAL_ROWS", support
    return False, "NOT_ENOUGH_REAL_ROWS", support


def _canonical_form(candidate) -> str:
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    form = getattr(candidate, "canonical_form", None)
    if isinstance(form, str) and form.strip():
        return form
    raise GuardRefusal(
        CANDIDATE_NOT_A_CANDIDATE,
        f"{type(candidate).__name__} names no canonical form, so there is nothing to verify",
    )


def verify(candidate, evidence, *, checker=None, verifier="VERIFIER") -> Verdict:
    """Run the one verification call. Imagined evidence never reaches the checker.

    Order matters and is the substance of the guardrail:

      1. If the evidence is an `ImaginedEvidence`, refuse `IMAGINED_EVIDENCE_CANNOT_VERIFY`.
         This happens **before** the checker is resolved or called, so no checker in this
         package ever sees imagined data.
      2. If the evidence is anything that is not a `RealEvidence` (including a hand-made
         object), refuse `EVIDENCE_IS_NOT_REAL_EVIDENCE`.
      3. Only then call the checker and mint a sealed `Verdict`.
    """
    if isinstance(evidence, ImaginedEvidence):
        raise GuardRefusal(
            IMAGINED_EVIDENCE_CANNOT_VERIFY,
            f"the evidence is the imagined world {evidence.world_id!r}; an imagined world can "
            f"propose a candidate but it can never verify one. No checker was called and no "
            f"verdict was minted",
        )
    if not isinstance(evidence, RealEvidence):
        raise GuardRefusal(
            EVIDENCE_IS_NOT_REAL_EVIDENCE,
            f"verification takes RealEvidence, got {type(evidence).__name__}; only rows that "
            f"came from outside can decide anything",
        )
    form = _canonical_form(candidate)
    check = exact_fit_checker if checker is None else checker
    if not callable(check):
        raise GuardRefusal(
            CHECKER_NOT_CALLABLE, f"a checker must be callable, got {type(check).__name__}"
        )
    passed, code, support = check(candidate, evidence)
    if not isinstance(passed, bool):
        raise GuardRefusal(
            CHECKER_NOT_CALLABLE,
            f"the checker returned {type(passed).__name__} where a yes or no was needed",
        )
    word = ADMITTED if passed else REFUSED
    return _mint(
        word,
        code,
        REAL_EVIDENCE,
        verifier,
        detail=f"candidate {form!r} checked against {len(evidence.rows())} real rows",
        support=support if isinstance(support, int) else 0,
    )


# --------------------------------------------------------------------------- #
# What a faculty may not return
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class BiasWriteAttempt:
    """A faculty's attempt to write the Bias, expressed as a value so it can be refused.

    A faculty that wants to write the Bias has to say so. `check_faculty_return` refuses this
    object wherever it appears in a return value, so the attempt travels no further than the
    faculty's own return statement.
    """

    key: str
    value: object = None
    coordinator: str = ""

    def as_dict(self) -> dict:
        return {"key": self.key, "value": self.value, "coordinator": self.coordinator}


def _looks_like_a_bias(value) -> bool:
    """True for an object that can write facts: it has `write` and a `version`."""
    return callable(getattr(type(value), "write", None)) and hasattr(value, "version")


def check_faculty_return(faculty, returned):
    """Refuse a faculty return that carries a Bias write, an admission, a verdict or evidence.

    Returns `returned` unchanged when it is clean, so a faculty ends with
    `return check_faculty_return(NAME, report)` and the check cannot be forgotten at the call
    site. The walk is bounded (`MAX_SCAN_DEPTH`) and refuses live objects: a return value is a
    small owned record, not a handle on the runtime.
    """
    if not isinstance(faculty, str) or not faculty.strip():
        raise GuardRefusal(FACULTY_NOT_NAMED, f"a faculty report must name its faculty, got {faculty!r}")
    _scan(returned, faculty, set(), 0)
    return returned


def _scan(value, faculty, seen, depth) -> None:
    if depth > MAX_SCAN_DEPTH:
        raise GuardRefusal(
            FACULTY_RETURNED_LIVE_OBJECT,
            f"the return value of {faculty} nests deeper than {MAX_SCAN_DEPTH}; a faculty "
            f"report is a small record, and a structure this deep is not one",
        )
    if value is None or isinstance(value, (str, bytes, int, float, bool)):
        return
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)

    if isinstance(value, BiasWriteAttempt):
        raise GuardRefusal(
            FACULTY_RETURNED_BIAS_WRITE,
            f"{faculty} returned a Bias write ({value.as_dict()}); a faculty proposes into the "
            f"held buffer and never writes what the brain believes",
        )
    if isinstance(value, Verdict):
        raise GuardRefusal(
            FACULTY_RETURNED_A_VERDICT,
            f"{faculty} returned a verification verdict ({value.word}); only the verifier "
            f"mints a verdict, and a faculty may not carry one out",
        )
    if isinstance(value, Evidence):
        raise GuardRefusal(
            FACULTY_RETURNED_EVIDENCE,
            f"{faculty} returned {type(value).__name__}; a faculty is given no evidence, so it "
            f"has none to hand back",
        )
    if _looks_like_a_bias(value):
        raise GuardRefusal(
            FACULTY_RETURNED_BIAS_WRITE,
            f"{faculty} returned the Bias itself ({type(value).__name__}); handing it back is "
            f"handing the faculty a write",
        )

    state = getattr(value, "claimed_state", None)
    if state is None:
        state = getattr(value, "state", None)
    if isinstance(state, str) and state in STATE_WORDS and state != HELD:
        code = (
            FACULTY_RETURNED_ADMITTED_CANDIDATE
            if state == ADMITTED
            else FACULTY_RETURNED_UNHELD_CANDIDATE
        )
        raise GuardRefusal(
            code,
            f"{faculty} returned a candidate in state {state}; a faculty may only ever write "
            f"{HELD}",
        )

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            _scan(getattr(value, field.name, None), faculty, seen, depth + 1)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            _scan(item, faculty, seen, depth + 1)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _scan(key, faculty, seen, depth + 1)
            _scan(item, faculty, seen, depth + 1)
        return
    raise GuardRefusal(
        FACULTY_RETURNED_LIVE_OBJECT,
        f"{faculty} returned a {type(value).__name__}, which is a live object rather than a "
        f"plain record; a faculty's return value must be readable without this process",
    )


# --------------------------------------------------------------------------- #
# The Bias door: reading is free, writing has exactly one shape
# --------------------------------------------------------------------------- #
class BiasReading:
    """A read-only view of a Bias. It has no `write`, no `snapshot` and no handle on the Bias.

    A faculty is given one of these. Because the object has no `write` attribute at all,
    `reading.write(...)` raises `AttributeError` rather than a permission error -- there is no
    method to refuse, which is the structural version of "a faculty may not write the Bias".
    """

    __slots__ = ("_version", "_digest", "_coordinator", "_facts")

    def __init__(self, version, digest, coordinator, facts) -> None:
        self._version = version
        self._digest = digest
        self._coordinator = coordinator
        self._facts = tuple((key, value) for key, value in facts)

    @property
    def version(self) -> int:
        return self._version

    @property
    def digest(self) -> str:
        return self._digest

    @property
    def coordinator(self) -> str:
        return self._coordinator

    @property
    def keys(self) -> tuple:
        return tuple(key for key, _ in self._facts)

    def has(self, key) -> bool:
        return any(stored == key for stored, _ in self._facts)

    def read(self, key):
        for stored, value in self._facts:
            if stored == key:
                return value
        raise GuardRefusal(
            "BIAS_KEY_NOT_WRITTEN",
            f"no fact named {key!r} was written; this reading carries {list(self.keys)}",
        )

    def as_dict(self) -> dict:
        return {
            "version": self._version,
            "digest": self._digest,
            "coordinator": self._coordinator,
            "keys": list(self.keys),
        }

    def __repr__(self) -> str:
        return f"BiasReading(version={self._version}, keys={list(self.keys)})"


def bias_reading(value) -> BiasReading:
    """A `BiasReading` from a `Bias` (or a `BiasReading` passed through unchanged).

    Refuses anything else. This is the only way a faculty is given a Bias, so a faculty never
    holds an object with a `write` method.
    """
    if isinstance(value, BiasReading):
        return value
    snapshot = getattr(value, "snapshot", None)
    if not callable(snapshot) or not hasattr(value, "version"):
        raise GuardRefusal(
            BIAS_READING_NEEDS_A_BIAS,
            f"a faculty reads a Bias, got {type(value).__name__}",
        )
    frozen = snapshot()
    facts = getattr(frozen, "facts", ())
    return BiasReading(
        version=getattr(frozen, "version", getattr(value, "version")),
        digest=getattr(frozen, "digest", ""),
        coordinator=getattr(frozen, "coordinator", ""),
        facts=facts,
    )


def coordinator_for_faculty(faculty) -> str:
    """The coordinator name a faculty would have to use to write the Bias: `FACULTY:<name>`.

    Not a name any faculty uses; a name that proves the Bias refuses one.
    """
    if not isinstance(faculty, str) or not faculty.strip():
        raise GuardRefusal(FACULTY_NOT_NAMED, f"a faculty needs a name, got {faculty!r}")
    return FACULTY_COORDINATOR_PREFIX + faculty


def believe(bias, *, coordinator, key, value, verdict):
    """The single door from a verified candidate to what the brain believes.

    Refuses unless `verdict` is a verdict this package minted, in the word `ADMITTED`, on
    `REAL_EVIDENCE`. A refused candidate, a candidate that is still `HELD`, and any candidate
    at all that came from a daydream have nothing that passes this door -- and it is the only
    function in this package that calls `Bias.write`.
    """
    if verdict is None:
        raise GuardRefusal(
            BELIEVE_CALLED_WITHOUT_A_VERDICT,
            "a write to the Bias needs a verification verdict; nothing is believed on the "
            "strength of having been proposed",
        )
    if not is_verdict(verdict):
        raise GuardRefusal(
            BELIEF_NEEDS_AN_ADMITTED_VERDICT,
            f"{verdict!r} is not a verdict minted by guard.verify(); a belief cannot rest on "
            f"an object that was not a verification",
        )
    if verdict.evidence_kind != REAL_EVIDENCE:
        raise GuardRefusal(
            BELIEF_NEEDS_REAL_EVIDENCE,
            f"the verdict rests on {verdict.evidence_kind} evidence; only real rows may move "
            f"what the brain believes",
        )
    if verdict.word != ADMITTED:
        raise GuardRefusal(
            BELIEF_NEEDS_AN_ADMITTED_VERDICT,
            f"the verdict is {verdict.word}, not {ADMITTED}; what the brain believes changes "
            f"only on an admission",
        )
    if not isinstance(coordinator, str) or not coordinator.strip():
        raise GuardRefusal(COORDINATOR_NOT_NAMED, "a Bias write needs a named coordinator")
    if coordinator.startswith(FACULTY_COORDINATOR_PREFIX):
        raise GuardRefusal(
            FACULTY_RETURNED_BIAS_WRITE,
            f"{coordinator!r} is a faculty coordinator; faculties never write the Bias",
        )
    return bias.write(key, value, coordinator)
