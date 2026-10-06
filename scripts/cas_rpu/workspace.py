"""The CAS Global Workspace — what the processor is currently holding.

The runtime's missing-component list names four things a component library
does not supply on its own. Three of them live here:

    binding and substitution   variables, objects, relations, identity across
                               steps (`Pattern`, `Workspace.match`)
    truth maintenance          facts, hypotheses, assumptions, derivations,
                               contradictions, and unknowns kept apart
                               (`Status`, `Workspace.contradictions`)
    the workspace itself       the active problem, premises, candidates, and
                               intermediate states

The fourth, scheduling, is in `runtime.py`.

Epistemic status is not decoration. A processor that cannot tell a premise it
was given from a conclusion it derived cannot detect a circular justification,
cannot retract cleanly, and cannot report *why* it believes something. Every
proposition therefore carries its status and its support, and every derived
proposition can be walked back to the roots it rests on.

Open versus closed world
------------------------
`Workspace.closed_world` decides what absence means, and it is the single
switch that separates "no, that is false" from "I do not know". This is the
distinction the RPM gate acts on: under an open world a chain that does not
close yields NEEDS_INFORMATION, never a confident NO.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace
from enum import Enum

VARIABLE_PREFIX = "?"


class WorkspaceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class Status(str, Enum):
    """How the workspace came to hold a proposition."""

    FACT = "fact"                # given as a premise
    ASSUMPTION = "assumption"    # taken on for the sake of a branch
    HYPOTHESIS = "hypothesis"    # surfaced by ^8, not yet tested
    DERIVED = "derived"          # produced by ^9 from support
    CONTRADICTED = "contradicted"
    RETRACTED = "retracted"


#: Statuses that count as currently believed.
LIVE = (Status.FACT, Status.ASSUMPTION, Status.HYPOTHESIS, Status.DERIVED)
#: Statuses that can carry an inference. A hypothesis cannot: it is a candidate,
#: and letting ^9 chain through untested hypotheses is how a reasoner
#: convinces itself of whatever it first guessed.
ASSERTIVE = (Status.FACT, Status.ASSUMPTION, Status.DERIVED)

#: How much weight a status carries, for deciding which of two competing
#: records of the same claim survives. This is a strength ordering and is
#: deliberately NOT the order of `LIVE`: a premise the processor was given
#: outranks one it derived, which outranks one it merely assumed for a branch,
#: which outranks a guess. Re-guessing something already established must not
#: demote it.
STRENGTH: dict[Status, int] = {
    Status.HYPOTHESIS: 0,
    Status.ASSUMPTION: 1,
    Status.DERIVED: 2,
    Status.FACT: 3,
}


@dataclass(frozen=True)
class Proposition:
    """One triple the workspace holds, with its epistemic provenance."""

    subject: str
    relation: str
    obj: str
    negated: bool = False
    status: Status = Status.FACT
    support: tuple[str, ...] = ()
    stage: str = ""
    cas: str = ""

    @property
    def key(self) -> str:
        """Identity of the claim itself, ignoring polarity and status."""
        return f"{self.subject}|{self.relation}|{self.obj}"

    @property
    def pid(self) -> str:
        """Identity including polarity. `not P` is a different proposition."""
        return ("~" if self.negated else "") + self.key

    def contradicts(self, other: "Proposition") -> bool:
        return self.key == other.key and self.negated != other.negated

    def __str__(self) -> str:
        arrow = "-/->" if self.negated else "->"
        return f"{self.subject} {arrow}[{self.relation}] {self.obj}"


@dataclass(frozen=True)
class Pattern:
    """A triple with `?variables` in any position.

    `Pattern("?x", "leads_to", "?y")` matches every edge and binds both ends.
    """

    subject: str
    relation: str
    obj: str
    negated: bool = False

    @staticmethod
    def is_variable(term: str) -> bool:
        return term.startswith(VARIABLE_PREFIX)

    def variables(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                t for t in (self.subject, self.relation, self.obj) if self.is_variable(t)
            )
        )

    def bind(self, bindings: dict[str, str]) -> "Pattern":
        """Substitute what is known; unbound variables stay variables."""
        return Pattern(
            bindings.get(self.subject, self.subject) if self.is_variable(self.subject) else self.subject,
            bindings.get(self.relation, self.relation) if self.is_variable(self.relation) else self.relation,
            bindings.get(self.obj, self.obj) if self.is_variable(self.obj) else self.obj,
            self.negated,
        )

    def unify(self, prop: Proposition, bindings: dict[str, str] | None = None) -> dict[str, str] | None:
        """Bindings that make this pattern the given proposition, or None.

        Consistent with any bindings passed in, so a conjunction of patterns
        can be matched by threading one dictionary through them -- which is
        what makes a multi-premise rule expressible at all.
        """
        if prop.negated != self.negated:
            return None
        out = dict(bindings or {})
        for term, value in (
            (self.subject, prop.subject),
            (self.relation, prop.relation),
            (self.obj, prop.obj),
        ):
            if self.is_variable(term):
                if term in out and out[term] != value:
                    return None
                out[term] = value
            elif term != value:
                return None
        return out


@dataclass
class Workspace:
    """The active problem: premises, hypotheses, derivations, and their history.

    Indexed by `pid`, so asserting the same claim twice does not duplicate it
    and asserting its negation is detected rather than silently coexisting.
    """

    closed_world: bool = False
    props: dict[str, Proposition] = field(default_factory=dict)
    journal: list[str] = field(default_factory=list)
    #: key -> the mark current when it was last asked. Lets an episode report
    #: only the gaps *it* hit, not every question the workspace ever heard.
    _asked: dict[str, int] = field(default_factory=dict)
    _marks: int = 0
    #: pid -> the status it held before being marked CONTRADICTED, so that
    #: retracting one side of a contradiction can reinstate the other.
    _prior: dict[str, Status] = field(default_factory=dict)

    # ---- population ------------------------------------------------------

    def add(self, prop: Proposition) -> Proposition:
        """Insert or strengthen a proposition, detecting contradiction.

        A stronger status wins: a claim first surfaced as a hypothesis and
        later derived becomes derived. The reverse never happens -- evidence
        does not decay back into a guess because someone re-guessed it.

        Polarity collisions are resolved by what each side *is*:

          assertive vs assertive   a CONTRADICTION. Both sides are marked and
                                   everything resting on either side is
                                   retracted, because a conclusion built on a
                                   contested premise has lost its footing.
          assertive vs hypothesis  a REFUTATION. The guess dies; the claim
                                   stands. A guess was never evidence, so
                                   nothing it touched needs to fall.
          hypothesis vs hypothesis coexist. Two guesses that disagree are a
                                   question, not a crisis.

        A claim arriving against a side that is already CONTRADICTED joins the
        contradiction rather than quietly reviving one half of it.
        """
        existing = self.props.get(prop.pid)
        if existing is not None and existing.status is Status.CONTRADICTED:
            # A disputed record absorbs re-assertions and guesses of the same
            # claim alike. Only retracting one side of the dispute changes it;
            # a fresh arrival must not quietly replace half of a contradiction.
            return existing

        counter_pid = ("" if prop.negated else "~") + prop.key
        counter = self.props.get(counter_pid)
        if counter is not None:
            if counter.status in ASSERTIVE and prop.status in ASSERTIVE:
                self._prior[counter.pid] = counter.status
                self._prior[prop.pid] = prop.status
                self.props[counter.pid] = replace(counter, status=Status.CONTRADICTED)
                self.props[prop.pid] = replace(prop, status=Status.CONTRADICTED)
                self.journal.append(f"contradiction {prop.key}")
                self._cascade(counter.pid)
                self._cascade(prop.pid)
                return self.props[prop.pid]
            if counter.status is Status.CONTRADICTED and prop.status in ASSERTIVE:
                self._prior.setdefault(prop.pid, prop.status)
                self.props[prop.pid] = replace(prop, status=Status.CONTRADICTED)
                self.journal.append(f"contradiction {prop.key}")
                return self.props[prop.pid]
            if counter.status is Status.HYPOTHESIS and prop.status in ASSERTIVE:
                self.props[counter.pid] = replace(counter, status=Status.RETRACTED)
                self.journal.append(f"refuted {counter.pid}")
            elif prop.status is Status.HYPOTHESIS and (
                counter.status in ASSERTIVE or counter.status is Status.CONTRADICTED
            ):
                self.props[prop.pid] = replace(prop, status=Status.RETRACTED)
                self.journal.append(f"refuted {prop.pid}")
                return self.props[prop.pid]

        existing = self.props.get(prop.pid)
        if existing is not None:
            if (
                existing.status in LIVE
                and prop.status in LIVE
                and STRENGTH[prop.status] <= STRENGTH[existing.status]
            ):
                return existing
        self.props[prop.pid] = prop
        self.journal.append(f"{prop.status.value} {prop.pid}")
        return prop

    def fact(self, subject: str, relation: str, obj: str, *, negated: bool = False) -> Proposition:
        return self.add(Proposition(subject, relation, obj, negated, Status.FACT))

    def assume(self, subject: str, relation: str, obj: str, *, negated: bool = False) -> Proposition:
        return self.add(Proposition(subject, relation, obj, negated, Status.ASSUMPTION))

    def hypothesize(
        self, subject: str, relation: str, obj: str, *, stage: str = "^8", negated: bool = False
    ) -> Proposition:
        return self.add(
            Proposition(subject, relation, obj, negated, Status.HYPOTHESIS, stage=stage)
        )

    def derive(
        self,
        subject: str,
        relation: str,
        obj: str,
        support: tuple[str, ...],
        *,
        stage: str = "^9",
        cas: str = "",
        negated: bool = False,
    ) -> Proposition:
        """Land a conclusion on named support.

        Support must already be present and assertive. A derivation resting on
        a hypothesis is refused (E-WS-002) -- that is the step by which a
        machine turns its own guess into its own evidence.
        """
        for pid in support:
            parent = self.props.get(pid)
            if parent is None:
                raise WorkspaceError("E-WS-001", f"support {pid!r} is not in the workspace")
            if parent.status not in ASSERTIVE:
                raise WorkspaceError(
                    "E-WS-002",
                    f"support {pid!r} has status {parent.status.value}; a conclusion may "
                    "not rest on it",
                )
        prop = Proposition(subject, relation, obj, negated, Status.DERIVED, tuple(support), stage, cas)
        if prop.pid in support:
            raise WorkspaceError("E-WS-003", f"{prop.pid} would support itself")
        return self.add(prop)

    def retract(self, pid: str) -> None:
        """Withdraw a proposition and everything resting on it.

        Retraction is transitive by construction. A processor that retracts an
        assumption but keeps its consequences is holding conclusions with no
        remaining reason to believe them.
        """
        prop = self.props.get(pid)
        if prop is None:
            raise WorkspaceError("E-WS-004", f"cannot retract absent {pid!r}")
        was_contradicted = prop.status is Status.CONTRADICTED
        self.props[pid] = replace(prop, status=Status.RETRACTED)
        self._prior.pop(pid, None)
        self.journal.append(f"retracted {pid}")
        self._cascade(pid)
        if was_contradicted:
            # Withdrawing one side of a contradiction leaves the other side
            # merely asserted again. It gets back the status it had before.
            counter_pid = ("" if prop.negated else "~") + prop.key
            counter = self.props.get(counter_pid)
            if counter is not None and counter.status is Status.CONTRADICTED:
                prior = self._prior.pop(counter_pid, Status.FACT)
                self.props[counter_pid] = replace(counter, status=prior)
                self.journal.append(f"reinstated {counter_pid}")

    def _cascade(self, pid: str) -> None:
        """Retract everything whose support names `pid`. Transitive."""
        for other in list(self.props.values()):
            if pid in other.support and other.status is not Status.RETRACTED:
                self.retract(other.pid)

    def sweep(self, stage: str) -> tuple[str, ...]:
        """Retract every live proposition produced by `stage`.

        Used at the end of an episode to clear `^8`'s own route hypotheses,
        so the bank never re-triggers on its prior output. Nothing can rest on
        a hypothesis (`derive` refuses), so the cascade is a no-op by law.
        """
        swept = tuple(
            sorted(p.pid for p in self.props.values() if p.status in LIVE and p.stage == stage)
        )
        for pid in swept:
            self.retract(pid)
        return swept

    def mark(self) -> int:
        """Advance and return the episode mark. See `lacunae(since=...)`."""
        self._marks += 1
        return self._marks

    # ---- query -----------------------------------------------------------

    def live(self) -> tuple[Proposition, ...]:
        return tuple(p for p in self.props.values() if p.status in LIVE)

    def assertive(self) -> tuple[Proposition, ...]:
        return tuple(p for p in self.props.values() if p.status in ASSERTIVE)

    def match(self, pattern: Pattern, bindings: dict[str, str] | None = None) -> list[dict[str, str]]:
        """Every binding under which `pattern` holds assertively."""
        out: list[dict[str, str]] = []
        for prop in self.assertive():
            found = pattern.unify(prop, bindings)
            if found is not None:
                out.append(found)
        return out

    def match_all(self, patterns: list[Pattern]) -> list[dict[str, str]]:
        """Bindings satisfying every pattern at once -- a conjunctive query."""
        frontier: list[dict[str, str]] = [{}]
        for pattern in patterns:
            nxt: list[dict[str, str]] = []
            for binding in frontier:
                nxt.extend(self.match(pattern.bind(binding), binding))
            frontier = nxt
            if not frontier:
                break
        deduped: list[dict[str, str]] = []
        for binding in frontier:
            if binding not in deduped:
                deduped.append(binding)
        return deduped

    def holds(self, subject: str, relation: str, obj: str) -> bool:
        prop = self.props.get(f"{subject}|{relation}|{obj}")
        return prop is not None and prop.status in ASSERTIVE

    def ask(self, subject: str, relation: str, obj: str) -> str:
        """YES / NO / UNKNOWN, honouring the world assumption.

        Under an open world, the absence of a claim is `UNKNOWN`. Under a
        closed world it is `NO`. Every question asked is recorded, so a later
        stage can see what the processor wanted to know and did not find --
        the lacuna signal the RPM gate turns into a sub-goal.
        """
        key = f"{subject}|{relation}|{obj}"
        self._asked[key] = self._marks
        prop = self.props.get(key)
        if prop is not None and prop.status in ASSERTIVE:
            return "YES"
        negative = self.props.get("~" + key)
        if negative is not None and negative.status in ASSERTIVE:
            return "NO"
        return "NO" if self.closed_world else "UNKNOWN"

    def contradictions(self) -> tuple[str, ...]:
        return tuple(
            sorted({p.key for p in self.props.values() if p.status is Status.CONTRADICTED})
        )

    def contested(self, subject: str, relation: str, obj: str) -> bool:
        """Is this exact link held in both polarities, each contradicting the other?"""
        key = f"{subject}|{relation}|{obj}"
        pos = self.props.get(key)
        neg = self.props.get("~" + key)
        return (
            pos is not None
            and neg is not None
            and pos.status is Status.CONTRADICTED
            and neg.status is Status.CONTRADICTED
        )

    def lacunae(self, since: int = 0) -> tuple[str, ...]:
        """Questions asked whose answer the workspace could not supply.

        `since` restricts the report to questions asked at or after that
        episode mark, so a long-lived workspace reports the gaps *this*
        episode hit rather than every unanswered question in its history.
        """
        return tuple(
            sorted(
                key
                for key, asked_at in self._asked.items()
                if asked_at >= since
                and not (
                    (self.props.get(key) and self.props[key].status in ASSERTIVE)
                    or (self.props.get("~" + key) and self.props["~" + key].status in ASSERTIVE)
                )
            )
        )

    def justification(self, pid: str, _seen: tuple[str, ...] = ()) -> dict:
        """The support tree beneath a proposition, down to its roots.

        This is what makes a conclusion auditable rather than merely produced.
        A cycle is reported as such instead of recursing forever.
        """
        if pid in _seen:
            return {"pid": pid, "cycle": True}
        prop = self.props.get(pid)
        if prop is None:
            raise WorkspaceError("E-WS-001", f"{pid!r} is not in the workspace")
        return {
            "pid": pid,
            "claim": str(prop),
            "status": prop.status.value,
            "stage": prop.stage,
            "support": [self.justification(s, _seen + (pid,)) for s in prop.support],
        }

    def roots(self, pid: str) -> tuple[str, ...]:
        """The premises a conclusion ultimately rests on."""
        prop = self.props.get(pid)
        if prop is None:
            raise WorkspaceError("E-WS-001", f"{pid!r} is not in the workspace")
        if not prop.support:
            return (pid,)
        out: list[str] = []
        for parent in prop.support:
            out.extend(self.roots(parent))
        return tuple(dict.fromkeys(out))

    def snapshot(self) -> dict:
        return {
            "closed_world": self.closed_world,
            "live": len(self.live()),
            "contradictions": list(self.contradictions()),
            "lacunae": list(self.lacunae()),
        }


def chain_patterns(relation: str, hops: int, start: str = "?a") -> list[Pattern]:
    """`hops` links of `relation` end to end, as a conjunctive query.

    `chain_patterns("leads_to", 2)` is `?a->?v1`, `?v1->?z`. Used by the
    decomposition bank to ask what a candidate route would require.
    """
    if hops < 1:
        raise WorkspaceError("E-WS-005", "a chain needs at least one hop")
    nodes = [start] + [f"?v{i}" for i in range(1, hops)] + ["?z"]
    return [Pattern(nodes[i], relation, nodes[i + 1]) for i in range(hops)]
