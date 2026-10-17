"""held.py -- the buffer where a faculty's candidate waits, undecided.

WHAT THIS MODULE DOES
---------------------
FACULTIES.md section 2.2 gives wondering one place to land: "The candidate lands in the
**pondering buffer** in state `HELD` (meaning: NO_EVIDENCE about it on real rows). It is
neither admitted nor refused. It does not touch any answer. It leaves `HELD` only by
evidence."

This module is that buffer, and it is the only store in the package:

  * **`put()` is the faculty door and it writes `HELD` and nothing else.** There is no
    argument that admits, refuses or expires a candidate. A proposal that *claims* any other
    state is refused with `HELD_ONLY_HELD_ENTERS`, so a faculty cannot talk its way into an
    admission by labelling one.
  * **`settle()` is the verifier door.** It needs a verdict that `guard.verify()` minted. A
    verdict-shaped object that was built by hand is refused, because `guard.is_verdict`
    re-checks the seal. This is what "only an external verifier callable can move a candidate
    out of `HELD`" means in code.
  * **`expire()` is the consolidator door.** It moves a `HELD` candidate to `EXPIRED` and can
    produce nothing else. Expiry verifies nothing, so it can never move a candidate towards
    belief; it exists because FACULTIES.md says `EXPIRED` is a state (age cap, logged) and
    DRIVE_LOOP.md gives F3 Vitality "buffer expiry" as its action.
  * **Nothing is ever deleted.** A refused candidate, an expired candidate and an admitted
    candidate all stay in the buffer with their whole history. `entries()` returns every
    candidate ever put in. `counts()` distinguishes the four states.
  * **Every state transition records who moved it and why**: a writer kind (`FACULTY`,
    `VERIFIER`, `CONSOLIDATOR`), the writer's name, its phi label when it has one, a reason
    word and a refusal code when the move came from a verdict.

The writer record's shape is taken from `continuity_build_v3/provenance.py:140-167`, where a
faculty writer is `{"kind": "FACULTY", "phi": <non-empty>}`; the fields here are those fields,
flattened onto one frozen record.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide whether a candidate is true. It records the verifier's verdict. The
    verifier is `guard.verify`, and it is the only thing that can produce the verdict this
    module accepts.
  * It does NOT write the Bias. Nothing here even sees a Bias; belief is `guard.believe`.
  * It does NOT return a candidate to the readout. FACULTIES.md (test plan H5) requires that
    the readout reads the buffer 0 times. The readout is not in this build; when it is, the
    rule it has to obey is written down in README.md.
  * It does NOT expire anything by itself on a timer. `expire` is called by the caller; with
    no cap named it refuses rather than pick a number (see the undecided lines below).
  * It does NOT run a faculty or a loop. `faculties.py` writes here; `drive_loop.py` calls the
    verifier and the expiry.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

from guard import (
    ADMITTED,
    EXPIRED,
    HELD,
    REFUSED,
    STATE_WORDS,
    is_verdict,
)

__all__ = [
    "HELD", "ADMITTED", "REFUSED", "EXPIRED", "STATE_WORDS",
    "DAYDREAM", "INSIGHT", "NO_LABEL",
    "FACULTY_WRITER", "VERIFIER_WRITER", "CONSOLIDATOR_WRITER",
    "Proposal", "Transition", "Entry", "HeldBuffer", "HeldRefusal",
]

#: The two labels a held candidate can carry. `DAYDREAM` is written by imagination and by
#: nothing else; `INSIGHT` is written only by this module, only on an admission, and only for
#: a candidate that came in as a daydream. FACULTIES.md section 2.4: "an insight = an imagined
#: recipe later admitted on real rows". Nothing else in this build is called an insight.
DAYDREAM = "DAYDREAM"
INSIGHT = "INSIGHT"
NO_LABEL = None

#: Writer kinds for a state transition.
FACULTY_WRITER = "FACULTY"
VERIFIER_WRITER = "VERIFIER"
CONSOLIDATOR_WRITER = "CONSOLIDATOR"
WRITER_KINDS = (FACULTY_WRITER, VERIFIER_WRITER, CONSOLIDATOR_WRITER)

#: Reason words. Every transition carries one, so "why" is never blank.
WHY_PROPOSED = "FACULTY_PROPOSED_HELD"
WHY_VERIFIED_ADMITTED = "VERIFIER_ADMITTED_ON_REAL_EVIDENCE"
WHY_VERIFIED_REFUSED = "VERIFIER_REFUSED"
WHY_AGE_CAP = "AGE_CAP_REACHED"
WHY_BUFFER_FULL = "BUFFER_FULL_OLDEST_HELD_FIRST"

#: Refusal codes.
HELD_ONLY_HELD_ENTERS = "HELD_ONLY_HELD_ENTERS"
HELD_CANDIDATE_UNKNOWN = "HELD_CANDIDATE_UNKNOWN"
HELD_ALREADY_SETTLED = "HELD_ALREADY_SETTLED"
HELD_ONLY_A_VERIFIER_MOVES = "HELD_ONLY_A_VERIFIER_MOVES"
HELD_CAP_NOT_NAMED = "HELD_CAP_NOT_NAMED"
HELD_BAD_TICK = "HELD_BAD_TICK"
HELD_TICK_WOULD_GO_BACK = "HELD_TICK_WOULD_GO_BACK"
HELD_FORM_EMPTY = "HELD_FORM_EMPTY"
HELD_FACULTY_NOT_NAMED = "HELD_FACULTY_NOT_NAMED"
HELD_CLAIMED_STATE_NOT_A_WORD = "HELD_CLAIMED_STATE_NOT_A_WORD"
HELD_INSIGHT_IS_NOT_A_FACULTY_LABEL = "HELD_INSIGHT_IS_NOT_A_FACULTY_LABEL"
HELD_BAD_PROPOSAL = "HELD_BAD_PROPOSAL"
HELD_BAD_CAP = "HELD_BAD_CAP"

# UNDECIDED IN DESIGN: how many candidates the buffer may hold and whether the cap counts only HELD or every state -- ARCHITECTURE.md section 3 gives "64 HELD; oldest-first expiry, logged" as PROPOSED and FACULTIES.md never states a capacity, so this build defaults to no cap, counts HELD only when a cap is named, and refuses nothing that it cannot log.
# UNDECIDED IN DESIGN: what the age cap is, in ticks or in entries -- FACULTIES.md section 2.2 lists "EXPIRED (age cap, logged, never silently dropped)" and gives no number and no unit, so this build requires the caller to name it and refuses with HELD_CAP_NOT_NAMED rather than pick one.
# UNDECIDED IN DESIGN: whether an expired or refused candidate may be revised and re-proposed as itself -- FACULTIES.md gives the four states and no route back out of REFUSED or EXPIRED, so this build keeps the old record for ever and every re-proposal enters as a new candidate with a new id.
# UNDECIDED IN DESIGN: whether a daydream keeps its DAYDREAM label after a refusal -- FACULTIES.md section 2.4 defines a daydream as a world or recipe "never confirmed by real rows", and a refused candidate was never confirmed, so this build leaves the label DAYDREAM on refusal and changes it to INSIGHT only on admission.


class HeldRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# What a faculty hands to the buffer
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Proposal:
    """One candidate a faculty wants to put in the buffer.

    `claimed_state` exists only so the buffer can refuse it: the only value accepted is
    `HELD`. `label` exists only so imagination can mark a daydream; `INSIGHT` is refused here
    because an insight is what an admission produces, not what a faculty writes.
    """

    canonical_form: str
    faculty: str
    target: str = ""
    phi: str = ""
    seed: object = None
    world: object = None
    label: object = NO_LABEL
    claimed_state: str = HELD

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_form, str) or not self.canonical_form.strip():
            raise HeldRefusal(
                HELD_FORM_EMPTY,
                f"a candidate needs a canonical form, got {self.canonical_form!r}; a candidate "
                f"nobody can name cannot be verified or refused",
            )
        if not isinstance(self.faculty, str) or not self.faculty.strip():
            raise HeldRefusal(
                HELD_FACULTY_NOT_NAMED,
                f"a candidate names the faculty that surfaced it, got {self.faculty!r}",
            )
        if self.claimed_state not in STATE_WORDS:
            raise HeldRefusal(
                HELD_CLAIMED_STATE_NOT_A_WORD,
                f"claimed_state {self.claimed_state!r} is not one of {list(STATE_WORDS)}",
            )
        if self.label == INSIGHT:
            raise HeldRefusal(
                HELD_INSIGHT_IS_NOT_A_FACULTY_LABEL,
                "INSIGHT is what a verification admission produces, not what a faculty "
                "writes; imagination may only label its world DAYDREAM",
            )
        if self.label not in (NO_LABEL, DAYDREAM):
            raise HeldRefusal(
                HELD_BAD_PROPOSAL,
                f"label {self.label!r} is neither {DAYDREAM} nor none",
            )
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise HeldRefusal(
                HELD_BAD_PROPOSAL,
                f"a seed is an integer or nothing, got {self.seed!r}; every draw a faculty "
                f"makes is saved so the run replays",
            )
        if self.world is not None and (not isinstance(self.world, str) or not self.world.strip()):
            raise HeldRefusal(
                HELD_BAD_PROPOSAL, f"an imagined-world name is a non-empty string, got {self.world!r}"
            )


# --------------------------------------------------------------------------- #
# The record of every move
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Transition:
    """One move of one candidate, with who moved it and why.

    The writer record is flattened onto this record: `writer_kind`, `moved_by`, `phi`. The
    shape follows `continuity_build_v3/provenance.py`'s faculty writer, where a faculty writer
    is a kind plus a phi.
    """

    candidate_id: str
    from_state: object
    to_state: str
    tick: int
    writer_kind: str
    moved_by: str
    phi: str = ""
    why: str = ""
    code: str = ""

    def as_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "tick": self.tick,
            "writer": {"kind": self.writer_kind, "name": self.moved_by, "phi": self.phi},
            "why": self.why,
            "code": self.code,
        }


@dataclasses.dataclass(frozen=True)
class Entry:
    """One candidate in the buffer: what it is, where it stands, and how it got there."""

    candidate_id: str
    proposal: Proposal
    state: str
    label: object
    entered_tick: int
    settled_tick: object
    transitions: tuple

    @property
    def canonical_form(self) -> str:
        return self.proposal.canonical_form

    @property
    def faculty(self) -> str:
        return self.proposal.faculty

    @property
    def is_daydream(self) -> bool:
        return self.label == DAYDREAM

    @property
    def is_insight(self) -> bool:
        return self.label == INSIGHT

    def as_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "canonical_form": self.canonical_form,
            "faculty": self.faculty,
            "target": self.proposal.target,
            "phi": self.proposal.phi,
            "seed": self.proposal.seed,
            "world": self.proposal.world,
            "state": self.state,
            "label": self.label,
            "entered_tick": self.entered_tick,
            "settled_tick": self.settled_tick,
            "transitions": [move.as_dict() for move in self.transitions],
        }


# --------------------------------------------------------------------------- #
# The buffer
# --------------------------------------------------------------------------- #
class HeldBuffer:
    """Candidates, their four states, and every move between them. Append-only in effect.

    The object has three doors and they are not interchangeable:

      * `put(proposal)` -- faculties. Always `HELD`.
      * `settle(candidate_id, verdict)` -- the verifier, through a sealed verdict.
      * `expire(...)` -- the consolidator. Always `EXPIRED`.

    There is no `admit`, no `refuse`, no `remove`, no `clear` and no `set_state`.
    """

    def __init__(self, name: str = "held") -> None:
        if not isinstance(name, str) or not name.strip():
            raise HeldRefusal(HELD_BAD_PROPOSAL, f"a buffer needs a name, got {name!r}")
        self._name = name
        self._tick = 0
        self._entries: dict = {}
        self._order: list = []
        self._next_id = 1
        self._transitions: list = []

    # -- read-only views ---------------------------------------------------- #
    @property
    def name(self) -> str:
        return self._name

    @property
    def tick(self) -> int:
        return self._tick

    def __len__(self) -> int:
        return len(self._order)

    def __repr__(self) -> str:
        return f"HeldBuffer({self._name!r}, {len(self._order)} candidates, tick={self._tick})"

    def entries(self) -> tuple:
        """Every candidate ever put in the buffer, in insertion order. Never a subset."""
        return tuple(self._entries[cid] for cid in self._order)

    def get(self, candidate_id) -> Entry:
        if candidate_id not in self._entries:
            raise HeldRefusal(
                HELD_CANDIDATE_UNKNOWN,
                f"no candidate {candidate_id!r} was ever put in {self._name!r}; it holds "
                f"{list(self._order)}",
            )
        return self._entries[candidate_id]

    def state_of(self, candidate_id) -> str:
        return self.get(candidate_id).state

    def label_of(self, candidate_id):
        return self.get(candidate_id).label

    def ids_in(self, state) -> tuple:
        if state not in STATE_WORDS:
            raise HeldRefusal(HELD_BAD_PROPOSAL, f"{state!r} is not one of {list(STATE_WORDS)}")
        return tuple(cid for cid in self._order if self._entries[cid].state == state)

    def held_ids(self) -> tuple:
        return self.ids_in(HELD)

    def admitted_ids(self) -> tuple:
        return self.ids_in(ADMITTED)

    def refused_ids(self) -> tuple:
        return self.ids_in(REFUSED)

    def expired_ids(self) -> tuple:
        return self.ids_in(EXPIRED)

    def daydream_ids(self) -> tuple:
        return tuple(cid for cid in self._order if self._entries[cid].is_daydream)

    def insight_ids(self) -> tuple:
        return tuple(cid for cid in self._order if self._entries[cid].is_insight)

    def counts(self) -> dict:
        out = {state: 0 for state in STATE_WORDS}
        for cid in self._order:
            out[self._entries[cid].state] += 1
        out["total"] = len(self._order)
        out[DAYDREAM] = len(self.daydream_ids())
        out[INSIGHT] = len(self.insight_ids())
        return out

    def transitions(self) -> tuple:
        """Every transition of every candidate, in the order it happened."""
        return tuple(self._transitions)

    def history_of(self, candidate_id) -> tuple:
        return self.get(candidate_id).transitions

    def digest(self) -> str:
        """sha256 over the whole buffer, so a run can be compared with itself."""
        payload = [entry.as_dict() for entry in self.entries()]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    # -- the clock ---------------------------------------------------------- #
    def begin_tick(self, tick) -> int:
        """Name the tick the next writes belong to. Ticks never go backwards."""
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise HeldRefusal(HELD_BAD_TICK, f"a tick is a non-negative integer, got {tick!r}")
        if tick < self._tick:
            raise HeldRefusal(
                HELD_TICK_WOULD_GO_BACK,
                f"this buffer is at tick {self._tick} and was told {tick}; a buffer that can "
                f"move its clock backwards can re-order its own history",
            )
        self._tick = tick
        return self._tick

    def _tick_or_fail(self, tick):
        if tick is None:
            return self._tick
        return self.begin_tick(tick)

    # -- door 1: the faculty ------------------------------------------------ #
    def put(self, proposal, *, tick=None) -> Entry:
        """Put one candidate in as `HELD`. Returns the entry.

        Refuses: a proposal that is not a `Proposal` (so nothing without a canonical form and
        a named faculty gets in), and a proposal whose `claimed_state` is anything but
        `HELD`. That second refusal is the direct-ADMITTED-write guard: there is no argument
        through which a faculty can put in a candidate already marked true.
        """
        if not isinstance(proposal, Proposal):
            raise HeldRefusal(
                HELD_BAD_PROPOSAL,
                f"the buffer takes Proposals, got {type(proposal).__name__}",
            )
        if proposal.claimed_state != HELD:
            raise HeldRefusal(
                HELD_ONLY_HELD_ENTERS,
                f"the proposal claims state {proposal.claimed_state!r}; a candidate written by a "
                f"faculty enters as {HELD} and nothing else. Only a verification verdict can "
                f"move it out",
            )
        at = self._tick_or_fail(tick)
        candidate_id = f"C{self._next_id}"
        self._next_id += 1
        first = Transition(
            candidate_id=candidate_id,
            from_state=None,
            to_state=HELD,
            tick=at,
            writer_kind=FACULTY_WRITER,
            moved_by=proposal.faculty,
            phi=proposal.phi,
            why=WHY_PROPOSED,
            code="",
        )
        entry = Entry(
            candidate_id=candidate_id,
            proposal=proposal,
            state=HELD,
            label=proposal.label,
            entered_tick=at,
            settled_tick=None,
            transitions=(first,),
        )
        self._entries[candidate_id] = entry
        self._order.append(candidate_id)
        self._transitions.append(first)
        return entry

    # -- door 2: the verifier ----------------------------------------------- #
    def settle(self, candidate_id, verdict, *, tick=None) -> Entry:
        """Move a `HELD` candidate by the verifier's verdict. `ADMITTED` or `REFUSED`.

        Refuses: an unknown candidate, a candidate that already left `HELD` (a state is not
        re-entered here -- the record stays as it is), and anything that is not a sealed
        verdict minted by `guard.verify`. A hand-made verdict-shaped object is refused with
        `HELD_ONLY_A_VERIFIER_MOVES`.
        """
        entry = self.get(candidate_id)
        if entry.state != HELD:
            raise HeldRefusal(
                HELD_ALREADY_SETTLED,
                f"candidate {candidate_id} is already {entry.state}; a settled candidate stays "
                f"recorded as it settled, and no verdict re-opens it",
            )
        if not is_verdict(verdict):
            raise HeldRefusal(
                HELD_ONLY_A_VERIFIER_MOVES,
                f"candidate {candidate_id} left {HELD} on a {type(verdict).__name__} object; "
                f"only a verdict minted by guard.verify() on real evidence moves a candidate, "
                f"and this is not one",
            )
        at = self._tick_or_fail(tick)
        if verdict.word == ADMITTED:
            state = ADMITTED
            why = WHY_VERIFIED_ADMITTED
            label = INSIGHT if entry.label == DAYDREAM else entry.label
        elif verdict.word == REFUSED:
            state = REFUSED
            why = WHY_VERIFIED_REFUSED
            label = entry.label
        else:  # pragma: no cover - is_verdict already refused every other word
            raise HeldRefusal(
                HELD_ONLY_A_VERIFIER_MOVES, f"verdict word {verdict.word!r} moves nothing"
            )
        move = Transition(
            candidate_id=candidate_id,
            from_state=HELD,
            to_state=state,
            tick=at,
            writer_kind=VERIFIER_WRITER,
            moved_by=verdict.verifier,
            phi="",
            why=why,
            code=verdict.code,
        )
        updated = dataclasses.replace(
            entry,
            state=state,
            label=label,
            settled_tick=at,
            transitions=entry.transitions + (move,),
        )
        self._entries[candidate_id] = updated
        self._transitions.append(move)
        return updated

    # -- door 3: the consolidator ------------------------------------------- #
    def expire(self, *, age_cap=None, capacity=None, tick=None) -> tuple:
        """Expire `HELD` candidates by an age cap, a capacity, or both. Returns their ids.

        Expiry produces `EXPIRED` and nothing else. It is not a verification, it never
        produces `ADMITTED`, and a candidate it expires stays in `entries()` with the reason
        recorded. With neither cap named it refuses rather than invent a number.
        """
        at = self._tick_or_fail(tick)
        for name, number in (("age_cap", age_cap), ("capacity", capacity)):
            if number is not None and (isinstance(number, bool) or not isinstance(number, int) or number < 0):
                raise HeldRefusal(HELD_BAD_CAP, f"{name} is a non-negative integer, got {number!r}")
        if age_cap is None and capacity is None:
            raise HeldRefusal(
                HELD_CAP_NOT_NAMED,
                "expiry needs an age cap, a capacity, or both; the design names an age cap and "
                "gives no number, so this buffer will not pick one",
            )
        expired: list = []
        if age_cap is not None:
            for cid in self.held_ids():
                entry = self._entries[cid]
                if at - entry.entered_tick >= age_cap:
                    expired.append(cid)
        if capacity is not None:
            held = [cid for cid in self.held_ids() if cid not in expired]
            while len(held) > capacity:
                expired.append(held.pop(0))
        for cid in expired:
            entry = self._entries[cid]
            move = Transition(
                candidate_id=cid,
                from_state=HELD,
                to_state=EXPIRED,
                tick=at,
                writer_kind=CONSOLIDATOR_WRITER,
                moved_by="consolidate",
                phi="",
                why=WHY_AGE_CAP if age_cap is not None else WHY_BUFFER_FULL,
                code="",
            )
            self._entries[cid] = dataclasses.replace(
                entry, state=EXPIRED, transitions=entry.transitions + (move,)
            )
            self._transitions.append(move)
        return tuple(expired)
