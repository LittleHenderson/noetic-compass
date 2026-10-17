"""disengage.py -- the owner's ladder: NOT DECLARED, CONFUSED, ASK, DISENGAGE WITH A REASON.

WHAT THIS MODULE DOES
---------------------
It implements the ladder the owner added on 2026-10-16, in his own direction, verbatim
(CONTINUITY_AND_DISENGAGE_20261016.md:104-107):

    "NOT DECLARED" -> "I'M CONFUSED, I HAVE NO IDEA" -> HELM ASK FOR CLARITY, FOR MORE
    INFORMATION, ETC. AND AT SOME POINT, DISENGAGE AFTER GIVING A REASON OF COURSE

It is a small deterministic state machine with exactly four steps:

    NOT_DECLARED -> CONFUSED -> ASK_CLARITY -> DISENGAGE

The rules the design states, each enforced here:

  * **Never guess at any step.** The ladder never supplies a value for the gap. Every
    result carries ``gap_value=None`` and the ladder has no way to set it.
  * **The ask names the actual missing item.** ``ask`` interpolates the gap name the caller
    passed in; an empty gap is refused as ``CLARITY_ASK_NEEDS_GAP`` rather than turned into
    a vague question.
  * **The disengage carries a reason.** An empty or whitespace-only reason is refused as
    ``DISENGAGE_NEEDS_REASON``, and the ladder does not advance.
  * **Disengage is terminal for that turn.** Calling ``step`` after it returns
    ``ALREADY_DISENGAGED``; it does not silently retry, does not repeat the ask, and does
    not append a second step to the receipt.
  * **Every step is recorded.** ``receipt`` gets one entry per performed step with the step
    name, the gap named, and the reason.

``run_ladder(gap, info_provided=False)`` walks the whole escalation to a disengage;
``run_ladder(gap, info_provided=True)`` shows that supplying the information returns to
normal: it asks, gets the answer, and never disengages.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT parse English, decide what the gap is, or verify an answer. The gap name is
    handed in by the caller and passed through byte for byte (MAP.md:52-55: identifiers are
    copied, never generated).
  * It does NOT choose where a step is permitted in the wider design, and it does not run
    as part of a thought's path; it is the ladder on its own.
  * It does NOT map itself onto the Noetics. The design maps the steps onto `CLARIFY`,
    `"I cannot tell."` and `REFUSE`, and those are language-layer words, not Noetic claims.
  * It does NOT retry, loop, or take a second turn. Disengage ends the turn.
  * It does NOT call any network, model, or clock.
  * It does NOT connect to the Recursive Possibility Atlas, and no step of the ladder reads
    or writes an atlas entry.

CLAIM CEILING (corrected in v4 -- S0 anchors on the real atlas model):
    MECHANISM ONLY. S0 ANCHORS TO THE REAL ATLAS MODEL AT COMMIT eb998556; THIS BUILD ADDS NO ATLAS OF ITS OWN. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The four steps, in order. Exactly four.
NOT_DECLARED = "NOT_DECLARED"
CONFUSED = "CONFUSED"
ASK_CLARITY = "ASK_CLARITY"
DISENGAGE = "DISENGAGE"
STEPS = (NOT_DECLARED, CONFUSED, ASK_CLARITY, DISENGAGE)

#: The fixed sentence the design pairs with step 2 (TAP_AND_INJECT.md:28-29: UNDETERMINED
#: is said as exactly "I cannot tell.", fixed, never drawn; mapped onto step 2 at
#: CONTINUITY_AND_DISENGAGE_20261016.md:113-116).
FIXED_CANNOT_TELL = "I cannot tell."

#: Result statuses.
OK = "OK"
ALREADY_DISENGAGED = "ALREADY_DISENGAGED"

#: Run outcomes.
OUTCOME_DISENGAGED = "DISENGAGED"
OUTCOME_RESUMED_NORMAL = "RESUMED_NORMAL"

#: Refusal codes.
DISENGAGE_NEEDS_REASON = "DISENGAGE_NEEDS_REASON"
CLARITY_ASK_NEEDS_GAP = "CLARITY_ASK_NEEDS_GAP"

# UNDECIDED IN DESIGN: whether the NOT DECLARED step speaks, and in what words -- the owner's ladder gives no sentence for it and CONTINUITY_AND_DISENGAGE_20261016.md:113-116 maps only step 2 onto "I cannot tell."; this build records the step in the receipt and says nothing.

# UNDECIDED IN DESIGN: what content the disengage reason must carry -- CONTINUITY_AND_DISENGAGE_20261016.md:122 requires "no, because X" and states no required fields; this build refuses only an empty reason.

# UNDECIDED IN DESIGN: whether a step may be skipped (for example disengage without asking) -- the ladder is given as an escalation and skipping is neither allowed nor forbidden; this build only ever takes the next step in order.

# UNDECIDED IN DESIGN: whether the same turn may re-enter the ladder after the information is supplied -- the packet says supplying it returns to normal and does not say whether a second gap in the same turn starts the ladder again; this build leaves the ladder resolved and starts no second one.


class DisengageRefusal(Exception):
    """A refusal with a stable code. The ladder advances only when a step is legal."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class StepResult:
    """What one call to ``step`` produced.

    ``gap_value`` is always ``None``: the ladder has no step that fills a gap, which is how
    "never guess at any step" is made checkable rather than promised.
    """

    index: int
    step: str
    status: str
    gap: str
    gap_value: None
    utterance: str | None
    reason: str | None
    note: str
    terminal: bool

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "step": self.step,
            "status": self.status,
            "gap": self.gap,
            "gap_value": self.gap_value,
            "utterance": self.utterance,
            "reason": self.reason,
            "note": self.note,
            "terminal": self.terminal,
        }


@dataclass(frozen=True)
class LadderRun:
    """The whole walk of the ladder for one gap, with its receipt.

    ``outcome`` is either ``DISENGAGED`` (the full four steps, with a reason) or
    ``RESUMED_NORMAL`` (the information was supplied, so the ladder never disengaged).
    """

    gap: str
    info_provided: bool
    outcome: str
    steps: tuple[str, ...]
    ask: str | None
    reason: str | None
    terminal: bool
    receipt: tuple[dict, ...]
    utterances: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict:
        return {
            "gap": self.gap,
            "info_provided": self.info_provided,
            "outcome": self.outcome,
            "steps": self.steps,
            "ask": self.ask,
            "reason": self.reason,
            "terminal": self.terminal,
            "utterances": self.utterances,
            "receipt": tuple(dict(entry) for entry in self.receipt),
        }


class DisengageLadder:
    """The four-step ladder for one gap. Deterministic: the same calls give the same steps.

    The machine starts at ``NOT_DECLARED``; each successful ``step()`` performs the current
    step, appends one receipt entry, and moves to the next. The disengage step needs a
    reason, and after it the ladder is terminal for that turn.
    """

    def __init__(self, gap: str) -> None:
        self.gap = gap
        self._index = 0
        self._done = False
        self._receipt: list[dict] = []
        self._refusals: list[dict] = []
        self._utterances: list[str] = []

    # -- read-only views -------------------------------------------------- #
    @property
    def state(self) -> str:
        """The current step: the one that ``step()`` will perform next."""
        return STEPS[self._index]

    @property
    def terminal(self) -> bool:
        """True once the disengage has been performed. Terminal for the turn."""
        return self._done

    @property
    def steps_taken(self) -> tuple[str, ...]:
        """The names of the steps performed so far, in order."""
        return tuple(entry["step"] for entry in self._receipt)

    @property
    def receipt(self) -> tuple[dict, ...]:
        """One entry per performed step: its name, the gap named, and the reason."""
        return tuple(dict(entry) for entry in self._receipt)

    @property
    def refusals(self) -> tuple[dict, ...]:
        """Refused attempts, kept apart from the receipt so the steps stay countable."""
        return tuple(dict(entry) for entry in self._refusals)

    @property
    def utterances(self) -> tuple[str, ...]:
        """Every sentence the ladder has said, in order. Step 1 says nothing."""
        return tuple(self._utterances)

    # -- the machine ------------------------------------------------------ #
    def step(self, reason: str | None = None) -> StepResult:
        """Perform the current step, or refuse. Never guesses, never fills the gap.

        ``reason`` is required at the disengage step and ignored before it.
        """
        if self._done:
            return StepResult(
                index=len(self._receipt),
                step=DISENGAGE,
                status=ALREADY_DISENGAGED,
                gap=self.gap,
                gap_value=None,
                utterance=None,
                reason=None,
                note=(
                    "disengage is terminal for this turn: no retry, no second ask, no second "
                    "receipt entry"
                ),
                terminal=True,
            )

        current = STEPS[self._index]
        reason_for_receipt = None

        if current == NOT_DECLARED:
            # See the UNDECIDED note above: the design gives no sentence for this step.
            utterance = None
            note = "the fact or cost is not on record; treated as the cautious class"
            next_index = 1
        elif current == CONFUSED:
            utterance = FIXED_CANNOT_TELL
            note = "say so plainly: I'm confused, I have no idea"
            next_index = 2
        elif current == ASK_CLARITY:
            if not isinstance(self.gap, str) or not self.gap.strip():
                self._refusals.append(
                    {
                        "step": current,
                        "gap": self.gap,
                        "reason": None,
                        "code": CLARITY_ASK_NEEDS_GAP,
                        "utterance": None,
                    }
                )
                raise DisengageRefusal(
                    CLARITY_ASK_NEEDS_GAP,
                    "the ask must name the actual missing item; the gap name is empty, and this "
                    "ladder does not ask a vague question",
                )
            utterance = f"I need {self.gap}. What is it?"
            note = f"CLARIFY names the exact item: {self.gap}"
            next_index = 3
        else:  # current == DISENGAGE
            if not isinstance(reason, str) or not reason.strip():
                self._refusals.append(
                    {
                        "step": current,
                        "gap": self.gap,
                        "reason": reason,
                        "code": DISENGAGE_NEEDS_REASON,
                        "utterance": None,
                    }
                )
                raise DisengageRefusal(
                    DISENGAGE_NEEDS_REASON,
                    "the disengage must carry a reason -- not 'no', but 'no, because X'",
                )
            utterance = f"I disengage because {reason}."
            note = "REFUSE / DISENGAGE with a stated reason"
            next_index = 3
            reason_for_receipt = reason

        entry = {
            "index": len(self._receipt) + 1,
            "step": current,
            "gap": self.gap,
            "reason": reason_for_receipt,
            "utterance": utterance,
            "note": note,
        }
        self._receipt.append(entry)
        if utterance is not None:
            self._utterances.append(utterance)

        if current == DISENGAGE:
            self._done = True
        else:
            self._index = next_index

        return StepResult(
            index=entry["index"],
            step=current,
            status=OK,
            gap=self.gap,
            gap_value=None,
            utterance=utterance,
            reason=reason_for_receipt,
            note=note,
            terminal=self._done,
        )


# --------------------------------------------------------------------------- #
# The two demonstrations the design asks for
# --------------------------------------------------------------------------- #
def default_reason(gap: str) -> str:
    """A reason built from the gap that was never supplied. Not a decorative word."""
    return f"{gap} was never supplied after it was asked for"


def run_ladder(gap: str, info_provided: bool = False, reason: str | None = None) -> LadderRun:
    """Walk the ladder for ``gap``.

    ``info_provided=False`` (the default) demonstrates the full escalation: not declared, say
    so plainly, ask by name, then disengage with a reason.

    ``info_provided=True`` demonstrates that supplying the information returns to normal: the
    ladder gets as far as the ask, the answer arrives, and it never disengages, so the turn
    resumes instead of ending.

    ``reason`` overrides the default reason on the disengage. A ``reason`` that is present but
    empty is refused as ``DISENGAGE_NEEDS_REASON``: the design wants a reason, not a blank.
    """
    ladder = DisengageLadder(gap)
    ladder.step()  # NOT_DECLARED
    ladder.step()  # CONFUSED
    ask = ladder.step()  # ASK_CLARITY

    if info_provided:
        return LadderRun(
            gap=ladder.gap,
            info_provided=True,
            outcome=OUTCOME_RESUMED_NORMAL,
            steps=ladder.steps_taken,
            ask=ask.utterance,
            reason=None,
            terminal=False,
            receipt=ladder.receipt,
            utterances=ladder.utterances,
        )

    final_reason = default_reason(ladder.gap) if reason is None else reason
    disengaged = ladder.step(reason=final_reason)
    return LadderRun(
        gap=ladder.gap,
        info_provided=False,
        outcome=OUTCOME_DISENGAGED,
        steps=ladder.steps_taken,
        ask=ask.utterance,
        reason=disengaged.reason,
        terminal=ladder.terminal,
        receipt=ladder.receipt,
        utterances=ladder.utterances,
    )
