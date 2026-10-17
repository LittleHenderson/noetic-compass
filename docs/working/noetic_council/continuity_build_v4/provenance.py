"""provenance.py -- FOLLOWED, CREATED and ATTEMPTED, by the provenance of the next pointer.

WHAT THIS MODULE DOES
---------------------
CONTINUITY.md:43-54 tells "follow a continuity of thought" and "create a continuity of
thought" apart by the provenance of the next-station pointer that the program writes at
every crossing. This module implements that classification exactly:

  * **FOLLOWED**  -- the pointer to the next station existed in the path record BEFORE
                     this tick.
  * **CREATED**   -- the pointer was written THIS TICK by a faculty or by an injection,
                     and the continuation it names is later admitted or answered.
  * **ATTEMPTED** -- a pointer written this tick whose continuation is refused, or that
                     stays HELD or open at the end. "NOT continuity; counted so that
                     creation cannot be inflated by proposals" (CONTINUITY.md:50).

``classify(crossing, path_record, later_outcomes)`` returns ``(word, reason)``. The writer
of a CREATED pointer is logged in the reason -- the faculty's Phi word (compiler-valid
spelling, e.g. ``Φ<8:9:6:0>``, digits joined by ``:``, innermost first, governing last) or
the injection's turn index (CONTINUITY.md:52-54).

``assert_shuffled_control(records)`` raises unless the shuffled-injection control produced
**0** CREATED continuations (CONTINUITY.md:54). It also raises when there are no shuffled
records at all, because a control that did not run cannot pass.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide the undecided cases. Where the design is silent -- a pointer written
    by the drive loop's arm rather than a faculty or an injection, or a crossing with no
    next pointer at all -- it REFUSES with ``PROVENANCE_UNDECIDABLE`` instead of choosing a
    word. Each such gap is marked as an undecided line in the code below and listed in
    README.md.
  * It does NOT show that anything was "thought up". These three are bookkeeping words; the
    only mark they earn is that the labels agree with the planted key on every crossing
    (CONTINUITY.md:56-58). Say it plainly: this module counts provenance, nothing more.
  * It does NOT run a brain, a faculty, an injection, or a drive loop. It reads records the
    caller supplies and returns a word and a reason.
  * It does NOT connect to the Recursive Possibility Atlas. An atlas crossing is a record
    like any other here, and nothing in this module reads an atlas or a node kind.

CLAIM CEILING (corrected in v4 -- S0 anchors on the real atlas model):
    MECHANISM ONLY. S0 ANCHORS TO THE REAL ATLAS MODEL AT COMMIT eb998556; THIS BUILD ADDS NO ATLAS OF ITS OWN. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

from collections.abc import Mapping

from seams import decode_reason, make_reason, read_field

#: The three words. Exactly these three, and no fourth.
FOLLOWED = "FOLLOWED"
CREATED = "CREATED"
ATTEMPTED = "ATTEMPTED"
WORDS = (FOLLOWED, CREATED, ATTEMPTED)

#: Writer kinds the design names: a faculty, or an injection (CONTINUITY.md:49).
WRITER_FACULTY = "FACULTY"
WRITER_INJECTION = "INJECTION"

#: Continuation outcomes. "admitted or answered" -> CREATED; "refused or stays HELD / open"
#: -> ATTEMPTED (CONTINUITY.md:49-50).
ADMITTED = "ADMITTED"
ANSWERED = "ANSWERED"
REFUSED = "REFUSED"
HELD = "HELD"
OPEN = "OPEN"
CREATING_STATUSES = (ADMITTED, ANSWERED)
ATTEMPTING_STATUSES = (REFUSED, HELD, OPEN)

#: The control label a shuffled-injection record carries.
CONTROL_SHUFFLED = "SHUFFLED"

#: Reason codes.
POINTER_EXISTED_BEFORE_TICK = "POINTER_EXISTED_BEFORE_TICK"
WRITTEN_THIS_TICK_AND_CONTINUATION_ADMITTED = "WRITTEN_THIS_TICK_AND_CONTINUATION_ADMITTED"
WRITTEN_THIS_TICK_AND_CONTINUATION_ANSWERED = "WRITTEN_THIS_TICK_AND_CONTINUATION_ANSWERED"
WRITTEN_THIS_TICK_CONTINUATION_REFUSED = "WRITTEN_THIS_TICK_CONTINUATION_REFUSED"
WRITTEN_THIS_TICK_CONTINUATION_HELD = "WRITTEN_THIS_TICK_CONTINUATION_HELD"
WRITTEN_THIS_TICK_CONTINUATION_STILL_OPEN = "WRITTEN_THIS_TICK_CONTINUATION_STILL_OPEN"

#: Refusal codes.
PROVENANCE_UNDECIDABLE = "PROVENANCE_UNDECIDABLE"
BAD_POINTER = "BAD_POINTER"
POINTER_NOT_IN_PATH_RECORD = "POINTER_NOT_IN_PATH_RECORD"
SHUFFLED_CONTROL_PRODUCED_CREATED = "SHUFFLED_CONTROL_PRODUCED_CREATED"
SHUFFLED_CONTROL_EMPTY = "SHUFFLED_CONTROL_EMPTY"
BAD_CONTROL_RECORD = "BAD_CONTROL_RECORD"


class ProvenanceRefusal(Exception):
    """A refusal with a stable code. Where the design is silent, this raises."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class ShuffledControlFailure(Exception):
    """The shuffled-injection control failed: it produced a CREATED continuation, or ran empty."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The pointer record
# --------------------------------------------------------------------------- #
def pointer_key(thought_id: str, station: str, tick: int, next_station: str) -> str:
    """A stable name for one next-station pointer: thought, station, tick, destination.

    Used to look the pointer's continuation up in ``later_outcomes``.
    """
    return f"{thought_id}:{station}@{tick}->{next_station}"


def _pointer_of(crossing):
    pointer = read_field(crossing, "next_pointer")
    if pointer is None:
        return None
    if not isinstance(pointer, Mapping):
        raise ProvenanceRefusal(
            BAD_POINTER, f"next_pointer must be a mapping, got {type(pointer).__name__}"
        )
    return pointer


def _next_station(pointer) -> str:
    next_station = pointer.get("next_station")
    if not isinstance(next_station, str) or not next_station:
        raise ProvenanceRefusal(
            BAD_POINTER, "next_pointer names no next_station, so no continuation can be read"
        )
    return next_station


def writer_label(writer) -> str:
    """A short, loggable label for the pointer's writer: the Phi word or the turn index."""
    if writer is None:
        raise ProvenanceRefusal(PROVENANCE_UNDECIDABLE, "the pointer names no writer")
    if not isinstance(writer, Mapping):
        raise ProvenanceRefusal(BAD_POINTER, "writer must be a mapping")
    kind = writer.get("kind")
    if kind == WRITER_FACULTY:
        phi = writer.get("phi")
        if not isinstance(phi, str) or not phi:
            raise ProvenanceRefusal(
                BAD_POINTER, "a faculty writer must carry its Phi word (e.g. 'Φ<8:9:6:0>')"
            )
        return f"faculty {phi}"
    if kind == WRITER_INJECTION:
        turn = writer.get("turn")
        if isinstance(turn, bool) or not isinstance(turn, int):
            raise ProvenanceRefusal(
                BAD_POINTER, "an injection writer must carry its turn index"
            )
        return f"injection at turn {turn}"
    # UNDECIDED IN DESIGN: which word applies to a pointer written this tick by the drive loop's arm rule -- CONTINUITY.md:48-50 names only "a faculty or an injection" as the writer of a CREATED pointer, while CONTINUITY.md:86 gives the arm rule the choice of the next focus; this build refuses rather than choose a word for it.
    raise ProvenanceRefusal(
        PROVENANCE_UNDECIDABLE,
        f"writer kind {kind!r} is neither a faculty nor an injection; the design names only "
        f"those two as the writer of a pointer written this tick (drivers: the loop's arm rule "
        f"also chooses the next focus, and the packet gives no word for that case)",
    )


def _find_prior(crossing, pointer, path_record):
    """The earliest earlier record of this same pointer, or ``None``.

    "Existed in the path record BEFORE this tick" is read strictly: the record's tick must
    be smaller than this crossing's tick. A pointer with the same origin and destination
    that sits at the same tick is this pointer, not an earlier one.

    # UNDECIDED IN DESIGN: what makes two pointer records the same pointer -- CONTINUITY.md:48 says only "the pointer to the next station", so this build matches on the same thought, the same station, the same next station, and a pointer_id when one is given.
    """
    thought_id = read_field(crossing, "thought_id")
    station = read_field(crossing, "station")
    tick = read_field(crossing, "tick")
    next_station = _next_station(pointer)
    wanted_id = pointer.get("pointer_id")
    best = None
    for entry in path_record or ():
        entry_pointer = read_field(entry, "next_pointer")
        if not isinstance(entry_pointer, Mapping):
            continue
        if read_field(entry, "thought_id") != thought_id:
            continue
        if read_field(entry, "station") != station:
            continue
        entry_tick = read_field(entry, "tick")
        if not isinstance(entry_tick, int) or entry_tick >= tick:
            continue
        if entry_pointer.get("next_station") != next_station:
            continue
        if wanted_id is not None and entry_pointer.get("pointer_id") not in (None, wanted_id):
            continue
        if best is None or entry_tick < read_field(best, "tick"):
            best = entry
    return best


def _lookup_outcome(key: str, pointer, later_outcomes):
    """The continuation's outcome record, or ``None`` when nothing is on record."""
    if not later_outcomes:
        return None
    candidate_keys = []
    pointer_id = pointer.get("pointer_id")
    if isinstance(pointer_id, str) and pointer_id:
        candidate_keys.append(pointer_id)
    candidate_keys.append(key)
    for candidate in candidate_keys:
        if candidate in later_outcomes:
            return later_outcomes[candidate]
    return None


def classify(crossing, path_record, later_outcomes) -> tuple[str, str]:
    """Return ``(word, reason)`` for one crossing: FOLLOWED, CREATED or ATTEMPTED.

    ``crossing`` carries the thought, station and tick, plus ``next_pointer``: the pointer
    to the next station, with

      * ``next_station`` -- where the pointer points (required);
      * ``pointer_id``   -- optional stable name, used to look the outcome up;
      * ``written_tick`` -- the tick the pointer was written, or ``None`` if it was not
                            written during this run (it was decoded, slotted, returned to,
                            or ordered beforehand);
      * ``writer``       -- ``{"kind": "FACULTY", "phi": "..."}`` or
                            ``{"kind": "INJECTION", "turn": n}`` when written this tick;
      * ``control``      -- ``"SHUFFLED"`` on a shuffled-injection control record.

    ``path_record`` is the append-only log of earlier crossings; ``later_outcomes`` maps a
    pointer id to ``{"status": one of ADMITTED, ANSWERED, REFUSED, HELD, OPEN}``.

    Where the design is silent the call is refused as ``PROVENANCE_UNDECIDABLE`` rather than
    answered with a guessed word. The reason string is ``"CODE | detail"``; use
    ``provenance.decode_reason`` or ``seams.decode_reason`` to split it.
    """
    pointer = _pointer_of(crossing)
    if pointer is None:
        # UNDECIDED IN DESIGN: which word applies to a crossing with no next-station pointer at all (the last station of a thought) -- the three words at CONTINUITY.md:46-50 do not cover it, so this build refuses rather than invent a fourth.
        raise ProvenanceRefusal(
            PROVENANCE_UNDECIDABLE,
            "this crossing carries no next-station pointer; FOLLOWED needs an earlier record of "
            "it and CREATED/ATTEMPTED need it written this tick, so none of the three words "
            "applies on the record given",
        )

    thought_id = read_field(crossing, "thought_id")
    station = read_field(crossing, "station")
    tick = read_field(crossing, "tick")
    next_station = _next_station(pointer)
    key = pointer_key(thought_id, station, tick, next_station)

    prior = _find_prior(crossing, pointer, path_record)
    if prior is not None:
        prior_tick = read_field(prior, "tick")
        return FOLLOWED, make_reason(
            POINTER_EXISTED_BEFORE_TICK,
            f"the pointer to {next_station} is already in the path record at tick {prior_tick}, "
            f"before this tick {tick}",
        )

    written_tick = pointer.get("written_tick")
    if written_tick is None:
        raise ProvenanceRefusal(
            PROVENANCE_UNDECIDABLE,
            f"the pointer to {next_station} carries no written_tick and no earlier record of it "
            f"exists, so its provenance cannot be read",
        )
    if isinstance(written_tick, bool) or not isinstance(written_tick, int):
        raise ProvenanceRefusal(BAD_POINTER, f"written_tick {written_tick!r} is not a tick")
    if written_tick > tick:
        raise ProvenanceRefusal(
            BAD_POINTER,
            f"the pointer to {next_station} is dated tick {written_tick}, after this crossing's "
            f"tick {tick}",
        )
    if written_tick < tick:
        raise ProvenanceRefusal(
            POINTER_NOT_IN_PATH_RECORD,
            f"the pointer to {next_station} was written at tick {written_tick}, before this tick "
            f"{tick}, but the path record holds no earlier entry for it",
        )

    label = writer_label(pointer.get("writer"))
    outcome = _lookup_outcome(key, pointer, later_outcomes)
    status = None if outcome is None else read_field(outcome, "status")
    if status is not None and status not in (ADMITTED, ANSWERED, REFUSED, HELD, OPEN):
        raise ProvenanceRefusal(
            BAD_POINTER,
            f"continuation status {status!r} is not one of {ADMITTED}, {ANSWERED}, {REFUSED}, "
            f"{HELD}, {OPEN}",
        )

    if status in CREATING_STATUSES:
        code = (
            WRITTEN_THIS_TICK_AND_CONTINUATION_ADMITTED
            if status == ADMITTED
            else WRITTEN_THIS_TICK_AND_CONTINUATION_ANSWERED
        )
        return CREATED, make_reason(
            code,
            f"written at tick {tick} by {label}; the continuation to {next_station} is "
            f"{status} later, so this is continuity the program created",
        )

    if status == REFUSED:
        return ATTEMPTED, make_reason(
            WRITTEN_THIS_TICK_CONTINUATION_REFUSED,
            f"written at tick {tick} by {label}; the continuation to {next_station} is REFUSED, "
            f"so this is not continuity",
        )
    if status == HELD:
        return ATTEMPTED, make_reason(
            WRITTEN_THIS_TICK_CONTINUATION_HELD,
            f"written at tick {tick} by {label}; the continuation to {next_station} stays HELD, "
            f"so this is not continuity",
        )
    # UNDECIDED IN DESIGN: how late a continuation may arrive and still count as CREATED -- CONTINUITY.md:49 says "later admitted or answered" and gives no window or end-of-record rule, so this build treats an outcome that is not on record as still open at the end (ATTEMPTED).
    return ATTEMPTED, make_reason(
        WRITTEN_THIS_TICK_CONTINUATION_STILL_OPEN,
        f"written at tick {tick} by {label}; the continuation to {next_station} is "
        f"{'HELD' if status == HELD else 'open'} at the end of the record, so this is not continuity",
    )


# --------------------------------------------------------------------------- #
# Classifying a whole log, and the shuffled-injection control
# --------------------------------------------------------------------------- #
def classify_all(crossings, path_record, later_outcomes) -> list[dict]:
    """Classify each crossing, carrying the control label through to the result.

    The result rows are small owned dicts: thought, station, tick, the pointer's key, the
    word, the reason and the control label. They are what ``assert_shuffled_control`` reads.
    """
    rows = []
    for crossing in crossings:
        word, reason = classify(crossing, path_record, later_outcomes)
        pointer = _pointer_of(crossing) or {}
        key = pointer_key(
            read_field(crossing, "thought_id"),
            read_field(crossing, "station"),
            read_field(crossing, "tick"),
            _next_station(pointer),
        )
        rows.append(
            {
                "thought_id": read_field(crossing, "thought_id"),
                "station": read_field(crossing, "station"),
                "tick": read_field(crossing, "tick"),
                "pointer_key": key,
                "word": word,
                "reason": reason,
                "control": pointer.get("control"),
            }
        )
    return rows


def assert_shuffled_control(records) -> int:
    """Raise unless the shuffled-injection control produced 0 CREATED continuations.

    CONTINUITY.md:54: "The shuffled-injection control must produce 0 CREATED continuations."
    A CREATED entry on a shuffled record means the program claimed to create a continuation
    out of a pointer whose source was scrambled, so the control has failed.

    Also raises ``SHUFFLED_CONTROL_EMPTY`` when no record carries the shuffled label: a
    control that produced no records proves nothing, and passing vacuously is the failure
    mode this guard exists to stop.

    Returns the number of shuffled records checked, so a caller can report the size of the
    control rather than just its verdict.
    """
    shuffled = 0
    offending = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ShuffledControlFailure(
                BAD_CONTROL_RECORD, f"record {index} is not a mapping"
            )
        if "control" not in record:
            raise ShuffledControlFailure(
                BAD_CONTROL_RECORD,
                f"record {index} carries no control label; an unlabelled record cannot be part "
                f"of the control and cannot be silently ignored",
            )
        if record.get("control") != CONTROL_SHUFFLED:
            continue
        shuffled += 1
        if record.get("word") == CREATED:
            offending.append(record)
    if offending:
        detail = "; ".join(
            f"{row.get('thought_id')}:{row.get('station')}@{row.get('tick')} -> {row.get('pointer_key')}"
            for row in offending
        )
        raise ShuffledControlFailure(
            SHUFFLED_CONTROL_PRODUCED_CREATED,
            f"the shuffled-injection control produced {len(offending)} CREATED continuation(s): {detail}",
        )
    if shuffled == 0:
        raise ShuffledControlFailure(
            SHUFFLED_CONTROL_EMPTY,
            "no shuffled-injection records were supplied; a control that did not run cannot pass",
        )
    return shuffled


def decode_reason_tuple(reason: str) -> tuple[str, str]:
    """Split a reason string into (code, detail). Re-exported for symmetry with seams."""
    return decode_reason(reason)
