"""Ablations — the organism's workspace with exactly one rule removed.

The Revision Streams family cannot show that truth maintenance is *necessary*:
a two-set replayer of the event log answers every probe correctly with no
truth maintenance in it (contract §0). What the family can show is that each
rule the workspace enforces is *doing something*: remove the rule and a
specific, named class of probe starts failing, while every other class keeps
passing. That is the diagnostic claim, and this module is its instrument.

Each class below subclasses `Workspace` and overrides the smallest surface
that removes one rule, and only that rule. The docstring of each names the
rule in the base class's own words, the failure a reasoner with that rule
missing exhibits, and the contract class (§7) expected to detect it. The
expectation is a prediction, not a result: `revision_experiment.py` reports
what actually happened, cell by cell, and the test suite pins only what is
robust.

Nothing here is a solver. An ablation is handed to the `Organism` through its
`workspace_factory` argument; the organism and the banks run unchanged over
the damaged workspace. A failure that appears can therefore be attributed to
the removed rule and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from workspace import ASSERTIVE, Proposition, Status, Workspace


# ---------------------------------------------------------------------------
# R — retraction
# ---------------------------------------------------------------------------

class NonTransitiveRetract(Workspace):
    """Rule removed: "Retraction is transitive by construction."

    `retract()` marks the proposition RETRACTED and stops. Whatever was derived
    from it keeps its status, so a conclusion the organism landed earlier is
    still answered from the record after its support is gone. The reasoner
    "retracts an assumption but keeps its consequences" -- the exact defect
    the base rule's docstring warns about.

    The contradiction cascade is deliberately left intact (dependents of a
    *disputed* proposition still fall) so that this ablation and `NoCascade`
    each remove one rule, not one and a half.

    Expected to fail: R-stale, R-deep (a held derivation outlives a retracted
    support). Expected to pass: everything that never held a derivation
    across the retraction.
    """

    removed = "Workspace.retract: the cascade over dependents"
    overrides = ("retract", "_cascade")

    def retract(self, pid: str) -> None:
        prop = self.props.get(pid)
        if prop is None:
            # Same refusal as the base; the rule removed is the cascade, not
            # the check that there is something to withdraw.
            super().retract(pid)
            return
        was_contradicted = prop.status is Status.CONTRADICTED
        self.props[pid] = replace(prop, status=Status.RETRACTED)
        self._prior.pop(pid, None)
        self.journal.append(f"retracted {pid} (no cascade)")
        if was_contradicted:
            counter_pid = ("" if prop.negated else "~") + prop.key
            counter = self.props.get(counter_pid)
            if counter is not None and counter.status is Status.CONTRADICTED:
                prior = self._prior.pop(counter_pid, Status.FACT)
                self.props[counter_pid] = replace(counter, status=prior)
                self.journal.append(f"reinstated {counter_pid}")

    def _cascade(self, pid: str) -> None:
        # Reached only from `add()`'s contradiction path. Dependents of a
        # disputed proposition fall transitively, exactly as in the base: the
        # base `retract` is used for them so the ablated one above is not.
        for other in list(self.props.values()):
            if pid in other.support and other.status is not Status.RETRACTED:
                Workspace.retract(self, other.pid)


# ---------------------------------------------------------------------------
# H — the hypothesis firewall
# ---------------------------------------------------------------------------

class NoFirewall(Workspace):
    """Rule removed: a guess the organism is *told* is not a given.

    A stream HYPOTHESIS (any stage other than `^8`) is filed as a FACT. The
    organism can now chain through what was only a "maybe", so a route whose
    one missing link was hypothesised is answered YES, and a later NEGATION of
    that link finds an assertive counterpart and raises a contradiction where
    the base workspace would have merely refuted the guess.

    `^8`'s own route bookkeeping (stage `"^8"`) is untouched: that is a
    different mechanism, swept at the end of every episode, and `NoSweep`
    ablates it separately.

    Expected to fail: H-bridge (YES instead of UNKNOWN/NO), H-refute
    (INADMISSIBLE instead of UNKNOWN/NO). Expected to pass: R, C, N.
    """

    removed = "Workspace.hypothesize: Status.HYPOTHESIS for told guesses"
    overrides = ("hypothesize",)

    def hypothesize(
        self, subject: str, relation: str, obj: str, *, stage: str = "^8", negated: bool = False
    ) -> Proposition:
        if stage == "^8":
            return super().hypothesize(subject, relation, obj, stage=stage, negated=negated)
        return self.add(Proposition(subject, relation, obj, negated, Status.FACT, stage=stage))


# ---------------------------------------------------------------------------
# C — contradiction
# ---------------------------------------------------------------------------

class LastWriterAdd(Workspace):
    """Rule removed: "assertive vs assertive: a CONTRADICTION. Both sides are marked."

    The newcomer wins. The earlier side is RETRACTED (with its dependents) and
    the new polarity is stored as if nothing had ever disagreed with it. No
    proposition is ever CONTRADICTED, so `contested()` is always false and the
    processor can never report a dispute: a question whose only route runs
    through a denied-and-asserted link is answered NO/UNKNOWN instead of
    INADMISSIBLE, and the organism silently believes whichever statement it
    heard last.

    Expected to fail: C-blocked, C-stale. Expected to pass: C-bypassed,
    C-unrelated, and the other classes.
    """

    removed = "Workspace.add: the assertive-vs-assertive contradiction"
    overrides = ("add",)

    def add(self, prop: Proposition) -> Proposition:
        counter_pid = ("" if prop.negated else "~") + prop.key
        counter = self.props.get(counter_pid)
        if counter is not None and counter.status in ASSERTIVE and prop.status in ASSERTIVE:
            self.props[counter.pid] = replace(counter, status=Status.RETRACTED)
            self.journal.append(f"overwritten {counter.pid}")
            self._cascade(counter.pid)
        return super().add(prop)


class NoCascade(Workspace):
    """Rule removed: "everything resting on either side is retracted."

    Both sides of a contradiction are still marked CONTRADICTED, but nothing
    that rests on them moves. A conclusion derived from a link that is now in
    dispute keeps standing as DERIVED and is answered from the record. This is
    the one ablation the organism's heartbeat is built to catch structurally:
    the audit finds a standing conclusion whose root is no longer assertive
    and raises E-ORG-003.

    Explicit retraction still cascades, so this and `NonTransitiveRetract`
    remove disjoint rules.

    Expected to fail: C-stale. Expected to pass: everything else.
    """

    removed = "Workspace.add: the cascade from a contradicted proposition"
    overrides = ("_cascade",)

    def _cascade(self, pid: str) -> None:
        prop = self.props.get(pid)
        if prop is not None and prop.status is Status.CONTRADICTED:
            return
        super()._cascade(pid)


# ---------------------------------------------------------------------------
# N — lacunae
# ---------------------------------------------------------------------------

class AmnesicAsk(Workspace):
    """Rule removed: "Every question asked is recorded."

    `ask()` answers and forgets. `lacunae()` therefore has nothing to report,
    the RPM gate has no sub-goal to name, and the organism's honest abstention
    degrades to a bare UNKNOWN. Verdicts are unchanged; the `named` column on
    open-world UNKNOWN probes is what fails.

    Expected to fail: the lacuna column of N-gap. Expected to pass: every
    verdict.
    """

    removed = "Workspace.ask: recording the question for lacunae()"
    overrides = ("ask",)

    def ask(self, subject: str, relation: str, obj: str) -> str:
        key = f"{subject}|{relation}|{obj}"
        prop = self.props.get(key)
        if prop is not None and prop.status in ASSERTIVE:
            return "YES"
        negative = self.props.get("~" + key)
        if negative is not None and negative.status in ASSERTIVE:
            return "NO"
        return "NO" if self.closed_world else "UNKNOWN"


@dataclass
class FixedWorld(Workspace):
    """Rule removed: "`closed_world` decides what absence means."

    The flag is accepted and ignored; the workspace always reasons under an
    open world. On the open-world half of a paired set this is invisible. On
    the closed-world half every NO-by-closure becomes UNKNOWN. That signature
    -- perfect on one world, wrong on exactly the closure probes of the other
    -- is what the paired generation in contract §7 exists to expose.

    Expected to fail: closed-world probes whose verdict is rule 5 (NO by
    closure). Expected to pass: the open-world set entirely.
    """

    removed = "Workspace.closed_world: honouring the world assumption"
    overrides = ("__post_init__",)

    def __post_init__(self) -> None:
        # Re-decorated with @dataclass so the generated __init__ calls this;
        # the base class has no __post_init__, so its __init__ never would.
        self.closed_world = False


class NoSweep(Workspace):
    """Rule removed: `^8` marks its route guesses as its own output.

    The bank files every surfaced route's conclusion as a HYPOTHESIS at stage
    `"^8"`. Two mechanisms key on that mark: the sweep at the end of every
    episode retracts exactly those records, and the next walk skips them, so a
    bank never re-triggers on its prior output. Remove the mark and both are
    gone at once -- the guesses linger and are walked -- which is the one
    rule, "a stage knows its own output", that the sweep and the skip jointly
    enforce. Disabling `sweep()` alone changes nothing: the walk would still
    skip the marked records (measured; see the test).

    With the mark gone, a later question whose route passes through an
    earlier unanswered question's endpoints is answered along the lingering
    guess: `^6` asks for it, finds a guess, and names it as a gap. That key is
    in neither `hyp` nor `assoc` nor the query pair, so the `named` column
    loses precision. Whether the generated family contains such a probe
    pattern is for the experiment to report; if it does not, the result is
    "not load-bearing on this family relative to the organism that lacks it",
    and nothing more.
    """

    removed = "Workspace.hypothesize: the stage mark on ^8's route guesses"
    overrides = ("hypothesize",)

    def hypothesize(
        self, subject: str, relation: str, obj: str, *, stage: str = "^8", negated: bool = False
    ) -> Proposition:
        if stage == "^8":
            stage = ""
        return super().hypothesize(subject, relation, obj, stage=stage, negated=negated)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Ablation:
    """One entry of the experiment's ablation axis."""

    name: str
    workspace: type[Workspace]
    removed: str
    expected_to_fail: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.name}: -{self.removed}"


ABLATIONS: tuple[Ablation, ...] = (
    Ablation("abl_nontransitive_retract", NonTransitiveRetract, NonTransitiveRetract.removed, ("R-stale", "R-deep")),
    Ablation("abl_no_firewall", NoFirewall, NoFirewall.removed, ("H-bridge", "H-refute")),
    Ablation("abl_last_writer_add", LastWriterAdd, LastWriterAdd.removed, ("C-blocked", "C-stale")),
    Ablation("abl_no_cascade", NoCascade, NoCascade.removed, ("C-stale",)),
    Ablation("abl_amnesic_ask", AmnesicAsk, AmnesicAsk.removed, ("N-gap:named",)),
    Ablation("abl_fixed_world", FixedWorld, FixedWorld.removed, ("closed-world rule-5 probes",)),
    Ablation("abl_no_sweep", NoSweep, NoSweep.removed, ("named precision after an earlier abstention",)),
)

BY_NAME: dict[str, Ablation] = {a.name: a for a in ABLATIONS}


def ablation(name: str) -> Ablation:
    try:
        return BY_NAME[name]
    except KeyError:
        raise KeyError(f"unknown ablation {name!r}; known: {', '.join(sorted(BY_NAME))}") from None

