"""loop.py -- one turn of the loop, five stages in a fixed order, with the jobs kept apart.

WHAT THIS MODULE DOES
---------------------
It runs one turn, in exactly this order, each stage's output feeding the next:

    1. READ_BIAS               read the Bias: the working memory in
    2. PROPOSE                 a CJT proposes under the Bias (a pluggable callable)
    3. OBSERVE                 compute the ASOM label from (operating region, semantic
                               outcome, saturated)
    4. GATE                    RPM decides proceed / repair / refuse
    5. DISENGAGE_OR_CONTINUE   if the gate cannot proceed, run the disengage ladder naming
                               the exact gap; otherwise continue

``Loop.turn(...)`` returns a frozen ``TurnRecord`` carrying all five stage outputs, the ASOM
label, the gate verdict, and the receipt.

THE ROLE SEPARATION -- this is the whole point of the file
-----------------------------------------------------------
  * **The Bias is the working memory.** Stage 1 reads it; stage 2 receives that reading.
  * **ASOM is a READOUT.** Stage 3 records one of four labels about how the CJT is
    operating. It is a display. ``asom.readout`` returns a string and nothing else.
  * **The gate is the GATE.** ``may_continue()`` is the only thing in this file that can say
    a turn may not proceed, and it takes one input: the gate's verdict.
  * **The ladder is what happens when the gate cannot proceed.**

The ASOM label cannot reach the gate. That is not a promise in this docstring, it is the
shape of the code:

  * the gate is called with a ``GateRequest``, and ``GateRequest`` has no field for the
    label, no field for the region, no field for the semantic outcome and no field for
    whether the region was saturated; the turn's cause travels on that record too, and the
    ``RpmCause`` it carries has no such field either;
  * ``may_continue()`` takes the verdict and nothing else, so no other value is in scope
    where the continue/do-not-continue decision is made;
  * the label is computed in stage 3 and read after that only to be written into the
    record and the receipt.

The test file proves it twice: once by running the whole matrix of turns with the label
computed and again with the label forced to each of the five possible outputs and requiring
identical decisions, and once by breaking the rule on purpose in a copy of this file and of
the gate and watching the same test fail.

THE GATE IS REAL
----------------
``rpm_gate`` is the default gate, and it is the RPM decision itself. It reads the turn's
cause -- which node of the D/W/P chain blocked, at what depth, whether the ancestor line is
invalid, what the runtime reports as missing, and the Bias versions of a returning thread --
and answers one of three words:

  * ``PROCEED`` -- nothing blocks and nothing is missing;
  * ``REPAIR``  -- a prerequisite is missing and a sub-goal can be opened for it; the gap is
    named exactly and the sub-goal is named by the engine's own notation;
  * ``REFUSE``  -- the ancestor line is invalid, the returning Bias is not strictly newer, or
    the sub-goal would sit past the recursion horizon (where the fix is flattening at the
    same level, named and not performed).

Every rule behind those words is somebody else's code, imported from the vendored copies in
``dwp/`` or from ``bias.py``: ``depth.check_depth`` owns the horizon, ``dwp.resolve`` owns
which functor answers a block, ``retraction`` owns the dirty propagation, and
``bias.check_version_increase`` owns "strictly newer". This module decides nothing about
them; it reads their answers and passes them on.

The turn's cause is supplied by the caller, as ``Loop.turn(..., cause=...)``. A turn with no
cause is a turn where nothing blocks and nothing is missing, which proceeds.

``stub_gate`` is still here, and it is **not** the default. It is kept as a labelled
placeholder so that a record can never be mistaken for an RPM decision after the fact: its
verdicts say ``stub=True`` and its reason says it checked nothing, while every verdict the
real gate returns says ``rpm=True``. ``proceeding_gate``, ``refusing_gate`` and
``repairing_gate`` are test doubles written here for tests, not RPM.

WHAT THIS MODULE DOES NOT DO
-----------------------------
  * It does NOT decide anything about the Bias: it reads a snapshot and never writes during a
    turn. Writing is ``Loop.remember``, a separate act, and one coordinator still owns the
    Bias.
  * It does NOT decide what a proposal says, what the operating region is, what the semantic
    outcome is, or whether the region is saturated. All four arrive from outside.
  * It does NOT make the RPM decision itself: it asks ``rpm_gate`` and records the answer. It
    adds no rule of its own on top of that answer.
  * It does NOT decide whether a node is blocked, at what depth, or whether an ancestor is
    dirty. Those arrive in the cause.
  * It does NOT open a sub-goal, perform a repair, or flatten a horizon chain. A REPAIR
    verdict names the sub-goal; a REFUSE verdict names the flatten plan; nothing here acts on
    either.
  * It does NOT parse English, render English, or carry language anywhere.
  * It does NOT retry, loop twice, or re-enter the ladder inside one turn.
  * It reads no clock, no file, no network, and writes nothing to disk.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM.
"""

from __future__ import annotations

from dataclasses import dataclass

import asom
import bias as bias_module
import disengage
import rpm_gate as rpm

__all__ = [
    "Loop", "TurnRecord", "Proposal", "Observation", "GateRequest", "GateVerdict",
    "LoopRefusal", "rpm_gate", "stub_gate", "proceeding_gate", "refusing_gate",
    "repairing_gate", "may_continue", "STAGES", "STAGE_READ_BIAS", "STAGE_PROPOSE",
    "STAGE_OBSERVE", "STAGE_GATE", "STAGE_DISENGAGE_OR_CONTINUE", "CONTINUE", "DISENGAGED",
    "REFUSED", "PROCEED", "REPAIR", "REFUSE", "OUTCOMES", "VERDICT_WORDS", "KNOWN_LABELS",
    "STUB_NOTE", "CLAIM_CEILING",
]

CLAIM_CEILING = "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM."

#: The five stage names, in order. A turn runs them in this order, once each.
STAGE_READ_BIAS = "READ_BIAS"
STAGE_PROPOSE = "PROPOSE"
STAGE_OBSERVE = "OBSERVE"
STAGE_GATE = "GATE"
STAGE_DISENGAGE_OR_CONTINUE = "DISENGAGE_OR_CONTINUE"
STAGES = (
    STAGE_READ_BIAS,
    STAGE_PROPOSE,
    STAGE_OBSERVE,
    STAGE_GATE,
    STAGE_DISENGAGE_OR_CONTINUE,
)

#: The gate's three words. They are defined in ``rpm_gate``, because they are the gate's, and
#: imported here so there is exactly one copy of each string in this build.
PROCEED = rpm.PROCEED
REPAIR = rpm.REPAIR
REFUSE = rpm.REFUSE
VERDICT_WORDS = rpm.VERDICT_WORDS

#: The turn's three outcomes.
CONTINUE = "CONTINUE"
DISENGAGED = "DISENGAGED"
REFUSED = "REFUSED"
OUTCOMES = (CONTINUE, DISENGAGED, REFUSED)

#: Every string the ASOM readout is allowed to return, for the record's own honesty flag.
KNOWN_LABELS = tuple(asom.LABELS) + (asom.NOT_EMITTED,)

#: What the retained placeholder says about itself, in its own reason field.
STUB_NOTE = (
    "STUB: this gate always proceeds and performed no RPM prerequisite check. It is kept "
    "only as a labelled placeholder and is not the loop's default gate; the default is the "
    "real RPM gate."
)

# Refusal codes. These are errors, not turn decisions: a refusal here produces no
# TurnRecord. The only thing that can decide a turn may not proceed is the gate.
LOOP_GATE_VERDICT_NOT_A_WORD = rpm.GATE_VERDICT_NOT_A_WORD
LOOP_PROPOSAL_NOT_A_PROPOSAL = "PROPOSAL_NOT_A_PROPOSAL"
LOOP_PROPOSAL_CITES_UNWRITTEN_FACT = "PROPOSAL_CITES_UNWRITTEN_FACT"
LOOP_NEEDS_A_PROPOSER = "LOOP_NEEDS_A_PROPOSER"
LOOP_NEEDS_A_GATE = "LOOP_NEEDS_A_GATE"
LOOP_NEEDS_AN_ASOM_READER = "LOOP_NEEDS_AN_ASOM_READER"
LOOP_NEEDS_A_BIAS = "LOOP_NEEDS_A_BIAS"
LOOP_NEEDS_A_COORDINATOR = "LOOP_NEEDS_A_COORDINATOR"
LOOP_BAD_SATURATED_FLAG = "BAD_SATURATED_FLAG"

# UNDECIDED IN SOURCES: whether one turn runs the ladder all the way to DISENGAGE or stops at ASK_CLARITY and ends there waiting for an answer -- the ladder's own ask (disengage.py:259) implies someone may answer it, while the owner's ladder is written as four steps ending in a disengage and "every step goes in the receipt" (THE_BUILD_RESTART_PLAN_20261016.md:88-94), so this build runs all four steps inside the one turn and never resumes inside it.

# UNDECIDED IN SOURCES: whether a REPAIR verdict is "the gate refusing" -- RPM is said to decide proceed / repair / refuse and the sources say what a repair names but never say what a turn does next, so this build treats REPAIR as "may not proceed", runs the ladder, and records the word REPAIR; nothing in this build performs a repair.

# UNDECIDED IN SOURCES: whether the disengage reason must be the gate's own stated reason or a separately named one -- the ladder requires a reason and says nothing about where it comes from, so this build passes the gate's reason through unchanged and lets the ladder refuse it if it is empty, rather than manufacturing one.

# UNDECIDED IN SOURCES: what a proposal must carry, and whether a proposal may cite a fact the Bias never carried -- the plan says the CJT proposes "under Bias" (THE_BUILD_RESTART_PLAN_20261016.md:13) and gives no content rule, so this build records the facts a proposal cites and refuses a citation of a fact the Bias did not hold, as a checkable form of "never invent".

# UNDECIDED IN SOURCES: who proposes, and whether the CJT that proposes must be the coordinator that owns the Bias -- the proposer is a pluggable callable here and no source says who may act on a Bias, so this build requires a proposer to be supplied and checks nothing about its identity.

# UNDECIDED IN SOURCES: whether the gate may read the operating region, the semantic outcome or the saturation flag at all -- RPM is described as deciding whether the next step may proceed and no source says what it may consult, so this build does not pass those three to the gate, which is what makes it structurally impossible for the ASOM label built from them to reach it.

# UNDECIDED IN SOURCES: whether the five stages are the whole turn, or whether a turn also writes the Bias -- attention is said to write into the Bias and the five stages only read it, so this build writes nothing during a turn and leaves writing to Loop.remember as a separate act.

# UNDECIDED IN SOURCES: what a proceeded turn hands to the next turn, and whether the next turn's Bias must be strictly newer than the one this turn read -- the plan's return rule requires a strictly newer Bias for a returned thread and says nothing about an ordinary consecutive turn, so this build requires a strictly newer Bias only of a thread that says it is returning (resume_from_version), and an ordinary turn requires nothing of the sort.

# UNDECIDED IN SOURCES: whether a gate that cannot proceed still needs its ASOM label recorded -- the plan says ASOM reports and never gates and says nothing about a turn that stops, so this build records the label on every turn, including the ones that disengage.

# UNDECIDED IN CANON: whether the turn's cause may be supplied by the same actor that proposes, and whether anything verifies that a block or a dirty ancestor really happened -- canon says nothing about who observes a block, so this build takes the cause from the caller, records it verbatim in the receipt, and checks nothing about its identity or its truth.

# UNDECIDED IN CANON: whether a REPAIR verdict ends the turn or pauses it waiting for the sub-goal -- canon says the action cannot be computed and never says whether the same turn resumes once the sub-goal is realized, so this build ends the turn at the ladder's disengage and records the named sub-goal in the receipt, and no later turn reads it back.

# UNDECIDED IN CANON: whether the sub-goal a REPAIR names must be recorded anywhere outside the turn -- no source gives a ledger for open sub-goals, so this build records it on the record and in the receipt and keeps no register, which is what makes the second turn in this build independent of the first.


class LoopRefusal(Exception):
    """A refusal with a stable code. Raised for a broken contract, never as a turn outcome."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The gate's two records
# --------------------------------------------------------------------------- #
#: The verdict record is the gate's own, defined in ``rpm_gate`` and re-exported here so that
#: ``loop.GateVerdict`` and ``rpm_gate.GateVerdict`` are the same class and not two shapes.
GateVerdict = rpm.GateVerdict


@dataclass(frozen=True)
class GateRequest:
    """Everything the gate is given. Note what is NOT here.

    There is no ASOM label field, no region field, no semantic-outcome field and no saturated
    field. So a gate -- the real one, the placeholder, or a test double -- cannot read the
    readout through this record even if it wanted to. That is the structural half of "ASOM
    must never gate anything"; the proof half is in the test file.

    ``cause`` is the turn's RPM cause: which node blocked, the depth, the state of the
    ancestor line, what is reported missing, and the Bias versions of a returning thread. It
    is an ``rpm_gate.RpmCause``, which carries no readout field either, and the gate refuses a
    request whose field list is not exactly the one this record has.
    """

    turn: int
    coordinator: str
    bias_version: int
    bias_digest: str
    proposal_text: str
    prerequisites: tuple
    cause: object = rpm.RpmCause()

    def as_dict(self) -> dict:
        return {
            "turn": self.turn,
            "coordinator": self.coordinator,
            "bias_version": self.bias_version,
            "bias_digest": self.bias_digest,
            "proposal_text": self.proposal_text,
            "prerequisites": list(self.prerequisites),
            "cause": self.cause.as_dict() if hasattr(self.cause, "as_dict") else repr(self.cause),
        }


def may_continue(verdict) -> bool:
    """THE ONLY continue/do-not-continue decision in this file. It reads one thing.

    Called with the gate's verdict and nothing else, so no other value -- no ASOM label, no
    region, no proposal, no Bias version -- is in scope here. If this function returned
    anything other than a function of the verdict, the role separation would be broken.
    """
    if not isinstance(verdict, GateVerdict):
        raise LoopRefusal(
            LOOP_GATE_VERDICT_NOT_A_WORD,
            f"may_continue() takes a GateVerdict, got {type(verdict).__name__}",
        )
    return verdict.can_proceed


# --------------------------------------------------------------------------- #
# The gate this build uses, and the doubles it tests with
# --------------------------------------------------------------------------- #
def rpm_gate(request: GateRequest) -> GateVerdict:
    """THE GATE. RPM decides, from the turn's cause alone. The loop's default.

    The decision itself is ``rpm_gate.rpm_gate``, which reads ``request.cause`` and asks the
    vendored engine. This wrapper exists so that ``loop.rpm_gate`` is the callable a Loop
    takes, and it adds no rule: it passes the request straight through.
    """
    return rpm.rpm_gate(request)


def stub_gate(request: GateRequest) -> GateVerdict:
    """THE PLACEHOLDER. Always proceeds, and says in its reason that it checked nothing.

    It is deliberately NOT the default any more. A verdict from it is marked ``stub=True`` and
    carries no RPM code, so a record can never be mistaken for an RPM decision after the fact.
    """
    return GateVerdict(verdict=PROCEED, gap=None, reason=STUB_NOTE, stub=True)


def proceeding_gate(request: GateRequest) -> GateVerdict:
    """A gate that always proceeds, not marked as the stub. For tests of the continue path."""
    return GateVerdict(
        verdict=PROCEED,
        gap=None,
        reason="proceed: every prerequisite this gate was asked about is supplied",
        stub=False,
    )


def refusing_gate(gap, reason):
    """A gate that always refuses, naming ``gap`` and saying ``reason``.

    For tests: it shows that a refusal which comes from the gate runs the ladder, and that
    a refusal runs the ladder no matter what the ASOM label says.
    """

    def gate(request: GateRequest) -> GateVerdict:
        return GateVerdict(verdict=REFUSE, gap=gap, reason=reason, stub=False)

    return gate


def repairing_gate(gap, reason):
    """A gate that always answers REPAIR. For tests: see the UNDECIDED note on REPAIR."""

    def gate(request: GateRequest) -> GateVerdict:
        return GateVerdict(verdict=REPAIR, gap=gap, reason=reason, stub=False)

    return gate


# --------------------------------------------------------------------------- #
# The other stage records
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Proposal:
    """What the CJT proposed, and which Bias facts it says it used.

    ``text`` is whatever the proposer says; this build does not parse or judge it.
    ``cites`` is checked against the snapshot the proposer was given -- a proposal may not
    cite a fact the Bias did not carry.
    """

    text: str
    cites: tuple = ()

    def as_dict(self) -> dict:
        return {"text": self.text, "cites": list(self.cites)}


@dataclass(frozen=True)
class Observation:
    """The stage-3 output: the three inputs and the ASOM label computed from them."""

    region: str
    semantic_outcome: str
    saturated: bool
    label: object
    label_known: bool

    def as_dict(self) -> dict:
        return {
            "region": self.region,
            "semantic_outcome": self.semantic_outcome,
            "saturated": self.saturated,
            "asom_label": self.label if isinstance(self.label, str) else repr(self.label),
            "label_known": self.label_known,
        }


@dataclass(frozen=True)
class TurnRecord:
    """One turn, carrying all five stage outputs, the label, the verdict and the receipt."""

    turn: int
    coordinator: str
    bias_snapshot: bias_module.BiasSnapshot
    proposal: Proposal
    observation: Observation
    gate: GateVerdict
    outcome: str
    ladder: object = None
    refusal_code: object = None
    refusal_detail: object = None
    stages_run: tuple = ()
    receipt: tuple = ()
    gate_calls: int = 0
    asom_calls: int = 0
    cause: object = None

    @property
    def asom_label(self):
        """The ASOM label this turn recorded. A display value; nothing branches on it."""
        return self.observation.label

    @property
    def gate_verdict(self) -> str:
        """The gate's word: PROCEED, REPAIR or REFUSE."""
        return self.gate.verdict

    @property
    def sub_goal(self):
        """The sub-goal a REPAIR named, or None. This build opens nothing."""
        return self.gate.sub_goal

    @property
    def continued(self) -> bool:
        """True when the turn went past the gate."""
        return self.outcome == CONTINUE

    @property
    def receipt_stages(self) -> tuple:
        """The stage (or ladder step) name of every receipt entry, in order."""
        return tuple(entry["stage"] for entry in self.receipt)

    @property
    def ladder_steps(self) -> tuple:
        """The ladder steps this turn performed, in order. Empty when it continued."""
        return tuple(
            entry["stage"] for entry in self.receipt if entry["kind"] == "LADDER_STEP"
        )

    def as_dict(self) -> dict:
        return {
            "turn": self.turn,
            "coordinator": self.coordinator,
            "stages_run": list(self.stages_run),
            "bias": self.bias_snapshot.as_dict(),
            "proposal": self.proposal.as_dict(),
            "observation": self.observation.as_dict(),
            "asom_label": self.asom_label,
            "cause": None if self.cause is None else self.cause.as_dict(),
            "gate": self.gate.as_dict(),
            "outcome": self.outcome,
            "ladder": self.ladder.as_dict() if self.ladder is not None else None,
            "refusal_code": self.refusal_code,
            "refusal_detail": self.refusal_detail,
            "receipt": [dict(entry) for entry in self.receipt],
            "gate_calls": self.gate_calls,
            "asom_calls": self.asom_calls,
        }

    def decision(self) -> tuple:
        """Everything this turn DECIDED, with nothing merely recorded.

        The ASOM label is deliberately absent: two turns with different labels and equal
        decisions are exactly the property the build must have. The first eight entries are the
        ones this tuple has always carried, in the order it has always carried them; the three
        the RPM gate added (its decision code, the sub-goal it named, the fix it named) follow.
        """
        return (
            self.gate.verdict,
            self.gate.gap,
            self.gate.reason,
            self.outcome,
            self.refusal_code,
            self.ladder_steps,
            None if self.ladder is None else self.ladder.ask,
            None if self.ladder is None else self.ladder.reason,
            self.gate.code,
            self.gate.sub_goal,
            self.gate.fix,
        )


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #
class Loop:
    """One loop with one Bias, one coordinator, one proposer, one gate and one readout.

    ``turn()`` runs the five stages and returns a ``TurnRecord``. Every collaborator is
    injected so the loop is testable: a proposer is a function of the Bias snapshot, a gate
    is a function of a ``GateRequest``, and the ASOM reader defaults to ``asom.readout``.

    The default gate is ``rpm_gate`` -- the RPM decision. A caller may pass any gate it likes
    (``stub_gate`` and the test doubles exist for that), and a record always says which kind
    of verdict it carries: ``stub=True`` for the placeholder, ``rpm=True`` for RPM's own.
    """

    def __init__(
        self,
        working_bias,
        coordinator,
        propose,
        gate=rpm_gate,
        asom_reader=asom.readout,
    ) -> None:
        if not isinstance(working_bias, bias_module.Bias):
            raise LoopRefusal(
                LOOP_NEEDS_A_BIAS,
                f"the loop reads a Bias, got {type(working_bias).__name__}",
            )
        if not isinstance(coordinator, str) or not coordinator.strip():
            raise LoopRefusal(
                LOOP_NEEDS_A_COORDINATOR,
                f"a coordinator must be named by a non-empty string, got {coordinator!r}",
            )
        for name, value, code in (
            ("propose", propose, LOOP_NEEDS_A_PROPOSER),
            ("gate", gate, LOOP_NEEDS_A_GATE),
            ("asom_reader", asom_reader, LOOP_NEEDS_AN_ASOM_READER),
        ):
            if not callable(value):
                raise LoopRefusal(code, f"{name} must be callable, got {type(value).__name__}")

        self._bias = working_bias
        self._coordinator = coordinator
        self._propose = propose
        self._gate = gate
        self._asom_reader = asom_reader
        self._turn = 0

    # -- read-only views ---------------------------------------------------- #
    @property
    def bias(self):
        """The Bias this loop reads."""
        return self._bias

    @property
    def coordinator(self) -> str:
        """The coordinator this loop acts as."""
        return self._coordinator

    @property
    def turn_count(self) -> int:
        """How many turns this loop has run."""
        return self._turn

    def remember(self, key, value) -> int:
        """Write one fact into the Bias, as this loop's coordinator.

        A separate act, not a stage: the five stages only read the Bias. If this loop's
        coordinator is not the Bias's owner, the Bias refuses -- the loop adds no rule of its
        own and cannot become a second writer.
        """
        return self._bias.write(key, value, self._coordinator)

    # -- the turn ----------------------------------------------------------- #
    def turn(self, region, outcome, saturated=False, prerequisites=(), cause=None):
        """Run one turn: read, propose, observe, gate, then disengage or continue.

        ``region``, ``outcome`` and ``saturated`` are the three observation inputs the
        runtime produces; the ASOM label is computed from them in stage 3. ``prerequisites``
        is what the turn declares it needs, and it goes to the gate unchanged as a record.

        ``cause`` is the turn's RPM cause (``rpm_gate.RpmCause``): which node blocked, at what
        depth, whether the ancestor line is invalid, what is reported missing, and the Bias
        versions of a returning thread. ``None`` means nothing blocks and nothing is missing,
        which the gate answers with PROCEED. A cause that is malformed is refused by the gate
        -- an error, not a verdict, and no record is produced.
        """
        if not isinstance(saturated, bool):
            raise LoopRefusal(
                LOOP_BAD_SATURATED_FLAG,
                f"saturated must be a bool, got {type(saturated).__name__}",
            )
        if cause is None:
            cause = rpm.RpmCause()

        # The number a record will carry. It is only taken up when a record is actually
        # returned, so a turn that raises a broken contract leaves no gap in the numbering and
        # a record's number is the index of that record.
        turn_number = self._turn + 1
        gate_calls = 0
        asom_calls = 0
        stages_run: list = []
        receipt: list = []

        # ---- 1. read the Bias ---------------------------------------------
        snapshot = self._bias.snapshot()
        stages_run.append(STAGE_READ_BIAS)
        receipt.append(
            {
                "index": len(receipt) + 1,
                "kind": "STAGE",
                "stage": STAGE_READ_BIAS,
                "of_turn": STAGE_READ_BIAS,
                "bias_version": snapshot.version,
                "bias_digest": snapshot.digest,
                "bias_keys": list(snapshot.keys()),
            }
        )

        # ---- 2. propose under the Bias ------------------------------------
        proposal = self._propose_proposal(snapshot)
        stages_run.append(STAGE_PROPOSE)
        receipt.append(
            {
                "index": len(receipt) + 1,
                "kind": "STAGE",
                "stage": STAGE_PROPOSE,
                "of_turn": STAGE_PROPOSE,
                "proposal": proposal.text,
                "cites": list(proposal.cites),
            }
        )

        # ---- 3. observe: the ASOM label -----------------------------------
        asom_calls += 1
        label = self._asom_reader(region, outcome, saturated)
        observation = Observation(
            region=region,
            semantic_outcome=outcome,
            saturated=saturated,
            label=label,
            label_known=isinstance(label, str) and label in KNOWN_LABELS,
        )
        stages_run.append(STAGE_OBSERVE)
        receipt.append(
            {
                "index": len(receipt) + 1,
                "kind": "STAGE",
                "stage": STAGE_OBSERVE,
                "of_turn": STAGE_OBSERVE,
                "asom_label": observation.as_dict()["asom_label"],
                "label_known": observation.label_known,
                "region": region,
                "semantic_outcome": outcome,
                "saturated": saturated,
            }
        )

        # ---- 4. gate ------------------------------------------------------
        request = GateRequest(
            turn=turn_number,
            coordinator=self._coordinator,
            bias_version=snapshot.version,
            bias_digest=snapshot.digest,
            proposal_text=proposal.text,
            prerequisites=tuple(prerequisites),
            cause=cause,
        )
        gate_calls += 1
        verdict = self._gate(request)  # THE GATE DECIDES. Nothing else may.
        if not isinstance(verdict, GateVerdict):
            raise LoopRefusal(
                LOOP_GATE_VERDICT_NOT_A_WORD,
                f"a gate must return a GateVerdict, got {type(verdict).__name__}",
            )
        stages_run.append(STAGE_GATE)
        receipt.append(
            {
                "index": len(receipt) + 1,
                "kind": "STAGE",
                "stage": STAGE_GATE,
                "of_turn": STAGE_GATE,
                "verdict": verdict.verdict,
                "gap": verdict.gap,
                "reason": verdict.reason,
                "stub": verdict.stub,
                "rpm": verdict.rpm,
                "code": verdict.code,
                "sub_goal": verdict.sub_goal,
                "fix": verdict.fix,
                "can_proceed": verdict.can_proceed,
                "cause": cause.as_dict() if hasattr(cause, "as_dict") else repr(cause),
            }
        )

        # ---- 5. disengage or continue -------------------------------------
        ladder_run = None
        refusal_code = None
        refusal_detail = None
        if may_continue(verdict):
            word = CONTINUE
            stages_run.append(CONTINUE)
            receipt.append(
                {
                    "index": len(receipt) + 1,
                    "kind": "STAGE",
                    "stage": CONTINUE,
                    "of_turn": STAGE_DISENGAGE_OR_CONTINUE,
                    "note": "the gate proceeded; the turn continues and the ladder is not run",
                }
            )
        else:
            ladder_run, refusal, ladder = self._walk_ladder(verdict.gap, verdict.reason)
            for entry in self._ladder_entries(ladder_run, ladder, receipt):
                receipt.append(entry)
                stages_run.append(entry["stage"])
            if refusal is not None:
                word = REFUSED
                refusal_code = refusal.code
                refusal_detail = refusal.detail
            else:
                word = DISENGAGED

        if tuple(stages_run[: len(STAGES) - 1]) != STAGES[: len(STAGES) - 1]:
            raise LoopRefusal(
                "LOOP_ORDER_VIOLATED",
                f"the five stages did not run in order: {list(stages_run)}",
            )

        self._turn = turn_number
        return TurnRecord(
            turn=turn_number,
            coordinator=self._coordinator,
            bias_snapshot=snapshot,
            proposal=proposal,
            observation=observation,
            gate=verdict,
            outcome=word,
            ladder=ladder_run,
            refusal_code=refusal_code,
            refusal_detail=refusal_detail,
            stages_run=tuple(stages_run),
            receipt=tuple(receipt),
            gate_calls=gate_calls,
            asom_calls=asom_calls,
            cause=cause,
        )

    # -- stage 2, in full --------------------------------------------------- #
    def _propose_proposal(self, snapshot) -> Proposal:
        """Call the proposer with the Bias snapshot and check what it hands back.

        The proposer is given the snapshot -- the reading stage 1 took -- and nothing else,
        so what it proposes is proposed under that Bias and no other.
        """
        raw = self._propose(snapshot)
        if isinstance(raw, Proposal):
            proposal = raw
        elif isinstance(raw, str):
            proposal = Proposal(text=raw, cites=())
        else:
            raise LoopRefusal(
                LOOP_PROPOSAL_NOT_A_PROPOSAL,
                f"a proposer must return a Proposal or a string, got {type(raw).__name__}",
            )
        if not isinstance(proposal.text, str):
            raise LoopRefusal(
                LOOP_PROPOSAL_NOT_A_PROPOSAL,
                f"a proposal's text must be a string, got {type(proposal.text).__name__}",
            )
        cites = tuple(proposal.cites)
        for name in cites:
            if not snapshot.has(name):
                raise LoopRefusal(
                    LOOP_PROPOSAL_CITES_UNWRITTEN_FACT,
                    f"the proposal cites {name!r}, which this Bias never carried (it carries "
                    f"{list(snapshot.keys())}); a proposal may not invent a fact it read",
                )
        return Proposal(text=proposal.text, cites=cites)

    # -- stage 5, in full --------------------------------------------------- #
    @staticmethod
    def _walk_ladder(gap, reason):
        """Run the owner's four steps. The ladder owns every rule about them.

        This method adds no rule of its own: an unnamed gap is refused by the ladder at the
        ask (CLARITY_ASK_NEEDS_GAP) and an empty reason is refused by the ladder at the
        disengage (DISENGAGE_NEEDS_REASON). Both refusals come back to the caller, which
        records them instead of asking a vague question or disengaging without a reason.
        """
        ladder = disengage.DisengageLadder(gap)
        ask_utterance = None
        final = None
        refusal = None
        try:
            ladder.step()  # NOT_DECLARED -- says nothing, records the step
            ladder.step()  # CONFUSED -- "I cannot tell."
            ask_utterance = ladder.step().utterance  # ASK_CLARITY -- names the exact gap
            final = ladder.step(reason=reason)  # DISENGAGE -- with a reason, or refused
        except disengage.DisengageRefusal as caught:
            refusal = caught

        if refusal is not None:
            return None, refusal, ladder

        run = disengage.LadderRun(
            gap=ladder.gap,
            info_provided=False,
            outcome=disengage.OUTCOME_DISENGAGED,
            steps=ladder.steps_taken,
            ask=ask_utterance,
            reason=final.reason,
            terminal=ladder.terminal,
            receipt=ladder.receipt,
            utterances=ladder.utterances,
        )
        return run, None, ladder

    @staticmethod
    def _ladder_entries(ladder_run, ladder, receipt):
        """One receipt entry per ladder step actually performed, in order.

        A refused ladder contributes the steps it did perform, not zero: a later reader has
        to see that it asked before it gave up.
        """
        source = ladder_run.receipt if ladder_run is not None else ladder.receipt
        entries = []
        for entry in source:
            entries.append(
                {
                    "index": len(receipt) + len(entries) + 1,
                    "kind": "LADDER_STEP",
                    "stage": entry["step"],
                    "of_turn": STAGE_DISENGAGE_OR_CONTINUE,
                    "gap": entry["gap"],
                    "reason": entry["reason"],
                    "utterance": entry["utterance"],
                    "note": entry["note"],
                }
            )
        return entries
